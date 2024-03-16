from warframe_simulacrum.weapon import Weapon, FireMode, FireModeEffect, EventTrigger
from warframe_simulacrum.unit import Unit, Protection
from typing import List, Tuple
from queue import PriorityQueue
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import time
import heapq
import numpy as np
from scipy.optimize import curve_fit
import os
import warframe_simulacrum.constants
from matplotlib.offsetbox import (AnchoredOffsetbox, DrawingArea, HPacker,
                                  TextArea)
from matplotlib import colors

class Simulacrum:
    def __init__(self, figure, axes) -> None:
        self.event_queue:"heapq[Tuple[int, int, EventTrigger]]" = []
        self.time = 0
        self.call_index = 0
        self.event_index = 0
        self.plot_text = None
        self.anchored_box = None
        self.fig = figure
        self.ax = axes
        self.df:pd.DataFrame = pd.DataFrame([])
        cid1 = self.fig.canvas.mpl_connect('button_press_event', lambda event: self.onclick(event, self.df))

    def reset(self):
        self.time = 0
        self.call_index = 0
        self.event_queue = []

    def get_call_index(self):
        idx = self.call_index
        self.call_index += 1
        return idx
        
    def run_simulation(self, enemies:List[Unit], fire_mode:FireMode, primer:FireMode=None):
        self.reset()
        for enemy in enemies:
            enemy.reset()
        if primer and len(primer.forcedProc)>0:
            enemy.pellet_hit(primer, fire_mode.target_bodypart)
        stats = enemies[0].get_current_stats()

        stats['time'] = stats['time'] - 1e-6
        stats['name'] = ""
        stats['event_index'] = -1
        data = [stats]

        event_time = fire_mode.chargeTime.modded + fire_mode.embedDelay.modded
        heapq.heappush(self.event_queue, (event_time, self.get_call_index(), EventTrigger(fire_mode.pull_trigger, event_time, enemy=enemies[0])))
        for enemy in enemies:
            prev_time = 0
            prev_time_adj = 0
            while enemy.overguard.current_value > 0 or enemy.health.current_value > 0:
                self.time, call_index, event = heapq.heappop(self.event_queue)
                
                event.func(**event.kwargs)

                if stats_changed(data[-1], enemy):
                    sts = enemy.get_current_stats()
                    sts['event_index'] = self.event_index
                    sts["name"] = event.name

                    # reset
                    adj_time = sts["time"]
                    # if current time is equal to previous time, we should adjust it for it to display properly
                    if sts["time"] == prev_time:
                        # adjust current time by the accumulated offset plus another small offset
                        adj_time = sts["time"] + abs(prev_time_adj - prev_time) + 1e-6
                    # current time is new previous time
                    prev_time = sts["time"]

                    # set this point to new time value
                    sts["time"] = adj_time
                    # save
                    prev_time_adj = adj_time

                    if event.info_callback is not None:
                        sts["name"] += f", {event.info_callback()}"
                    data.append(sts)
                
                self.event_index += 1
                
                if self.time > 20 :
                    break

        df = pd.DataFrame(data)
        df_melt = pd.melt(df, id_vars=["time", "event_index", "name"], var_name="variable", value_name="value")
        df_melt = df_melt.drop_duplicates(subset=["variable", "value"])

        stats = enemy.get_stats()
        names = [key for key,value in stats.items() if value > 0 ]
        self.df = df_melt[(df_melt["variable"].isin(names))].copy()

        # self.fig, self.ax = plt.subplots()
        # cid12 = self.fig.canvas.mpl_connect('button_release_event', self.offclick) 

        # plot the data using seaborn
        sns.lineplot(data=self.df, x="time", y="value", hue="variable", marker="x", estimator=None, errorbar=None, markeredgecolor='black', drawstyle='steps-post', ax=self.ax)
        self.ax.set_ylim(bottom=0)
        self.ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

        box1 = TextArea("\nClick on point to see more info.\n", textprops=dict(color="k"))
        self.anchored_box = AnchoredOffsetbox(loc='lower left',
                                 child=box1, pad=0.4,
                                 frameon=True,
                                 bbox_to_anchor=(0., 1.02),
                                 bbox_transform=self.ax.transAxes,
                                 borderpad=0.,)
        self.ax.add_artist(self.anchored_box) 

        self.fig.tight_layout()

        
    def onclick(self, event, df:pd.DataFrame):
        # display_str = ''
        if self.plot_text is not None:
            self.plot_text.remove()
            self.plot_text = None

        if self.anchored_box is not None:
            self.anchored_box.remove()
            self.anchored_box = None
        
        if event.xdata is None or event.ydata is None or event.button == 3:
            box1 = TextArea("\nClick on point to see more info.\n", textprops=dict(color="k"))
            self.anchored_box = AnchoredOffsetbox(loc='lower left',
                                    child=box1, pad=0.4,
                                    frameon=True,
                                    bbox_to_anchor=(0., 1.02),
                                    bbox_transform=self.ax.transAxes,
                                    borderpad=0.,)
            self.ax.add_artist(self.anchored_box) 
            self.fig.canvas.draw()
            return

        x, y = (event.xdata, event.ydata)

        ### new
        t_min = df["time"].min()
        t_div = df["time"].max() - t_min
        df["time_norm"] = (df["time"] - t_min)/t_div
        v_min = df["value"].min()
        v_div = df["value"].max() - v_min
        df["value_norm"] = (df["value"] - v_min)/v_div

        df["time_"] = abs(df["time_norm"] - (x-t_min)/t_div)
        df["value_"] = abs(df["value_norm"] - (y-v_min)/v_div)
        df["dist_"] = np.sqrt(df["time_"]**2 + df["value_"]**2)
        df1 = df[(df['dist_'] == df['dist_'].min())]
        if len(df1.index)==0:
            return
        t = df1['time'].iloc[0]
        vb = df1['variable'].iloc[0]
        v = df1['value'].iloc[0]
        ci = df1['event_index'].iloc[0]
        name = df1['name'].iloc[0]
        
        df2 = df[(df["time"] <= t) & (df["variable"] == vb) & (df["event_index"] < ci)]
        
        if len(df2.index) == 0 :
            delta = 0
            tdelta = 1
        else:
            df2 = df2[(df2["time"] == df2["time"].max()) ]
            s2 = df2.iloc[-1]
            delta = s2['value'] - v
            tdelta = t - s2['time']

        txt = f"t={t:.1}s, {vb}={v:.1}\ndelta={(delta):.2f}\n{name}"
        left,right = self.ax.get_xlim()
        bot, top = self.ax.get_ylim()
        vspan = abs(top-bot)
        span = right-left
        if t > left+span/2:
            text_xoffset = (t-left)*(-0.1)
            text_yoffset = -delta/2
            ha = 'right'
            va='top'
        else:
            text_xoffset = (right-t)*(0.1)
            text_yoffset = delta/2
            ha = 'left'
            va='bottom'

        if v > bot+vspan/2:
            text_yoffset = (v-bot)*(-0.25)
        else:
            text_yoffset = (top-v)*(0.25)
            
        self.plot_text = self.ax.annotate("",
                            xy=(t,v), xycoords='data',
                            xytext=(t+text_xoffset, v+text_yoffset), textcoords='data',
                            arrowprops=dict(arrowstyle="simple", connectionstyle="arc3,rad=-0.2"),
                            ha=ha, va=va)
        
        bbox_text = f"Time: {t:.1f}s, {vb.capitalize()}: {v:.1f}\nDamage: {(delta):.2f}\nInfo: {name}"
        box1 = TextArea(bbox_text, textprops=dict(color="k"))
        self.anchored_box = AnchoredOffsetbox(loc='lower left',
                                 child=box1, pad=0.4,
                                 frameon=True,
                                 bbox_to_anchor=(0., 1.02),
                                 bbox_transform=self.ax.transAxes,
                                 borderpad=0.,)
        self.ax.add_artist(self.anchored_box) 
        
        self.fig.canvas.draw()

    def offclick(self, event):
        self.fig.canvas.draw()

    def fast_run(self, enemies:List[Unit], fire_mode:FireMode):
        event_time = fire_mode.chargeTime.modded + fire_mode.embedDelay.modded
        heapq.heappush(self.event_queue, (event_time, self.get_call_index(), EventTrigger(fire_mode.pull_trigger, event_time, enemy=enemies[0])))

        for enemy in enemies:
            while enemy.overguard.current_value > 0 or enemy.health.current_value > 0:
                self.time, _, event = heapq.heappop(self.event_queue)
                event.func(event.fire_mode, enemy)
                
                if self.time > 20 :
                    break

