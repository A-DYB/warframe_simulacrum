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
13  Void
14  True
15  Tau
16  Cinematic (slash proc damage)
17  Shield Drain
18  Health Drain
19  Energy Drain
- Unused types -
20  Suicide
21  Physical
22  Base Elemental
23  Compound Elemental
24  Any
25  Invalid
'''

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

    'Tenno Shield' :     np.array([0.75]*20),
    'Tenno Health' :     np.array([1]*20),
    'Tenno Armor' :      np.array([1]*20),

    'Overguard' :        np.array([1]*13+[1.5]+[1]*6),
    'None' :          np.array([1]*20)
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


# proc_info = {"IMPACT":{"duration":6, "max_stacks":10}, "PUNCTURE":{"duration":6, "max_stacks":10}, "SLASH":{"duration":6, "max_stacks":10}, 
#              "HEAT":{"duration":6, "max_stacks":10}, "COLD":{"duration":6, "max_stacks":10}, "ELECTRIC":{"duration":6, "max_stacks":10}, 
#              "TOXIN":{"duration":6, "max_stacks":10}, "BLAST":{"duration":6, "max_stacks":10}, "RADIATION":{"duration":6, "max_stacks":10}, 
#              "GAS":{"duration":6, "max_stacks":10}, "MAGNETIC":{"duration":6, "max_stacks":10}, "VIRAL":{"duration":6, "max_stacks":10}, 
#              "CORROSIVE":{"duration":6, "max_stacks":10}, "VOID":{"duration":6, "max_stacks":10}}

PROC_INFO = {0:{"name":"Impact", "duration":6, "max_stacks":5}, 1:{"name":"Puncture", "duration":6, "max_stacks":5}, 2:{"name":"Slash", "duration":6, "max_stacks":10000}, 
             3:{"name":"Heat", "duration":6, "max_stacks":10000}, 4:{"name":"Cold", "duration":6, "max_stacks":9}, 5:{"name":"Electric", "duration":6, "max_stacks":10000}, 
             6:{"name":"Toxin", "duration":6, "max_stacks":10000}, 7:{"name":"Blast", "duration":6, "max_stacks":10}, 8:{"name":"Radiation", "duration":12, "max_stacks":10}, 
             9:{"name":"Gas", "duration":6, "max_stacks":10}, 10:{"name":"Magnetic", "duration":6, "max_stacks":10}, 11:{"name":"Viral", "duration":6, "max_stacks":10}, 
             12:{"name":"Corrosive", "duration":8, "max_stacks":10}, 13:{"name":"Void", "duration":3, "max_stacks":1}}

MAX_TIME_OFFSET = 1000

COMBINE_ADD = "COMBINE_ADD"
COMBINE_MULTIPLY = "COMBINE_MULTIPLY"

BASE_RULE  = r"(?<=^)(?:-?\d+(?:\.\d*)?|-?\.\d+)(?=$|[\s,])|(?<=[\s,\$?])(?:-?\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])"
RIVEN_RULE =r"(?<=^)(?:\$-?\d+(?:\.\d*)?|-?\.\d+)(?=$|[\s,])|(?<=[\s,])(?:\$-?\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])"
BASE_ADDITIVE_RULE =r"(?<=^a)(?:-?\d+(?:\.\d*)?|-?\.\d+)(?=$|[\s,])|(?<=[\s,]a)(?:-?\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])"
FINAL_ADDITIVE_RULE =r"(?<=^)(?:-?\d+(?:\.\d*)?|-?\.\d+)(?=a$|a[\s,])|(?<=[\s,])(?:-?\d+(?:\.\d*)?|\.\d+)(?=a$|a[\s,])"
UNCOMBINED_RULE =r"(?<=^ue)(?:\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])|(?<=[\s,]ue)(?:\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])"
MULTIPLIER_RULE =r"(?<=^x)(?:\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])|(?<=[\s,]x)(?:\d+(?:\.\d*)?|\.\d+)(?=$|[\s,])"
PERCENT_RULE =r"(?<=^)(?:-?\d+(?:\.\d*)?|-?\.\d+)(?=%$|%[\s,])|(?<=[\s,])(?:-?\d+(?:\.\d*)?|\.\d+)(?=%$|%[\s,])"

DAMAGE_NONE = np.array([0]*20)

HEAT_ARMOR_STRIP = {0:1, 1:0.85, 2:0.7, 3:0.6, 4:0.5}
CORROSIVE_ARMOR_STRIP = {0:1, 1:0.74, 2:0.68, 3:0.62, 4:0.56, 5:0.50, 6:0.44, 7:0.38, 8:0.32, 9:0.26, 10:0.2}
VIRAL_DEBUFF = {0:1, 1:2, 2:2.25, 3:2.5, 4:2.75, 5:3, 6:3.25, 7:3.5, 8:3.75, 9:4, 10:4.25}
MAGNETIC_DEBUFF = {0:1, 1:2, 2:2.25, 3:2.5, 4:2.75, 5:3, 6:3.25, 7:3.5, 8:3.75, 9:4, 10:4.25}

ARMOR_RATIO = 1/300