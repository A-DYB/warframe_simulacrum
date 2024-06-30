from __future__ import annotations

import numpy as np
import os 
from pathlib import Path
import json
import re
import warframe_simulacrum.constants as const
import heapq
import copy
import collections.abc

from random import random
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from warframe_simulacrum.simulation import Simulacrum
    from warframe_simulacrum.unit import Unit


class Weapon():
    def __init__(self, name:str, ui, simulation:Simulacrum) -> None:
        self.name = name
        self.ui = ui
        self.simulation = simulation
        self.data = self.get_weapon_data()

        self.riven_type = self.data.get("rivenType", "")
        self.fire_modes:dict = {f'{name}':FireMode(self, name) for name in self.data.get("fireModes", {})}

        # Mods
        self.combineElemental_m = {"indices":[]}

        self.damagePerShot_m = {"base":0, "additive_base":0, 
                                "condition_overload_base":0, "multiplicative_condition_overload":0, 
                                "direct":0, "final_multiplier":1, 
                                "multishot_multiplier":1, 'multishot_damage':0, "headshot_base":0}
        self.criticalChance_m = {"base":0, "additive_base":0, "additive_final":0, "covenant":0, "deadly_munitions":1}
        self.criticalMultiplier_m = {"base":0, "additive_base":0, "additive_final":0, "final_multiplier":1}
        self.procChance_m = {"base":0, "additive_base":0, "additive_final":0, "final_multiplier":1, "multishot_multiplier":1}
        self.magazineSize_m = {"base":0}
        self.fireRate_m = {"base":0, "final_multiplier":1}
        self.reloadTime_m = {"base":0}
        self.multishot_m = {"base":0}
        self.heat_m = {"base":0, "uncombinable":0}
        self.cold_m = {"base":0, "uncombinable":0}
        self.electric_m = {"base":0, "uncombinable":0}
        self.toxin_m = {"base":0, "uncombinable":0}
        self.blast_m = {"base":0}
        self.radiation_m = {"base":0}
        self.gas_m = {"base":0}
        self.magnetic_m = {"base":0}
        self.viral_m = {"base":0}
        self.corrosive_m = {"base":0}

        self.impact_m = {"base":0, "stance":0}
        self.puncture_m = {"base":0, "stance":0}
        self.slash_m = {"base":0, "stance":0}

        self.statusDuration_m = {"base":0}
        self.factionDamage_m = {"base":0}
        self.ammoCost_m = {"base":0, "energized_munitions":0}

        self.special_m = {"encumber_chance":0, "attrition_chance":0}

        self.last_encumber_time = 0

    
    def get_weapon_data(self):
        current_folder = Path(__file__).parent.resolve()
        with open(os.path.join(current_folder, "data", "ExportWeapons.json"), 'r') as f:
            weapon_data = json.load(f)

        return weapon_data.get(self.name, {})
    
    def update_data(self):
        current_folder = Path(__file__).parent.resolve()
        with open(os.path.join(current_folder, "data", "ExportWeapons.json"), 'r') as f:
            weapon_data = json.load(f)
        self.data = weapon_data.get(self.name, {})
        # default_data = copy.deepcopy(const.DEFAULT_WEAPON_CONFIG)
        # self.data = update(default_data, data)

        # # default_fm = copy.deepcopy(const.DEFAULT_FIRE_MODE)
        # if len(self.data.get('fireModes', {})) == 0:
        #     self.data['fireModes'] = {'default':copy.deepcopy(const.DEFAULT_FIRE_MODE)}
        # for k, fm in self.data.get('fireModes', {}).items():
        #     self.data['fireModes'][k] = update(copy.deepcopy(const.DEFAULT_FIRE_MODE), fm)
    
        self.riven_type = self.data.get("rivenType", "")
        self.fire_modes:dict = {f'{name}':FireMode(self, name) for name in self.data.get("fireModes", {})}
        self.apply_mods()
    
    def reset(self):
        for fire_mode in self.fire_modes:
            self.fire_modes[fire_mode].reset()

    def get_mod_dict(self):
        return {attr: value for attr, value in vars(self).items() if attr.endswith('_m')}

    def load_mod_config(self, mods:dict):
        for attr, value in vars(self).items():
            if not attr.endswith('_m'):
                continue

            if isinstance(getattr(self, attr), dict):
                getattr(self, attr).update( mods.get(attr, {}) )

        self.combineElemental_m = mods.get("combineElemental_m", {"indices":[]})
        self.apply_mods()
    
    def apply_mods(self):
        for fm in self.fire_modes:
            self.fire_modes[fm].apply_mods()

