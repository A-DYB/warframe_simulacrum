from __future__ import annotations

import json
from random import random, randint
import numpy as np
from pathlib import Path
import os
import math
import copy
import collections.abc
import warframe_simulacrum.procs as pm

import warframe_simulacrum.constants as const
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from warframe_simulacrum.simulation import Simulacrum
    from warframe_simulacrum.weapon import FireMode

class Unit:
    def __init__(self, name: str, level: int, simulation:Simulacrum, protection_scaling=const.NEW_PROTECTION_SCALING):
        self.name = name
        self.level = level
        self.protection_scaling = protection_scaling
        self.simulation = simulation

        self.update_data()

        self.proc_controller = ProcController(self)
        self.damage_controller = DamageController(self)

        if self.overguard.current_value > 0:
            self.proc_controller.cold_proc_manager.max_stacks = 4
            self.procImmunities[const.DT_INDEX['DT_RADIATION']] = 0

        # state
        self.current_animation = 'normal'
        self.unique_proc_count = 0
        self.unique_proc_delta = False
        self.armor_dr = np.array([1]*20, dtype=np.single)
        self.set_armor_dr()

        self.last_damage = 0
        self.last_t0_damage = 0

    def update_data(self):
        data = self.get_unit_data()
        default_data = copy.deepcopy(const.DEFAULT_ENEMY_CONFIG)
        unit_data = update(default_data, data)

        self.base_level = unit_data.get("base_level", 1)
        self.level = max(self.base_level, self.level)
        self.faction:str = unit_data["faction"]
        self.is_eximus:bool = unit_data.get("is_eximus", False)
        self.procImmunities: np.array = np.array([1]*20, dtype=np.single)
        self.damage_controller_type = unit_data.get("damage_controller_type", "DC_NORMAL")
        self.critical_controller_type = unit_data.get("critical_controller_type", "CC_NORMAL")
        self.base_dr = <float>unit_data.get("base_dr", 1)
        self.health_vulnerability = <float>unit_data.get("health_vulnerability", 1)
        self.shield_vulnerability = <float>unit_data.get("shield_vulnerability", 1)
        self.proc_info = copy.deepcopy(const.PROC_INFO)
        if 'proc_info' in unit_data:
            self.proc_info = update(self.proc_info, unit_data['proc_info'])

        self.health = Protection(self, unit_data["base_health"], "health", unit_data["health_type"])
        self.armor = Protection(self, unit_data["base_armor"], "armor", unit_data["armor_type"])
        self.shield = Protection(self, unit_data["base_shield"], "shield", unit_data["shield_type"])
        self.overguard = Protection(self, unit_data["base_overguard"], "overguard", "Overguard")

        self.bodypart_multipliers = dict(body=dict(multiplier=1,critical_damage_multiplier=1), head=dict(multiplier=3,critical_damage_multiplier=2))
        if 'bodypart_multipliers' in unit_data:
            self.bodypart_multipliers = unit_data['bodypart_multipliers']

        self.animation_multipliers = dict(normal=dict(multiplier=1,critical_damage_multiplier=1))
        if 'animation_multipliers' in unit_data:
            self.animation_multipliers = unit_data['animation_multipliers']

    def get_preview_info(self):
        info = [
            ("Enemy", self.name.capitalize(), ''),
            ("Level", f'{self.base_level:.0f} -> {self.level:.0f}', ''),
            ("Faction", self.faction.capitalize(), ''),
        ]
        info1 = []
        if self.damage_controller_type != 'DC_NORMAL': info1.append(("Damage Controller", self.damage_controller_type, '')) 
        if self.critical_controller_type != 'CC_NORMAL': info1.append(("Critical Controller", self.critical_controller_type, ''))
        if len(info1)>0: 
            info.append(("Category", "", '')) 
            info += info1

        info2 = []
        if self.base_dr != 1: info2.append(("Base DR", f'{self.base_dr*100:.1f}%', '')) 
        if self.health_vulnerability != 1: info2.append(("Health Vulnerabiltiy", f'{self.health_vulnerability:.2f}x', '')) 
        if self.shield_vulnerability != 1: info2.append(("Shield Vulnerabiltiy", f'{self.shield_vulnerability:.2f}x', '')) 
        if len(info2)>0: 
            info.append(("Category", "", '')) 
            info += info2

        info.append(("Category", "", '')) 
        if self.overguard.current_value > 0: info.append(("Overguard", f'{self.overguard.base:.1f} -> {self.overguard.current_value:.1f}', '')) 
        if self.shield.current_value > 0: info.append(("Shield", f'{self.shield.base:.1f} -> {self.shield.current_value:.1f}', self.shield.protection_type_variant)) 
        if self.health.current_value > 0: info.append(("Health", f'{self.health.base:.1f} -> {self.health.current_value:.1f}', self.health.protection_type_variant)) 
        if self.armor.current_value > 0: info.append(("Armor", f'{self.armor.base:.1f} -> {self.armor.current_value:.0f}', self.armor.protection_type_variant)) 

        return info

    def get_unit_data(self) -> dict:
        with open(os.path.join(Path(__file__).parent.resolve(),"data", "unit_data.json")) as f:
            data = json.load(f)
        return data.get(self.name, {})
    
    def reset(self):
        self.health.reset()
        self.armor.reset()
        self.shield.reset()
        self.overguard.reset()
        self.proc_controller.reset()

        if self.overguard.current_value > 0:
            self.proc_controller.cold_proc_manager.max_stacks = 4
            self.procImmunities[const.DT_INDEX['DT_RADIATION']] = 0
        
        self.current_animation = 'normal'
        self.unique_proc_count = 0
        self.unique_proc_delta = False
        self.armor_dr = np.array([1]*20, dtype=np.single)
        self.set_armor_dr()

        self.last_damage = 0
        self.last_t0_damage = 0
    
    def set_armor_dr(self):
        cdef int current_armor = self.armor.current_value

        if current_armor >= 1:
            np.reciprocal((self.armor.modifier*(<float>-1) + <float>2)*(current_armor * const.ARMOR_RATIO)+1, out=self.armor_dr)
            np.multiply(self.armor.modifier, self.armor_dr, out=self.armor_dr)
            self.armor_dr[const.DT_INDEX["DT_FINISHER"]] = <float>1
            self.armor_dr[const.DT_INDEX["DT_CINEMATIC"]] = <float>1
            self.armor_dr[const.DT_INDEX["DT_HEALTH_DRAIN"]] = <float>1
        else:
            self.armor_dr *= <float>0
            self.armor_dr += <float>1
            

    def pellet_hit(self, fire_mode:FireMode, bodypart='body'):
        cdef float multiplier = 1
        # calculate conditional multiplier
        if fire_mode.unique_proc_count != self.unique_proc_count and fire_mode.condition_overloaded:
            fire_mode.unique_proc_count = self.unique_proc_count
            fire_mode.calc_modded_damage()

        if fire_mode.weapon.special_m['devouring_attrition'] > 0 :
            if self.damage_controller.critical_tier==0 and random() > 0.5:
                multiplier *= 21

        cdef float cd = self.get_critical_multiplier(fire_mode, bodypart) 
        enemy_multiplier = self.apply_damage(fire_mode, fire_mode.damagePerShot.modded * multiplier, critical_multiplier=cd, bodypart=bodypart)

        cdef float status_damage_base = fire_mode.totalDamage.modded * enemy_multiplier * self.damage_controller.unmodified_tiered_critical_multiplier
        self.apply_status(fire_mode, status_damage_base, bodypart)

    def apply_damage(self, fire_mode:FireMode, damage:np.array, critical_multiplier=1, bodypart='body', damage_tag=None):
        cdef float multiplier = 1
        cdef float bodypart_multiplier = <float>self.bodypart_multipliers.get(bodypart, {}).get('multiplier', 1)
        if damage_tag == 'radial' and bodypart == 'head':
            bodypart_multiplier = 1
        cdef float bodypart_bonus = 1
        if bodypart == 'head':
            bodypart_bonus = (1 + <float>fire_mode.weapon.damagePerShot_m["headshot_base"])
        
        # body part bonuses
        multiplier *= (bodypart_multiplier * bodypart_bonus * <float>self.animation_multipliers[self.current_animation]['multiplier'] )
        multiplier *= self.base_dr
        multiplier *= (<float>fire_mode.weapon.damagePerShot_m["multishot_multiplier"] * (1 + fire_mode.multishot_damage))

        # # faction bonuses
        cdef float faction_bonus = (1 + <float>fire_mode.weapon.factionDamage_m["base"])
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
        cdef float dr = 1
        cdef float applied_damage = 0
        cdef float accumulated_applied_damage = 0

        if self.overguard.current_value > 0:
            tot_damage = damage * self.overguard.modifier * self.overguard.total_damage_multiplier
            dr = self.damage_controller.func(fire_mode, tot_damage, critical_multiplier) 
            applied_damage = np.sum(tot_damage * dr * critical_multiplier)
            self.overguard.current_value -= applied_damage
            if self.overguard.current_value <= 0:
                self.proc_controller.cold_proc_manager.max_stacks = self.proc_info['PT_COLD']['max_stacks']
                self.procImmunities[const.DT_INDEX['DT_RADIATION']] = 1
            accumulated_applied_damage += applied_damage
        elif self.shield.current_value > 0: # TODO
            if damage[6] > 0:
                health_damage = damage[6] * self.armor_dr[6] * self.health.modifier[6] * self.health.total_damage_multiplier * self.health_vulnerability
                dr = self.damage_controller.func(fire_mode, health_damage, critical_multiplier) * critical_multiplier
                applied_damage = health_damage * dr * critical_multiplier
                self.health.current_value -= applied_damage
                accumulated_applied_damage += applied_damage

            shield_damage = damage * self.shield.modifier * self.shield.total_damage_multiplier * self.shield_vulnerability
            dr = self.damage_controller.func(fire_mode, shield_damage, critical_multiplier) 
            applied_damage = np.sum(shield_damage * dr * critical_multiplier)
            self.shield.current_value -= applied_damage
            accumulated_applied_damage += applied_damage
        else:
            health_damage = damage * self.armor_dr * self.health.modifier * self.health.total_damage_multiplier * self.health_vulnerability
            dr = self.damage_controller.func(fire_mode, health_damage, critical_multiplier)
            applied_damage = np.sum(health_damage * dr * critical_multiplier) 
            accumulated_applied_damage += applied_damage
            self.health.current_value -= applied_damage

        self.last_damage = accumulated_applied_damage
        # return applied damage
        return overguard - self.overguard.current_value, shield - self.shield.current_value, health - self.health.current_value
    
    def get_critical_multiplier(self, fire_mode:FireMode, bodypart:str):
        cdef float bodypart_crit_bonus = <float>1
        cdef float animation_crit_bonus = <float>1
        cdef float criticalMultiplier_cold = <float>0
        cdef float base_critical_multiplier = <float>1
        cdef float effective_critical_multiplier = <float>1
        
        puncture_count = self.proc_controller.puncture_proc_manager.count
        criticalChance_puncture = 0 if fire_mode.radial else puncture_count * 0.05
        critical_chance = fire_mode.criticalChance.modded + criticalChance_puncture
        critical_tier = int(critical_chance) + int(random() < critical_chance % 1)
        # self.damage_controller.critical_tier = critical_tier

        if critical_tier > 0:
            bodypart_crit_bonus = <float>1 if fire_mode.radial else self.bodypart_multipliers.get(bodypart, {}).get('critical_damage_multiplier', 1)
            animation_crit_bonus = <float>1 if fire_mode.radial else self.animation_multipliers.get(self.current_animation, {}).get('critical_damage_multiplier', 1)

            cold_count = self.proc_controller.cold_proc_manager.count
            criticalMultiplier_cold = 0 if fire_mode.radial else <float>min(1, cold_count) * <float>0.1 + <float>max(0, cold_count-1) * <float>0.05
            base_critical_multiplier = (fire_mode.criticalMultiplier.modded + criticalMultiplier_cold) * bodypart_crit_bonus * <float>fire_mode.weapon.criticalMultiplier_m["final_multiplier"]
            effective_critical_multiplier = self.damage_controller.cc_func(base_critical_multiplier, critical_tier)
            return effective_critical_multiplier
        else:
            effective_critical_multiplier = self.damage_controller.cc_func(fire_mode.criticalMultiplier.modded, critical_tier)
            return effective_critical_multiplier

    def apply_status(self, fire_mode:FireMode, status_damage: float, bodypart:str):
        total_status_chance = fire_mode.procChance.modded * fire_mode.weapon.procChance_m['multishot_multiplier']
        status_tier = int(total_status_chance) + int(random() < (total_status_chance) % 1)
        status_procced = 0

        for _ in range(status_tier):
            roll = random()
            for i, effect_chance in enumerate(fire_mode.procProbabilities):
                if roll < effect_chance:
                    self.proc_controller.add_proc(i, fire_mode, status_damage, bodypart)
                    status_procced += 1
                    break
                else:
                    roll -= effect_chance
        
        for proc_index in fire_mode.forcedProc:
            self.proc_controller.add_proc(proc_index, fire_mode, status_damage, bodypart)
            status_procced += 1

        encumber_chance = fire_mode.weapon.special_m['encumber']
        if status_procced>0 and fire_mode.weapon.last_encumber_time != self.simulation.time and encumber_chance > 0:
            encumber_tier = int(encumber_chance) + int(random() < (encumber_chance) % 1)
            for _ in range(encumber_tier):
                self.proc_controller.add_proc(randint(3, 12), fire_mode, 1, bodypart)
                fire_mode.weapon.last_encumber_time = self.simulation.time
    
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
        return f"Crit Tier {self.damage_controller.critical_tier}, Crit Mult = {self.damage_controller.tiered_critical_multiplier:.3f}"
    
    def apply_corrosive_armor_strip(self, proc_manager:pm.DefaultProcManager):
        armor_strip = const.CORROSIVE_ARMOR_STRIP[proc_manager.count]
        self.armor.set_value_multiplier("Corrosive armor strip", armor_strip)

    def apply_viral_debuff(self, proc_manager:pm.DefaultProcManager):
        debuff = const.VIRAL_DEBUFF[proc_manager.count]
        self.health.set_damage_multiplier("Viral debuff", debuff)

    def apply_magnetic_debuff(self, proc_manager:pm.DefaultProcManager):
        debuff = const.MAGNETIC_DEBUFF[proc_manager.count]
        self.shield.set_damage_multiplier("Magnetic debuff", debuff)

