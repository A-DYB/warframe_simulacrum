from __future__ import annotations
from collections import deque
import numpy as np
import constants as const
from typing import List, TYPE_CHECKING
import heapq

from weapon import EventTrigger, FireMode
if TYPE_CHECKING:
    from unit import Unit

class Proc:
    def __init__(self, enemy: Unit, fire_mode: FireMode, duration: int, damage: float):
        self.fire_mode = fire_mode
        self.enemy = enemy
        self.simulation = self.enemy.simulation
        self.duration = duration
        self.damage = damage

        self.expiry = self.simulation.time + self.duration
        self.expired = False
        self.executed_count = 0
        self.ticks = int(self.duration)
        
        self.offset = self.simulation.time
        self.next_event = self.offset + 1

class DefaultProcManager():
    def __init__(self, enemy:Unit, proc_id:int, count_change_callback=None):
        self.enemy = enemy
        self.simulation = enemy.simulation
        self.proc_dq: deque[Proc] = deque([])
        self.next_event = const.MAX_TIME_OFFSET
        self.proc_id = proc_id
        self.count_change_callback = count_change_callback
        self.count = 0

        self.max_stacks = const.PROC_INFO[proc_id]['max_stacks']
        self.base_duration = const.PROC_INFO[proc_id]['duration']

    def reset(self):
        self.next_event = const.MAX_TIME_OFFSET
        self.proc_dq.clear()
        self.max_stacks = const.PROC_INFO[self.proc_id]['max_stacks']
        self.count = 0

    def add_proc(self, fire_mode: FireMode, damage: float):
        duration = self.base_duration * (1 + fire_mode.statusDuration_m["base"].value)
        new_proc = Proc(self.enemy, fire_mode, duration, damage)
        delta = True

        if self.count == 0:
            self.next_event = new_proc.expiry
            heapq.heappush(self.simulation.event_queue, (self.next_event, self.simulation.get_call_index(), EventTrigger(self.remove_expired_proc)))
            self.enemy.unique_proc_count += 1
        elif self.count == self.max_stacks:
            delta = False
            self.proc_dq.popleft()
            self.count -= 1
            if self.count > 0:
                self.next_event = self.proc_dq[0].expiry
            else:
                self.next_event = new_proc.expiry

        self.proc_dq.append(new_proc)
        self.count += 1


        if self.count_change_callback is not None and delta:
            self.count_change_callback(self)
    
    def remove_expired_proc(self):
        if self.count == 0:
            return
        
        if self.proc_dq[0].expiry <= self.simulation.time:
            self.proc_dq.popleft()
            self.count -= 1

            if self.count == 0:
                self.enemy.unique_proc_count -= 1
            
            if self.count > 0:
                self.next_event = self.proc_dq[0].expiry
                heapq.heappush(self.simulation.event_queue, (self.next_event, self.simulation.get_call_index(), EventTrigger(self.remove_expired_proc)))

            if self.count_change_callback is not None:
                self.count_change_callback(self)

class ProcContainer:
    def __init__(self, enemy:Unit, index, manager: ContainerizedProcManager):
        self.manager = manager
        self.enemy = enemy
        self.simulation = enemy.simulation
        self.index = index
        self.next_event = const.MAX_TIME_OFFSET
        self.total_damage = np.array([0]*20, dtype=float)
        self.proc_dq: deque[Proc] = deque([])
        self.count = 0

    def add_proc(self, proc: Proc):
        # If it is a new container, set the event time to first proc
        if self.count == 0:
            # self.total_damage[const.PROCID_DAMAGETYPE[self.manager.proc_id]] = 1
            self.next_event = proc.next_event
            heapq.heappush(self.simulation.event_queue, (self.next_event, self.simulation.get_call_index(), EventTrigger(self.damage_event, name=f"{const.PROC_INFO[self.manager.proc_id]['name']} proc", info_callback=self.get_damage_info, fire_mode=proc.fire_mode)))
            heapq.heappush(self.simulation.event_queue, (proc.expiry, self.simulation.get_call_index(), EventTrigger(self.expiry_event)))
            if self.manager.count == 0:
                self.enemy.unique_proc_count += 1

        self.proc_dq.append(proc)
        self.total_damage[const.PROCID_DAMAGETYPE[self.manager.proc_id]] += proc.damage
        self.count += 1
        self.manager.count += 1

    def damage_event(self, fire_mode:FireMode):
        if self.count == 0:
            return
        
        app_dmg = self.enemy.apply_damage(fire_mode, self.total_damage, bodypart='body')
        self.manager.total_applied_damage += app_dmg

        self.next_event += 1
        heapq.heappush(self.simulation.event_queue, (self.next_event, self.simulation.get_call_index(), EventTrigger(self.damage_event, name=f"{const.PROC_INFO[self.manager.proc_id]['name']} proc", info_callback=self.get_damage_info, fire_mode=fire_mode)))

    def expiry_event(self):
        if self.count>0 and self.simulation.time >= self.proc_dq[0].expiry:
            self.total_damage[const.PROCID_DAMAGETYPE[self.manager.proc_id]] -= self.proc_dq[0].damage
            self.proc_dq.popleft()
            self.count -= 1
            self.manager.count -= 1
            if self.manager.count == 0:
                self.enemy.unique_proc_count -= 1

            if self.count == 0:
                return
            heapq.heappush(self.simulation.event_queue, (self.proc_dq[0].expiry, self.simulation.get_call_index(), EventTrigger(self.expiry_event)))
    
    def get_damage_info(self):
        return f"bin count={self.count}"
            