class FireMode():
    def __init__(self, weapon:Weapon, name:str) -> None:
        '''
        
        '''
        self.weapon = weapon
        self.name = name
        self.data = weapon.data["fireModes"][self.name]
        self.simulation = weapon.simulation
        self.primary_effect = True
        self.attack_index = 1

        self.trigger = self.data.get("trigger", "AUTO")

        self.damagePerShot = DamageParameter( np.array(self.data.get("damagePerShot", np.array([0]*20, dtype=np.single)), dtype=np.single) )
        self.totalDamage = Parameter( self.data.get("totalDamage", 1) )
        self.criticalChance = Parameter( self.data.get("criticalChance", 0) )
        self.criticalMultiplier = Parameter( self.data.get("criticalMultiplier", 1) )
        self.procChance = Parameter( self.data.get("procChance", 0) )
        self.procProbabilities = np.array([0]*20, dtype=np.single)
        self.procAllowances = np.array([1]*20, dtype=np.single)

        self.magazineSize = ModifyParameter( self.data.get("magazineSize", 100) )
        self.fireRate = Parameter( self.data.get("fireRate", 1) )
        self.fireTime = Parameter( 20 if self.fireRate.modded == 0 else 1/self.fireRate.modded )
        self.reloadTime = Parameter( self.data.get("reloadTime", 1) )
        self.multishot = Parameter( self.data.get("multishot", 1) )
        self.ammoCost = Parameter( self.data.get("ammoCost", 1) )
        self.chargeTime = Parameter( self.data.get("chargeTime", 0) )
        self.embedDelay = Parameter( self.data.get("embedDelay", 0) )

        self.forcedProc = self.data.get("forcedProc", []) # indices corresponding to proc that will be forced

        self.radial = self.data.get("radial", False)
        self.unique_proc_count = 0
        self.condition_overloaded = False
        self.multishot_damage = <float>0

        # self.fire_mode_effects:List[FireModeEffect] = [FireModeEffect(self, name) for name in self.data.get("secondaryEffects", {})]
        self.fire_mode_effects:dict = {f'{name}':FireModeEffect(self, name) for name in self.data.get("secondaryEffects", {})}

        self.target_bodypart = 'body'


    def get_preview_info(self):
        info = [
            ("Weapon", self.weapon.name, ''),
            ("Fire Mode", self.name.capitalize(), ''),
            ("Trigger", self.trigger, ''),
            ("Multishot", f'{self.multishot.modded:.1f}', ''),
            ("Critical Chance", f'{self.criticalChance.modded*100:.1f}%', ''),
            ("Critical Multiplier", f'{self.criticalMultiplier.modded:.1f}x', ''),
            ("Status Chance", f'{self.procChance.modded*100:.1f}%', ''),
            ("Fire Rate", f'{self.fireRate.modded:.1f}', ''),
            ("Radial", str(self.radial), ''),
            ("Category","", ''),
            ("Reload", f'{self.reloadTime.modded:.1f}s', ''),
            ("Magazine", f'{self.magazineSize.modded:.0f}', ''),
            
        ]
        if self.ammoCost.modded != 1: info.append(("Ammo Cost", f'{self.ammoCost.modded:.2f}', '')) 
        if self.chargeTime.modded != 0: info.append(("Charge Time", f'{self.chargeTime.modded:.2f}s', '')) 
        if self.embedDelay.modded != 0: info.append(("Embed Delay", f'{self.embedDelay.modded:.2f}s', '')) 
        info.append(("Category", "", '')) 
        info.append(("Category", "Damage", ''))
        for i, elem in enumerate(self.damagePerShot.modded):
            prop = 0 if sum(self.damagePerShot.proportions)==0 else self.damagePerShot.proportions[i]/sum(self.damagePerShot.proportions)
            if round(elem,2) > 0: info.append((const.INDEX_D[i], f'{self.damagePerShot.base[i]:.2f} -> {elem:.2f}', f'Proportion: {prop*100:.1f}%, Proc Chance: {self.procProbabilities[i]*100:.1f}%')) 
        return info

    def reset(self):
        self.attack_index = 1
        self.unique_proc_count = 0
        self.multishot_damage = <float>0
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
        self.forcedProc = self.data.get("forcedProc", [])

        self.apply_mods()

    def apply_mods(self):
        self.condition_overloaded = (self.weapon.damagePerShot_m["condition_overload_base"] > 0) or (self.weapon.damagePerShot_m["multiplicative_condition_overload"] > 0)

        ## Damage
        self.calc_full_damage_stack()
        
        ## Critical Chance
        self.criticalChance.modded = ((self.criticalChance.base + self.weapon.criticalChance_m["additive_base"]) * \
                                                (1 + self.weapon.criticalChance_m["base"]) + self.weapon.criticalChance_m["additive_final"] ) * \
                                                    self.weapon.criticalChance_m["deadly_munitions"] + self.weapon.criticalChance_m["covenant"]

        # ## Critical Damage
         # quantization happens on the base value, not the modded value
        self.criticalMultiplier.reset()
        cdef float cm_base_modified = self.criticalMultiplier.base_modified
        cdef float cm_modded = 1

        cm_base_modified += <float>self.weapon.criticalMultiplier_m["additive_base"]
        cm_base_modified = round(cm_base_modified  * const.CD_QT)  * const.I_CD_QT

        self.criticalMultiplier.base_modified = cm_base_modified
        cm_modded = self.criticalMultiplier.base_modified * (<float>1 + <float>self.weapon.criticalMultiplier_m["base"]) + <float>self.weapon.criticalMultiplier_m["additive_final"] 
        self.criticalMultiplier.modded = cm_modded


        ## Multishot
        self.multishot.modded = <float>self.multishot.base * (<float>1 + <float>self.weapon.multishot_m["base"]) if self.primary_effect else <float>self.multishot.base
        if self.trigger == "HELD":
            self.multishot.modded = min(1, self.multishot.modded) + max(0, self.multishot.modded-1) * <float>self.weapon.damagePerShot_m["multishot_damage"]

        ## Status chance
        self.procChance.modded = ((self.procChance.base + self.weapon.procChance_m["additive_base"]) * (1 + self.weapon.procChance_m["base"]) \
                                    + self.weapon.procChance_m["additive_final"]) *\
                                        self.weapon.procChance_m["final_multiplier"]

        ## Other
        self.fireRate.modded = <float>self.fireRate.base * (<float>1 + <float>self.weapon.fireRate_m["base"])
        self.fireTime.modded = <float>20 if self.fireRate.modded<=0.05 else <float>(1 / self.fireRate.modded)
        self.reloadTime.modded = self.reloadTime.base / (1 + self.weapon.reloadTime_m["base"])
        self.magazineSize.modded = self.magazineSize.base * (1 + self.weapon.magazineSize_m["base"])
        self.chargeTime.modded = self.chargeTime.base / (1 + self.weapon.fireRate_m["base"])
        self.embedDelay.modded = self.embedDelay.base
        self.ammoCost.modded = self.ammoCost.base * max(0, 1 - self.weapon.ammoCost_m["base"]) * max(0, 1 - self.weapon.ammoCost_m["energized_munitions"])

        for fire_mode_effect in self.fire_mode_effects:
            self.fire_mode_effects[fire_mode_effect].apply_mods()

    def calc_full_damage_stack(self):
        np.copyto( self.damagePerShot.proportions, self.damagePerShot.base_proportions )
        self.damagePerShot.proportions[0] *= (<float>1 + <float>self.weapon.impact_m["base"])
        self.damagePerShot.proportions[1] *= (<float>1 + <float>self.weapon.puncture_m["base"])
        self.damagePerShot.proportions[2] *= (<float>1 + <float>self.weapon.slash_m["base"])

        self.damagePerShot.proportions[3] += <float>self.weapon.heat_m["base"]
        self.damagePerShot.proportions[4] += <float>self.weapon.cold_m["base"]
        self.damagePerShot.proportions[5] += <float>self.weapon.electric_m["base"]
        self.damagePerShot.proportions[6] += <float>self.weapon.toxin_m["base"]

        self.damagePerShot.proportions[7] += <float>self.weapon.blast_m["base"]
        self.damagePerShot.proportions[8] += <float>self.weapon.radiation_m["base"]
        self.damagePerShot.proportions[9] += <float>self.weapon.gas_m["base"]
        self.damagePerShot.proportions[10] += <float>self.weapon.magnetic_m["base"]
        self.damagePerShot.proportions[11] += <float>self.weapon.viral_m["base"]
        self.damagePerShot.proportions[12] += <float>self.weapon.corrosive_m["base"]

        # combine elements in desired order
        for idx in self.weapon.combineElemental_m["indices"]:
            if idx==7:
                self.damagePerShot.proportions[7] += self.damagePerShot.proportions[3] + self.damagePerShot.proportions[4]
                self.damagePerShot.proportions[3] = 0
                self.damagePerShot.proportions[4] = 0
            elif idx==8:
                self.damagePerShot.proportions[8] += self.damagePerShot.proportions[3] + self.damagePerShot.proportions[5]
                self.damagePerShot.proportions[3] = 0
                self.damagePerShot.proportions[5] = 0
            elif idx==9:
                self.damagePerShot.proportions[9] += self.damagePerShot.proportions[3] + self.damagePerShot.proportions[6]
                self.damagePerShot.proportions[3] = 0
                self.damagePerShot.proportions[6] = 0
            elif idx==10:
                self.damagePerShot.proportions[10] += self.damagePerShot.proportions[4] + self.damagePerShot.proportions[5]
                self.damagePerShot.proportions[4] = 0
                self.damagePerShot.proportions[5] = 0
            elif idx==11:
                self.damagePerShot.proportions[11] += self.damagePerShot.proportions[4] + self.damagePerShot.proportions[6]
                self.damagePerShot.proportions[4] = 0
                self.damagePerShot.proportions[6] = 0
            elif idx==12:
                self.damagePerShot.proportions[12] += self.damagePerShot.proportions[5] + self.damagePerShot.proportions[6]
                self.damagePerShot.proportions[5] = 0
                self.damagePerShot.proportions[6] = 0

        self.procProbabilities = self.damagePerShot.proportions * self.procAllowances
        tot_weight = sum(self.procProbabilities)
        self.procProbabilities *= 1/tot_weight if tot_weight>0 else 0
        self.damagePerShot.quantized = np.round(self.damagePerShot.proportions * <float>16)/<float>16

        self.calc_modded_damage()

        for fire_mode_effect in self.fire_mode_effects:
            self.fire_mode_effects[fire_mode_effect].calc_full_damage_stack()

    def calc_modded_damage(self):
        self.damagePerShot.set_base_total(self.totalDamage.base + <float>self.weapon.damagePerShot_m["additive_base"])
        self.totalDamage.base_modified = self.damagePerShot.base_total

        cdef float direct_damage = <float>0 if self.radial else <float>self.unique_proc_count * (<float>self.weapon.damagePerShot_m["condition_overload_base"] + <float>self.weapon.damagePerShot_m["direct"])
        # multiplicative_condition_overload
        cdef float direct_damage_multiplier = <float>0 if self.radial else <float>self.unique_proc_count * (<float>self.weapon.damagePerShot_m["multiplicative_condition_overload"])

        cdef float damage_multiplier = (<float>1 + <float>self.weapon.damagePerShot_m["base"] + direct_damage) * \
                                    <float>self.weapon.damagePerShot_m["final_multiplier"] * (1 + direct_damage_multiplier)

        self.damagePerShot.modded = ((self.damagePerShot.quantized * self.damagePerShot.base_total) * damage_multiplier).astype(np.single)
        self.totalDamage.modded = self.totalDamage.base_modified * damage_multiplier

        for fire_mode_effect in self.fire_mode_effects:
            self.fire_mode_effects[fire_mode_effect].calc_modded_damage()

    def pull_trigger(self, enemy:Unit):
        multishot_roll = get_tier(self.multishot.modded)
        multishot = multishot_roll

        self.magazineSize.current -= self.ammoCost.modded
        # print(self.magazineSize.current)

        if self.trigger == "HELD":
            self.weapon.damagePerShot_m["multishot_multiplier"] = multishot_roll
            self.weapon.procChance_m["multishot_multiplier"] = multishot_roll
            multishot = <float>1

        for i in range(multishot):
            if self.trigger != "HELD":
                self.multishot_damage = <float>0 if i == 0 else <float>self.weapon.damagePerShot_m["multishot_damage"]

            fm_time = self.simulation.time + self.embedDelay.modded
            heapq.heappush(self.simulation.event_queue, (fm_time, self.simulation.consume_call_index(), EventTrigger(enemy.pellet_hit, name="Pellet hit", fire_mode=self, info_callback=enemy.get_last_crit_info, bodypart=self.target_bodypart)))

            for fme in self.fire_mode_effects.values():
                fme_time = fme.embedDelay.modded + fm_time + 1e-4
                for _ in range(get_tier(fme.multishot.modded)):
                    heapq.heappush(self.simulation.event_queue, (fme_time, self.simulation.consume_call_index(), EventTrigger(enemy.pellet_hit, name=f"{fme.name} hit", fire_mode=fme, info_callback=enemy.get_last_crit_info, bodypart=self.target_bodypart)))


        if self.magazineSize.current > 0:
            next_event = self.simulation.time + self.fireTime.modded + self.chargeTime.modded
        else:
            self.magazineSize.current = self.magazineSize.modded
            next_event = self.simulation.time + max(self.reloadTime.modded, self.fireTime.modded) + self.chargeTime.modded

        heapq.heappush(self.simulation.event_queue, (next_event, self.simulation.consume_call_index(), EventTrigger(self.pull_trigger, enemy=enemy)))

    def get_info(self):
        return dict(weapon=self.weapon.name, fire_mode=self.name)

