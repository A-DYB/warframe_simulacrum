from weapon import Weapon, FireMode, FireModeEffect, EventTrigger
from unit import Unit
from typing import List, Tuple
from queue import PriorityQueue
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import time

class Simulacrum:
    def __init__(self) -> None:
        self.event_queue:"PriorityQueue[Tuple[int, int, EventTrigger]]" = PriorityQueue()
        self.time = 0
        self.call_index = 0

    def reset(self):
        self.time = 0
        self.call_index = 0
        self.event_queue = PriorityQueue()

    def get_call_index(self):
        idx = self.call_index
        self.call_index += 1
        return idx
        
    def run_simulation(self, enemies:List[Unit], fire_mode:FireMode):
        stats = enemies[0].get_current_stats()
        stats['time'] = stats['time'] - 1e-6
        data = [stats]

        event_time = fire_mode.chargeTime.modded + fire_mode.embedDelay.modded
        self.event_queue.put((event_time, self.get_call_index(), EventTrigger(fire_mode, fire_mode.pull_trigger, event_time)))
        for enemy in enemies:
            while enemy.overguard.current_value > 0 or enemy.health.current_value > 0:
                self.time, _, event = self.event_queue.get()
                event.func(event.fire_mode, enemy)

                if stats_changed(data[-1], enemy):
                    data.append(enemy.get_current_stats())
                
                if self.time > 20 :
                    break

        df = pd.DataFrame(data)
        df_melt = pd.melt(df, id_vars=["time"], var_name="variable", value_name="value")

        stats = enemy.get_stats()
        names = [key for key,value in stats.items() if value > 0 ]
        dff = df_melt[(df_melt["variable"].isin(names))]

        # plot the data using seaborn
        sns.lineplot(data=dff, x="time", y="value", hue="variable", marker="x", estimator=None, errorbar=None, markeredgecolor='black', drawstyle='steps-post')
        plt.ylim(bottom=0)
        plt.show()

    def fast_run(self, enemies:List[Unit], fire_mode:FireMode):
        event_time = fire_mode.chargeTime.modded + fire_mode.embedDelay.modded
        self.event_queue.put((event_time, self.get_call_index(), EventTrigger(fire_mode, fire_mode.pull_trigger, event_time)))
        for enemy in enemies:
            while enemy.overguard.current_value > 0 or enemy.health.current_value > 0:
                self.time, _, event = self.event_queue.get()
                event.func(event.fire_mode, enemy)
                
                if self.time > 20 :
                    break
        # print(self.time)

def stats_changed(prev_data:dict, enemy:Unit):
    if prev_data["overguard"] == enemy.overguard.current_value and prev_data["shield"] == enemy.shield.current_value\
                        and prev_data["health"] == enemy.health.current_value and prev_data["armor"] == enemy.armor.current_value:
        return False
    return True

def run_reapeated(simulation:Simulacrum, enemy:Unit, weapon:Weapon, count=20):
    t1 = time.time()
    for _ in range(count):
        simulation.reset()
        enemy.reset()
        weapon.reset()

        simulation.fast_run([enemy], weapon.fire_modes[0])
    t2 = time.time()
    print(t2-t1)

def run_once(simulation:Simulacrum, enemy:Unit, weapon:Weapon):
    simulation.run_simulation([enemy], weapon.fire_modes[0])

simulation = Simulacrum()
enemy = Unit("Arid Lancer", 9000, simulation)
weapon = Weapon("Synapse", None, simulation)
# run_once(simulation, enemy, weapon)
run_reapeated(simulation, enemy, weapon)


# import pstats, cProfile
# profiler = cProfile.Profile()
# profiler.enable()
# # run_reapeated(simulation, enemy, weapon, count=1)
# simulation.fast_run( [enemy], weapon.fire_modes[0])
# profiler.disable()
# stats = pstats.Stats(profiler).sort_stats('tottime')
# stats.print_stats()