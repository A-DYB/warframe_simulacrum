from __future__ import annotations
from collections import deque
import numpy as np
import constants
from typing import List, TYPE_CHECKING

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

class ProcContainer:
    def __init__(self, enemy:Unit, index, manager: ContainerizedProcManager):
        self.manager = manager
        self.enemy = enemy
        self.simulation = enemy.simulation
        self.index = index
        self.next_event = constants.MAX_TIME_OFFSET
        self.total_damage = np.array([0]*20, dtype=float)
        self.proc_dq: deque[Proc] = deque([])
        self.count = 0

    def add_proc(self, proc: Proc):
        # If it is a new container, set the event time to first proc
        if self.count == 0:
            self.next_event = proc.next_event
            self.simulation.event_queue.put((self.next_event, self.simulation.get_call_index(), EventTrigger(proc.fire_mode, self.damage_event, self.next_event)))
            self.simulation.event_queue.put((proc.expiry, self.simulation.get_call_index(), EventTrigger(proc.fire_mode, self.expiry_event, proc.expiry)))
            if self.manager.count == 0:
                self.enemy.unique_proc_count += 1

        self.proc_dq.append(proc)
        self.total_damage += proc.damage
        self.count += 1

    def damage_event(self, fire_mode:FireMode, enemy:Unit):
        if self.count == 0:
            return
        
        app_dmg = self.enemy.apply_damage(fire_mode, self.total_damage, constants.DAMAGE_NONE, source='proc')
        self.manager.total_applied_damage += app_dmg

        self.next_event += 1
        self.simulation.event_queue.put((self.next_event, self.simulation.get_call_index(), EventTrigger(fire_mode, self.damage_event, self.next_event)))

    def expiry_event(self, fire_mode, enemy):
        if self.count>0 and self.simulation.time >= self.proc_dq[0].expiry:
            self.total_damage -= self.proc_dq[0].damage
            self.proc_dq.popleft()
            self.simulation.event_queue.put((self.proc_dq[0].expiry, self.simulation.get_call_index(), EventTrigger(self.proc_dq[0].fire_mode, self.expiry_event, self.proc_dq[0].expiry)))
            self.count -= 1
            self.manager.count -= 1
            if self.manager.count == 0:
                self.enemy.unique_proc_count -= 1

class DefaultProcManager():
    def __init__(self, enemy:Unit, proc_id:int, count_change_callback=None):
        self.enemy = enemy
        self.simulation = enemy.simulation
        self.proc_dq: deque[Proc] = deque([])
        self.next_event = constants.MAX_TIME_OFFSET
        self.proc_id = proc_id
        self.count_change_callback = count_change_callback
        self.count = 0

        self.max_stacks = constants.PROC_INFO[proc_id]['max_stacks']
        self.base_duration = constants.PROC_INFO[proc_id]['duration']

    def reset(self):
        self.next_event = constants.MAX_TIME_OFFSET
        self.proc_dq.clear()
        self.max_stacks = constants.PROC_INFO[self.proc_id]['max_stacks']
        self.count = 0

    def add_proc(self, fire_mode: FireMode, damage: np.array):
        duration = self.base_duration * (1 + fire_mode.statusDuration_m["base"])
        new_proc = Proc(self.enemy, fire_mode, duration, damage)
        delta = False

        if self.count == 0:
            self.next_event = new_proc.expiry
            self.simulation.event_queue.put((self.next_event, self.simulation.get_call_index(), EventTrigger(fire_mode, self.remove_expired_proc, self.next_event)))
            delta = True
            self.enemy.unique_proc_count += 1
        elif self.count == self.max_stacks:
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
    
    def remove_expired_proc(self, fire_mode, enemy):
        if self.count == 0:
            return
        
        if self.proc_dq[0].expiry <= self.simulation.time:
            self.proc_dq.popleft()
            self.count -= 1

            if self.count == 0:
                self.enemy.unique_proc_count -= 1
            
            if self.count > 0:
                self.next_event = self.proc_dq[0].expiry
                self.simulation.event_queue.put((self.next_event, self.simulation.get_call_index(), EventTrigger(fire_mode, self.remove_expired_proc, self.next_event)))

            if self.count_change_callback is not None:
                self.count_change_callback(self)


class ContainerizedProcManager:
    def __init__(self, enemy:Unit, proc_id:int):
        self.enemy = enemy
        self.simulation = enemy.simulation
        self.container_list: deque["ProcContainer"] = deque([ProcContainer(self.enemy, i, self) for i in range(10)])
        self.container_index: int = 0 # the next container to add to
        self.proc_id: str = proc_id
        self.base_duration = constants.PROC_INFO[proc_id]['duration']
        self.total_applied_damage: float = 0
        self.count = 0

    def reset(self):
        self.container_list = deque([ProcContainer(self.enemy, i, self) for i in range(10)])
        self.container_index = 0
        self.total_applied_damage = 0
        self.max_stacks = constants.PROC_INFO[self.proc_id]['max_stacks']
        self.count = 0

    def add_proc(self, fire_mode:FireMode, damage:np.array):
        duration = self.base_duration * (1 + fire_mode.statusDuration_m["base"])
        if self.proc_id == 2:
            damage = 0.35 * damage 
        elif self.proc_id == 6:
            damage = 0.5 * damage * (1 + fire_mode.toxin_m["base"])
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
        self.count += 1