def stats_changed(prev_data:dict, enemy:Unit):
    if prev_data["overguard"] == enemy.overguard.current_value and prev_data["shield"] == enemy.shield.current_value\
                        and prev_data["health"] == enemy.health.current_value and prev_data["armor"] == enemy.armor.current_value:
        return False
    return True

def run_reapeated(simulation:Simulacrum, enemy:Unit, fire_mode:FireMode, count=20):
    for _ in range(count):
        simulation.reset()
        enemy.reset()
        fire_mode.reset()

        simulation.fast_run([enemy], fire_mode)

def run_once(simulation:Simulacrum, enemy:Unit, fire_mode:FireMode):
    simulation.run_simulation([enemy], fire_mode)


def damage_test(enemy:Unit, fire_mode:FireMode, game_dmg, crit_tier, bodypart='body'):
    tier_name = {0:"White", 1:"Yellow", 2:"Orange", 3:"Red", 4:"Red!", 5:"Red!!", 6:"Red!!!"}
    enemy.reset()
    fire_mode.reset()

    fire_mode.criticalChance.modded = crit_tier
    fire_mode.target_bodypart = bodypart
    enemy.pellet_hit(fire_mode, bodypart)
    enemy_data = enemy.get_info()
    weapon_data = fire_mode.get_info()
    print(f"{tier_name[crit_tier]}: {enemy.last_damage:.3f}")
    input("Confirm")
    data = dict(game_dmg=game_dmg, calc_damage=enemy.last_damage, t0_dmg=enemy.last_t0_damage, \
                fire_rate=fire_mode.fireRate.modded, multishot=fire_mode.multishot.modded, \
                    cd=enemy.damage_controller.critical_multiplier, tiered_cd=enemy.damage_controller.tiered_critical_multiplier, ct=enemy.damage_controller.critical_tier, bodypart=bodypart,
                     mods=fire_mode.get_mod_dict() )
    data.update(enemy_data)
    data.update(weapon_data)
    df = pd.DataFrame([data])
    df.to_csv("./data_archon.csv", mode='a', header=not os.path.isfile("./data1.csv"), index=False)

