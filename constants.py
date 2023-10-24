import numpy as np
'''
List of damage types and their indices
0   Impact
1   Puncture
2   Slash
3   Heat
4   Cold
5   Electric
6   Toxin
7   Blast
8   Radiation
9   Gas
10  Magnetic
11  Viral
12  Corrosive
13  DT_FINISHER
14  DT_RADIANT
15  DT_SENTIENT
16  DT_CINEMATIC
17  DT_SHIELD_DRAIN
18  DT_HEALTH_DRAIN
19  DT_ENERGY_DRAIN
20  DT_SUICIDE
21  DT_PHYSICAL
22  DT_BASE_ELEMENTAL
23  DT_COMPOUND_ELEMENTAL
24  DT_ANY
25  DT_INVALID
'''
DT_INDEX = {"DT_IMPACT":0, "DT_PUNCTURE":1, "DT_SLASH":2, "DT_HEAT":3,
            "DT_COLD":4,"DT_ELECTRIC":5,"DT_TOXIN":6,"DT_BLAST":7,
            "DT_RADIATION":8,"DT_GAS":9,"DT_MAGNETIC":10,"DT_VIRAL":11,
            "DT_CORROSIVE":12,"DT_FINISHER":13,"DT_RADIANT":14,"DT_SENTIENT":15,
            "DT_CINEMATIC":16,"DT_SHIELD_DRAIN":17,"DT_HEALTH_DRAIN":18,"DT_ENERGY_DRAIN":19,
            "DT_SUICIDE":20,"DT_PHYSICAL":21,"DT_BASE_ELEMENTAL":22,"DT_COMPOUND_ELEMENTAL":23,
            "DT_ANY":0,"DT_INVALID":24}