class AOEProcManager:
    def __init__(self, enemy:Unit, proc_id: int):
        self.enemy = enemy
        self.simulation = enemy.simulation
        self.proc_id = proc_id

        self.max_stacks = constants.PROC_INFO[proc_id]['max_stacks']
        self.base_duration = constants.PROC_INFO[proc_id]['duration']

        self.proc_dq: deque[Proc]= deque([])
        self.init_time: int = constants.MAX_TIME_OFFSET
        self.next_tick_event: float = self.init_time
        self.total_damage: np.array = np.array([0]*20, dtype=float)
        
        self.total_applied_damage: float = 0
        self.count = 0

    def reset(self):
        self.total_applied_damage = 0
        self.proc_dq.clear()
        self.init_time = constants.MAX_TIME_OFFSET
        self.next_tick_event = constants.MAX_TIME_OFFSET
        self.total_damage *= 0
        self.max_stacks = constants.PROC_INFO[self.proc_id]['max_stacks']
        self.count = 0

    def add_proc(self, fire_mode:FireMode, damage: np.array):
        duration = self.base_duration * (1 + fire_mode.statusDuration_m["base"])

        if self.count == 0:
            self.init_time = self.simulation.time
            self.next_tick_event = self.init_time
            self.simulation.event_queue.put((self.next_tick_event, self.simulation.get_call_index(), EventTrigger(fire_mode, self.damage_event, self.next_tick_event)))

            expiry = self.simulation.time + duration
            self.simulation.event_queue.put((expiry, self.simulation.get_call_index(), EventTrigger(fire_mode, self.expiry_event, expiry)))
            self.enemy.unique_proc_count += 1
        elif self.count >= self.max_stacks:
            # remove oldest proc
            while self.count >= self.max_stacks:
                old_proc = self.proc_dq.popleft()
                self.total_damage -= old_proc.damage
                self.count -= 1

        if self.proc_id == 5: # can replace with index
            damage = 0.5 * damage * (1 + fire_mode.electric_m["base"])
        elif self.proc_id == 9:
            damage = 0.5 * damage
        else:
            damage = damage

        new_proc = Proc(self.enemy, fire_mode, duration, damage)
        self.total_damage += new_proc.damage
        self.proc_dq.append(new_proc)
        self.count += 1

    def damage_event(self, fire_mode, enemy):
        self.expiry_event(fire_mode, enemy)
        if self.count == 0:
            return
        
        applied_dmg = self.enemy.apply_damage(fire_mode, self.total_damage, constants.DAMAGE_NONE, source='elec proc')
        self.total_applied_damage += applied_dmg
        self.next_tick_event += 1
        # always put on event queue because even if expiry is imminent, another refresher proc can happen before then
        self.simulation.event_queue.put((self.next_tick_event, self.simulation.get_call_index(), EventTrigger(fire_mode, self.damage_event, self.next_tick_event)))

    def expiry_event(self, fire_mode, enemy):
        if self.count == 0:
            return
        
        if self.proc_dq[0].expiry <= self.simulation.time:
            old_proc = self.proc_dq.popleft()
            self.total_damage -= old_proc.damage
            self.count -= 1

            if self.count == 0:
                self.enemy.unique_proc_count -= 1

            if self.count > 0:
                self.simulation.event_queue.put((self.proc_dq[0].expiry, self.simulation.get_call_index(), EventTrigger(fire_mode, self.expiry_event, self.proc_dq[0].expiry)))

    