def aid(x):
    # This function returns the memory
    # block address of an array.
    return x.__array_interface__['data'][0]

def get_tier(chance):
    return int(random()<(chance%1)) + int(chance)

class FireModeEffect(FireMode):
    def __init__(self, fire_mode:FireMode, name:str) -> None:
        self.fire_mode = fire_mode
        self.weapon = fire_mode.weapon
        self.name = name
        self.primary_effect = False
        self.data = fire_mode.data["secondaryEffects"][self.name]

        self.damagePerShot = DamageParameter( np.array(self.data.get("damagePerShot", np.array([0]*20, dtype=np.single)), dtype=np.single) )
        self.totalDamage = Parameter( self.data.get("totalDamage", sum(self.damagePerShot.base)) )

        self.criticalChance = Parameter( self.data.get("criticalChance", fire_mode.criticalChance.base) )
        self.criticalMultiplier = Parameter( self.data.get("criticalMultiplier", fire_mode.criticalMultiplier.base) )
        self.procChance = Parameter( self.data.get("procChance", fire_mode.procChance) )

        self.multishot = Parameter( self.data.get("multishot", <float>1) )
        self.embedDelay = Parameter( self.data.get("embedDelay", <float>0) )
        self.forcedProc = self.data.get("forcedProc", [])
        self.radial = self.data.get("radial", False)

        # self.fire_mode_effects:List[FireModeEffect] = []
        self.fire_mode_effects:dict = {}

    def __getattr__(self, attr):
        return getattr(self.fire_mode, attr)


