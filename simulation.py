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
from scipy.optimize import curve_fit
import sympy
from sympy import Symbol
import os

class Simulacrum:
    def __init__(self) -> None:
        self.event_queue:"heapq[Tuple[int, int, EventTrigger]]" = []
        self.time = 0
        self.call_index = 0
        self.event_index = 0
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
        stats['event_index'] = -1
        data = [stats]

        event_time = fire_mode.chargeTime.modded + fire_mode.embedDelay.modded
        heapq.heappush(self.event_queue, (event_time, self.get_call_index(), EventTrigger(fire_mode.pull_trigger, event_time, enemy=enemies[0])))
        for enemy in enemies:
            while enemy.overguard.current_value > 0 or enemy.health.current_value > 0:
                self.time, call_index, event = heapq.heappop(self.event_queue)
                
                event.func(**event.kwargs)

                if stats_changed(data[-1], enemy):
                    sts = enemy.get_current_stats()
                    sts['event_index'] = self.event_index
                    sts["name"] = event.name
                    if event.info_callback is not None:
                        sts["name"] += f", {event.info_callback()}"
                    data.append(sts)
                
                self.event_index += 1
                
                if self.time > 20 :
                    break

        df = pd.DataFrame(data)
        df_melt = pd.melt(df, id_vars=["time", "event_index", "name"], var_name="variable", value_name="value")

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
        ci = df1['event_index'].iloc[0]
        name = df1['name'].iloc[0]
        
        df2 = df[(df["time"] <= t) & (df["variable"] == vb) & (df["event_index"] < ci)]
        # print(df2)
        if len(df2.index) == 0 :
            delta = 0
            tdelta = 1
        else:
            df2 = df2[(df2["time"] == df2["time"].max()) ]
            s2 = df2.iloc[-1]
            delta = s2['value'] - v
            tdelta = t - s2['time']

        txt = f"t={t:.1f}s, {vb}={v:.1f}\ndelta={(delta):.2f}\n{name}"
        left,right = self.ax.get_xlim()
        top,bot = self.ax.get_ylim()
        vspan = abs(top-bot)
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

def run_reapeated(simulation:Simulacrum, enemy:Unit, weapon:Weapon, count=20):
    for _ in range(count):
        simulation.reset()
        enemy.reset()
        weapon.reset()

        simulation.fast_run([enemy], weapon.fire_modes[0])

def run_once(simulation:Simulacrum, enemy:Unit, weapon:Weapon):
    simulation.run_simulation([enemy], weapon.fire_modes[0])



def damage_test(enemy:Unit, weapon:Weapon):
    fire_mode = weapon.fire_modes[0]
    # for cc in range(6):
    #     fire_mode.criticalChance.modded = cc
    #     enemy.pellet_hit(fire_mode)
    #     print(f"{tier_name[cc]}: {enemy.last_damage:.1f}")

    # frs = [0,0.2,0.4,0.6,0.8,1,1.2,1.32]
    # fire_mode.criticalChance.modded = 2
    # ydata = []
    # xdata = []
    # for fr in frs:
    #     tfr = 1+1.2+fr
    #     fire_mode.fireRate.modded = fire_mode.fireRate.base * tfr
    #     enemy.pellet_hit(fire_mode)
    #     print(f"Dmg: {enemy.last_damage:.1f}, ",sep="")
    #     inp = input()
    #     xdata.append(fire_mode.fireRate.modded * fire_mode.multishot.modded)
    #     ydata.append(float(inp)/enemy.last_damage)

    # fit(xdata, ydata)
    game_dmg = 4661
    fr = 1 + 0.6 + 0.72 + 0.15 + 0.8
    fire_mode.criticalChance.modded = 3


    fire_mode.fireRate.modded = fire_mode.fireRate.base * fr
    enemy.pellet_hit(fire_mode)
    dps_mult=fire_mode.fireRate.modded * fire_mode.multishot.modded
    data = dict(game_dmg=game_dmg, calc_damage=enemy.last_damage, t0_dmg=enemy.last_t0_damage, dps_mult=dps_mult, cd=enemy.damage_controller.critical_multiplier, ct=enemy.damage_controller.critical_tier )
    df = pd.DataFrame([data])
    df.to_csv("./data.csv", mode='a', header=not os.path.isfile("./data.csv"), index=False)

def func(x, a, b):
    return a * x + b

