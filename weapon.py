from __future__ import annotations

import numpy as np
import os 
from pathlib import Path
import json
import re
import constants as const
import heapq

from random import random
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from simulation import Simulacrum
    from unit import Unit


class Weapon():
    def __init__(self, name:str, ui, simulation:Simulacrum) -> None:
        self.name = name
        self.ui = ui
        self.simulation = simulation
        self.data = self.get_weapon_data()

        self.riven_type = self.data.get("rivenType", "")
        self.fire_modes:List[FireMode] = [FireMode(self, name) for name in self.data.get("fireModes", {})]
    
    def get_weapon_data(self):
        current_folder = Path(__file__).parent.resolve()
        with open(os.path.join(current_folder, "data", "ExportWeapons.json"), 'r') as f:
            weapon_data = json.load(f)

        return weapon_data.get(self.name, {})
    
    def reset(self):
        for fire_mode in self.fire_modes:
            fire_mode.reset()

class FireMode():
    def __init__(self, weapon:Weapon, name:str) -> None:
        self.weapon = weapon
        self.name = name
        self.data = weapon.data["fireModes"][self.name]
        self.simulation = weapon.simulation
        self.fire_mode_effects:List[FireModeEffect] = [FireModeEffect(self, name) for name in self.data.get("secondaryEffects", {})]
        self.attack_index = 1

        self.trigger = self.data.get("trigger", "AUTO")

        self.damagePerShot = DamageParameter( np.array(self.data.get("damagePerShot", np.array([0]*20)), dtype=float) )
        self.totalDamage = Parameter( self.data.get("totalDamage", 1) )
        self.criticalChance = Parameter( self.data.get("criticalChance", 0) )
        self.criticalMultiplier = Parameter( self.data.get("criticalMultiplier", 1) )
        self.criticalMultiplier.base = round(self.criticalMultiplier.base * (128 - 1/32), 0) / (128 - 1/32) # quantization happens on the base value, not the modded value
        self.procChance = Parameter( self.data.get("procChance", 0) )
        self.procProbabilities = np.array([0]*20, dtype=float)
        self.procAllowances = np.array([1]*20, dtype=float)

        self.magazineSize = ModifyParameter( self.data.get("magazineSize", 100) )
        self.fireRate = Parameter( self.data.get("fireRate", 5) )
        self.fireTime = Parameter( 1/self.fireRate.modded )
        self.reloadTime = Parameter( self.data.get("reloadTime", 1) )
        self.multishot = Parameter( self.data.get("multishot", 1) )
        self.ammoCost = Parameter( self.data.get("ammoCost", 1) )
        self.chargeTime = Parameter( self.data.get("chargeTime", 0) )
        self.embedDelay = Parameter( self.data.get("embedDelay", 0) )

        self.forcedProc = self.data.get("forcedProc", []) # indices corresponding to proc that will be forced

        self.radial = False
        self.unique_proc_count = 0
        self.condition_overloaded = False
        self.mod_damage_multiplier = 1
        self.accumulated_damage_multiplier = 1

        # mods
        self.damagePerShot_m = {"base":Mod(changed_callbacks=[self.calc_modded_damage]), "additive_base":Mod(changed_callbacks=[self.calc_modded_damage]), 
                                "condition_overload_base":Mod(changed_callbacks=[self.calc_modded_damage]), "condition_overload_multiplier":Mod(changed_callbacks=[self.calc_modded_damage]), 
                                "direct":Mod(changed_callbacks=[self.calc_modded_damage]), "final_multiplier":Mod(value=1,changed_callbacks=[self.calc_modded_damage]), 
                                "multishot_multiplier":Mod(value=1,changed_callbacks=[self.calc_modded_damage])}
        self.criticalChance_m = {"base":Mod(), "additive_base":Mod(), "additive_final":Mod(), "covenant":Mod(), "deadly_munitions":Mod(value=1)}
        self.criticalMultiplier_m = {"base":Mod(), "additive_base":Mod(), "additive_final":Mod(), "final_multiplier":Mod(value=1)}
        self.procChance_m = {"base":Mod(), "additive_base":Mod(), "additive_final":Mod(), "final_multiplier":Mod(value=1), "multishot_multiplier":Mod(value=1)}
        self.magazineSize_m = {"base":Mod()}
        self.fireRate_m = {"base":Mod(), "final_multiplier":Mod(value=1)}
        self.reloadTime_m = {"base":Mod()}
        self.multishot_m = {"base":Mod()}
        self.heat_m = {"base":Mod(), "uncombinable":Mod()}
        self.cold_m = {"base":Mod(), "uncombinable":Mod()}
        self.electric_m = {"base":Mod(), "uncombinable":Mod()}
        self.toxin_m = {"base":Mod(), "uncombinable":Mod()}
        self.blast_m = {"base":Mod()}
        self.radiation_m = {"base":Mod()}
        self.gas_m = {"base":Mod()}
        self.magnetic_m = {"base":Mod()}
        self.viral_m = {"base":Mod()}
        self.corrosive_m = {"base":Mod()}

        self.impact_m = {"base":Mod(), "stance":Mod()}
        self.puncture_m = {"base":Mod(), "stance":Mod()}
        self.slash_m = {"base":Mod(), "stance":Mod()}

        self.statusDuration_m = {"base":Mod()}
        self.factionDamage_m = {"base":Mod()}
        self.ammoCost_m = {"base":Mod(), "energized_munitions":Mod()}

        self.load_mods()
        self.apply_mods()
        self.condition_overloaded = (self.damagePerShot_m["condition_overload_base"] > 0) or (self.damagePerShot_m["condition_overload_multiplier"] > 0)

    def reset(self):
        self.attack_index = 1

        self.damagePerShot.reset()
        self.criticalChance.reset()
        self.criticalMultiplier.reset()
        self.procChance.reset()
        self.magazineSize.reset()
        self.fireRate.reset()
        self.fireTime.reset()
        self.reloadTime.reset()
        self.multishot.reset()
        self.ammoCost.reset()
        self.chargeTime.reset()
        self.embedDelay.reset()

    def load_mods(self):
        self.damagePerShot_m["direct"].value = 0
        # self.damagePerShot_m["final_multiplier"].value = 1
        self.damagePerShot_m["base"].value = 2.2
        self.damagePerShot_m["additive_base"].value = 4
        self.factionDamage_m["base"].value = 0.55 + 0.5
        # self.slash_m["base"].value = 1.2
        self.heat_m["base"].value = 0.9


    def apply_mods(self):
        ## Damage
        self.calc_full_damage_stack()
        
        ## Critical Chance
        self.criticalChance.modded = ((self.criticalChance.base + self.criticalChance_m["additive_base"].value) * \
                                                (1 + self.criticalChance_m["base"].value) + self.criticalChance_m["additive_final"].value ) * \
                                                    self.criticalChance_m["deadly_munitions"].value + self.criticalChance_m["covenant"].value

        # ## Critical Damage
        self.criticalMultiplier.modded = ((self.criticalMultiplier.base + self.criticalMultiplier_m["additive_base"].value) * \
                                                    (1 + self.criticalMultiplier_m["base"].value) + self.criticalMultiplier_m["additive_final"].value )

        ## Status chance
        self.procChance.modded = (self.procChance.base + self.procChance_m["additive_base"].value) * \
                                        ((1 + self.procChance_m["base"].value) + self.procChance_m["additive_final"].value) *\
                                        self.procChance_m["final_multiplier"].value * self.procChance_m["multishot_multiplier"].value

        ## Other
        self.multishot.modded = self.multishot.base * (1 + self.multishot_m["base"].value)
        self.fireRate.modded = self.fireRate.base * (1 + self.fireRate_m["base"].value)
        self.fireTime.modded = 1 / self.fireRate.modded
        self.reloadTime.modded = self.reloadTime.base / (1 + self.reloadTime_m["base"].value)
        self.magazineSize.modded = self.magazineSize.base * (1 + self.magazineSize_m["base"].value)
        self.chargeTime.modded = self.chargeTime.base / (1 + self.fireRate_m["base"].value)
        self.magazineSize.modded = self.magazineSize.base * (1 + self.magazineSize_m["base"].value)
        self.embedDelay.modded = self.embedDelay.base
        self.ammoCost.modded = self.ammoCost.base * max(0, 1 - self.ammoCost_m["base"].value) * max(0, 1 - self.ammoCost_m["energized_munitions"].value)

    def calc_full_damage_stack(self):
        np.copyto( self.damagePerShot.proportions, self.damagePerShot.base_proportions )
        self.damagePerShot.proportions[0] *= (1 + self.impact_m["base"].value)
        self.damagePerShot.proportions[1] *= (1 + self.puncture_m["base"].value)
        self.damagePerShot.proportions[2] *= (1 + self.slash_m["base"].value)

        self.damagePerShot.proportions[3] += self.heat_m["base"].value
        self.damagePerShot.proportions[4] += self.cold_m["base"].value
        self.damagePerShot.proportions[5] += self.electric_m["base"].value
        self.damagePerShot.proportions[6] += self.toxin_m["base"].value

        self.damagePerShot.proportions[7] += self.blast_m["base"].value
        self.damagePerShot.proportions[8] += self.radiation_m["base"].value
        self.damagePerShot.proportions[9] += self.gas_m["base"].value
        self.damagePerShot.proportions[10] += self.magnetic_m["base"].value
        self.damagePerShot.proportions[11] += self.viral_m["base"].value
        self.damagePerShot.proportions[12] += self.corrosive_m["base"].value

        self.procProbabilities = self.damagePerShot.proportions * self.procAllowances
        tot_weight = sum(self.procProbabilities)
        self.procProbabilities *= 1/tot_weight if tot_weight>0 else 0

        self.damagePerShot.quantized = np.round(self.damagePerShot.proportions * 16)/16

        self.calc_modded_damage()

    def calc_modded_damage(self):
        self.damagePerShot.set_base_total(self.totalDamage.base + self.damagePerShot_m["additive_base"].value)
        self.totalDamage.base = self.damagePerShot.base_total


        direct_damage = 0 if self.radial else self.unique_proc_count * (self.damagePerShot_m["condition_overload_base"].value + self.damagePerShot_m["direct"].value)
        damage_multiplier = (1 + self.damagePerShot_m["base"].value + direct_damage) * \
                                self.damagePerShot_m["multishot_multiplier"].value * \
                                    self.damagePerShot_m["final_multiplier"].value
        
        self.mod_damage_multiplier = damage_multiplier
        self.accumulated_damage_multiplier = damage_multiplier

        self.damagePerShot.modded = (self.damagePerShot.quantized * self.damagePerShot.base_total) * damage_multiplier
        self.totalDamage.modded = self.totalDamage.base * damage_multiplier

    def pull_trigger(self, fire_mode, enemy:Unit):
        multishot_roll = get_tier(self.multishot.modded)
        multishot = multishot_roll

        self.magazineSize.current -= self.ammoCost.modded

        if self.trigger == "HELD":
            self.damagePerShot_m["multishot_multiplier"].set_value(multishot_roll)
            self.procChance_m["multishot_multiplier"].set_value(multishot_roll)
            multishot = 1

        for _ in range(multishot):
            fm_time = self.simulation.time + self.embedDelay.modded
            heapq.heappush(self.simulation.event_queue, (fm_time, self.simulation.get_call_index(), EventTrigger(self, enemy.pellet_hit, fm_time, name="Pellet hit")))

            for fme in self.fire_mode_effects:
                fme_time = fme.embedDelay + fm_time
                heapq.heappush(self.simulation.event_queue, (fme_time, self.simulation.get_call_index(), EventTrigger(fme, enemy.pellet_hit, fme_time, name="Pellet hit")))


        if self.magazineSize.current > 0:
            next_event = self.simulation.time + self.fireTime.modded + self.chargeTime.modded
        else:
            self.magazineSize.current = self.magazineSize.modded
            next_event = self.simulation.time + max(self.reloadTime.modded, self.fireTime.modded) + self.chargeTime.modded

        heapq.heappush(self.simulation.event_queue, (next_event, self.simulation.get_call_index(), EventTrigger(fire_mode, self.pull_trigger, next_event)))

