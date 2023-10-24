from weapon import Weapon, FireMode, FireModeEffect, EventTrigger
from unit import Unit
from typing import List, Tuple
from queue import PriorityQueue
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import time
import heapq
import numpy as np

class Simulacrum:
    def __init__(self) -> None:
        self.event_queue:"heapq[Tuple[int, int, EventTrigger]]" = []
        self.time = 0
        self.call_index = 0
        self.plot_text = None
        self.fig = None
        self.ax = None

    def reset(self):
        self.time = 0
        self.call_index = 0
        self.event_queue = []

    def get_call_index(self):
        idx = self.call_index
        self.call_index += 1
        return idx
        
    def run_simulation(self, enemies:List[Unit], fire_mode:FireMode):
        stats = enemies[0].get_current_stats()
        stats['time'] = stats['time'] - 1e-6
        stats['name'] = ""
        data = [stats]

        event_time = fire_mode.chargeTime.modded + fire_mode.embedDelay.modded
        heapq.heappush(self.event_queue, (event_time, self.get_call_index(), EventTrigger(fire_mode, fire_mode.pull_trigger, event_time)))
        for enemy in enemies:
            while enemy.overguard.current_value > 0 or enemy.health.current_value > 0:
                self.time, _, event = heapq.heappop(self.event_queue)
                event.func(event.fire_mode, enemy)

                if stats_changed(data[-1], enemy):
                    sts = enemy.get_current_stats()
                    sts["name"] = event.name
                    if event.info_callback is not None:
                        sts["name"] += f", {event.info_callback()}"
                    data.append(sts)
                
                if self.time > 20 :
                    break

        df = pd.DataFrame(data)
        df_melt = pd.melt(df, id_vars=["time", "call_index", "name"], var_name="variable", value_name="value")

        stats = enemy.get_stats()
        names = [key for key,value in stats.items() if value > 0 ]
        dff = df_melt[(df_melt["variable"].isin(names))].copy()

        self.fig, self.ax = plt.subplots()
        cid1 = self.fig.canvas.mpl_connect('button_press_event', lambda event: self.onclick(event, dff))
        # cid12 = self.fig.canvas.mpl_connect('button_release_event', self.offclick) 

        # plot the data using seaborn
        sns.lineplot(data=dff, x="time", y="value", hue="variable", marker="x", estimator=None, errorbar=None, markeredgecolor='black', drawstyle='steps-post', ax=self.ax)
        plt.ylim(bottom=0)
        plt.show()
        
    def onclick(self, event, df:pd.DataFrame):
        # display_str = ''
        if self.plot_text is not None:
            self.plot_text.remove()
            self.plot_text = None
        
        if event.xdata is None or event.ydata is None:
            self.fig.canvas.draw()
            return

        x, y = (event.xdata, event.ydata)
        df["time_"] = abs(df["time"] - x)
        df["value_"] = abs(df["value"] - y)
        df["dist_"] = np.sqrt(df["time_"]**2 + df["value_"]**2)
        df1 = df[(df['dist_'] == df['dist_'].min())]
        t = df1['time'].iloc[0]
        vb = df1['variable'].iloc[0]
        v = df1['value'].iloc[0]
        ci = df1['call_index'].iloc[0]
        name = df1['name'].iloc[0]
        
        df2 = df[(df["call_index"] < ci) & (df["variable"] == vb)]
        if len(df2.index) == 0 :
            delta = 0
            tdelta = 1
        else:
            s2 = df2.iloc[-1]
            delta = s2['value'] - v
            tdelta = t - s2['time']


        txt = f"t={t:.1f}s, {vb}={v:.1f}\ndelta={(delta):.2f}\n{name}"
        left,right = self.ax.get_xlim()
        span = right-left
        if t > left+span/2:
            text_xoffset = (t-left)*(-0.25)
            text_yoffset = -delta/2
            ha = 'right'
            va='top'
        else:
            text_xoffset = (right-t)*(0.25)
            text_yoffset = delta/2
            ha = 'left'
            va='bottom'

        # text_xoffset=(right-left)*0.25

        self.plot_text = self.ax.annotate(txt,
                            xy=(t,v), xycoords='data',
                            xytext=(t+text_xoffset, v+text_yoffset), textcoords='data',
                            arrowprops=dict(arrowstyle="->", connectionstyle="arc3"),
                            ha=ha, va=va)
        
        # self.plot_text = plt.text(t, v, txt, fontsize=8)
        # self.plot_text.set_bbox(dict(facecolor='white', alpha=0.7, edgecolor='black'))
        self.fig.canvas.draw()

    def offclick(self, event):
        self.fig.canvas.draw()

    def fast_run(self, enemies:List[Unit], fire_mode:FireMode):
        event_time = fire_mode.chargeTime.modded + fire_mode.embedDelay.modded
        heapq.heappush(self.event_queue, (event_time, self.get_call_index(), EventTrigger(fire_mode, fire_mode.pull_trigger, event_time)))

        for enemy in enemies:
            while enemy.overguard.current_value > 0 or enemy.health.current_value > 0:
                self.time, _, event = heapq.heappop(self.event_queue)
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
    # t1 = time.time()
    for _ in range(count):
        simulation.reset()
        enemy.reset()
        weapon.reset()

        simulation.fast_run([enemy], weapon.fire_modes[0])
    # t2 = time.time()
    # print(t2-t1)

def run_once(simulation:Simulacrum, enemy:Unit, weapon:Weapon):
    simulation.run_simulation([enemy], weapon.fire_modes[0])

simulation = Simulacrum()
# enemy = Unit("Arid Lancer", 9999, simulation)
enemy = Unit("Charger Eximus", 50, simulation)
# weapon = Weapon("Synapse", None, simulation)
# weapon = Weapon("Lex", None, simulation)
# weapon = Weapon("Vaykor Marelok", None, simulation)
weapon = Weapon("Hystrix", None, simulation)
# weapon = Weapon("Lex", None, simulation)
run_once(simulation, enemy, weapon)
# run_reapeated(simulation, enemy, weapon)


# import pstats, cProfile
# profiler = cProfile.Profile()
# profiler.enable()
# simulation.fast_run( [enemy], weapon.fire_modes[0])
# profiler.disable()
# stats = pstats.Stats(profiler).sort_stats('tottime')
# stats.print_stats()