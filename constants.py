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
modifiers = {
    'Ferrite' :          np.array([1.00, 1.50, 0.85, 1.00, 1.00, 1.00, 1.00, 0.75, 1.00, 1.00, 1.00, 1.00, 1.75, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),
    'Alloy' :            np.array([1.00, 1.15, 0.50, 1.00, 1.25, 0.50, 1.00, 1.00, 1.75, 1.00, 0.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),
    'Infested Sinew' :   np.array([1.00, 1.25, 1.00, 1.00, 1.25, 1.00, 1.00, 0.50, 1.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),

    'Proto Shield' :     np.array([1.15, 0.50, 1.00, 0.50, 1.00, 1.00, 0.00, 1.00, 1.00, 1.00, 1.75, 1.00, 0.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),
    'Shield' :           np.array([1.50, 0.80, 1.00, 1.00, 1.50, 1.00, 0.00, 1.00, 0.75, 1.00, 1.75, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),
    'Eidolon Shield' :   np.array([0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00], dtype=np.single),

    'Infested' :         np.array([1.00, 1.00, 1.25, 1.25, 1.00, 1.00, 1.00, 1.00, 0.50, 1.75, 1.00, 0.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),
    'Robotic' :          np.array([1.00, 1.25, 0.75, 1.00, 1.00, 1.50, 0.75, 1.00, 1.25, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),
    'Cloned Flesh' :     np.array([0.75, 1.00, 1.25, 1.25, 1.00, 1.00, 1.00, 1.00, 1.00, 0.50, 1.00, 1.75, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),
    'Infested Flesh' :   np.array([1.00, 1.00, 1.50, 1.50, 0.50, 1.00, 1.00, 1.00, 1.00, 1.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),
    'Flesh' :            np.array([0.75, 1.00, 1.25, 1.00, 1.00, 1.00, 1.50, 1.00, 1.00, 0.75, 1.00, 1.50, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),
    'Fossilized' :       np.array([1.00, 1.00, 1.15, 1.00, 0.75, 1.00, 0.50, 1.50, 0.25, 1.00, 1.00, 1.00, 1.75, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),
    'Machinery' :        np.array([1.25, 1.00, 1.00, 1.00, 1.00, 1.50, 0.75, 1.75, 1.00, 1.00, 1.00, 0.75, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),
    'Indifferent Facade':np.array([1.00, 1.25, 0.50, 1.00, 1.00, 1.25, 1.00, 1.00, 1.75, 1.00, 1.00, 0.50, 1.00, 1.00, 1.50, 1.00, 1.00, 1.00, 1.00, 1.00], dtype=np.single),

    'Tenno Shield' :     np.array([0.75]*20, dtype=np.single),
    'Tenno Health' :     np.array([1]*20, dtype=np.single),
    'Tenno Armor' :      np.array([1]*20, dtype=np.single),

    'Overguard' :        np.array([1]*13+[1.5]+[1]*6, dtype=np.single),
    'None' :          np.array([1]*20, dtype=np.single)
}

DT_INDEX = {"DT_IMPACT":0, "DT_PUNCTURE":1, "DT_SLASH":2, "DT_HEAT":3,
            "DT_COLD":4,"DT_ELECTRIC":5,"DT_TOXIN":6,"DT_BLAST":7,
            "DT_RADIATION":8,"DT_GAS":9,"DT_MAGNETIC":10,"DT_VIRAL":11,
            "DT_CORROSIVE":12,"DT_FINISHER":13,"DT_RADIANT":14,"DT_SENTIENT":15,
            "DT_CINEMATIC":16,"DT_SHIELD_DRAIN":17,"DT_HEALTH_DRAIN":18,"DT_ENERGY_DRAIN":19,
            "DT_SUICIDE":20,"DT_PHYSICAL":21,"DT_BASE_ELEMENTAL":22,"DT_COMPOUND_ELEMENTAL":23,
            "DT_ANY":0,"DT_INVALID":24}

PT_INDEX = {"PT_IMPACT":0, "PT_PUNCTURE":1, "PT_SLASH":2, "PT_HEAT":3,
            "PT_COLD":4,"PT_ELECTRIC":5,"PT_TOXIN":6,"PT_BLAST":7,
            "PT_RADIATION":8,"PT_GAS":9,"PT_MAGNETIC":10,"PT_VIRAL":11,
            "PT_CORROSIVE":12,"PT_FINISHER":13,"PT_RADIANT":14,"PT_SENTIENT":15,
            "PT_CINEMATIC":16,"PT_SHIELD_DRAIN":17,"PT_HEALTH_DRAIN":18,"PT_ENERGY_DRAIN":19,
            "PT_SUICIDE":20,"PT_PHYSICAL":21,"PT_BASE_ELEMENTAL":22,"PT_COMPOUND_ELEMENTAL":23,
            "PT_ANY":24,"PT_INVALID":25}

INDEX_DT = {v: k for k, v in DT_INDEX.items()}
INDEX_PT = {v: k for k, v in PT_INDEX.items()}

PROC_INFO = {"PT_IMPACT": {"name": "Impact", "duration": 6, "max_stacks": 5}, "PT_PUNCTURE": {"name": "Puncture","duration": 6,"max_stacks": 5},
             "PT_SLASH": {"name": "Slash","duration": 6,"max_stacks": 50000, "damage_scaling":0.35}, "PT_HEAT": {"name": "Heat","duration": 6,"max_stacks": 50000,"refresh": True, "damage_scaling":0.5},
             "PT_COLD": {"name": "Cold","duration": 6,"max_stacks": 9},"PT_ELECTRIC": {"name": "Electric","duration": 6,"max_stacks": 50000, "damage_scaling":0.5},
             "PT_TOXIN": {"name": "Toxin","duration": 6,"max_stacks": 50000, "damage_scaling":0.5},"PT_BLAST": {"name": "Blast","duration": 10,"max_stacks": 4},"PT_RADIATION": {"name": "Radiation","duration": 12,"max_stacks": 10},
             "PT_GAS": {"name": "Gas","duration": 6,"max_stacks": 10, "damage_scaling":0.5},"PT_MAGNETIC": {"name": "Magnetic","duration": 6,"max_stacks": 10},"PT_VIRAL": {"name": "Viral","duration": 6,"max_stacks": 10},
             "PT_CORROSIVE": {"name": "Corrosive","duration": 8,"max_stacks": 10},"PT_RADIANT": {"name": "Void","duration": 3,"max_stacks": 1}}


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
CORROSIVE_ARMOR_STRIP.update({f:max(v,0) for f,v in zip(range(11,26),[0.2-0.06*i for i in range(1,16)])})
VIRAL_DEBUFF = {0:1, 1:2, 2:2.25, 3:2.5, 4:2.75, 5:3, 6:3.25, 7:3.5, 8:3.75, 9:4, 10:4.25}
MAGNETIC_DEBUFF = {0:1, 1:2, 2:2.25, 3:2.5, 4:2.75, 5:3, 6:3.25, 7:3.5, 8:3.75, 9:4, 10:4.25}

ARMOR_RATIO = 1/300
COMBINE_ADD = 'COMBINE_ADD'
COMBINE_MULTIPLY = 'COMBINE_MULTIPLY'

CD_QT = np.float32(4095/32)
I_CD_QT = np.float32(1/CD_QT)