def aid(x):
    # This function returns the memory
    # block address of an array.
    return x.__array_interface__['data'][0]

def get_tier(chance):
    return int(random()<(chance%1)) + int(chance)

class FireModeEffect():
    def __init__(self, fire_mode:FireMode, name:str) -> None:
        self.fire_mode = fire_mode
        self.weapon = fire_mode.weapon
        self.name = name
        self.next_event_timestamp = const.MAX_TIME_OFFSET
        self.data = fire_mode.data["secondaryEffects"].value[self.name]

        self.damagePerShot = np.array(self.data.get("damagePerShot", fire_mode.damagePerShot))
        self.criticalChance = self.data.get("criticalChance", fire_mode.criticalChance)
        self.criticalMultiplier = self.data.get("criticalMultiplier", fire_mode.criticalMultiplier)
        self.procChance = self.data.get("procChance", fire_mode.procChance)

        self.multishot = self.data.get("multishot", 1)
        self.embedDelay = self.data.get("embedDelay", 0)
        self.forcedProc = self.data.get("forcedProc", [])


class DamageParameter():
    def __init__(self, base: np.array) -> None:
        self.base = base
        self.base_total: int = sum(self.base)
        self.base_proportions = base/self.base_total
        self.proportions = self.base_proportions.copy()
        self.quantized = self.base.copy()
        self.modded = self.base.copy()

    def reset(self):
        self.modded = self.base.copy()
        self.quantized = self.base.copy()

    def set_base_total(self, value):
        if value == self.base_total:
            return
        
        self.base = self.base_proportions * value
        self.base_total = value

    # def multiply(self, val):
    #     self.modded *= val
    #     self.quantized *= val