class DamageParameter():
    def __init__(self, base: np.array) -> None:
        self.base = base.astype(np.single)
        self.base_modified = base.copy()
        self.base_total = <float>np.sum(self.base_modified)
        self.base_proportions = (self.base_modified/self.base_total).astype(np.single) if self.base_total > 0 else np.array([0]*20, dtype=np.single)
        self.proportions = self.base_proportions.copy()
        self.quantized = self.base_modified.copy()
        self.modded = self.base_modified.copy()

    def reset(self):
        self.base_modified = self.base
        self.base_total = <float>np.sum(self.base_modified)
        self.base_proportions = (self.base_modified/self.base_total).astype(np.single) if self.base_total > 0 else np.array([0]*20, dtype=np.single)
        self.proportions = self.base_proportions.copy()
        self.modded = self.base_modified.copy()
        self.quantized = self.base_modified.copy()

    def set_base_total(self, value):
        cdef float new_base_total = value
        if new_base_total == self.base_total:
            return
        
        self.base_modified = self.base_proportions * new_base_total
        self.base_total = new_base_total


class ModifyParameter():
    def __init__(self, base) -> None:
        self.base = <float>base
        self.modded = <float>base
        self.current = <float>base

    def reset(self):
        self.modded = self.base
        self.current = self.modded


class Parameter():
    def __init__(self, base) -> None:
        if isinstance(base, Parameter):
            self.base = <float>base.base
            self.base_modified = <float>base.base
            self.modded = <float>base.modded
        else:
            self.base = <float>base
            self.base_modified = <float>base
            self.modded = <float>base

    def reset(self):
        self.base_modified = self.base
        self.modded = self.base


class EventTrigger():
    def __init__(self, func, name="", info_callback=None, **kwargs) -> None:
        self.func = func 
        self.kwargs = kwargs # kwargs for func
        self.name = name
        self.info_callback = info_callback

def parse_text(text, combine_rule=const.COMBINE_ADD, parse_rule=const.BASE_RULE):
    if combine_rule == const.COMBINE_ADD:
        return sum([float(i) for i in re.findall(parse_rule, text)])
    elif combine_rule == const.COMBINE_MULTIPLY:
        str_list = re.findall(const.BASE_RULE, text)
        if len(str_list)>0:
            return np.prod(np.array([float(i) for i in str_list], dtype=np.single))
        else:
            return 1
    return None

def update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update(d.get(k, {}), v)
        else:
            d[k] = v
    return d