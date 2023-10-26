from __future__ import annotations

import json
from random import random
import numpy as np
from pathlib import Path
import os
import math
import procs as pm

import constants as const
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from simulation import Simulacrum
    from weapon import FireMode

class Unit:
    def __init__(self, name: str, level: int, simulation:Simulacrum):
        self.name = name
        self.level = level
        self.simulation = simulation

        unit_data = self.get_unit_data()

        self.base_level = unit_data.get("base_level", 1)
        self.level = max(self.base_level, self.level)
        self.faction:str = unit_data["faction"]
        self.type: str = unit_data["type"]
        self.is_eximus:bool = unit_data.get("is_eximus", False)
        self.procImmunities: np.array = np.array([1]*20, dtype=float)
        self.damage_controller_type = unit_data.get("damage_controller_type", "normal")

        self.health = Protection(self, unit_data["base_health"], "health", unit_data["health_type"])
        self.armor = Protection(self, unit_data["base_armor"], "armor", unit_data["armor_type"])
        self.shield = Protection(self, unit_data["base_shield"], "shield", unit_data["shield_type"])
        self.overguard = Protection(self, unit_data["base_overguard"], "overguard", "Overguard")

        self.proc_controller = ProcController(self)
        self.damage_controller = DamageController(self)

        self.bodypart_multipliers = dict(body=dict(multiplier=1,critical_damage_multiplier=1), head=dict(multiplier=3,critical_damage_multiplier=2))

        self.unique_proc_count = 0
        self.unique_proc_delta = False
        self.armor_dr = np.array([1]*20, dtype=float)
        self.set_armor_dr()


    def get_unit_data(self) -> dict:
        with open(os.path.join(Path(__file__).parent.resolve(),"data", "unit_data.json")) as f:
            data = json.load(f)
        return data[self.name]
    
    def reset(self):
        self.health.reset()
        self.armor.reset()
        self.shield.reset()
        self.overguard.reset()
        self.proc_controller.reset()
    
    def set_armor_dr(self):
        current_armor = self.armor.current_value
        if int(current_armor) >= 1:
            np.reciprocal((self.armor.modifier*(-1)+2)*(current_armor * const.ARMOR_RATIO)+1, out=self.armor_dr)
            np.multiply(self.armor.modifier, self.armor_dr, out=self.armor_dr)
            self.armor_dr[const.DT_INDEX["DT_FINISHER"]] = 1
            self.armor_dr[const.DT_INDEX["DT_CINEMATIC"]] = 1
            self.armor_dr[const.DT_INDEX["DT_HEALTH_DRAIN"]] = 1
            

    def pellet_hit(self, fire_mode:FireMode, bodypart='body'):
        # calculate conditional multiplier
        if fire_mode.unique_proc_count != self.unique_proc_count and fire_mode.condition_overloaded:
            fire_mode.unique_proc_count = self.unique_proc_count
            fire_mode.calc_modded_damage()

        cd = self.get_critical_multiplier(fire_mode, bodypart)
        enemy_multiplier = self.apply_damage(fire_mode, fire_mode.damagePerShot.modded, critical_multiplier=cd)

        self.apply_status(fire_mode, fire_mode.totalDamage.modded * enemy_multiplier)

    def apply_damage(self, fire_mode:FireMode, damage:np.array, critical_multiplier=1, bodypart='body'):
        multiplier = 1
        
        # body part bonuses
        multiplier *= self.bodypart_multipliers[bodypart]['multiplier']

        # # faction bonuses
        faction_bonus = (1 + fire_mode.factionDamage_m["base"].value)
        multiplier *= faction_bonus

        og, sg, hg = self.remove_protection(fire_mode, damage * multiplier, critical_multiplier)

        if self.health.current_value <= 0 and self.overguard.current_value <= 0:
            return multiplier
        
        if self.overguard.current_value < 0:
            ratio = abs(self.overguard.current_value/og)
            self.overguard.current_value = 0
            og, sg, hg = self.remove_protection(fire_mode, damage * multiplier * ratio, 1)

            if self.shield.current_value < 0:
                ratio = abs(self.shield.current_value/sg)
                self.shield.current_value = 0
                self.remove_protection(fire_mode, damage * multiplier * ratio, 1) 

        elif self.shield.current_value < 0:
            ratio = abs(self.shield.current_value/sg)
            self.shield.current_value = 0
            self.remove_protection(fire_mode, damage * multiplier * ratio, 1)
        
        return multiplier
    
    def get_critical_multiplier(self, fire_mode:FireMode, bodypart:str):
        puncture_count = self.proc_controller.puncture_proc_manager.count
        criticalChance_puncture = 0 if fire_mode.radial else puncture_count * 0.05
        critical_chance = fire_mode.criticalChance.modded + criticalChance_puncture
        critical_tier = int(critical_chance) + int(random() < critical_chance % 1)

        if critical_tier > 0:
            bodypart_crit_bonus = 1 if fire_mode.radial else self.bodypart_multipliers[bodypart]['critical_damage_multiplier']

            cold_count = self.proc_controller.cold_proc_manager.count
            criticalMultiplier_cold = 0 if fire_mode.radial else min(1, cold_count) * 0.1 + max(0, cold_count-1) * 0.05
            base_critical_multiplier = (fire_mode.criticalMultiplier.modded + criticalMultiplier_cold) * bodypart_crit_bonus * fire_mode.criticalMultiplier_m["final_multiplier"].value

            
            effective_critical_multiplier = critical_tier * (base_critical_multiplier - 1) + 1
            return effective_critical_multiplier
        return 1

    def apply_status(self, fire_mode:FireMode, status_damage: float):
        total_status_chance = fire_mode.procChance.modded * fire_mode.procChance_m['multishot_multiplier'].value
        status_tier = int(total_status_chance) + int(random() < (total_status_chance) % 1)

        for _ in range(status_tier):
            roll = random()
            for i, effect_chance in enumerate(fire_mode.procProbabilities):
                if roll < effect_chance:
                    self.proc_controller.add_proc(i, fire_mode, status_damage)
                    break
                else:
                    roll -= effect_chance

        for proc_index in fire_mode.forcedProc:
            self.proc_controller.add_proc(proc_index, fire_mode, status_damage)

    def remove_protection(self, fire_mode: FireMode, damage:np.array, critical_multiplier):
        overguard = self.overguard.current_value
        shield = self.shield.current_value
        health = self.health.current_value
        if self.overguard.current_value > 0:
            tot_damage = sum(damage * self.overguard.modifier * self.overguard.total_debuff)
            tot_damage = self.damage_controller.func(fire_mode, tot_damage) * critical_multiplier
            self.overguard.current_value -= tot_damage
        elif self.shield.current_value > 0: # TODO
            self.health.current_value -= damage[6] * self.armor_dr[6] * self.health.modifier[6] * self.health.total_debuff
            self.shield.current_value -= sum(damage * self.shield.modifier * self.shield.total_debuff)
        else:
            tot_damage = sum(damage * self.armor_dr * self.health.modifier * self.health.total_debuff)
            tot_damage = self.damage_controller.func(fire_mode, tot_damage) * critical_multiplier
            self.health.current_value -= sum(damage * self.armor_dr * self.health.modifier * self.health.total_debuff)
        
        # return applied damage
        return overguard - self.overguard.current_value, shield - self.shield.current_value, health - self.health.current_value
    
    def get_current_stats(self):
        vals = {"time":self.simulation.time, "overguard":self.overguard.current_value, "shield":self.shield.current_value\
                     , "health":self.health.current_value, "armor":self.armor.current_value}

        return vals
    
    def get_stats(self):
        vals = {"overguard":self.overguard.max_value, "shield":self.shield.max_value\
                     , "health":self.health.max_value, "armor":self.armor.max_value}
        return vals
    
    def apply_corrosive_armor_strip(self, proc_manager:pm.DefaultProcManager):
        armor_strip = const.CORROSIVE_ARMOR_STRIP[proc_manager.count]
        self.armor.apply_affliction("Corrosive armor strip", armor_strip)

    def apply_viral_debuff(self, proc_manager:pm.DefaultProcManager):
        debuff = const.VIRAL_DEBUFF[proc_manager.count]
        self.health.debuffs["Viral debuff"] = debuff
        self.health.apply_debuff("Viral debuff", debuff)

    def apply_magnetic_debuff(self, proc_manager:pm.DefaultProcManager):
        debuff = const.MAGNETIC_DEBUFF[proc_manager.count]
        self.shield.apply_debuff("Magnetic debuff", debuff)