class ContainerizedProcManager:
    def __init__(self, enemy:Unit, proc_id:int):
        self.enemy = enemy
        self.simulation = enemy.simulation
        self.container_list: deque["ProcContainer"] = deque([ProcContainer(self.enemy, i, self) for i in range(10)])
        self.container_index: int = 0 # the next container to add to
        self.proc_id: str = proc_id
        self.base_duration = const.PROC_INFO[proc_id]['duration']
        self.total_applied_damage: float = 0
        self.count = 0

    def reset(self):
        self.container_list = deque([ProcContainer(self.enemy, i, self) for i in range(10)])
        self.container_index = 0
        self.total_applied_damage = 0
        self.max_stacks = const.PROC_INFO[self.proc_id]['max_stacks']
        self.count = 0

    def add_proc(self, fire_mode:FireMode, damage:float):
        duration = self.base_duration * (1 + fire_mode.statusDuration_m["base"].value)
        if self.proc_id == const.DT_INDEX["DT_SLASH"]:
            damage = 0.35 * damage 
        elif self.proc_id == const.DT_INDEX["DT_TOXIN"]:
            damage = 0.5 * damage  * (1 + fire_mode.toxin_m["base"].value)
        else:
            damage = damage 
        
        new_proc = Proc(self.enemy, fire_mode, duration, damage)

        # If multiple procs happen at the same time, add them to the same container
        previous_container = self.container_list[(self.container_index-1) % 10]
        if len(previous_container.proc_dq) > 0 and previous_container.proc_dq[-1].offset == self.simulation.time:
            # add it to same container as last proc
            previous_container.add_proc(new_proc)
        else:
            # add to next container and increment container index
            self.container_list[self.container_index].add_proc(new_proc)
            self.container_index = (self.container_index + 1) % 10