def fit(tier=2):
    x = Symbol('x')

    # corners = [8.6594, 10.2184, 17.3188]
    # corners = [8.6594, 10.2184, 14.2]
    # corners = [8.6594, 9.43, 14.2]
    corn = [[8.6594, 10.2184, 14.2], [8.6594, 9.43, 14.2], [8.6594, 9.6, 14.2], [8.6594, 11, 14.2]]

    df = pd.read_csv("./data.csv")
    # df = df[(df.ct==tier)]

    # df["ratio"] = df.game_dmg / df.calc_damage
    df["in_dps"] = df.t0_dmg * df.dps_mult #* df.cd
    df["out_dps"] = df.game_dmg * df.dps_mult / df.cd
    df["ratio"] = df.out_dps / df.in_dps



    plt.scatter(df.in_dps, df.ratio)

    for cd, corners in list(zip(df.cd.unique(), corn)) :
        popt1, popt2 = None, None
        lcorner =6
        rcorner =0
        for i, corner in enumerate(corners):
            if i == 0:
                rcorner = corner
            else:
                lcorner = rcorner
                rcorner = corner

            dfp = df[(abs(df.cd - cd)<0.01) & (df.dps_mult>lcorner) & (df.dps_mult<rcorner)]
            if len(dfp.index) <= 1:
                continue

            # popt, pcov = curve_fit(func, dfp.dps_mult, dfp.ratio)
            # xfit = np.linspace(lcorner-.2,rcorner+0.2)
            bdmg = dfp.t0_dmg.iloc[0]
            popt, pcov = curve_fit(func, dfp.in_dps, dfp.ratio)
            xfit = np.linspace((lcorner-.2)*bdmg,(rcorner+0.2)*bdmg)
            plt.plot(xfit, func(xfit, popt[0], popt[1]))
            print(popt)
            
            # popt, pcov = curve_fit(func, xdata[(xdata>lcorner) & (xdata<rcorner)], ydata[(xdata>lcorner) & (xdata<rcorner)])
            # xfit = np.linspace(min(xdata),max(xdata))
            # plt.plot(xfit, func(xfit, popt[0], popt[1]))

            if i == 0:
                popt2 = popt
            else:
                popt1 = popt2
                popt2 = popt

                res = sympy.solve(popt1[0]*x+popt1[1] - (popt2[0]*x+popt2[1]))
                print(res, res[0]*bdmg)
        print()
    plt.show()

def plot_dps(tier=2):
    x = Symbol('x')

    # corners = [8.6594, 10.2184, 17.3188]
    # corners = [8.6594, 10.2184, 14.2]
    # corners = [8.6594, 9.43, 14.2]
    corn = [[8.6594, 10.2184, 14.2], [8.6594, 9.43, 14.2], [8.6594, 9.6, 14.2]]

    df = pd.read_csv("./data.csv")
    # df = df[(df.ct==tier)]


    df["in_dps"] = df.t0_dmg * df.dps_mult #* df.cd
    df["out_dps"] = df.game_dmg * df.dps_mult / df.cd

    # plt.scatter(df.in_dps, df.out_dps)
    sns.scatterplot(data=df, x='in_dps', y='out_dps', hue='cd')



   
    plt.show()

def static_dps1(damage_in, dps_multiplier_in, cm, ct):

    tier_min = (1-1/ct)
    dps_reducer = (tier_min/(cm-tier_min) + 1)

    dps_multiplier_in = dps_multiplier_in / dps_reducer

    tier0_dps = damage_in * dps_multiplier_in

    if tier0_dps <= 1000:
        return damage_in
    elif tier0_dps >= 1000 and tier0_dps <= 2500:
        return dps_reducer*((0.8*tier0_dps+200))/dps_multiplier_in
    elif tier0_dps >= 2500 and tier0_dps <= 5000:
        return dps_reducer*((0.7*tier0_dps+450))/dps_multiplier_in
    elif tier0_dps >= 5000 and tier0_dps <= 10000:
        return dps_reducer*((0.4*tier0_dps+1950))/dps_multiplier_in
    elif tier0_dps >= 10000 and tier0_dps <= 20000:
        return dps_reducer*((0.2*tier0_dps+3950))/dps_multiplier_in
    elif tier0_dps >= 20000:
        return dps_reducer*((0.1*tier0_dps+5950))/dps_multiplier_in
    
def static_dps(damage_in, dps_multiplier_in, cm, ct):

    tier_min = (1-1/max(1, ct))
    dps_reducer = (tier_min/(cm-tier_min) + 1)

    dps_multiplier_in = dps_multiplier_in / dps_reducer

    tier0_dps = damage_in * dps_multiplier_in

    dr=1
    if tier0_dps >= 1000 and tier0_dps <= 2500:
        dr = 0.8 + 200/tier0_dps
    elif tier0_dps >= 2500 and tier0_dps <= 5000:
        dr = 0.7 + 450/tier0_dps
    elif tier0_dps >= 5000 and tier0_dps <= 10000:
        dr = 0.4+1950/tier0_dps
    elif tier0_dps >= 10000 and tier0_dps <= 20000:
        dr = 0.2+3950/tier0_dps
    elif tier0_dps >= 20000:
        dr = 0.1+5950/tier0_dps
    return damage_in * dr 
    