class Protection:
    def __init__(self, unit: Unit, base: int, type: str, type_variant: str) -> None:
        self.unit = unit

        self.base = base
        self.modified_base = self.base

        self.type = type
        self.type_variant = type_variant
        self.modifier = const.modifiers[self.type_variant]
        self.level_multiplier = self.get_level_multiplier()

        self.max_value = self.base * self.level_multiplier
        self.current_value = self.max_value

        self.bonus = 1
        self.afflictions: dict = {} # corrosive, heat armor strip
        self.debuffs: dict = {} # viral / magnetic status
        self.total_debuff = 1

    def reset(self):
        self.modified_base = self.base
        self.max_value = self.base * self.level_multiplier * self.bonus 
        self.current_value = self.max_value
        self.afflictions = {}
        self.debuffs = {}
        self.total_debuff = 1
        if self.type == 'armor':
            self.unit.set_armor_dr()

    # ex. shattering impact, mag's 3
    def remove_base_value(self, value):
        pct = self.current_value/self.max_value
        self.modified_base -= value
        self.max_value = self.modified_base * self.level_multiplier * self.bonus 
        self.current_value = self.max_value * pct
        if self.type == 'armor':
            self.unit.set_armor_dr()

    def get_level_multiplier(self):
        scale_factor_list = const.protection_scale_factors[self.type]
        selected_factors = None
        for scale_factor in scale_factor_list:
            if scale_factor["is_eximus"] != self.unit.is_eximus:
                continue
            if self.unit.level < scale_factor["level_start"] or self.unit.level > scale_factor["level_stop"]:
                continue
            selected_factors = scale_factor
            break
        if selected_factors is None:
            raise Exception("Cannot find valid Protection scale factors")
        
        f_low = selected_factors["f_low"]
        f_hi = selected_factors["f_hi"]
        f_bonus = selected_factors["f_bonus"]

        smoothstep_start = selected_factors["smoothstep_start"]
        smoothstep_stop = selected_factors["smoothstep_stop"]

        lvl_lo = selected_factors["level_start"]
        lvl_hi = selected_factors["level_stop"]

        f1 = f_low[0] + f_low[1]*(self.unit.level - self.unit.base_level)**f_low[2]
        f2 = f_hi[0] + f_hi[1]*(self.unit.level - self.unit.base_level)**f_hi[2]
        t = (self.unit.level-self.unit.base_level-smoothstep_start)/(smoothstep_stop - smoothstep_start)
        t = max(0, min(1,t))
        s = 3*t**2-2*t**3

        bonus = f_bonus[0] + f_bonus[1]*(self.unit.level - lvl_lo)
        
        return (f1*(1-s)+f2*s) * bonus
    
    def apply_affliction(self, name, value):
        if self.current_value <= 0:
            self.afflictions[name] = value
            return
        old_affliction = math.prod([f for f in self.afflictions.values()])
        self.afflictions[name] = value
        new_affliction = math.prod([f for f in self.afflictions.values()])
        self.current_value = new_affliction * (self.current_value / old_affliction)
        
        if self.current_value <= 0.5:
            self.current_value = 0

        if self.type == 'armor':
            self.unit.set_armor_dr()

    def apply_debuff(self, name, value):
        self.debuffs[name] = value
        self.total_debuff = math.prod([f for f in self.debuffs.values()])

