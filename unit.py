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
        self.ud= unit_data

        self.base_level = unit_data.get("base_level", 1)
        self.level = max(self.base_level, self.level)
        self.faction:str = unit_data["faction"]
        self.type: str = unit_data["type"]
        self.is_eximus:bool = unit_data.get("is_eximus", False)
        self.procImmunities: np.array = np.array([1]*20, dtype=np.single)
        self.damage_controller_type = unit_data.get("damage_controller_type", "DC_NORMAL")
        self.critical_controller_type = unit_data.get("critical_controller_type", "CC_NORMAL")
        self.base_dr = unit_data.get("base_dr", 1)
        self.health_vulnerability = unit_data.get("health_vulnerability", 1)
        self.shield_vulnerability = unit_data.get("shield_vulnerability", 1)
        self.proc_info = const.PROC_INFO.copy()
        if 'proc_info' in unit_data:
            for k,v in unit_data['proc_info'].items():
                self.proc_info[k] = v

        self.health = Protection(self, unit_data["base_health"], "health", unit_data["health_type"])
        self.armor = Protection(self, unit_data["base_armor"], "armor", unit_data["armor_type"])
        self.shield = Protection(self, unit_data["base_shield"], "shield", unit_data["shield_type"])
        self.overguard = Protection(self, unit_data["base_overguard"], "overguard", "Overguard")

        self.proc_controller = ProcController(self)
        self.damage_controller = DamageController(self)

        if self.overguard.current_value > 0:
            self.proc_controller.cold_proc_manager.max_stacks = 4
            self.procImmunities[const.DT_INDEX['DT_RADIATION']] = 0

        self.bodypart_multipliers = dict(body=dict(multiplier=1,critical_damage_multiplier=1), head=dict(multiplier=3,critical_damage_multiplier=2))
        if 'bodypart_multipliers' in unit_data:
            self.bodypart_multipliers = unit_data['bodypart_multipliers']

        self.animation_multipliers = dict(normal=dict(multiplier=1,critical_damage_multiplier=1))
        if 'animation_multipliers' in unit_data:
            self.animation_multipliers = unit_data['animation_multipliers']

        self.unique_proc_count = 0
        self.unique_proc_delta = False
        self.armor_dr = np.array([1]*20, dtype=np.single)
        self.set_armor_dr()

        self.last_damage = 0
        self.last_t0_damage = 0


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

        if self.overguard.current_value > 0:
            self.proc_controller.cold_proc_manager.max_stacks = 4
            self.procImmunities[const.DT_INDEX['DT_RADIATION']] = 0
        
        self.unique_proc_count = 0
        self.unique_proc_delta = False
        self.armor_dr = np.array([1]*20, dtype=np.single)
        self.set_armor_dr()
    
    def set_armor_dr(self):
        current_armor = self.armor.current_value
        if int(current_armor) >= 1:
            np.reciprocal((self.armor.modifier*(-1)+2)*(current_armor * const.ARMOR_RATIO)+1, out=self.armor_dr)
            np.multiply(self.armor.modifier, self.armor_dr, out=self.armor_dr)
            self.armor_dr[const.DT_INDEX["DT_FINISHER"]] = 1
            self.armor_dr[const.DT_INDEX["DT_CINEMATIC"]] = 1
            self.armor_dr[const.DT_INDEX["DT_HEALTH_DRAIN"]] = 1
        else:
            self.armor_dr *= 0
            self.armor_dr += 1
            

    def pellet_hit(self, fire_mode:FireMode, bodypart='body', animation='normal'):
        # calculate conditional multiplier
        if fire_mode.unique_proc_count != self.unique_proc_count and fire_mode.condition_overloaded:
            fire_mode.unique_proc_count = self.unique_proc_count
            fire_mode.calc_modded_damage()

        cd = self.get_critical_multiplier(fire_mode, bodypart, animation)
        enemy_multiplier = self.apply_damage(fire_mode, fire_mode.damagePerShot.modded, critical_multiplier=cd, bodypart=bodypart, animation=animation)

        self.apply_status(fire_mode, fire_mode.totalDamage.modded * enemy_multiplier * self.damage_controller.unmodified_tiered_critical_multiplier)

    def apply_damage(self, fire_mode:FireMode, damage:np.array, critical_multiplier=1, bodypart='body', animation='normal'):
        multiplier = 1
        
        # body part bonuses
        multiplier *= (self.bodypart_multipliers[bodypart]['multiplier'] * self.animation_multipliers[animation]['multiplier'] )
        multiplier *= self.base_dr

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
    
    def remove_protection(self, fire_mode: FireMode, damage:np.array, critical_multiplier):
        overguard = self.overguard.current_value
        shield = self.shield.current_value
        health = self.health.current_value
        
        tot_damage = 0
        if self.overguard.current_value > 0:
            tot_damage = sum(damage * self.overguard.modifier * self.overguard.total_damage_multiplier)
            tot_damage = self.damage_controller.func(fire_mode, tot_damage, critical_multiplier) * critical_multiplier
            self.overguard.current_value -= tot_damage
            if self.overguard.current_value <= 0:
                self.proc_controller.cold_proc_manager.max_stacks = self.proc_info['PT_COLD']['max_stacks']
                self.procImmunities[const.DT_INDEX['DT_RADIATION']] = 1
        elif self.shield.current_value > 0: # TODO
            if damage[6] > 0:
                health_damage = damage[6] * self.armor_dr[6] * self.health.modifier[6] * self.health.total_damage_multiplier * self.health_vulnerability
                health_damage = self.damage_controller.func(fire_mode, health_damage, critical_multiplier) * critical_multiplier
                self.health.current_value -= health_damage
                tot_damage += health_damage

            shield_damage = sum(damage * self.shield.modifier * self.shield.total_damage_multiplier) * self.shield_vulnerability
            shield_damage = self.damage_controller.func(fire_mode, shield_damage, critical_multiplier) * critical_multiplier
            self.shield.current_value -= shield_damage
            tot_damage += shield_damage
        else:
            # tot_damage = sum(damage * self.armor_dr * self.health.modifier * self.health.total_damage_multiplier) * self.health_vulnerability
            # print(tot_damage* critical_multiplier)
            # tot_damage = self.damage_controller.func(fire_mode, tot_damage, critical_multiplier) * critical_multiplier
            # self.health.current_value -= tot_damage
            tot_damage = (damage * self.armor_dr * self.health.modifier * self.health.total_damage_multiplier) * self.health_vulnerability
            test = tot_damage* critical_multiplier 
            critical_multiplier = np.float32(critical_multiplier)
            print(sum(test), test.dtype, tot_damage.dtype, type(critical_multiplier), type(test))
            print(tot_damage)
            print(np.float32(sum(tot_damage)))
            tot_damage = np.float32(sum(tot_damage))
            
            tot_damage = self.damage_controller.func(fire_mode, tot_damage, critical_multiplier) * critical_multiplier
            print('her', type(tot_damage))
            self.health.current_value -= tot_damage

        self.last_damage = tot_damage
        # return applied damage
        return overguard - self.overguard.current_value, shield - self.shield.current_value, health - self.health.current_value
    
    def get_critical_multiplier(self, fire_mode:FireMode, bodypart:str, animation:str):
        puncture_count = self.proc_controller.puncture_proc_manager.count
        criticalChance_puncture = 0 if fire_mode.radial else puncture_count * 0.05
        critical_chance = fire_mode.criticalChance.modded + criticalChance_puncture
        critical_tier = int(critical_chance) + int(random() < critical_chance % 1)
        # self.damage_controller.critical_tier = critical_tier

        if critical_tier > 0:
            bodypart_crit_bonus = 1 if fire_mode.radial else self.bodypart_multipliers[bodypart]['critical_damage_multiplier']
            animation_crit_bonus = 1 if fire_mode.radial else self.animation_multipliers[animation]['critical_damage_multiplier']

            cold_count = self.proc_controller.cold_proc_manager.count
            criticalMultiplier_cold = 0 if fire_mode.radial else np.float32(min(1, cold_count) * 0.1 + max(0, cold_count-1) * 0.05)
            base_critical_multiplier = np.float32((fire_mode.criticalMultiplier.modded + criticalMultiplier_cold) * bodypart_crit_bonus * fire_mode.criticalMultiplier_m["final_multiplier"].value)
            effective_critical_multiplier = self.damage_controller.cc_func(base_critical_multiplier, critical_tier)
            print(type(effective_critical_multiplier))
            return effective_critical_multiplier
        else:
            effective_critical_multiplier = self.damage_controller.cc_func(fire_mode.criticalMultiplier.modded, critical_tier)
            return effective_critical_multiplier

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
    
    def get_current_stats(self):
        vals = {"time":self.simulation.time, "overguard":self.overguard.current_value, "shield":self.shield.current_value\
                     , "health":self.health.current_value, "armor":self.armor.current_value}

        return vals
    
    def get_stats(self):
        vals = {"overguard":self.overguard.max_value, "shield":self.shield.max_value\
                     , "health":self.health.max_value, "armor":self.armor.max_value}
        return vals
    
    def get_info(self):
        vals = {"enemy":self.name, "overguard":self.overguard.max_value, "shield":self.shield.max_value\
                     , "health":self.health.max_value, "armor":self.armor.max_value}
        return vals
    
    def get_last_crit_info(self):
        return f"Tier {self.damage_controller.critical_tier}, crit mult = {self.damage_controller.tiered_critical_multiplier:.3f}"
    
    def apply_corrosive_armor_strip(self, proc_manager:pm.DefaultProcManager):
        armor_strip = const.CORROSIVE_ARMOR_STRIP[proc_manager.count]
        self.armor.set_value_multiplier("Corrosive armor strip", armor_strip)

    def apply_viral_debuff(self, proc_manager:pm.DefaultProcManager):
        debuff = const.VIRAL_DEBUFF[proc_manager.count]
        self.health.debuffs["Viral debuff"] = debuff
        self.health.set_damage_multiplier("Viral debuff", debuff)

    def apply_magnetic_debuff(self, proc_manager:pm.DefaultProcManager):
        debuff = const.MAGNETIC_DEBUFF[proc_manager.count]
        self.shield.set_damage_multiplier("Magnetic debuff", debuff)

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
        self.value_multipliers: dict = {} # corrosive, heat armor strip
        self.damage_multipliers: dict = {} # viral / magnetic status
        self.total_damage_multiplier = 1

    def reset(self):
        self.modified_base = self.base
        self.max_value = self.base * self.level_multiplier * self.bonus 
        self.current_value = self.max_value
        self.value_multipliers = {}
        self.damage_multipliers = {}
        self.total_damage_multiplier = 1
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
    
    def set_value_multiplier(self, name, value):
        if self.current_value <= 0:
            self.value_multipliers[name] = value
            return
        old_affliction = math.prod([f for f in self.value_multipliers.values()])
        self.value_multipliers[name] = value
        new_affliction = math.prod([f for f in self.value_multipliers.values()])
        self.current_value = new_affliction * (self.current_value / old_affliction)
        
        if self.current_value <= 0.5:
            self.current_value = 0

        if self.type == 'armor':
            self.unit.set_armor_dr()

    def set_damage_multiplier(self, name, value):
        self.damage_multipliers[name] = value
        self.total_damage_multiplier = math.prod([f for f in self.damage_multipliers.values()])

