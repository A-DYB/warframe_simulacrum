from __future__ import annotations

import json
from random import random
import numpy as np
from pathlib import Path
import os
import math
import procs as pm

import constants
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

        self.health = Protection(self, unit_data["base_health"], "health", unit_data["health_type"])
        self.armor = Protection(self, unit_data["base_armor"], "armor", unit_data["armor_type"])
        self.shield = Protection(self, unit_data["base_shield"], "shield", unit_data["shield_type"])
        self.overguard = Protection(self, unit_data["base_overguard"], "overguard", "Overguard")

        self.proc_controller = ProcController(self)

        self.unique_proc_count = 0
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
            np.reciprocal((self.armor.modifier*(-1)+2)*(current_armor * constants.ARMOR_RATIO)+1, out=self.armor_dr)
            np.multiply(self.armor.modifier, self.armor_dr, out=self.armor_dr)
            self.armor_dr[14] = 1

    def pellet_hit(self, fire_mode:FireMode, enemy:"Unit"):
        # apply critical multiplier to the damage instance
        # TODO this has to be inside apply_damage to account for body part
        critical_tier = int(fire_mode.criticalChance.modded) + int(random() < fire_mode.criticalChance.modded % 1)
        effective_critical_multiplier = critical_tier * (fire_mode.criticalMultiplier.modded - 1) + 1

        #apply damage
        status_damage = self.apply_damage(fire_mode, fire_mode.damagePerShot.quantized.copy(), fire_mode.elementalDamagePerShot.quantized, fire_mode.damagePerShot.modded, effective_critical_multiplier, source="pellet")

        # apply status procs 
        self.apply_status(fire_mode, status_damage)

    def apply_damage(self, fire_mode:FireMode, damage:np.array, bonus_damage:np.array, base_damage: np.array, critical_multiplier=1, body_part=None, source="None"):
        # copy the arrays
        damage_total = (damage + bonus_damage).copy()
        damage_status = base_damage.copy()
        
        # body part bonuses
        damage_total *= 1
        damage_status *= 1

        # # faction bonuses
        faction_bonus = (1 + fire_mode.factionDamage_m["base"])
        damage_total *= faction_bonus
        damage_status *= faction_bonus

        # # apply crit
        damage_total *= critical_multiplier
        damage_status *= critical_multiplier

        # print(sum(damage_total), sum(damage_status))

        og, sg, hg = self.remove_protection(damage_total)

        # print(f"Damage at {self.simulation.time:.2f}s: {([f'{og:.1f}', f'{sg:.1f}', f'{hg:.1f}'])}, source:{source}")

        if self.health.current_value <= 0 and self.overguard.current_value <= 0:
            return damage_status
        
        if self.overguard.current_value < 0:
            ratio = abs(self.overguard.current_value/og)
            self.overguard.current_value = 0
            og, sg, hg = self.remove_protection(damage_total * ratio)

            if self.shield.current_value < 0:
                ratio = abs(self.shield.current_value/sg)
                self.shield.current_value = 0
                self.remove_protection(damage_total * ratio) 

        elif self.shield.current_value < 0:
            ratio = abs(self.shield.current_value/sg)
            self.shield.current_value = 0
            self.remove_protection(damage_total * ratio)
        
        return damage_status

    def apply_status(self, fire_mode:FireMode, status_damage: np.array):
        status_tier = int(fire_mode.procChance.modded) + int(random() < fire_mode.procChance.modded % 1)

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

    def remove_protection(self, damage:np.array):
        overguard = self.overguard.current_value
        shield = self.shield.current_value
        health = self.health.current_value
        if self.overguard.current_value > 0:
            self.overguard.current_value -= sum(damage * self.overguard.modifier * self.overguard.total_debuff)
        elif self.shield.current_value > 0:
            self.health.current_value -= damage[6] * self.armor_dr[6] * self.health.modifier[6] * self.health.total_debuff
            self.shield.current_value -= sum(damage * self.shield.modifier * self.shield.total_debuff)
        else:
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
        armor_strip = constants.CORROSIVE_ARMOR_STRIP[proc_manager.count]
        self.armor.apply_affliction("Corrosive armor strip", armor_strip)

    def apply_viral_debuff(self, proc_manager:pm.DefaultProcManager):
        debuff = constants.VIRAL_DEBUFF[proc_manager.count]
        self.health.debuffs["Viral debuff"] = debuff
        self.health.apply_debuff("Viral debuff", debuff)

    def apply_magnetic_debuff(self, proc_manager:pm.DefaultProcManager):
        debuff = constants.MAGNETIC_DEBUFF[proc_manager.count]
        self.shield.apply_debuff("Magnetic debuff", debuff)


class Protection:
    def __init__(self, unit: Unit, base: int, type: str, type_variant: str) -> None:
        self.unit = unit

        self.base = base
        self.modified_base = self.base

        self.type = type
        self.type_variant = type_variant
        self.modifier = constants.modifiers[self.type_variant]
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
        scale_factor_list = constants.protection_scale_factors[self.type]
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

    def add_proc(self, proc_index:int, fire_mode:FireMode, status_damage: np.array):
        self.proc_managers[proc_index].add_proc(fire_mode, status_damage)

    def reset(self):
        for pm in self.proc_managers:
            pm.reset()