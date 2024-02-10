from weapon import Weapon, FireMode, FireModeEffect, EventTrigger
from unit import Unit, Protection
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
import constants

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


def damage_test(enemy:Unit, weapon:Weapon, game_dmg, crit_tier, bodypart='body'):
    enemy.reset()
    weapon.reset()

    fire_mode = weapon.fire_modes[0]
    fire_mode.criticalChance.modded = crit_tier

    enemy.pellet_hit(fire_mode, bodypart=bodypart)
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

# def func(x, a, b, c):
#     return (x)/((x-a)/(460000) + 1)

def func(x, a, b, c):
    a=143
    b=20
    correction_factor = a + x * c/ (1 + x * c/b)
    return (x)/((x-correction_factor)/(460000) + 1)

def plot_dps():
    x = Symbol('x')

    df = pd.read_csv("./data1.csv")
    # df = df[(df.weapon=="Lanka")]
    # df = df[(df.weapon=="Knell Prime")]
    # df = df[(df.weapon=="Rubico Prime")]
    # df = df[(df.weapon=="Rubico Prime")|(df.weapon=="Knell Prime")|(df.weapon=="Rubico")|(df.weapon=="Vectis Prime")]
    # df = df[(df.weapon=="Rubico")]
    # df = df[(df.weapon=="Vectis Prime")]

    df["in_dps"] = df.t0_dmg * df.multishot * df.tiered_cd
    df["in_dps"] = df.t0_dmg * df.multishot * df.tiered_cd

    df["thry_dps"] = df.calc_damage * df.multishot
    df["out_dps"] = df.game_dmg * df.multishot 
    df["ratio"] = df.out_dps / df.in_dps 

    df["diff"] = df.out_dps - df.thry_dps 


    fig,axs = plt.subplots(2,1, sharex=True)
    # axs[0].scatter(df["in_dps"], df["out_dps"])
    sns.scatterplot(data=df, x='in_dps', y='out_dps', hue='fire_rate', style='multishot', ax=axs[0])
    # popt, pcov = curve_fit(func, df["in_dps"], df["out_dps"])
    popt, pcov = curve_fit(lambda x, a, b: func(x, a, b, df.fire_rate), df["in_dps"], df["out_dps"])
    xfit = np.linspace(0, 3e6, 200000)
    # axs[0].plot(xfit, func(xfit, *popt))
    axs[0].plot(xfit, func(xfit, *popt, [1]*len(xfit)))
    # err = df["out_dps"] - func(df["in_dps"], *popt)
    # err = df["game_dmg"] - func(df["in_dps"], *popt)/df.multishot
    err = df["game_dmg"] - func(df["in_dps"], *popt, df.fire_rate)/df.multishot
    axs[1].scatter(df["in_dps"], err)

    print(popt)
    axs[1].set_ylabel('err')
    plt.show()

    # plt.scatter(df.in_dps, df.out_dps)
    # sns.scatterplot(data=df, x='in_dps', y='diff', hue='weapon', style='multishot')
    # plt.show()

def plot_dps2():
    base_dr = 0.8
    corners = [[0,1500],[1500,3000],[3000,6000],[6000,8000],[8000,10000],\
               [10000,12000],[12000,14000],[14000,16000],[16000,19000],[19000,22000],\
               [22000,25500],[25500,28000],[28000,31000]]
    corners = [[0,460000]]
    # corners = [[0,3000],[3000,100000]]
    i1 = [40940,32867,38101,2042,3409,1223,853]
    o1=[30575,24872,28587,1628,2712,976,681]
    i2 = [10025,4815,3434,2056,1113,1105,3262,1952,2719,2405,1439,862,2887,1728]
    o2 = [7883,3820,2731,1639,889,882,2595,1557,2165,1916,1149,688,2298,1378]
    i3 = [34346,22676,18730,16367,9799,9710,9656,8587]
    o3 = [25928,17453,14512,12731,7708,7639,7597,6768]
    i4 = [33885,22372,13395,8472,8938,8472,27203,16289,9752,31367,18777,11243,8558]
    o4 = [25599,17228,10472,6679,7041,6679,20780,12672,7672,23796,14547,8822,6746]
    i5=[ 31498,24091,23966,14350,32629,21543,12899,8157,35943,21521,12886,8986]+\
            [19732,4092,33462,20033,11995,8472,13389,5742,3437,390078]+\
            [374,303,732,340,277,247,7504,6124,4997,4078,3328]
    o5=[23890,18498, 18406,11200,24701,16612,10093,6434,27063,16596,10083,7078]+\
            [15262,3251,25298,15487,9400,6679,10468,4548,2734,185929]+\
            [299,243,585,272,222,198,5926,4847,3963,3240,2647]

    in_dps = np.array(i1+i2+i3+i4+i5, dtype=float)
    out_dps = np.array(o1+o2+o3+o4+o5, dtype=float)

    in_dps *= base_dr

    fig,axs = plt.subplots(2,1, sharex=True)
    axs[0].scatter(in_dps, out_dps)
    op=0
    for low,high in corners:
        out_dps1 = out_dps[(in_dps<high) & (in_dps>low)]
        in_dps1 = in_dps[(in_dps<high) & (in_dps>low)]
        if len(out_dps1) <= 1:
            print('single data point')
            continue
        if len(out_dps1) != len(in_dps1):
            print('improper len')
            continue

        # popt, pcov = curve_fit(func, in_dps1, out_dps1)
        popt, pcov = curve_fit(lambda x, a, b: func(x, a, b, [1]*len(in_dps1)), in_dps1, out_dps1)

        # print(popt[0]-op, popt[0]/op)
        op = popt[0]
        xfit = np.linspace(low, high, 200000)
        axs[0].plot(xfit, func(xfit, *popt, [1]*len(xfit)))
        # err = out_dps1 - func(in_dps1, *popt)
        err = out_dps1 - func(in_dps1, *popt, [1]*len(in_dps1))
        axs[1].scatter(in_dps1, err)

        print(popt)
    axs[1].set_ylabel('err')
    plt.show()