class AOEProcManager:
    def __init__(self, enemy:Unit, proc_id: int):
        self.enemy = enemy
        self.simulation = enemy.simulation
        self.proc_id = proc_id

        self.max_stacks = const.PROC_INFO[proc_id]['max_stacks']
        self.base_duration = const.PROC_INFO[proc_id]['duration']

        self.proc_dq: deque[Proc]= deque([])
        self.init_time: int = const.MAX_TIME_OFFSET
        self.next_tick_event: float = self.init_time
        self.total_damage: np.array = np.array([0]*20, dtype=float)
        
        self.total_applied_damage: float = 0
        self.count = 0

    def reset(self):
        self.total_applied_damage = 0
        self.proc_dq.clear()
        self.init_time = const.MAX_TIME_OFFSET
        self.next_tick_event = const.MAX_TIME_OFFSET
        self.total_damage *= 0
        self.max_stacks = const.PROC_INFO[self.proc_id]['max_stacks']
        self.count = 0

    def add_proc(self, fire_mode:FireMode, damage: float):
        duration = self.base_duration * (1 + fire_mode.statusDuration_m["base"].value)
        min_dmg = 0
        if self.count == 0:
            min_dmg = 0
            self.init_time = self.simulation.time
            self.next_tick_event = self.init_time
            heapq.heappush(self.simulation.event_queue, (self.next_tick_event, self.simulation.get_call_index(), EventTrigger(self.damage_event, name=f"{const.PROC_INFO[self.proc_id]['name']} proc", info_callback=self.get_damage_info, fire_mode=fire_mode)))

            expiry = self.simulation.time + duration
            heapq.heappush(self.simulation.event_queue, (expiry, self.simulation.get_call_index(), EventTrigger(self.expiry_event)))
            self.enemy.unique_proc_count += 1
        elif self.count >= self.max_stacks:
            # remove oldest proc
            while self.count >= self.max_stacks:
                old_proc = self.proc_dq.popleft()
                self.total_damage[const.PROCID_DAMAGETYPE[self.proc_id]] -= old_proc.damage
                self.count -= 1

        if self.proc_id == const.DT_INDEX["DT_ELECTRIC"]:
            damage = min_dmg + 0.5 * damage  * (1 + fire_mode.electric_m["base"].value)
        elif self.proc_id == const.DT_INDEX["DT_GAS"]:
            damage = min_dmg + 0.5 * damage 
        else:
            damage = min_dmg + damage 

        new_proc = Proc(self.enemy, fire_mode, duration, damage)
        self.total_damage[const.PROCID_DAMAGETYPE[self.proc_id]] += new_proc.damage
        self.proc_dq.append(new_proc)
        self.count += 1

    def damage_event(self, fire_mode):
        self.expiry_event()
        if self.count == 0:
            return
        
        applied_dmg = self.enemy.apply_damage(fire_mode, self.total_damage, bodypart='body')
        self.total_applied_damage += applied_dmg
        self.next_tick_event += 1
        # always put on event queue because even if expiry is imminent, another refresher proc can happen before then
        heapq.heappush(self.simulation.event_queue, (self.next_tick_event, self.simulation.get_call_index(), EventTrigger(self.damage_event, name=f"{const.PROC_INFO[self.proc_id]['name']} proc", info_callback=self.get_damage_info, fire_mode=fire_mode)))

    def expiry_event(self):
        if self.count == 0:
            return
        
        if self.proc_dq[0].expiry <= self.simulation.time:
            old_proc = self.proc_dq.popleft()
            self.total_damage[const.PROCID_DAMAGETYPE[self.proc_id]] -= old_proc.damage
            self.count -= 1

            if self.count == 0:
                self.enemy.unique_proc_count -= 1

            if self.count > 0:
                heapq.heappush(self.simulation.event_queue, (self.proc_dq[0].expiry, self.simulation.get_call_index(), EventTrigger(self.expiry_event)))
    
    def get_damage_info(self):
        return f"count={self.count}"

    
