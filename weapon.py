from __future__ import annotations

import numpy as np
import os 
from pathlib import Path
import json
import re
import constants

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

        self.damagePerShot = Parameter( np.array(self.data.get("damagePerShot", np.array([0]*20)), dtype=float) )
        self.elementalDamagePerShot = np.array([0]*20, dtype=float) # physical and elemental modded damage - this is separate because of complications with quantization and status damage
        self.totalQuantizedDamagePerShot = np.array([0]*20, dtype=float)
        self.criticalChance = Parameter( self.data.get("criticalChance", 0) )
        self.criticalMultiplier = Parameter( self.data.get("criticalMultiplier", 1) )
        self.criticalMultiplier.base = round(self.criticalMultiplier.base * (128 - 1/32), 0) / (128 - 1/32) # quantization happens on the base value, not the modded value
        self.procChance = Parameter( self.data.get("procChance", 0) )
        self.procProbabilities = np.array([0]*20)
        self.procCumulativeProbabilities = np.array([0]*20)


        self.magazineSize = Parameter( self.data.get("magazineSize", 100) )
        self.fireRate = Parameter( self.data.get("fireRate", 5) )
        self.reloadTime = Parameter( self.data.get("reloadTime", 1) )
        self.multishot = Parameter( self.data.get("multishot", 1) )
        self.ammoCost = Parameter( self.data.get("ammoCost", 1) )
        self.chargeTime = Parameter( self.data.get("chargeTime", 0) )
        self.embedDelay = Parameter( self.data.get("embedDelay", 0) )

        self.forcedProc = self.data.get("forcedProc", []) # indices corresponding to proc that will be forced

        self.radial = False

        # mods
        self.damagePerShot_m = {"base":0, "condition_overload_base":0, "condition_overload_multiplier":0, "direct":0, "final_multiplier":1, "multishot_multiplier":1}
        self.bonusDamagePerShot_m = {"additive_base":0}
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

        self.load_mods()

        self.refresh = True

    def reset(self):
        self.attack_index = 1

        self.damagePerShot.reset()
        self.elementalDamagePerShot = np.array([0]*20, dtype=float)
        self.totalQuantizedDamagePerShot = np.array([0]*20, dtype=float)
        self.criticalChance.reset()
        self.criticalMultiplier.reset()
        self.procChance.reset()
        self.magazineSize.reset()
        self.fireRate.reset()
        self.reloadTime.reset()
        self.multishot.reset()
        self.ammoCost.reset()
        self.chargeTime.reset()
        self.embedDelay.reset()

    def load_mods(self):
        self.damagePerShot_m["base"] = 0
        self.damagePerShot_m["final_multiplier"] = 1

    

    def pull_trigger(self, fire_mode, enemy:Unit):
        # add secondary effect to event queue and update its next event timestamp

        multishot_roll = get_tier(self.multishot.modded)
        multishot = multishot_roll

        self.magazineSize.current -= self.ammoCost.modded

        if self.trigger == "HELD":
            self.damagePerShot_m["multishot_multiplier"] = multishot_roll
            self.procChance_m["multishot_multiplier"] = multishot_roll
            multishot = 1

        for _ in range(multishot):
            fm_time = self.simulation.time + self.embedDelay.modded
            self.simulation.event_queue.put((fm_time, self.simulation.get_call_index(), EventTrigger(self, enemy.pellet_hit, fm_time)))

            for fme in self.fire_mode_effects:
                fme_time = fme.embedDelay + fm_time
                self.simulation.event_queue.put((fme_time, self.simulation.get_call_index(), EventTrigger(fme, enemy.pellet_hit, fme_time)))


        if self.magazineSize.current > 0:
            next_event = self.simulation.time + 1/self.fireRate.modded + self.chargeTime.modded
        # reload
        else:
            self.magazineSize.current = self.magazineSize.modded
            next_event = self.simulation.time + max(self.reloadTime.modded, 1/self.fireRate.modded) + self.chargeTime.modded

        self.simulation.event_queue.put((next_event, self.simulation.get_call_index(), EventTrigger(fire_mode, self.pull_trigger, next_event)))

def get_tier(chance):
    return int(random()<(chance%1)) + int(chance)

class FireModeEffect():
    def __init__(self, fire_mode:FireMode, name:str) -> None:
        self.fire_mode = fire_mode
        self.weapon = fire_mode.weapon
        self.name = name
        self.next_event_timestamp = constants.MAX_TIME_OFFSET
        self.data = fire_mode.data["secondaryEffects"][self.name]

        self.damagePerShot = np.array(self.data.get("damagePerShot", fire_mode.damagePerShot))
        self.criticalChance = self.data.get("criticalChance", fire_mode.criticalChance)
        self.criticalMultiplier = self.data.get("criticalMultiplier", fire_mode.criticalMultiplier)
        self.procChance = self.data.get("procChance", fire_mode.procChance)

        self.multishot = self.data.get("multishot", 1)
        self.embedDelay = self.data.get("embedDelay", 0)
        self.forcedProc = self.data.get("forcedProc", [])

class Parameter():
    def __init__(self, base) -> None:
        self.base = base
        self.modded = base
        self.current = self.modded

    def reset(self):
        self.modded = self.base
        self.current = self.modded

class EventTrigger():
    def __init__(self, fire_mode:[FireModeEffect, FireMode], func, time:int) -> None:
        self.fire_mode = fire_mode
        self.func = func # should accept FireMode and Unit as arguments
        self.time = time   

def parse_text(text, combine_rule=constants.COMBINE_ADD, parse_rule=constants.BASE_RULE):
    if combine_rule == constants.COMBINE_ADD:
        return sum([float(i) for i in re.findall(parse_rule, text)])
    elif combine_rule == constants.COMBINE_MULTIPLY:
        str_list = re.findall(constants.BASE_RULE, text)
        if len(str_list)>0:
            return np.prod(np.array([float(i) for i in str_list]))
        else:
            return 1
    return None