class Protection:
    def __init__(self, unit: Unit, base, protection_type: str, protection_type_variant: str) -> None:
        self.unit = unit

        self.base = <float>base
        self.modified_base = self.base

        self.protection_type = protection_type
        self.protection_type_variant = protection_type_variant
        self.modifier = const.modifiers[self.protection_type_variant]
        self.level_multiplier = self.get_level_multiplier()

        self.max_value =(self.base * self.level_multiplier)
        self.current_value = self.max_value

        self.bonus = <float>1
        self.mission_multipliers: dict = {} # corrosive, heat armor strip
        self.value_multipliers: dict = {} # corrosive, heat armor strip
        self.damage_multipliers: dict = {} # viral / magnetic status
        self.total_damage_multiplier = <float>1

    def reset(self):
        self.modified_base = self.base
        self.max_value = (self.base * self.level_multiplier * self.bonus)
        self.current_value = self.max_value * math.prod([<float>f for f in self.mission_multipliers.values()])
        self.value_multipliers = {}
        self.damage_multipliers = {}
        self.total_damage_multiplier = <float>1
        if self.protection_type == 'armor':
            self.unit.set_armor_dr()

    # ex. shattering impact, mag's 3
    def remove_base_value(self, value):
        pct = self.current_value/self.max_value
        self.modified_base -= value
        self.max_value = self.modified_base * self.level_multiplier * self.bonus 
        self.current_value = (self.max_value * pct)
        self.max_value = self.max_value
        if self.protection_type == 'armor':
            self.unit.set_armor_dr()

    def get_level_multiplier(self):
        cdef float old_multiplier = 1
        scale_factor_list = const.protection_scale_factors[self.protection_type]
        if self.unit.protection_scaling == const.OLD_PROTECTION_SCALING and "f_old" in scale_factor_list[0]:
            selected_factors = scale_factor_list[0]
            f_old = selected_factors["f_old"]
            old_multiplier = <float>f_old[0] + <float>f_old[1]*(self.unit.level - self.unit.base_level)**<float>f_old[2]
            return old_multiplier

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

        cdef float lvl_lo = selected_factors["level_start"]
        cdef float lvl_hi = selected_factors["level_stop"]

        cdef float f1 = <float>f_low[0] + <float>f_low[1]*(self.unit.level - self.unit.base_level)**<float>f_low[2]
        cdef float f2 = <float>f_hi[0] + <float>f_hi[1]*(self.unit.level - self.unit.base_level)**<float>f_hi[2]
        cdef float t = (self.unit.level-self.unit.base_level-smoothstep_start)/(smoothstep_stop - smoothstep_start)
        t = max(0, min(1,t))
        cdef float s = <float>3*t**<float>2-<float>2*t**<float>3

        cdef float bonus = <float>f_bonus[0] + <float>f_bonus[1]*(self.unit.level - lvl_lo)
        cdef float res = (f1*(<float>1-s)+f2*s) * bonus
        
        return res
    
    def set_mission_multiplier(self, name, value):
        # self.mission_multipliers[name] = <float>value
        # self.current_value = <float>math.prod([<float>f for f in self.mission_multipliers.values()])

        if self.current_value <= 0:
            self.mission_multipliers[name] = value
            return
        cdef float old_affliction = math.prod([<float>f for f in self.mission_multipliers.values()])
        self.mission_multipliers[name] = <float>value
        cdef float new_affliction = math.prod([<float>f for f in self.mission_multipliers.values()])
        self.current_value = <float>(new_affliction * (self.current_value / old_affliction))

        if self.protection_type == 'armor':
            self.unit.set_armor_dr()
    
    def set_value_multiplier(self, name, value):
        if self.current_value <= 0:
            self.value_multipliers[name] = value
            return
        cdef float old_affliction = math.prod([<float>f for f in self.value_multipliers.values()])
        self.value_multipliers[name] = <float>value
        cdef float new_affliction = math.prod([<float>f for f in self.value_multipliers.values()])
        self.current_value = <float>(new_affliction * (self.current_value / old_affliction))
        
        if self.current_value <= 0.5:
            self.current_value = 0

        if self.protection_type == 'armor':
            self.unit.set_armor_dr()

    def set_damage_multiplier(self, name, value):
        self.damage_multipliers[name] = value
        self.total_damage_multiplier = <float>math.prod([<float>f for f in self.damage_multipliers.values()])

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
        self.knockdown_proc_manager = pm.DefaultProcManager(enemy, const.PT_INDEX['PT_KNOCKDOWN'])
        self.microwave_proc_manager = pm.DefaultProcManager(enemy, const.PT_INDEX['PT_MICROWAVE'])

        self.proc_managers: List[pm.DefaultProcManager] = [self.impact_proc_manager, self.puncture_proc_manager, self.slash_proc_manager,
                                self.heat_proc_manager, self.cold_proc_manager, self.electric_proc_manager,
                                self.toxin_proc_manager, self.blast_proc_manager, self.radiation_proc_manager,
                                self.gas_proc_manager, self.magnetic_proc_manager, self.viral_proc_manager,
                                self.corrosive_proc_manager, self.void_proc_manager, self.knockdown_proc_manager, self.microwave_proc_manager]

    def add_proc(self, proc_index:int, fire_mode:FireMode, status_damage: float, bodypart:str):
        self.proc_managers[proc_index].add_proc(fire_mode, status_damage, bodypart)

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
        self.critical_multiplier = <float>1
        self.tiered_critical_multiplier = <float>1
        self.unmodified_tiered_critical_multiplier = <float>1
        self.critical_tier = 0
        

    def normal(self, fire_mode: FireMode, damage: np.array, *args):
        self.enemy.last_t0_damage = np.sum(damage)
        return <float>1

    def static_dps_1(self, fire_mode: FireMode, damage: np.array, critical_multiplier:float):
        cdef float tier_min = (<float>1-<float>1/max(1,self.critical_tier))
        cdef float dps_reducer = (tier_min/(self.critical_multiplier-tier_min) + <float>1)

        # Weird shotgun mechanic
        cdef float dps_multiplier = fire_mode.fireRate.modded * fire_mode.multishot.modded
        dps_multiplier = <float>1 if dps_multiplier==0 else dps_multiplier # lanka shenans
        dps_multiplier = dps_multiplier/<float>2 if fire_mode.multishot.base > 1 else dps_multiplier
        dps_multiplier = dps_multiplier / dps_reducer
        cdef float tier0_dps = np.sum(damage * dps_multiplier)

        self.enemy.last_t0_damage = np.sum(damage)

        cdef float dr = 1
        if tier0_dps >= 1000 and tier0_dps <= 2500:
            dr = <float>0.8 + <float>200/tier0_dps
        elif tier0_dps >= 2500 and tier0_dps <= 5000:
            dr = <float>0.7 + <float>450/tier0_dps
        elif tier0_dps >= 5000 and tier0_dps <= 10000:
            dr = <float>0.4+<float>1950/tier0_dps
        elif tier0_dps >= 10000 and tier0_dps <= 20000:
            dr = <float>0.2+<float>3950/tier0_dps
        elif tier0_dps >= 20000:
            dr = <float>0.1+<float>5950/tier0_dps
        return dr
    
    def static_dps_2(self, fire_mode: FireMode, damage: np.array, critical_multiplier:float):
        cdef float tier_min = (<float>1-<float>1/max(1,self.critical_tier))
        cdef float dps_reducer = (tier_min/(self.critical_multiplier-tier_min) + <float>1)

        cdef float dps_multiplier = fire_mode.fireRate.modded * fire_mode.multishot.modded
        # Weird shotgun mechanic
        dps_multiplier = dps_multiplier/<float>2 if fire_mode.multishot.base > 1 else dps_multiplier

        dps_multiplier = dps_multiplier / dps_reducer
        cdef float tier0_dps = np.sum(damage * dps_multiplier)

        self.enemy.last_t0_damage = np.sum(damage)

        cdef float dr = 1
        if tier0_dps >= 3000 and tier0_dps <= 7500:
            dr = <float>0.8 + <float>600/tier0_dps
        elif tier0_dps >= 7500 and tier0_dps <= 22500:
            dr = <float>1.6/3 + <float>2600/tier0_dps
        elif tier0_dps >= 22500:
            dr = <float>14600/tier0_dps
        return dr
    
    def dynamic_dps_1(self, fire_mode: FireMode, damage: np.array, critical_multiplier:float):
        cdef float dpt = np.sum(damage) * critical_multiplier * <float>fire_mode.multishot.modded
        self.enemy.last_t0_damage = np.sum(damage)

        cdef float cap = 460e3
        cdef float dr = <float>1/(<float>1 + <float>(dpt/cap))
        return dr
    
    def dynamic_dps_2(self, fire_mode: FireMode, damage: np.array, critical_multiplier:float):
        cdef float dpt = np.sum(damage * <float>fire_mode.multishot.modded * critical_multiplier)
        self.enemy.last_t0_damage = np.sum(damage)

        cdef float cap = 175e3
        cdef float dr = <float>1/(<float>1+(dpt)/cap)
        return dr
    
    def crit_controller_0(self, critical_multiplier, critical_tier):
        self.critical_tier = critical_tier
        self.critical_multiplier = critical_multiplier

        ## scale critical multiplier to the tier
        if critical_tier == 0:
            self.tiered_critical_multiplier = <float>1
            self.unmodified_tiered_critical_multiplier = self.tiered_critical_multiplier
            return self.tiered_critical_multiplier
        
        cdef float tiered_critical_multiplier = (critical_multiplier-<float>1) * critical_tier + <float>1
        self.tiered_critical_multiplier = tiered_critical_multiplier
        self.unmodified_tiered_critical_multiplier = self.tiered_critical_multiplier
        return self.tiered_critical_multiplier
    
    def crit_controller_1(self, critical_multiplier, critical_tier):
        self.critical_tier = critical_tier
        self.critical_multiplier = critical_multiplier

        if critical_tier == 0:
            self.tiered_critical_multiplier = <float>1
            self.unmodified_tiered_critical_multiplier = self.tiered_critical_multiplier
            return self.tiered_critical_multiplier

        cdef float tier_1 = (critical_multiplier - <float>1) * <float>0.5 + <float>1
        cdef float tier_increase = tier_1/(<float>1 + <float>1/(critical_multiplier - <float>1))

        cdef float tiered_critical_multiplier = tier_1 + (critical_tier-<float>1) * tier_increase
        self.tiered_critical_multiplier = tiered_critical_multiplier

        cdef float unmodified_tiered_critical_multiplier = (critical_multiplier-<float>1)*critical_tier + <float>1
        self.unmodified_tiered_critical_multiplier = unmodified_tiered_critical_multiplier

        return self.tiered_critical_multiplier 


def update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update(d.get(k, {}), v)
        else:
            d[k] = v
    return d