def static_dps_old(damage_in, dps_multiplier_in, cm, ct):
    dps_multiplier_in = dps_multiplier_in
    tier0_dps = damage_in * dps_multiplier_in

    if tier0_dps <= 1000:
        return damage_in
    elif tier0_dps >= 1000 and tier0_dps <= 2500:
        return ((0.8*tier0_dps+200))/dps_multiplier_in
    elif tier0_dps >= 2500 and tier0_dps <= 5000:
        return ((0.7*tier0_dps+450))/dps_multiplier_in
    elif tier0_dps >= 5000 and tier0_dps <= 10000:
        return ((0.4*tier0_dps+1950))/dps_multiplier_in
    elif tier0_dps >= 10000 and tier0_dps <= 20000:
        return ((0.2*tier0_dps+3950))/dps_multiplier_in
    elif tier0_dps >= 20000:
        return ((0.1*tier0_dps+5950))/dps_multiplier_in
    
def test_theory():
    x = np.linspace(1, 30000, 1000)
    y = []
    for ct in range(0,101):
        for elem in x:
            res = static_dps(1, elem, 3.2, ct)
            old = static_dps_old(1, elem, 3.2, ct)
            y.append(dict(tier0_dps=elem, out_damage=res, out_old = old, crit_tier=ct))
    df = pd.DataFrame(y)
    sns.lineplot(data=df, x='tier0_dps', y='out_damage', hue='crit_tier')

    df['ratio'] = df.out_damage/df.out_old
    # sns.lineplot(data=df, x='tier0_dps', y='ratio', hue='crit_tier')

    plt.show()

def print_tiers(enemy:Unit, weapon:Weapon):
    fire_mode = weapon.fire_modes[0]
    for cc in range(6):
        fire_mode.criticalChance.modded = cc
        if fire_mode.trigger == 'HELD':
            fire_mode.damagePerShot_m["multishot_multiplier"].set_value(int(fire_mode.multishot.modded))
            enemy.pellet_hit(fire_mode)
            dmg_lo = enemy.last_damage

            fire_mode.damagePerShot_m["multishot_multiplier"].set_value(int(fire_mode.multishot.modded)+1)
            enemy.pellet_hit(fire_mode)
            dmg_hi = enemy.last_damage

            print(f"{tier_name[cc]}: {dmg_lo:.1f}-{dmg_hi:.2f}")
        else:
            enemy.pellet_hit(fire_mode)
            print(f"{tier_name[cc]}: {enemy.last_damage:.2f}")

def print_status_tiers(enemy:Unit, weapon:Weapon, proc_index:int):
    for cc in range(6):
        enemy.reset()
        enemy.armor.apply_affliction("Full stip", 0)
        # enemy.shield.apply_affliction("Full stip", 0)
        weapon.reset()
        fire_mode = weapon.fire_modes[0]
        fire_mode.forcedProc = [proc_index]
        fire_mode.procProbabilities = np.array([0]*20)

        fire_mode.criticalChance.modded = cc
        enemy.pellet_hit(fire_mode)
        enemy.proc_controller.proc_managers[proc_index].damage_event(fire_mode)
        print(f"{tier_name[cc]}: {enemy.last_damage:.2f}")

tier_name = {0:"White", 1:"Yellow", 2:"Orange", 3:"Red", 4:"Red!", 5:"Red!!"}
simulation = Simulacrum()
# enemy = Unit("Demolisher Devourer", 75, simulation)
# enemy.armor.apply_affliction("Full stip", 0)
# enemy = Unit("Charger Eximus", 80, simulation)

enemy = Unit("Acolyte", 80, simulation)
enemy.armor.apply_affliction("Full stip", 0)
enemy.shield.apply_affliction("Full stip", 0)

# weapon = Weapon("Vasto Prime", None, simulation)
# weapon = Weapon("Quanta Vandal", None, simulation)
weapon = Weapon("Hystrix", None, simulation)


# damage_test(enemy, weapon)
# fit()

# plot_dps()
# print_tiers(enemy, weapon)
print_status_tiers(enemy, weapon, 5)
# test_theory()

# enemy = Unit("Charger Eximus", 80, simulation)
# weapon = Weapon("Synapse", None, simulation)
# weapon = Weapon("Lex Prime", None, simulation)
# weapon = Weapon("Vaykor Marelok", None, simulation)
# weapon = Weapon("Hystrix", None, simulation)
# weapon = Weapon("Lex", None, simulation)


# run_once(simulation, enemy, weapon)
# run_reapeated(simulation, enemy, weapon)


# import pstats, cProfile
# profiler = cProfile.Profile()
# profiler.enable()
# simulation.fast_run( [enemy], weapon.fire_modes[0])
# profiler.disable()
# stats = pstats.Stats(profiler).sort_stats('tottime')
# stats.print_stats()