def print_tiers(enemy:Unit, fire_mode:FireMode, bodypart='body', animation='normal', enemy_afflictions:list=[], num_tiers=6):
    tier_name = {0:"White", 1:"Yellow", 2:"Orange", 3:"Red", 4:"Red!", 5:"Red!!", 6:"Red!!!"}
    print(f'bodypart:{bodypart}, animation:{animation}\n')
    fire_mode.target_bodypart = bodypart


    for cc in range(num_tiers):
        enemy.reset()
        for func, *args in enemy_afflictions:
            func(*args)
        
        fire_mode.reset()
        fire_mode.criticalChance.modded = cc
        if fire_mode.trigger == 'HELD':
            fire_mode.damagePerShot_m["multishot_multiplier"]=(int(fire_mode.multishot.modded))
            enemy.pellet_hit(fire_mode, bodypart)
            dmg_lo = enemy.last_damage

            enemy.reset()
            for func, *args in enemy_afflictions:
                func(*args)
            fire_mode.reset()
            fire_mode.criticalChance.modded = cc

            fire_mode.damagePerShot_m["multishot_multiplier"]=(int(fire_mode.multishot.modded)+1)
            enemy.pellet_hit(fire_mode, bodypart)
            dmg_hi = enemy.last_damage

            print(f"{tier_name[cc]}: {dmg_lo:.1f}-{dmg_hi:.2f}")
        else:
            enemy.pellet_hit(fire_mode, bodypart)
            print(f"{tier_name[cc]}: {enemy.last_damage:.3f}")
    print()

