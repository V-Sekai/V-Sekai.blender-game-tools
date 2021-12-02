

# ---------------- BONE DICTIONARY -------------------
# | - holds the matching values for the
# | - FaceitRig to the landmarks(vert index)
# | - asymmetric and symmetric vert order
# ----------------------------------------------


# ---------------- ASYMMETRIC ------------------------
# | - 0-70 : vertices in the reference mesh
# | - 100-.. : other world points such as eye or jaw


bone_dict_asymmetric = {
    0: {
        'head': ['DEF-chin'],
        'tail': ['jaw_master', 'DEF-jaw'],
        'all': ['chin', ],
    },
    1: {
        'head': ['DEF-jaw'],
        'tail': [],
        'all': ['jaw'],
    },
    2: {
        'head': ['DEF-chin.001'],
        'tail': ['DEF-chin', ],
        'all': ['chin.001', ],
    },
    3: {
        'head': [],
        'tail': ['DEF-chin.001'],
        'all': ['chin.002'],
    },
    4: {
        'head': ['DEF-chin.R'],
        'tail': ['DEF-jaw.R.001'],
        'all': ['chin.R'],
    },
    5: {
        'head': ['DEF-chin.L'],
        'tail': ['DEF-jaw.L.001'],
        'all': ['chin.L'],
    },
    6: {
        'head': ['DEF-lip.B.L', 'DEF-lip.B.R'],
        'tail': [],
        'all': ['lip.B'],
    },
    7: {
        'head': ['DEF-lip.B.R.001'],
        'tail': ['DEF-lip.B.R'],
        'all': ['lip.B.R.001'],
    },
    8: {
        'head': ['DEF-lip.B.L.001'],
        'tail': ['DEF-lip.B.L'],
        'all': ['lip.B.L.001'],
    },
    9: {
        'head': ['DEF-lip.T.L', 'DEF-lip.T.R'],
        'tail': [],
        'all': ['lip.T'],
    },
    10: {
        'head': ['DEF-lip.T.R.001'],
        'tail': ['DEF-lip.T.R'],
        'all': ['lip.T.R.001'],
    },
    11: {
        'head': ['DEF-lip.T.L.001'],
        'tail': ['DEF-lip.T.L'],
        'all': ['lip.T.L.001'],
    },
    12: {
        'head': ['DEF-cheek.B.L'],
        'tail': ['DEF-chin.L', 'DEF-lip.T.L.001', 'DEF-lip.B.L.001'],
        'all': ['lips.L'],
    },
    13: {
        'head': ['DEF-cheek.B.R'],
        'tail': ['DEF-chin.R', 'DEF-lip.T.R.001', 'DEF-lip.B.R.001'],
        'all': ['lips.R'],
    },
    14: {
        'head': [],
        'tail': ['DEF-nose.003'],
        'all': ['DEF-nose.004', 'nose.004', 'nose_master'],
    },
    # cheeck low
    15: {
        'head': ['DEF-cheek.B.R.001'],
        'tail': ['DEF-cheek.B.R'],
        'all': ['cheek.B.R.001'],
    },
    16: {
        'head': ['DEF-cheek.B.L.001'],
        'tail': ['DEF-cheek.B.L'],
        'all': ['cheek.B.L.001'],
    },
    17: {
        'head': ['DEF-nose.L.001'],
        'tail': ['DEF-nose.L'],
        'all': ['nose.L.001'],
    },
    18: {
        'head': ['DEF-nose.R.001'],
        'tail': ['DEF-nose.R'],
        'all': ['nose.R.001'],
    },
    19: {
        'head': ['DEF-jaw.L.001'],
        'tail': ['DEF-jaw.L'],
        'all': ['jaw.L.001'],
    },
    20: {
        'head': ['DEF-jaw.R.001'],
        'tail': ['DEF-jaw.R'],
        'all': ['jaw.R.001'],
    },
    21: {
        'head': ['DEF-nose.002'],
        'tail': ['DEF-nose.L.001', 'DEF-nose.R.001', 'DEF-nose.001'],
        'all': ['nose.002'],
    },
    22: {
        'head': ['DEF-cheek.T.R.001'],
        'tail': ['DEF-cheek.T.R'],
        'all': ['cheek.T.R.001'],
    },
    23: {
        'head': ['DEF-cheek.T.L.001'],
        'tail': ['DEF-cheek.T.L'],
        'all': ['cheek.T.L.001'],
    },

    24: {
        'head': ['DEF-jaw.R'],
        'tail': ['DEF-temple.R'],
        'all': ['jaw.R'],
    },
    25: {
        'head': ['DEF-jaw.L'],
        'tail': ['DEF-temple.L'],
        'all': ['jaw.L'],
    },
    26: {
        'head': ['DEF-nose.L'],
        'tail': ['DEF-cheek.T.L.001'],
        'all': ['nose.L'],
    },
    27: {
        'head': ['DEF-nose.R'],
        'tail': ['DEF-cheek.T.R.001'],
        'all': ['nose.R'],
    },
    28: {
        'head': ['DEF-lid.B.R.001'],
        'tail': ['MCH-lid.B.R.001', 'DEF-lid.B.R'],
        'all': ['lid.B.R.001'],
    },
    29: {
        'head': ['DEF-lid.B.L.001'],
        'tail': ['MCH-lid.B.L.001', 'DEF-lid.B.L'],
        'all': ['lid.B.L.001'],
    },
    30: {
        'head': ['DEF-lid.B.L.002'],
        'tail': ['DEF-lid.B.L.001', 'MCH-lid.B.L.002'],
        'all': ['lid.B.L.002'],
    },
    31: {
        'head': ['DEF-lid.B.R.002'],
        'tail': ['DEF-lid.B.R.001', 'MCH-lid.B.R.002'],
        'all': ['lid.B.R.002'],
    },
    32: {
        'head': ['DEF-lid.B.L'],
        'tail': ['DEF-lid.T.L.003', 'MCH-lid.B.L'],
        'all': ['lid.B.L'],
    },
    33: {
        'head': ['DEF-lid.B.R'],
        'tail': ['DEF-lid.T.R.003', 'MCH-lid.B.R'],
        'all': ['lid.B.R'],
    },
    34: {
        'head': ['DEF-lid.B.L.003'],
        'tail': ['DEF-lid.B.L.002', 'MCH-lid.B.L.003'],
        'all': ['lid.B.L.003'],
    },
    35: {
        'head': ['DEF-lid.B.R.003'],
        'tail': ['DEF-lid.B.R.002', 'MCH-lid.B.R.003'],
        'all': ['lid.B.R.003'],
    },
    36: {
        'head': ['DEF-nose'],
        'tail': ['DEF-brow.T.L.003', 'DEF-brow.T.R.003'],
        'all': ['nose'],
    },
    37: {
        'head': ['DEF-lid.T.L.003'],
        'tail': ['DEF-lid.T.L.002', 'MCH-lid.T.L.003'],
        'all': ['lid.T.L.003'],
    },
    38: {
        'head': ['DEF-lid.T.R.003'],
        'tail': ['DEF-lid.T.R.002', 'MCH-lid.T.R.003'],
        'all': ['lid.T.R.003'],
    },
    39: {
        'head': [],
        'tail': ['DEF-brow.B.R.003'],
        'all': ['brow.B.R.004'],
    },
    40: {
        'head': [],
        'tail': ['DEF-brow.B.L.003'],
        'all': ['brow.B.L.004'],
    },
    41: {
        'head': ['DEF-lid.T.L'],
        'tail': ['DEF-lid.B.L.003', 'MCH-lid.T.L'],
        'all': ['lid.T.L'],
    },
    42: {
        'head': ['DEF-lid.T.R'],
        'tail': ['DEF-lid.B.R.003', 'MCH-lid.T.R'],
        'all': ['lid.T.R'],
    },
    43: {
        'head': ['DEF-lid.T.R.002'],
        'tail': ['DEF-lid.T.R.001', 'MCH-lid.T.R.002'],
        'all': ['lid.T.R.002'],
    },
    44: {
        'head': ['DEF-lid.T.L.002'],
        'tail': ['DEF-lid.T.L.001', 'MCH-lid.T.L.002'],
        'all': ['lid.T.L.002'],
    },
    45: {
        'head': ['DEF-lid.T.L.001'],
        'tail': ['DEF-lid.T.L', 'MCH-lid.T.L.001'],
        'all': ['lid.T.L.001'],
    },
    46: {
        'head': ['DEF-lid.T.R.001'],
        'tail': ['DEF-lid.T.R', 'MCH-lid.T.R.001'],
        'all': ['lid.T.R.001'],
    },
    47: {
        'head': ['DEF-brow.B.L.003'],
        'tail': ['DEF-brow.B.L.002'],
        'all': ['brow.B.L.003'],
    },
    48: {
        'head': ['DEF-brow.B.R.003'],
        'tail': ['DEF-brow.B.R.002'],
        'all': ['brow.B.R.003'],
    },
    49: {
        'head': ['DEF-brow.T.L', 'DEF-cheek.T.L'],
        'tail': ['DEF-cheek.B.L.001'],
        'all': ['brow.T.L'],
    },
    50: {
        'head': ['DEF-brow.T.R', 'DEF-cheek.T.R'],
        'tail': ['DEF-cheek.B.R.001'],
        'all': ['brow.T.R'],
    },
    51: {
        'head': ['DEF-brow.B.R'],
        'tail': [],
        'all': ['brow.B.R'],
    },
    52: {
        'head': ['DEF-brow.B.L'],
        'tail': [],
        'all': ['brow.B.L'],
    },
    53: {
        'head': ['DEF-brow.B.R.002'],
        'tail': ['DEF-brow.B.R.001'],
        'all': ['brow.B.R.002'],
    },
    54: {
        'head': ['DEF-brow.B.L.002'],
        'tail': ['DEF-brow.B.L.001'],
        'all': ['brow.B.L.002'],
    },
    55: {
        'head': ['DEF-brow.B.R.001'],
        'tail': ['DEF-brow.B.R'],
        'all': ['brow.B.R.001'],
    },
    56: {
        'head': ['DEF-brow.B.L.001'],
        'tail': ['DEF-brow.B.L'],
        'all': ['brow.B.L.001'],
    },
    57: {
        'head': ['DEF-brow.T.L.003'],
        'tail': ['DEF-brow.T.L.002', 'DEF-forehead.L'],
        'all': ['brow.T.L.003'],
    },
    58: {
        'head': ['DEF-brow.T.R.003'],
        'tail': ['DEF-brow.T.R.002', 'DEF-forehead.R'],
        'all': ['brow.T.R.003'],
    },
    59: {
        'head': ['DEF_forhead_01.L', 'DEF-temple.L'],
        'tail': [],
        'all': [],
    },
    60: {
        'head': ['DEF_forhead_01.R', 'DEF-temple.R'],
        'tail': [],
        'all': [],
    },
    61: {
        'head': ['DEF-brow.T.R.001'],
        'tail': ['DEF-brow.T.R', 'DEF-forehead.R.002'],
        'all': ['brow.T.R.001'],
    },
    62: {
        'head': ['DEF-brow.T.L.001'],
        'tail': ['DEF-brow.T.L', 'DEF-forehead.L.002'],
        'all': ['brow.T.L.001'],
    },
    63: {
        'head': ['DEF-brow.T.L.002'],
        'tail': ['DEF-brow.T.L.001', 'DEF-forehead.L.001'],
        'all': ['brow.T.L.002'],
    },
    64: {
        'head': ['DEF-brow.T.R.002'],
        'tail': ['DEF-brow.T.R.001', 'DEF-forehead.R.001'],
        'all': ['brow.T.R.002'],
    },
    65: {
        'head': [],
        'tail': ['DEF_forhead_04.L', 'DEF_forhead_04.R'],
        'all': [],
    },
    66: {
        'head': ['DEF-forehead.R', 'DEF_forhead_04.R'],
        'tail': ['DEF_forhead_03.R'],
        'all': [],
    },
    67: {
        'head': ['DEF-forehead.L', 'DEF_forhead_04.L'],
        'tail': ['DEF_forhead_03.L'],
        'all': [],
    },
    68: {
        'head': ['DEF_forhead_02.R', 'DEF-forehead.R.002'],
        'tail': ['DEF_forhead_01.R'],
        'all': [],
    },
    69: {
        'head': ['DEF_forhead_02.L', 'DEF-forehead.L.002'],
        'tail': ['DEF_forhead_01.L'],
        'all': [],
    },
    70: {
        'head': ['DEF_forhead_03.R', 'DEF-forehead.R.001'],
        'tail': ['DEF_forhead_02.R'],
        'all': [],
    },
    71: {
        'head': ['DEF_forhead_03.L', 'DEF-forehead.L.001'],
        'tail': ['DEF_forhead_02.L'],
        'all': [],
    },

    101: {
        'head': ['MCH-lid.T.L', 'MCH-lid.T.L.001', 'MCH-lid.T.L.002', 'MCH-lid.T.L.003', 'MCH-lid.B.L', 'MCH-lid.B.L.001', 'MCH-lid.B.L.002', 'MCH-lid.B.L.003', ],
        'tail': [],
        'all': ['master_eye.L', 'DEF_eye.L', 'MCH-eye.L'],
    },
    102: {
        'head': [],
        'tail': [],
        'all': ['jaw_master', 'MCH-mouth_lock', 'MCH-jaw_master', 'MCH-jaw_master.001', 'MCH-jaw_master.002', 'MCH-jaw_master.003', 'MCH-jaw_master.004'],
    },
    103: {
        'head': ['DEF-nose.001'],
        'tail': ['DEF-nose'],
        'all': ['nose.001'],
    },
    104: {
        'head': [],
        'tail': ['DEF-nose.004'],
        'all': ['nose.005'],
    },
    105: {
        'head': ['DEF-nose.003'],
        'tail': ['DEF-nose.002'],
        'all': ['nose.003'],
    },
    106: {
        'head': [],
        'tail': [],
        'all': ['DEF-teeth.T', 'teeth.T'],
    },
    107: {
        'head': [],
        'tail': [],
        'all': ['DEF-teeth.B', 'teeth.B'],
    },
    108: {
        'head': [],
        'tail': [],
        'all': ['tongue_master', 'tongue', 'DEF-tongue', 'tongue.003', 'MCH-tongue.001', 'tongue.001', 'DEF-tongue.001', 'MCH-tongue.002', 'tongue.002', 'DEF-tongue.002'],
    },
    109: {
        'head': [],
        'tail': [],
        'all': ['DEF-face', 'MCH-eyes_parent']
    },
    111: {
        'head': ['MCH-lid.T.R', 'MCH-lid.T.R.001', 'MCH-lid.T.R.002', 'MCH-lid.T.R.003', 'MCH-lid.B.R', 'MCH-lid.B.R.001', 'MCH-lid.B.R.002', 'MCH-lid.B.R.003', ],
        'tail': [],
        'all': ['master_eye.R', 'DEF_eye.R', 'MCH-eye.R'],
    },

}
# ---------------- SYMMETRIC -------------------------
# | - 0-40 : vertices in the reference mesh
# | - 100-.. : other world points such as eye or jaw
# ----------------------------------------------------
bone_dict_symmetric = {
    0: {
        'head': ['DEF-jaw'],
        'tail': [],
        'all': ['jaw'],
    },
    1: {
        'head': ['DEF-chin'],
        'tail': ['jaw_master', 'DEF-jaw'],
        'all': ['chin', ],
    },
    2: {
        'head': ['DEF-chin.001'],
        'tail': ['DEF-chin', ],
        'all': ['chin.001', ],
    },
    3: {
        'head': [],
        'tail': ['DEF-chin.001'],
        'all': ['chin.002'],
    },
    # chin side
    4: {
        'head': ['DEF-chin.L'],
        'tail': ['DEF-jaw.L.001'],
        'all': ['chin.L'],
    },
    # lowerlip mid
    5: {
        'head': ['DEF-lip.B.L'],
        'tail': [],
        'all': ['lip.B'],
    },
    # lower lip side
    6: {
        'head': ['DEF-lip.B.L.001'],
        'tail': ['DEF-lip.B.L'],
        'all': ['lip.B.L.001'],
    },
    # lip corner
    7: {
        'head': ['DEF-cheek.B.L'],
        'tail': ['DEF-chin.L', 'DEF-lip.T.L.001', 'DEF-lip.B.L.001'],
        'all': ['lips.L'],
    },
    # upper lip mid
    8: {
        'head': ['DEF-lip.T.L'],
        'tail': [],
        'all': ['lip.T'],
    },
    # upper lip side
    9: {
        'head': ['DEF-lip.T.L.001'],
        'tail': ['DEF-lip.T.L'],
        'all': ['lip.T.L.001'],
    },
    # nose low
    10: {
        'head': [],
        'tail': ['DEF-nose.003'],
        'all': ['DEF-nose.004', 'nose.004', 'nose_master'],
    },
    # nose tip
    11: {
        'head': ['DEF-nose.002'],
        'tail': ['DEF-nose.L.001', 'DEF-nose.001'],
        'all': ['nose.002'],
    },
    # jaw mid
    12: {
        'head': ['DEF-jaw.L.001'],
        'tail': ['DEF-jaw.L'],
        'all': ['jaw.L.001'],
    },
    # nose wing
    13: {
        'head': ['DEF-nose.L.001'],
        'tail': ['DEF-nose.L'],
        'all': ['nose.L.001'],
    },
    # cheeck low
    14: {
        'head': ['DEF-cheek.B.L.001'],
        'tail': ['DEF-cheek.B.L'],
        'all': ['cheek.B.L.001'],
    },
    # cheeck high
    15: {
        'head': ['DEF-cheek.T.L.001'],
        'tail': ['DEF-cheek.T.L'],
        'all': ['cheek.T.L.001'],
    },
    # nose side
    16: {
        'head': ['DEF-nose.L'],
        'tail': ['DEF-cheek.T.L.001'],
        'all': ['nose.L'],
    },
    # EL_lower_1
    17: {
        'head': ['DEF-lid.B.L.001'],
        'tail': ['MCH-lid.B.L.001', 'DEF-lid.B.L'],
        'all': ['lid.B.L.001'],
    },
    # EL_corner
    18: {
        'head': ['DEF-lid.B.L'],
        'tail': ['DEF-lid.T.L.003', 'MCH-lid.B.L'],
        'all': ['lid.B.L'],
    },
    # nose side
    19: {
        'head': ['DEF-lid.B.L.002'],
        'tail': ['DEF-lid.B.L.001', 'MCH-lid.B.L.002'],
        'all': ['lid.B.L.002'],
    },
    # nose side
    20: {
        'head': [],
        'tail': ['DEF-brow.B.L.003'],
        'all': ['brow.B.L.004'],
    },
    21: {
        'head': ['DEF-nose'],
        'tail': ['DEF-brow.T.L.003'],
        'all': ['nose'],
    },
    22: {
        'head': ['DEF-jaw.L'],
        'tail': ['DEF-temple.L'],
        'all': ['jaw.L'],
    },
    23: {
        'head': ['DEF-lid.T.L.003'],
        'tail': ['DEF-lid.T.L.002', 'MCH-lid.T.L.003'],
        'all': ['lid.T.L.003'],
    },
    24: {
        'head': ['DEF-lid.B.L.003'],
        'tail': ['MCH-lid.B.L.003', 'DEF-lid.B.L.002'],
        'all': ['lid.B.L.003'],
    },
    25: {
        'head': ['DEF-brow.T.L', 'DEF-cheek.T.L'],
        'tail': ['DEF-cheek.B.L.001'],
        'all': ['brow.T.L'],
    },
    26: {
        'head': ['DEF-brow.B.L.003'],
        'tail': ['DEF-brow.B.L.002'],
        'all': ['brow.B.L.003'],
    },
    27: {
        'head': ['DEF-lid.T.L.002'],
        'tail': ['DEF-lid.T.L.001', 'MCH-lid.T.L.002'],
        'all': ['lid.T.L.002'],
    },
    28: {
        'head': ['DEF-lid.T.L'],
        'tail': ['DEF-lid.B.L.003', 'MCH-lid.T.L'],
        'all': ['lid.T.L'],
    },
    29: {
        'head': ['DEF-lid.T.L.001'],
        'tail': ['DEF-lid.T.L', 'MCH-lid.T.L.001'],
        'all': ['lid.T.L.001'],
    },
    30: {
        'head': ['DEF-brow.T.L.003'],
        'tail': ['DEF-brow.T.L.002', 'DEF-forehead.L'],
        'all': ['brow.T.L.003'],
    },
    31: {
        'head': ['DEF-brow.B.L.002'],
        'tail': ['DEF-brow.B.L.001'],
        'all': ['brow.B.L.002'],
    },
    32: {
        'head': ['DEF-brow.B.L'],
        'tail': [],
        'all': ['brow.B.L'],
    },
    33: {
        'head': ['DEF-brow.B.L.001'],
        'tail': ['DEF-brow.B.L'],
        'all': ['brow.B.L.001'],
    },
    34: {
        'head': ['DEF-brow.T.L.002'],
        'tail': ['DEF-brow.T.L.001', 'DEF-forehead.L.001'],
        'all': ['brow.T.L.002'],
    },
    35: {
        'head': ['DEF-brow.T.L.001'],
        'tail': ['DEF-brow.T.L', 'DEF-forehead.L.002'],
        'all': ['brow.T.L.001'],
    },
    36: {
        'head': [],
        'tail': ['DEF_forhead_04.L'],
        'all': [],
    },
    37: {
        'head': ['DEF_forhead_01.L', 'DEF-temple.L'],
        'tail': [],
        'all': [],
    },
    38: {
        'head': ['DEF-forehead.L', 'DEF_forhead_04.L'],
        'tail': ['DEF_forhead_03.L'],
        'all': [],
    },
    39: {
        'head': ['DEF_forhead_03.L', 'DEF-forehead.L.001'],
        'tail': ['DEF_forhead_02.L'],
        'all': [],
    },
    40: {
        'head': ['DEF_forhead_02.L', 'DEF-forehead.L.002'],
        'tail': ['DEF_forhead_01.L'],
        'all': [],
    },
    101: {
        'head': ['MCH-lid.T.L', 'MCH-lid.T.L.001', 'MCH-lid.T.L.002', 'MCH-lid.T.L.003', 'MCH-lid.B.L', 'MCH-lid.B.L.001', 'MCH-lid.B.L.002', 'MCH-lid.B.L.003', ],
        'tail': [],
        'all': ['master_eye.L', 'DEF_eye.L', 'MCH-eye.L'],
    },
    102: {
        'head': [],
        'tail': [],
        'all': ['jaw_master', 'MCH-mouth_lock', 'MCH-jaw_master', 'MCH-jaw_master.001', 'MCH-jaw_master.002', 'MCH-jaw_master.003', 'MCH-jaw_master.004'],
    },
    103: {
        'head': ['DEF-nose.001'],
        'tail': ['DEF-nose'],
        'all': ['nose.001'],
    },
    104: {
        'head': [],
        'tail': ['DEF-nose.004'],
        'all': ['nose.005'],
    },
    105: {
        'head': ['DEF-nose.003'],
        'tail': ['DEF-nose.002'],
        'all': ['nose.003'],
    },
    106: {
        'head': [],
        'tail': [],
        'all': ['DEF-teeth.T', 'teeth.T'],
    },
    107: {
        'head': [],
        'tail': [],
        'all': ['DEF-teeth.B', 'teeth.B'],
    },
    108: {
        'head': [],
        'tail': [],
        'all': ['tongue_master', 'tongue', 'DEF-tongue', 'tongue.003', 'MCH-tongue.001', 'tongue.001', 'DEF-tongue.001', 'MCH-tongue.002', 'tongue.002', 'DEF-tongue.002'],
    },
    109: {
        'head': [],
        'tail': [],
        'all': ['DEF-face', 'MCH-eyes_parent']
    },
    111: {
        'head': ['MCH-lid.T.R', 'MCH-lid.T.R.001', 'MCH-lid.T.R.002', 'MCH-lid.T.R.003', 'MCH-lid.B.R', 'MCH-lid.B.R.001', 'MCH-lid.B.R.002', 'MCH-lid.B.R.003', ],
        'tail': [],
        'all': ['master_eye.R', 'DEF_eye.R', 'MCH-eye.R'],
    },
}