def print_tiers(enemy:Unit, weapon:Weapon, bodypart='body', animation='normal', enemy_afflictions:list=[], num_tiers=6):
    print(f'bodypart:{bodypart}, animation:{animation}\n')
    fire_mode = weapon.fire_modes[0]
    for cc in range(num_tiers):
        enemy.reset()
        for func, *args in enemy_afflictions:
            func(*args)
        
        weapon.reset()
        fire_mode.criticalChance.modded = cc
        if fire_mode.trigger == 'HELD':
            fire_mode.damagePerShot_m["multishot_multiplier"]=(int(fire_mode.multishot.modded))
            enemy.pellet_hit(fire_mode, bodypart, animation)
            dmg_lo = enemy.last_damage

            enemy.reset()
            for func, *args in enemy_afflictions:
                func(*args)
            weapon.reset()
            fire_mode.criticalChance.modded = cc

            fire_mode.damagePerShot_m["multishot_multiplier"]=(int(fire_mode.multishot.modded)+1)
            enemy.pellet_hit(fire_mode, bodypart, animation)
            dmg_hi = enemy.last_damage

            print(f"{tier_name[cc]}: {dmg_lo:.1f}-{dmg_hi:.2f}")
        else:
            enemy.pellet_hit(fire_mode, bodypart, animation)
            print(f"{tier_name[cc]}: {enemy.last_damage:.3f}")
    print()

def print_status_tiers(enemy:Unit, weapon:Weapon, proc_index:int, bodypart='body', animation='normal', enemy_afflictions:list=[], num_tiers=1):
    for cc in range(num_tiers):
        enemy.reset()
        for func, *args in enemy_afflictions:
            func(*args)
        
        weapon.reset()
        fire_mode = weapon.fire_modes[0]
        fire_mode.forcedProc = [proc_index]
        fire_mode.procProbabilities = np.array([0]*20)

        fire_mode.criticalChance.modded = cc
        enemy.pellet_hit(fire_mode, bodypart, animation)
        enemy.proc_controller.proc_managers[proc_index].damage_event(fire_mode)
        print(f"{tier_name[cc]}: {enemy.last_damage:.2f}")

def test_force_tier(enemy:Unit, weapon:Weapon, bodypart='body', animation='normal', crit_tier=2):
    fire_mode = weapon.fire_modes[0]
    for i in range(10000):
        enemy.reset()
        weapon.reset()

        fire_mode.criticalChance.modded = crit_tier

        enemy.pellet_hit(fire_mode, bodypart, animation)
        if i==0:
            ref_dmg = enemy.last_damage
            continue
        if ref_dmg != enemy.last_damage:
            print('Bad damage')
            break