def get_first_damage(enemy:Unit, fire_mode:FireMode, bodypart='body', animation='normal', enemy_afflictions:list=[], critical_tiers:list=[0], primer:FireMode=None):
    if len(critical_tiers) == 0:
        return
    tier_name = {0:"White", 1:"Yellow", 2:"Orange", 3:"Red", 4:"Red!", 5:"Red!!", 6:"Red!!!"}
    fire_mode.target_bodypart = bodypart

    res = []
    for cc in critical_tiers:
        enemy.reset()
        for func, *args in enemy_afflictions:
            func(*args)
        if primer and len(primer.forcedProc)>0:
            enemy.pellet_hit(primer, bodypart)
        
        fire_mode.reset()
        fire_mode.criticalChance.modded = cc
        if fire_mode.trigger == 'HELD':
            fire_mode.damagePerShot_m["multishot_multiplier"]=(int(fire_mode.multishot.modded))
            enemy.pellet_hit(fire_mode, bodypart)
            dmg_lo = enemy.last_damage

            enemy.reset()
            for func, *args in enemy_afflictions:
                func(*args)
            if primer and len(primer.forcedProc)>0:
                enemy.pellet_hit(primer, bodypart)

            fire_mode.reset()
            fire_mode.criticalChance.modded = cc

            fire_mode.damagePerShot_m["multishot_multiplier"]=(int(fire_mode.multishot.modded)+1)
            enemy.pellet_hit(fire_mode, bodypart)
            dmg_hi = enemy.last_damage

            res.append({'critical_tier':cc, 'damage':f'{dmg_lo:.3f} - {dmg_hi:.3f}'})
        else:
            enemy.pellet_hit(fire_mode, bodypart)
            res.append({'critical_tier':cc, 'damage':f'{enemy.last_damage:.3f}'})
    fire_mode.reset()
    return res


def print_status_tiers(enemy:Unit, fire_mode:FireMode, proc_index:int, bodypart='body', animation='normal', enemy_afflictions:list=[], num_tiers=1):
    tier_name = {0:"White", 1:"Yellow", 2:"Orange", 3:"Red", 4:"Red!", 5:"Red!!", 6:"Red!!!"}
    fire_mode.target_bodypart = bodypart

    for cc in range(num_tiers):
        enemy.reset()
        for func, *args in enemy_afflictions:
            func(*args)
        
        fire_mode.reset()
        fire_mode.forcedProc = [proc_index]
        fire_mode.procProbabilities = np.array([0]*20)

        fire_mode.criticalChance.modded = cc
        enemy.pellet_hit(fire_mode, bodypart)
        enemy.proc_controller.proc_managers[proc_index].damage_event(fire_mode)
        print(f"{tier_name[cc]}: {enemy.last_damage:.2f}")

def get_first_status_damage(enemy:Unit, fire_mode:FireMode, proc_indices:list, bodypart='body', animation='normal', enemy_afflictions:list=[], critical_tiers:list=[0], primer:FireMode=None):
    tier_name = {0:"White", 1:"Yellow", 2:"Orange", 3:"Red", 4:"Red!", 5:"Red!!", 6:"Red!!!"}
    fire_mode.target_bodypart = bodypart

    if len(critical_tiers) == 0:
        return
    res = []
    for i, proc_index in enumerate(proc_indices):
        for cc in critical_tiers:
            enemy.reset()
            if primer and len(primer.forcedProc)>0:
                enemy.pellet_hit(primer, bodypart)
            
            for func, *args in enemy_afflictions:
                func(*args)
            
            fire_mode.reset()
            fire_mode.forcedProc = [proc_index]
            fire_mode.procProbabilities = np.array([0]*20)

            fire_mode.criticalChance.modded = cc
            enemy.pellet_hit(fire_mode, bodypart)
            # for ctr in enemy.proc_controller.proc_managers[proc_index].container_list:
            #     print(ctr.get_damage_info())
            enemy.proc_controller.proc_managers[proc_index].damage_event(fire_mode)
            res.append({'proc_index':proc_index, 'critical_tier':cc, 'damage':f'{enemy.last_damage:.3f}', 'list_index':i})
    fire_mode.reset()
    return res
