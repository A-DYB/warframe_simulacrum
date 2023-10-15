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
    
    def get_armor_dr(self, ):
        current_armor = self.armor.current_value
        if int(current_armor) >= 1:
            armor_dr = self.armor.modifier * np.reciprocal((self.armor.modifier*(-1)+2)*(current_armor/300)+1)
            armor_dr[14] = 1
            return armor_dr
        return constants.modifiers["None"]
    
    def apply_mods(self, fire_mode:FireMode):
        if not fire_mode.refresh:
            return
        fire_mode.refresh = False
        ## Damage
        direct_damage = 0 if fire_mode.radial else self.unique_proc_count * fire_mode.damagePerShot_m["condition_overload_base"] + fire_mode.damagePerShot_m["direct"]
        
        # bonus base damage
        weights = fire_mode.damagePerShot.base/max(sum(fire_mode.damagePerShot.base), 0.01)
        damagePerShot_bonus = weights * fire_mode.bonusDamagePerShot_m["additive_base"]
        
        fire_mode.damagePerShot.modded = (fire_mode.damagePerShot.base + damagePerShot_bonus) * \
                                            (1 + fire_mode.damagePerShot_m["base"] + direct_damage) * \
                                                fire_mode.damagePerShot_m["multishot_multiplier"] * \
                                                    fire_mode.damagePerShot_m["final_multiplier"]
        
        ## Critical Chance
        puncture_count = self.proc_controller.puncture_proc_manager.count
        criticalChance_puncture = 0 if fire_mode.radial else puncture_count * 0.05
        fire_mode.criticalChance.modded = ((fire_mode.criticalChance.base + fire_mode.criticalChance_m["additive_base"]) * \
                                                (1 + fire_mode.criticalChance_m["base"]) + fire_mode.criticalChance_m["additive_final"] + criticalChance_puncture) * \
                                                    fire_mode.criticalChance_m["deadly_munitions"] + fire_mode.criticalChance_m["covenant"]

        ## Critical Damage
        cold_count = self.proc_controller.cold_proc_manager.count
        criticalMultiplier_cold = 0 if fire_mode.radial else min(1, cold_count) * 0.1 + max(0, cold_count-1) * 0.05
        fire_mode.criticalMultiplier.modded = ((fire_mode.criticalMultiplier.base + fire_mode.criticalMultiplier_m["additive_base"]) * \
                                                    (1 + fire_mode.criticalMultiplier_m["base"]) + fire_mode.criticalMultiplier_m["additive_final"] + criticalMultiplier_cold) * \
                                                        fire_mode.criticalMultiplier_m["final_multiplier"]

        # Bonus damage types
        total_base_damage = sum(fire_mode.damagePerShot.modded)
        fire_mode.elementalDamagePerShot[0] = fire_mode.damagePerShot.modded[0] * fire_mode.impact_m["base"]
        fire_mode.elementalDamagePerShot[1] = fire_mode.damagePerShot.modded[1] * fire_mode.puncture_m["base"]
        fire_mode.elementalDamagePerShot[2] = fire_mode.damagePerShot.modded[2] * fire_mode.slash_m["base"]

        fire_mode.elementalDamagePerShot[3] = total_base_damage * fire_mode.heat_m["base"]
        fire_mode.elementalDamagePerShot[4] = total_base_damage * fire_mode.cold_m["base"]
        fire_mode.elementalDamagePerShot[5] = total_base_damage * fire_mode.electric_m["base"]
        fire_mode.elementalDamagePerShot[6] = total_base_damage * fire_mode.toxin_m["base"]

        ## Status chance
        fire_mode.procChance.modded = (fire_mode.procChance.base + fire_mode.procChance_m["additive_base"]) * \
                                        ((1 + fire_mode.procChance_m["base"]) + fire_mode.procChance_m["additive_final"]) *\
                                        fire_mode.procChance_m["final_multiplier"] * fire_mode.procChance_m["multishot_multiplier"]
        fire_mode.procProbabilities = np.add(fire_mode.damagePerShot.modded + fire_mode.elementalDamagePerShot, out=fire_mode.procProbabilities)
        fire_mode.procProbabilities = np.multiply( fire_mode.procProbabilities, self.procImmunities, out=fire_mode.procProbabilities)
        tot_weight = sum(fire_mode.procProbabilities)
        fire_mode.procProbabilities *= 1/tot_weight if tot_weight>0 else 0

        fire_mode.procCumulativeProbabilities = 0

        ## Other
        fire_mode.multishot.modded = fire_mode.multishot.base * (1 + fire_mode.multishot_m["base"])
        fire_mode.fireRate.modded = fire_mode.fireRate.base * (1 + fire_mode.fireRate_m["base"])
        fire_mode.reloadTime.modded = fire_mode.reloadTime.base / (1 + fire_mode.reloadTime_m["base"])
        fire_mode.magazineSize.modded = fire_mode.magazineSize.base * (1 + fire_mode.magazineSize_m["base"])
        fire_mode.chargeTime.modded = fire_mode.chargeTime.base / (1 + fire_mode.fireRate_m["base"])
        fire_mode.magazineSize.modded = fire_mode.magazineSize.base * (1 + fire_mode.magazineSize_m["base"])
        fire_mode.embedDelay.modded = fire_mode.embedDelay.base
        fire_mode.ammoCost.modded = fire_mode.ammoCost.base * max(0, 1 - fire_mode.ammoCost_m["base"]) * max(0, 1 - fire_mode.ammoCost_m["energized_munitions"])

    def pellet_hit(self, fire_mode:FireMode, enemy:"Unit"):
        # apply the mods
        self.apply_mods(fire_mode) 

        # apply critical multiplier to the damage instance
        critical_tier = int(fire_mode.criticalChance.modded) + int(random() < fire_mode.criticalChance.modded % 1)
        effective_critical_multiplier = critical_tier * (fire_mode.criticalMultiplier.modded - 1) + 1

        #apply damage
        status_damage = self.apply_damage(fire_mode, fire_mode.damagePerShot.modded, fire_mode.elementalDamagePerShot, effective_critical_multiplier, source="pellet")

        # apply status procs 
        self.apply_status(fire_mode, status_damage)

    def apply_damage(self, fire_mode:FireMode, damage:np.array, bonus_damage:np.array, critical_multiplier=1, body_part=None, source="None"):
        total_damage = damage + bonus_damage
        # body part bonuses
        total_damage *= 1

        # faction bonuses
        total_damage *= (1 + fire_mode.factionDamage_m["base"])

        status_damage = total_damage

        # quantize
        quanta = sum(damage) / 16
        total_damage = np.round( total_damage / quanta, 0) * quanta

        # apply crit
        total_damage *= critical_multiplier
        status_damage *= critical_multiplier

        armor_dr = self.get_armor_dr()
        armor_dr = constants.modifiers["None"]
        og, sg, hg = self.remove_protection(total_damage, armor_dr)

        # print(f"Damage at {self.simulation.time:.2f}s: {([f'{og:.1f}', f'{sg:.1f}', f'{hg:.1f}'])}, source:{source}")

        if self.health.current_value <= 0 and self.overguard.current_value <= 0:
            return status_damage
        
        if self.overguard.current_value < 0:
            ratio = abs(self.overguard.current_value/og)
            self.overguard.current_value = 0
            og, sg, hg = self.remove_protection(total_damage * ratio, armor_dr)

            if self.shield.current_value < 0:
                ratio = abs(self.shield.current_value/sg)
                self.shield.current_value = 0
                self.remove_protection(total_damage * ratio, armor_dr) 

        elif self.shield.current_value < 0:
            ratio = abs(self.shield.current_value/sg)
            self.shield.current_value = 0
            self.remove_protection(total_damage * ratio, armor_dr)
        
        return status_damage

    def apply_status(self, fire_mode:FireMode, status_damage: np.array):
        status_tier = int(fire_mode.procChance.modded) + int(random() < fire_mode.procChance.modded % 1)
        
        # calculate status effect chances
        # damage_weights = (fire_mode.damagePerShot.modded + fire_mode.elementalDamagePerShot) * self.procImmunities
        # if sum(damage_weights) == 0:
        #     effect_chances = [0] * 20
        # else:
        #     effect_chances = damage_weights / sum(damage_weights)

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

    def remove_protection(self, damage:np.array, armor_dr):
        overguard = self.overguard.current_value
        shield = self.shield.current_value
        health = self.health.current_value
        if self.overguard.current_value > 0:
            overguard_debuff = math.prod([f for f in self.overguard.debuffs.values()])
            self.overguard.current_value -= sum(damage * self.overguard.modifier * overguard_debuff)
        elif self.shield.current_value > 0:
            health_debuff = math.prod([f for f in self.health.debuffs.values()])
            shield_debuff = math.prod([f for f in self.shield.debuffs.values()])
            self.health.current_value -= damage[6] * armor_dr[6] * self.health.modifier[6] * health_debuff
            self.shield.current_value -= sum(damage * self.shield.modifier * shield_debuff)
        else:
            health_debuff = math.prod([f for f in self.health.debuffs.values()])
            self.health.current_value -= sum(damage * armor_dr * self.health.modifier * health_debuff)
        
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

    def apply_magnetic_debuff(self, proc_manager:pm.DefaultProcManager):
        debuff = constants.MAGNETIC_DEBUFF[proc_manager.count]
        self.shield.debuffs["Magnetic debuff"] = debuff

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

    def reset(self):
        self.modified_base = self.base
        self.max_value = self.base * self.level_multiplier * self.bonus 
        self.current_value = self.max_value
        self.afflictions = {}
        self.debuffs = {}

    def apply_bonus(self, bonus):
        self.bonus *= bonus
        self.max_value = self.max_value * bonus
        self.current_value = self.max_value

    # ex. shattering impact, mag's 3
    def remove_base_value(self, value):
        pct = self.current_value/self.max_value
        self.modified_base -= value
        self.max_value = self.modified_base * self.level_multiplier * self.bonus 
        self.current_value = self.max_value * pct

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