class ProcController():
    def __init__(self, enemy: Unit) -> None:
        self.enemy = enemy
        self.impact_proc_manager = pm.DefaultProcManager(enemy, const.PT_INDEX['PT_IMPACT'])
        self.puncture_proc_manager = pm.DefaultProcManager(enemy, const.PT_INDEX['PT_PUNCTURE'])
        self.slash_proc_manager = pm.ContainerizedProcManager(enemy, const.PT_INDEX['PT_SLASH'])
        self.heat_proc_manager = pm.HeatProcManager(enemy, const.PT_INDEX['PT_HEAT'])
        self.cold_proc_manager = pm.DefaultProcManager(enemy, const.PT_INDEX['PT_COLD'])
        self.electric_proc_manager = pm.AOEProcManager(enemy, const.PT_INDEX['PT_ELECTRIC'])
        self.toxin_proc_manager = pm.ContainerizedProcManager(enemy, const.PT_INDEX['PT_TOXIN'])
        self.blast_proc_manager = pm.DefaultProcManager(enemy, const.PT_INDEX['PT_BLAST'])
        self.radiation_proc_manager = pm.DefaultProcManager(enemy, const.PT_INDEX['PT_RADIATION'])
        self.gas_proc_manager = pm.AOEProcManager(enemy, const.PT_INDEX['PT_GAS'])
        self.magnetic_proc_manager = pm.DefaultProcManager(enemy, const.PT_INDEX['PT_MAGNETIC'], count_change_callback=enemy.apply_magnetic_debuff)
        self.viral_proc_manager = pm.DefaultProcManager(enemy, const.PT_INDEX['PT_VIRAL'], count_change_callback=enemy.apply_viral_debuff)
        self.corrosive_proc_manager = pm.DefaultProcManager(enemy, const.PT_INDEX['PT_CORROSIVE'], count_change_callback=enemy.apply_corrosive_armor_strip)
        self.void_proc_manager = pm.DefaultProcManager(enemy, const.PT_INDEX['PT_RADIANT'])

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
        self.name_controller = {"DC_NORMAL":self.normal, "DC_STATIC_DPS_1":self.static_dps_1, "DC_STATIC_DPS_2":self.static_dps_2, "DC_DYNAMIC_DPS_1":self.dynamic_dps_1, "DC_DYNAMIC_DPS_2":self.dynamic_dps_2}
        self.name_crit_controller = {"CC_NORMAL":self.crit_controller_0, "CC_1":self.crit_controller_1}
        self.func = self.name_controller[enemy.damage_controller_type]
        self.cc_func = self.name_crit_controller[enemy.critical_controller_type]
        self.critical_multiplier = 1
        self.tiered_critical_multiplier = 1
        self.unmodified_tiered_critical_multiplier = 1
        self.critical_tier = 0
        

    def normal(self, fire_mode: FireMode, damage: float, *args):
        print('yo', type(damage))
        self.enemy.last_t0_damage = damage
        return damage

    def static_dps_1(self, fire_mode: FireMode, damage: float, critical_multiplier:float):
        tier_min = (1-1/max(1,self.critical_tier))
        dps_reducer = (tier_min/(self.critical_multiplier-tier_min) + 1)

        # Weird shotgun mechanic
        dps_multiplier = fire_mode.fireRate.modded * fire_mode.multishot.modded
        dps_multiplier = 1 if dps_multiplier==0 else dps_multiplier # lanka shenans
        dps_multiplier = dps_multiplier/2 if fire_mode.multishot.base > 1 else dps_multiplier
        dps_multiplier = dps_multiplier / dps_reducer
        tier0_dps = damage * dps_multiplier

        self.enemy.last_t0_damage = damage

        dr = 1
        if tier0_dps >= 1000 and tier0_dps <= 2500:
            dr = 0.8 + 200/tier0_dps
        elif tier0_dps >= 2500 and tier0_dps <= 5000:
            dr = 0.7 + 450/tier0_dps
        elif tier0_dps >= 5000 and tier0_dps <= 10000:
            dr = 0.4+1950/tier0_dps
        elif tier0_dps >= 10000 and tier0_dps <= 20000:
            dr = 0.2+3950/tier0_dps
        elif tier0_dps >= 20000:
            dr = 0.1+5950/tier0_dps
        return damage * dr
    
    def static_dps_2(self, fire_mode: FireMode, damage: float, critical_multiplier:float):
        tier_min = (1-1/max(1,self.critical_tier))
        dps_reducer = (tier_min/(self.critical_multiplier-tier_min) + 1)

        dps_multiplier = fire_mode.fireRate.modded * fire_mode.multishot.modded
        # Weird shotgun mechanic
        dps_multiplier = dps_multiplier/2 if fire_mode.multishot.base > 1 else dps_multiplier

        dps_multiplier = dps_multiplier / dps_reducer
        tier0_dps = damage * dps_multiplier 

        self.enemy.last_t0_damage = damage

        dr = 1
        if tier0_dps >= 3000 and tier0_dps <= 7500:
            dr = 0.8 + 600/tier0_dps
        elif tier0_dps >= 7500 and tier0_dps <= 22500:
            dr = 1.6/3 + 2600/tier0_dps
        elif tier0_dps >= 22500:
            dr = 14600/tier0_dps
        return damage * dr
    
    def dynamic_dps_1(self, fire_mode: FireMode, damage: float, critical_multiplier:float):
        ms_multiplier = fire_mode.multishot.modded
        dps_multiplier = ms_multiplier * fire_mode.fireRate.modded
        dps = damage * ms_multiplier * critical_multiplier
        self.enemy.last_t0_damage = damage

        correction_factor = 0
        # print(correction_factor)
        # correction_factor = 164

        cap = 460e3
        dr = 1/(1+(dps-correction_factor)/cap)
        return damage * dr
    
    def dynamic_dps_2(self, fire_mode: FireMode, damage: float, critical_multiplier:float):
        ms_multiplier = fire_mode.multishot.modded
        dps_multiplier = ms_multiplier * fire_mode.fireRate.modded
        dps = damage * ms_multiplier * critical_multiplier
        self.enemy.last_t0_damage = damage

        correction_factor = 0

        cap = 175e3
        dr = 1/(1+(dps-correction_factor)/cap)
        return damage * dr
    
    def crit_controller_0(self, critical_multiplier, critical_tier):
        self.critical_tier = critical_tier
        self.critical_multiplier = critical_multiplier

        ## scale critical multiplier to the tier
        if critical_tier == 0:
            self.tiered_critical_multiplier = 1
            return self.tiered_critical_multiplier
        
        self.tiered_critical_multiplier = (critical_multiplier-1)*critical_tier +1
        self.unmodified_tiered_critical_multiplier = self.tiered_critical_multiplier
        return self.tiered_critical_multiplier
    
    def crit_controller_1(self, critical_multiplier, critical_tier):
        self.critical_tier = critical_tier
        self.critical_multiplier = critical_multiplier

        if critical_tier == 0:
            self.tiered_critical_multiplier = 1
            return self.tiered_critical_multiplier

        tier_1 = (critical_multiplier-1)*0.5+1
        tier_increase = tier_1/(1+1/(critical_multiplier-1))

        self.tiered_critical_multiplier = tier_1 + (critical_tier-1) * tier_increase
        self.unmodified_tiered_critical_multiplier = (critical_multiplier-1)*critical_tier + 1
        return self.tiered_critical_multiplier 