def test_frag():
    tier_name = {0:"White", 1:"Yellow", 2:"Orange", 3:"Red", 4:"Red!", 5:"Red!!"}
    simulation = Simulacrum()

    # enemy = Unit("Charger Eximus", 225, simulation)
    enemy = Unit("Archon", 155, simulation)
    # enemy = Unit("The Anatomizer", 225, simulation)
    enemy.health.set_value_multiplier(',', 2.5)


    weapon = Weapon('Dex Pixia Prime', None, simulation)
    fm = weapon.fire_modes[0]
    fm.damagePerShot_m['base'] = 2.2 - 0.15 + 0.27
    fm.damagePerShot_m['final_multiplier'] = (1 + 0.55 + 0.9) 
    fm.damagePerShot_m['additive_base'] = 110
    fm.fireRate_m['base'] = 0.6 + 0.9 + 0.72 + 0.4 + 1.2 + 0.67
    fm.multishot_m['base'] = 1
    fm.criticalMultiplier_m['base'] = 1.1 #+ 0.03125
    # fm.criticalMultiplier_m['additive_final'] = 0.1
    fm.criticalMultiplier_m['additive_base'] = 0
    fm.criticalMultiplier_m['final_multiplier'] = 1.6 #1.6=yellow, 1.65=orange...
    fm.radiation_m['base'] = 0.6
    fm.factionDamage_m['base'] = 0.3
    fm.cold_m['base'] = 0.9
    fm.apply_mods()

    # print_tiers(enemy, weapon, bodypart='appendage', animation='normal', enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5]], num_tiers=2)
    # print_tiers(enemy, weapon, bodypart='appendage', animation='slam', enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5]], num_tiers=2)
    print_tiers(enemy, weapon, bodypart='body', animation='normal', enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5]], num_tiers=2)
    # print_tiers(enemy, weapon, bodypart='body', animation='slam', enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5]], num_tiers=2)
    # print_tiers(enemy, weapon, bodypart='head', animation='normal', enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5]], num_tiers=2)
    # print_tiers(enemy, weapon, bodypart='head', animation='slam', enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5]], num_tiers=2)
    print_tiers(enemy, weapon, bodypart='orb', animation='laser_hands', enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5]], num_tiers=3)

def test_archon():
    
    simulation = Simulacrum()

    enemy = Unit("Archon", 150, simulation)
    print(enemy.armor.max_value)


    weapon = Weapon('Dex Pixia Prime', None, simulation)
    fm = weapon.fire_modes[0]
    fm.damagePerShot_m['base'] = 2.2 - 0.15 + 0.27
    fm.damagePerShot_m['final_multiplier'] = (1 + 0.55 + 0.9) 
    fm.damagePerShot_m['additive_base'] = 110
    fm.fireRate_m['base'] = 0.6 + 0.9 + 0.72 + 0.4 + 1.2 + 0.67
    fm.multishot_m['base'] = 1
    fm.criticalMultiplier_m['base'] = 1.1
    # fm.corrosive_m['base'] = 1.2
    fm.radiation_m['base'] = 0.6
    fm.cold_m['base'] = 0.9
    fm.apply_mods()

    print_tiers(enemy, weapon, bodypart='head', enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5],[enemy.armor.set_value_multiplier, "SP", 1]], num_tiers=2)


def test_archon2():
    
    simulation = Simulacrum()

    enemy = Unit("Archon", 150, simulation)
    print(enemy.armor.max_value)


    weapon = Weapon('Rubico Prime', None, simulation)
    fm = weapon.fire_modes[0]
    fm.damagePerShot_m['base'] = 1.65
    fm.damagePerShot_m['final_multiplier'] = 2.5
    fm.multishot_m['base'] = 0.9
    fm.criticalMultiplier_m['base'] = 1.2 + 0.6 + 0.5
    # fm.radiation_m['base'] = 0.6 + 0.9*2
    fm.corrosive_m['base'] = 0.6 + 0.9*2
    # fm.combine_elemental = [8]
    fm.combine_elemental = [12]
    fm.apply_mods()

    print_tiers(enemy, weapon, bodypart='head', enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5],[enemy.armor.set_value_multiplier, "SP", 1]], num_tiers=3)

def test_archon22():
    
    simulation = Simulacrum()

    enemy = Unit("Archon", 150, simulation)
    print(enemy.armor.max_value)
    print(enemy.health.max_value*2.5*0.5)



    weapon = Weapon('Rubico Prime', None, simulation)
    fm = weapon.fire_modes[0]
    fm.damagePerShot_m['base'] = 1.65
    fm.damagePerShot_m['final_multiplier'] = 2
    fm.multishot_m['base'] = 0.9
    fm.criticalMultiplier_m['base'] = 1.2 + 0.6 + 0.5
    # fm.radiation_m['base'] = 0.6 + 0.9*2
    fm.corrosive_m['base'] = 0.6 + 0.9*2
    # fm.combine_elemental = [8]
    fm.combine_elemental = [12]
    fm.apply_mods()

    print_tiers(enemy, weapon, bodypart='head', enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5],[enemy.armor.set_value_multiplier, "SP", 1]], num_tiers=3)