modifiers = {
    'Ferrite' :          np.array([1.00, 1.50, 0.85, 1.00, 1.00, 1.00, 1.00, 0.75, 1.00, 1.00, 1.00, 1.00, 1.75, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),
    'Alloy' :            np.array([1.00, 1.15, 0.50, 1.00, 1.25, 0.50, 1.00, 1.00, 1.75, 1.00, 0.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),
    'Infested Sinew' :   np.array([1.00, 1.25, 1.00, 1.00, 1.25, 1.00, 1.00, 0.50, 1.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),

    'Proto Shield' :     np.array([1.15, 0.50, 1.00, 0.50, 1.00, 1.00, 0.00, 1.00, 1.00, 1.00, 1.75, 1.00, 0.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),
    'Shield' :           np.array([1.50, 0.80, 1.00, 1.00, 1.50, 1.00, 0.00, 1.00, 0.75, 1.00, 1.75, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),
    'Eidolon Shield' :   np.array([0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00]),

    'Infested' :         np.array([1.00, 1.00, 1.25, 1.25, 1.00, 1.00, 1.00, 1.00, 0.50, 1.75, 1.00, 0.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),
    'Robotic' :          np.array([1.00, 1.25, 0.75, 1.00, 1.00, 1.50, 0.75, 1.00, 1.25, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),
    'Cloned Flesh' :     np.array([0.75, 1.00, 1.25, 1.25, 1.00, 1.00, 1.00, 1.00, 1.00, 0.50, 1.00, 1.75, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),
    'Infested Flesh' :   np.array([1.00, 1.00, 1.50, 1.50, 0.50, 1.00, 1.00, 1.00, 1.00, 1.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),
    'Flesh' :            np.array([0.75, 1.00, 1.25, 1.00, 1.00, 1.00, 1.50, 1.00, 1.00, 0.75, 1.00, 1.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),
    'Fossilized' :       np.array([1.00, 1.00, 1.15, 1.00, 0.75, 1.00, 0.50, 1.50, 0.25, 1.00, 1.00, 1.00, 1.75, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),
    'Machinery' :        np.array([1.25, 1.00, 1.00, 1.00, 1.00, 1.50, 0.75, 1.75, 1.00, 1.00, 1.00, 0.75, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00]),

    'Tenno Shield' :     np.array([0.75]*20, dtype=float),
    'Tenno Health' :     np.array([1]*20, dtype=float),
    'Tenno Armor' :      np.array([1]*20, dtype=float),

    'Overguard' :        np.array([1]*13+[1.5]+[1]*6, dtype=float),
    'None' :          np.array([1]*20, dtype=float)
}

protection_scale_factors = { "health": [{"is_eximus": False, "level_start":1, "level_stop":9999, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.015, 2], "f_hi": [1, 24*(5**0.5)/5, 0.5], "f_bonus": [1, 0]}, 
                                        {"is_eximus": True, "level_start":1, "level_stop":25, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.015, 2], "f_hi": [1, 24*(5**0.5)/5, 0.5], "f_bonus": [1, 0]},
                                        {"is_eximus": True, "level_start":25, "level_stop":35, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.015, 2], "f_hi": [1, 24*(5**0.5)/5, 0.5], "f_bonus": [1, 0.05]},
                                        {"is_eximus": True, "level_start":35, "level_stop":50, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.015, 2], "f_hi": [1, 24*(5**0.5)/5, 0.5], "f_bonus": [1.5, 0.1]},
                                        {"is_eximus": True, "level_start":50, "level_stop":100, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.015, 2], "f_hi": [1, 24*(5**0.5)/5, 0.5], "f_bonus": [3, 0.02]},
                                        {"is_eximus": True, "level_start":100, "level_stop":9999, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.015, 2], "f_hi": [1, 24*(5**0.5)/5, 0.5], "f_bonus": [4, 0]}
                                        ],
                            "armor": [{"is_eximus": False, "level_start":1, "level_stop":9999, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.005, 1.75], "f_hi": [1, 0.4, 0.75], "f_bonus": [1, 0]}, 
                                        {"is_eximus": True, "level_start":1, "level_stop":25, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.005, 1.75], "f_hi": [1, 0.4, 0.75], "f_bonus": [1, 0]},
                                        {"is_eximus": True, "level_start":25, "level_stop":35, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.005, 1.75], "f_hi": [1, 0.4, 0.75], "f_bonus": [1, 0.0125]},
                                        {"is_eximus": True, "level_start":35, "level_stop":50, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.005, 1.75], "f_hi": [1, 0.4, 0.75], "f_bonus": [1.125, 1/15]},
                                        {"is_eximus": True, "level_start":50, "level_stop":100, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.005, 1.75], "f_hi": [1, 0.4, 0.75], "f_bonus": [1.375, 0.005]},
                                        {"is_eximus": True, "level_start":100, "level_stop":9999, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.005, 1.75], "f_hi": [1, 0.4, 0.75], "f_bonus": [1.625, 0]}
                                        ],
                            "shield": [{"is_eximus": False, "level_start":1, "level_stop":9999, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.02, 1.75], "f_hi": [1, 1.6, 0.75], "f_bonus": [1, 0]}, 
                                        {"is_eximus": True, "level_start":1, "level_stop":25, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.02, 1.75], "f_hi": [1, 1.6, 0.75], "f_bonus": [1, 0]},
                                        {"is_eximus": True, "level_start":25, "level_stop":35, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.02, 1.75], "f_hi": [1, 1.6, 0.75], "f_bonus": [1, 0.0325]},
                                        {"is_eximus": True, "level_start":35, "level_stop":50, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.02, 1.75], "f_hi": [1, 1.6, 0.75], "f_bonus": [1.325, 0.065]},
                                        {"is_eximus": True, "level_start":50, "level_stop":100, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.02, 1.75], "f_hi": [1, 1.6, 0.75], "f_bonus": [2.3, 0.013]},
                                        {"is_eximus": True, "level_start":100, "level_stop":9999, "smoothstep_start": 70, "smoothstep_stop":80, "f_low": [1, 0.02, 1.75], "f_hi": [1, 1.6, 0.75], "f_bonus": [2.95, 0]}
                                        ],
                            "overguard": [{"is_eximus": False, "level_start":1, "level_stop":9999, "smoothstep_start": 45, "smoothstep_stop":50, "f_low": [1, 0.0015, 4], "f_hi": [1, 260, 0.9], "f_bonus": [1, 0]}, 
                                        {"is_eximus": True, "level_start":1, "level_stop":9999, "smoothstep_start": 45, "smoothstep_stop":50, "f_low": [1, 0.0015, 4], "f_hi": [1, 260, 0.9], "f_bonus": [1, 0]}
                                        ]}