class ModifyParameter():
    def __init__(self, base) -> None:
        self.base = base
        self.modded = base
        self.current = base

    def reset(self):
        self.modded = self.base
        self.current = self.modded


class Parameter():
    def __init__(self, base) -> None:
        self.base = base
        self.modded = base

    def reset(self):
        self.modded = self.base


class Mod():
    def __init__(self, key='', value=0, changed_callbacks=[]) -> None:
        self.key = key
        self.value = value
        self.changed_callbacks = changed_callbacks

    def set_value(self, value):
        if self.value == value:
            return
        
        for callback in self.changed_callbacks:
            callback()


class EventTrigger():
    def __init__(self, fire_mode:[FireModeEffect, FireMode], func, time:int, name="", info_callback=None) -> None:
        self.fire_mode = fire_mode
        self.func = func # should accept FireMode and Unit as arguments
        self.time = time   
        self.name = name
        self.info_callback = info_callback

def parse_text(text, combine_rule=const.COMBINE_ADD, parse_rule=const.BASE_RULE):
    if combine_rule == const.COMBINE_ADD:
        return sum([float(i) for i in re.findall(parse_rule, text)])
    elif combine_rule == const.COMBINE_MULTIPLY:
        str_list = re.findall(const.BASE_RULE, text)
        if len(str_list)>0:
            return np.prod(np.array([float(i) for i in str_list]))
        else:
            return 1
    return None