class ProcController():
    def __init__(self, enemy: Unit) -> None:
        self.enemy = enemy
        self.impact_proc_manager = pm.DefaultProcManager(enemy, 0)
        self.puncture_proc_manager = pm.DefaultProcManager(enemy, 1)
        self.slash_proc_manager = pm.ContainerizedProcManager(enemy, 2)
        self.heat_proc_manager = pm.HeatProcManager(enemy, 3)
        self.cold_proc_manager = pm.DefaultProcManager(enemy, 4)
        self.electric_proc_manager = pm.AOEProcManager(enemy, 5)
        self.toxin_proc_manager = pm.ContainerizedProcManager(enemy, 6)
        self.blast_proc_manager = pm.DefaultProcManager(enemy, 7)
        self.radiation_proc_manager = pm.DefaultProcManager(enemy, 8)
        self.gas_proc_manager = pm.AOEProcManager(enemy, 9)
        self.magnetic_proc_manager = pm.DefaultProcManager(enemy, 10, count_change_callback=enemy.apply_magnetic_debuff)
        self.viral_proc_manager = pm.DefaultProcManager(enemy, 11, count_change_callback=enemy.apply_viral_debuff)
        self.corrosive_proc_manager = pm.DefaultProcManager(enemy, 12, count_change_callback=enemy.apply_corrosive_armor_strip)
        self.void_proc_manager = pm.DefaultProcManager(enemy, 13)

        self.proc_managers: List[pm.DefaultProcManager] = [self.impact_proc_manager, self.puncture_proc_manager, self.slash_proc_manager,
                                self.heat_proc_manager, self.cold_proc_manager, self.electric_proc_manager,
                                self.toxin_proc_manager, self.blast_proc_manager, self.radiation_proc_manager,
                                self.gas_proc_manager, self.magnetic_proc_manager, self.viral_proc_manager,
                                self.corrosive_proc_manager, self.void_proc_manager]

    def add_proc(self, proc_index:int, fire_mode:FireMode, status_damage: float):
        self.proc_managers[proc_index].add_proc(fire_mode, status_damage)

    def reset(self):
        for pm in self.proc_managers:
            pm.reset()