def test_archon3():
    
    simulation = Simulacrum()

    enemy = Unit("Archon", 150, simulation)
    print(enemy.armor.max_value)


    weapon = Weapon('Knell Prime', None, simulation)
    fm = weapon.fire_modes[0]
    fm.damagePerShot_m['base'] =-0.15 + 2.2
    fm.damagePerShot_m['final_multiplier'] = 1
    fm.multishot_m['base'] = 1
    fm.criticalMultiplier_m['base'] = 1.1
    fm.criticalMultiplier_m['additive_final'] = 1.5
    fm.radiation_m['base'] = 0.6 + 1.65+0.9
    # fm.corrosive_m['base'] = 0.6 + 0.9*2
    # fm.combine_elemental = [8]
    # fm.combine_elemental = [12]
    fm.apply_mods()

    print_tiers(enemy, weapon, bodypart='head', enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5],[enemy.armor.set_value_multiplier, "SP", 1]], num_tiers=3)

def test_archon1():
    
    simulation = Simulacrum()

    # enemy = Unit("Archon", 150, simulation)
    enemy = Unit("Butcher", 150, simulation)
    print(enemy.armor.max_value)


    weapon = Weapon('Lanka', None, simulation)
    fm = weapon.fire_modes[0]
    fm.damagePerShot_m['base'] = np.float32(1.65 + 1.2*3 )
    fm.damagePerShot_m['final_multiplier'] = np.float32((1.6 + 0.3) * 3 * 11.15 )# * 7.44
    fm.multishot_m['base'] = 0
    fm.criticalMultiplier_m['base'] = np.float32(1.2 + 0.6 )
    # fm.radiation_m['base'] = 0.6 + 0.9*2
    # fm.combine_elemental = [8]

    # fm.corrosive_m['base'] = 0.6 + 0.9*2
    # fm.combine_elemental = [12]

    fm.radiation_m['base'] = np.float32(0.9*2)
    fm.cold_m['base'] = np.float32(1.65)
    fm.combine_elemental = [constants.DT_INDEX['DT_RADIATION']]

    fm.apply_mods()

    print_tiers(enemy, weapon, bodypart='head', enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5],[enemy.armor.set_value_multiplier, "SP", 0]], num_tiers=3)

def test_archon_acrid():
    
    simulation = Simulacrum()

    enemy = Unit("Archon", 150, simulation)

    weapon = Weapon('Acrid', None, simulation)
    fm = weapon.fire_modes[0]
    fm.damagePerShot_m['base'] = 2.2

    fm.radiation_m['base'] = 1.65*2

    fm.apply_mods()

    print_tiers(enemy, weapon, bodypart='head', num_tiers=2)


def test_frag1():
    
    simulation = Simulacrum()

    enemy = Unit("The Fragmented", 150, simulation)



    weapon = Weapon('Vasto Prime', None, simulation)
    fm = weapon.fire_modes[0]
    fm.damagePerShot_m['base'] = 2.2 + 0.27
    fm.damagePerShot_m['additive_base'] = 24 + 0
    fm.criticalMultiplier_m['base'] = 1.1
    fm.criticalMultiplier_m['additive_base'] = 0.8
    fm.criticalMultiplier_m['additive_final'] = 4
    fm.criticalMultiplier_m['final_multiplier'] = 1

    fm.radiation_m['base'] = 0.9*2


    fm.apply_mods()

    print_tiers(enemy, weapon, bodypart='orb', animation='laser_hands',enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5],[enemy.armor.set_value_multiplier, "SP", 1]], num_tiers=7)
    # print_tiers(enemy, weapon, bodypart='body', animation='normal',enemy_afflictions=[[enemy.health.set_value_multiplier, "SP", 2.5],[enemy.armor.set_value_multiplier, "SP", 1]], num_tiers=7)


tier_name = {0:"White", 1:"Yellow", 2:"Orange", 3:"Red", 4:"Red!", 5:"Red!!", 6:"Red!!!"}
# test_frag1()
# test_archon2()
# test_archon1()
# test_archon_acrid()
simulation = Simulacrum()
enemy = Unit("Archon", 150, simulation)
# enemy = Unit("Elite Lancer", 185, simulation)
# print(enemy.armor.max_value)
weapon = Weapon('Euphona Prime', None, simulation)
fm = weapon.fire_modes[0]

fm.damagePerShot_m['base'] = 2.2 + 1.65
fm.multishot_m['base'] = 0.6 + 1.2
fm.criticalMultiplier_m['base'] = 1.1

fm.radiation_m['base'] = 0.9*2

fm.apply_mods()

game_dmg = 321
# damage_test(enemy, weapon, game_dmg, crit_tier=0)
print_tiers(enemy, weapon, bodypart="head", num_tiers=2)

# print_status_tiers(enemy, weapon, constants.DT_INDEX['DT_TOXIN'])