PROC_INFO = {0:{"name":"Impact", "duration":6, "max_stacks":5}, 1:{"name":"Puncture", "duration":6, "max_stacks":5}, 2:{"name":"Slash", "duration":6, "max_stacks":10000}, 
             3:{"name":"Heat", "duration":6, "max_stacks":10000}, 4:{"name":"Cold", "duration":6, "max_stacks":9}, 5:{"name":"Electric", "duration":6, "max_stacks":10000}, 
             6:{"name":"Toxin", "duration":6, "max_stacks":10000}, 7:{"name":"Blast", "duration":6, "max_stacks":10}, 8:{"name":"Radiation", "duration":12, "max_stacks":10}, 
             9:{"name":"Gas", "duration":6, "max_stacks":10}, 10:{"name":"Magnetic", "duration":6, "max_stacks":10}, 11:{"name":"Viral", "duration":6, "max_stacks":10}, 
             12:{"name":"Corrosive", "duration":8, "max_stacks":10}, 13:{"name":"Void", "duration":3, "max_stacks":1}}

PROCID_DAMAGETYPE = {i:i for i in range(14)}
PROCID_DAMAGETYPE[2] = 16 # slash -> cinematic

MAX_TIME_OFFSET = 1000

BASE_RULE  = r"(?<=^)(?:-?\d+(?:\.\d*)?|-?\.\d+)(?=$|[\s,])|(?<=[\s,\$?])(?:-?\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])"
RIVEN_RULE =r"(?<=^)(?:\$-?\d+(?:\.\d*)?|-?\.\d+)(?=$|[\s,])|(?<=[\s,])(?:\$-?\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])"
BASE_ADDITIVE_RULE =r"(?<=^a)(?:-?\d+(?:\.\d*)?|-?\.\d+)(?=$|[\s,])|(?<=[\s,]a)(?:-?\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])"
FINAL_ADDITIVE_RULE =r"(?<=^)(?:-?\d+(?:\.\d*)?|-?\.\d+)(?=a$|a[\s,])|(?<=[\s,])(?:-?\d+(?:\.\d*)?|\.\d+)(?=a$|a[\s,])"
UNCOMBINED_RULE =r"(?<=^ue)(?:\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])|(?<=[\s,]ue)(?:\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])"
MULTIPLIER_RULE =r"(?<=^x)(?:\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])|(?<=[\s,]x)(?:\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])"
PERCENT_RULE =r"(?<=^)(?:-?\d+(?:\.\d*)?|-?\.\d+)(?=%$|%[\s,])|(?<=[\s,])(?:-?\d+(?:\.\d*)?|\.\d+)(?=%$|%[\s,])"

DAMAGE_NONE = np.array([0]*20, dtype=float)

HEAT_ARMOR_STRIP = {0:1, 1:0.85, 2:0.7, 3:0.6, 4:0.5}
CORROSIVE_ARMOR_STRIP = {0:1, 1:0.74, 2:0.68, 3:0.62, 4:0.56, 5:0.50, 6:0.44, 7:0.38, 8:0.32, 9:0.26, 10:0.2}
VIRAL_DEBUFF = {0:1, 1:2, 2:2.25, 3:2.5, 4:2.75, 5:3, 6:3.25, 7:3.5, 8:3.75, 9:4, 10:4.25}
MAGNETIC_DEBUFF = {0:1, 1:2, 2:2.25, 3:2.5, 4:2.75, 5:3, 6:3.25, 7:3.5, 8:3.75, 9:4, 10:4.25}

ARMOR_RATIO = 1/300
COMBINE_ADD = 'COMBINE_ADD'
COMBINE_MULTIPLY = 'COMBINE_MULTIPLY'