class HeatProcManager:
    def __init__(self, enemy:Unit, proc_id:int):
        self.proc_dq: deque[Proc] = deque([])
        self.proc_id = proc_id
        self.total_applied_damage = 0
        self.max_stacks = constants.PROC_INFO[proc_id]['max_stacks']
        self.base_duration = constants.PROC_INFO[proc_id]['duration']
        self.base_armor_strip_delay = 0.5
        self.base_armor_regen_delay = 1.5
        self.strip_index = 0

        self.init_time = constants.MAX_TIME_OFFSET
        self.next_tick_event = constants.MAX_TIME_OFFSET
        self.expiry = 0

        self.total_damage = np.array([0]*20, dtype=float)
        self.count = 0

        self.enemy = enemy
        self.simulation = enemy.simulation

    def reset(self):
        # do not reset strip index
        self.proc_dq.clear()
        self.total_applied_damage = 0

        self.init_time = constants.MAX_TIME_OFFSET
        self.next_tick_event = self.init_time + 1
        self.expiry = 0
        self.strip_index = 0

        self.max_stacks = constants.PROC_INFO[self.proc_id]['max_stacks']
        
        self.total_damage *= 0
        self.count = 0

    def clear_proc(self):
        # do not reset strip index
        self.proc_dq.clear()

        self.init_time = constants.MAX_TIME_OFFSET
        self.next_tick_event = constants.MAX_TIME_OFFSET
        self.expiry = 0
        self.total_damage *= 0

    def add_proc(self, fire_mode:FireMode, damage: np.array):
        if self.count == 0:
            self.init_time = self.simulation.time
            self.next_tick_event = self.init_time + 1
            
            duration = self.base_duration * (1 + fire_mode.statusDuration_m["base"])
            expiry = self.simulation.time + duration
            damage = 0.5 * damage * (1 + fire_mode.heat_m["base"])

            armor_strip_delay = self.base_armor_strip_delay * (1 + fire_mode.statusDuration_m["base"])
            # schedule heat strip
            self.simulation.event_queue.put((self.simulation.time + armor_strip_delay, self.simulation.get_call_index(), EventTrigger(fire_mode, self.armor_strip_event, self.simulation.time + armor_strip_delay)))
            self.simulation.event_queue.put((self.next_tick_event, self.simulation.get_call_index(), EventTrigger(fire_mode, self.damage_event, self.next_tick_event)))
            self.simulation.event_queue.put((expiry, self.simulation.get_call_index(), EventTrigger(fire_mode, self.expiry_event, expiry)))
            self.enemy.unique_proc_count += 1
        else:
            damage = 0.5 * damage * (1 + self.proc_dq[0].fire_mode.heat_m["base"])
            duration = self.base_duration * (1 + self.proc_dq[0].fire_mode.statusDuration_m["base"])
    
        new_proc = Proc(self.enemy, fire_mode, duration, damage)
        self.expiry = new_proc.expiry

        self.total_damage += new_proc.damage
        self.proc_dq.append(new_proc)
        self.count += 1


    def damage_event(self, fire_mode, enemy):
        if self.count == 0:
            return 
        applied_dmg = self.enemy.apply_damage(self.proc_dq[0].fire_mode, self.total_damage, constants.DAMAGE_NONE, source='proc')
        self.total_applied_damage += applied_dmg
        self.next_tick_event += 1
        # always put on event queue because even if expiry is imminent, another refresher proc can happen before then
        self.simulation.event_queue.put((self.next_tick_event, self.simulation.get_call_index(), EventTrigger(fire_mode, self.damage_event, self.next_tick_event)))

    def expiry_event(self, fire_mode, enemy):
        if self.count == 0:
            return
        
        if self.expiry <= self.simulation.time:
            armor_regen_delay = self.base_armor_regen_delay * (1 + self.proc_dq[0].fire_mode.statusDuration_m["base"])
            # before reset, pass the fire_mode from the original proc so the status duration is preserved
            self.simulation.event_queue.put((self.simulation.time + armor_regen_delay, self.simulation.get_call_index(), EventTrigger(self.proc_dq[0].fire_mode, self.armor_regen_event, self.simulation.time + armor_regen_delay)))
            self.count = 0
            self.clear_proc()
            self.enemy.unique_proc_count -= 1
        else:
            self.simulation.event_queue.put((self.expiry, self.simulation.get_call_index(), EventTrigger(fire_mode, self.expiry_event, self.expiry)))  

    def armor_strip_event(self, fire_mode: FireMode, enemy:Unit):
        self.strip_index += 1
        if self.strip_index > 4:
            self.strip_index = 4
            return 
        
        strip_value = constants.HEAT_ARMOR_STRIP[self.strip_index]
        enemy.armor.apply_affliction("Heat armor strip", strip_value)

        if self.strip_index < 4:
            armor_strip_delay = self.base_armor_strip_delay * (1 + self.proc_dq[0].fire_mode.statusDuration_m["base"])
            self.simulation.event_queue.put((self.simulation.time + armor_strip_delay, self.simulation.get_call_index(), EventTrigger(fire_mode, self.armor_strip_event, self.simulation.time + armor_strip_delay)))

    def armor_regen_event(self, fire_mode: FireMode, enemy:Unit):
        # if another proc happens, return
        if self.count > 0:
            return
        
        self.strip_index -= 1
        if self.strip_index < 0:
            self.strip_index = 0
            return 
        
        strip_value = constants.HEAT_ARMOR_STRIP[self.strip_index]
        enemy.armor.apply_affliction("Heat armor strip", strip_value)
        if self.strip_index > 0:
            armor_regen_delay = self.base_armor_regen_delay * (1 + fire_mode.statusDuration_m["base"])
            self.simulation.event_queue.put((self.simulation.time + armor_regen_delay, self.simulation.get_call_index(), EventTrigger(fire_mode, self.armor_regen_event, self.simulation.time + armor_regen_delay)))