class HeatProcManager:
    def __init__(self, enemy:Unit, proc_id:int):
        self.proc_dq: deque[Proc] = deque([])
        self.proc_id = proc_id
        self.total_applied_damage = 0
        self.max_stacks = const.PROC_INFO[proc_id]['max_stacks']
        self.base_duration = const.PROC_INFO[proc_id]['duration']
        self.base_armor_strip_delay = 0.5
        self.base_armor_regen_delay = 1.5
        self.strip_index = 0

        self.init_time = const.MAX_TIME_OFFSET
        self.next_tick_event = const.MAX_TIME_OFFSET
        self.expiry = 0

        self.total_damage = np.array([0]*20, dtype=float)
        self.count = 0

        self.enemy = enemy
        self.simulation = enemy.simulation

    def reset(self):
        # do not reset strip index
        self.proc_dq.clear()
        self.total_applied_damage = 0

        self.init_time = const.MAX_TIME_OFFSET
        self.next_tick_event = self.init_time + 1
        self.expiry = 0
        self.strip_index = 0

        self.max_stacks = const.PROC_INFO[self.proc_id]['max_stacks']
        
        self.total_damage *= 0
        self.count = 0

    def clear_proc(self):
        # do not reset strip index
        self.proc_dq.clear()

        self.init_time = const.MAX_TIME_OFFSET
        self.next_tick_event = const.MAX_TIME_OFFSET
        self.expiry = 0
        self.total_damage *= 0

    def add_proc(self, fire_mode:FireMode, damage: np.array):
        if self.count == 0:
            self.init_time = self.simulation.time
            self.next_tick_event = self.init_time + 1
            
            duration = self.base_duration * (1 + fire_mode.statusDuration_m["base"].value)
            expiry = self.simulation.time + duration
            damage = 1 + 0.5 * damage  * (1 + fire_mode.heat_m["base"].value)

            armor_strip_delay = self.base_armor_strip_delay * (1 + fire_mode.statusDuration_m["base"].value)
            # schedule heat strip
            heapq.heappush(self.simulation.event_queue, (self.simulation.time + armor_strip_delay, self.simulation.get_call_index(), EventTrigger(self.armor_strip_event, fire_mode=fire_mode)))
            heapq.heappush(self.simulation.event_queue, (self.next_tick_event, self.simulation.get_call_index(), EventTrigger(self.damage_event, name=f"{const.PROC_INFO[self.proc_id]['name']} proc", info_callback=self.get_damage_info, fire_mode=fire_mode)))
            heapq.heappush(self.simulation.event_queue, (expiry, self.simulation.get_call_index(), EventTrigger(self.expiry_event, fire_mode=fire_mode)))
            self.enemy.unique_proc_count += 1
        else:
            damage = 0.5 * damage * (1 + self.proc_dq[0].fire_mode.heat_m["base"].value)
            duration = self.base_duration * (1 + self.proc_dq[0].fire_mode.statusDuration_m["base"].value)
    
        new_proc = Proc(self.enemy, fire_mode, duration, damage)
        self.expiry = new_proc.expiry

        self.total_damage[const.PROCID_DAMAGETYPE[self.proc_id]] += new_proc.damage
        self.proc_dq.append(new_proc)
        self.count += 1


    def damage_event(self, fire_mode):
        if self.count == 0:
            return 
        applied_dmg = self.enemy.apply_damage(self.proc_dq[0].fire_mode, self.total_damage, bodypart='body')
        self.total_applied_damage += applied_dmg
        self.next_tick_event += 1
        # always put on event queue because even if expiry is imminent, another refresher proc can happen before then
        heapq.heappush(self.simulation.event_queue, (self.next_tick_event, self.simulation.get_call_index(), EventTrigger(self.damage_event, name=f"{const.PROC_INFO[self.proc_id]['name']} proc", info_callback=self.get_damage_info, fire_mode=fire_mode)))

    def expiry_event(self, fire_mode):
        if self.count == 0:
            return
        
        if self.expiry <= self.simulation.time:
            armor_regen_delay = self.base_armor_regen_delay * (1 + self.proc_dq[0].fire_mode.statusDuration_m["base"].value)
            # before reset, pass the fire_mode from the original proc so the status duration is preserved
            heapq.heappush(self.simulation.event_queue, (self.simulation.time + armor_regen_delay, self.simulation.get_call_index(), EventTrigger(self.armor_regen_event, fire_mode=fire_mode)))
            self.count = 0
            self.clear_proc()
            self.enemy.unique_proc_count -= 1
        else:
            heapq.heappush(self.simulation.event_queue, (self.expiry, self.simulation.get_call_index(), EventTrigger(self.expiry_event, fire_mode=fire_mode)))  

    def armor_strip_event(self, fire_mode: FireMode):
        self.strip_index += 1
        if self.strip_index > 4:
            self.strip_index = 4
            return 
        
        strip_value = const.HEAT_ARMOR_STRIP[self.strip_index]
        self.enemy.armor.apply_affliction("Heat armor strip", strip_value)

        if self.strip_index < 4:
            armor_strip_delay = self.base_armor_strip_delay * (1 + self.proc_dq[0].fire_mode.statusDuration_m["base"].value)
            heapq.heappush(self.simulation.event_queue, (self.simulation.time + armor_strip_delay, self.simulation.get_call_index(), EventTrigger(self.armor_strip_event, fire_mode=fire_mode)))

    def armor_regen_event(self, fire_mode: FireMode):
        if self.count > 0:
            return
        
        self.strip_index -= 1
        if self.strip_index < 0:
            self.strip_index = 0
            return 
        
        strip_value = const.HEAT_ARMOR_STRIP[self.strip_index]
        self.enemy.armor.apply_affliction("Heat armor strip", strip_value)
        if self.strip_index > 0:
            armor_regen_delay = self.base_armor_regen_delay * (1 + fire_mode.statusDuration_m["base"].value)
            heapq.heappush(self.simulation.event_queue, (self.simulation.time + armor_regen_delay, self.simulation.get_call_index(), EventTrigger(self.armor_regen_event, fire_mode=fire_mode)))

    def get_damage_info(self):
        return f"count={self.count}"