class DamageController():
    def __init__(self, enemy: Unit) -> None:
        self.enemy = enemy
        self.name_controller = {"normal":self.normal, "static_dps":self.static_dps}
        self.func = self.name_controller[enemy.damage_controller_type]

    def normal(self, fire_mode: FireMode, damage: float):
        return damage

    def static_dps(self, fire_mode: FireMode, damage: float):
        # Weird shotgun mechanic
        dps_multiplier = fire_mode.fireRate.modded * fire_mode.multishot.modded
        dps_multiplier = dps_multiplier/2 if fire_mode.multishot.base > 1 else dps_multiplier
        tier0_dps = damage * dps_multiplier

        if tier0_dps <= 1000:
            return damage
        elif tier0_dps >= 1000 and tier0_dps <= 2500:
            return ((0.8*tier0_dps+200))/dps_multiplier
        elif tier0_dps >= 2500 and tier0_dps <= 5000:
            return ((0.7*tier0_dps+450))/dps_multiplier
        elif tier0_dps >= 5000 and tier0_dps <= 10000:
            return ((0.4*tier0_dps+1950))/dps_multiplier
        elif tier0_dps >= 10000 and tier0_dps <= 20000:
            return ((0.2*tier0_dps+3950))/dps_multiplier
        elif tier0_dps >= 20000:
            return ((0.1*tier0_dps+5950))/dps_multiplier
