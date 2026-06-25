class PROTOTYPE_H:

    """Register: reg0"""
    REG0_SW = "rw"
    REG0_HW = "r"
    REG0_WIDTH = 3
    REG0_OFFSET = 0x0
    REG0_RESET = 0x0

    """ Field: field0 """
    REG0_FIELD0_OFFSET = 0
    REG0_FIELD0_WIDTH = 1
    REG0_FIELD0_RESET = 0x0
    REG0_FIELD0_MASK = 0x1
    REG0_FIELD0_SW = "rw"
    REG0_FIELD0_HW = "r"

    """ Field: field1 """
    REG0_FIELD1_OFFSET = 1
    REG0_FIELD1_WIDTH = 2
    REG0_FIELD1_RESET = 0x0
    REG0_FIELD1_MASK = 0x6
    REG0_FIELD1_SW = "rw"
    REG0_FIELD1_HW = "r"

    """Register: reg1"""
    REG1_SW = "ro"
    REG1_HW = "w"
    REG1_WIDTH = 6
    REG1_OFFSET = 0x4
    REG1_RESET = 0x0

    """ Field: field0 """
    REG1_FIELD0_OFFSET = 0
    REG1_FIELD0_WIDTH = 4
    REG1_FIELD0_RESET = 0x0
    REG1_FIELD0_MASK = 0xf
    REG1_FIELD0_SW = "ro"
    REG1_FIELD0_HW = "w"

    """ Field: field1 """
    REG1_FIELD1_OFFSET = 4
    REG1_FIELD1_WIDTH = 1
    REG1_FIELD1_RESET = 0x0
    REG1_FIELD1_MASK = 0x10
    REG1_FIELD1_SW = "ro"
    REG1_FIELD1_HW = "w"

    """ Field: field2 """
    REG1_FIELD2_OFFSET = 5
    REG1_FIELD2_WIDTH = 1
    REG1_FIELD2_RESET = 0x0
    REG1_FIELD2_MASK = 0x20
    REG1_FIELD2_SW = "ro"
    REG1_FIELD2_HW = "w"

    """Register: reg2"""
    REG2_SW = "wo"
    REG2_HW = "r"
    REG2_WIDTH = 1
    REG2_OFFSET = 0x8
    REG2_RESET = 0x0

    """ Field: field0 """
    REG2_FIELD0_OFFSET = 0
    REG2_FIELD0_WIDTH = 1
    REG2_FIELD0_RESET = 0x0
    REG2_FIELD0_MASK = 0x1
    REG2_FIELD0_SW = "wo"
    REG2_FIELD0_HW = "r"

    """Register: reg3"""
    REG3_SW = "rw"
    REG3_HW = "na"
    REG3_WIDTH = 8
    REG3_OFFSET = 0xc
    REG3_RESET = 0x0

    """ Field: field0 """
    REG3_FIELD0_OFFSET = 0
    REG3_FIELD0_WIDTH = 8
    REG3_FIELD0_RESET = 0x0
    REG3_FIELD0_MASK = 0xff
    REG3_FIELD0_SW = "rw"
    REG3_FIELD0_HW = "na"

    """Register: reg4"""
    REG4_SW = "rw"
    REG4_HW = "r"
    REG4_WIDTH = 9
    REG4_OFFSET = 0x10
    REG4_RESET = 0x0

    """ Field: field0 """
    REG4_FIELD0_OFFSET = 0
    REG4_FIELD0_WIDTH = 4
    REG4_FIELD0_RESET = 0x0
    REG4_FIELD0_MASK = 0xf
    REG4_FIELD0_SW = "rw"
    REG4_FIELD0_HW = "rw"

    """ Field: field1 """
    REG4_FIELD1_OFFSET = 8
    REG4_FIELD1_WIDTH = 1
    REG4_FIELD1_RESET = 0x0
    REG4_FIELD1_MASK = 0x100
    REG4_FIELD1_SW = "rw"
    REG4_FIELD1_HW = "r"

    """Register: reg5"""
    REG5_SW = "rw"
    REG5_HW = "r"
    REG5_WIDTH = 8
    REG5_OFFSET = 0x14
    REG5_RESET = 0x0

    """ Field: field0 """
    REG5_FIELD0_OFFSET = 0
    REG5_FIELD0_WIDTH = 4
    REG5_FIELD0_RESET = 0x0
    REG5_FIELD0_MASK = 0xf
    REG5_FIELD0_SW = "rw"
    REG5_FIELD0_HW = "r"
    REG5_FIELD0_ONREAD = "rclr"

    """ Field: field1 """
    REG5_FIELD1_OFFSET = 4
    REG5_FIELD1_WIDTH = 4
    REG5_FIELD1_RESET = 0x0
    REG5_FIELD1_MASK = 0xf0
    REG5_FIELD1_SW = "rw"
    REG5_FIELD1_HW = "r"
    REG5_FIELD1_ONREAD = "rset"

    """Register: reg6"""
    REG6_SW = "rw"
    REG6_HW = "r"
    REG6_WIDTH = 12
    REG6_OFFSET = 0x18
    REG6_RESET = 0xf0

    """ Field: field0 """
    REG6_FIELD0_OFFSET = 0
    REG6_FIELD0_WIDTH = 4
    REG6_FIELD0_RESET = 0x0
    REG6_FIELD0_MASK = 0xf
    REG6_FIELD0_SW = "rw"
    REG6_FIELD0_HW = "r"
    REG6_FIELD0_ONWRITE = "woset"

    """ Field: field1 """
    REG6_FIELD1_OFFSET = 4
    REG6_FIELD1_WIDTH = 4
    REG6_FIELD1_RESET = 0xf
    REG6_FIELD1_MASK = 0xf0
    REG6_FIELD1_SW = "rw"
    REG6_FIELD1_HW = "r"
    REG6_FIELD1_ONWRITE = "woclr"

    """ Field: field2 """
    REG6_FIELD2_OFFSET = 8
    REG6_FIELD2_WIDTH = 4
    REG6_FIELD2_RESET = 0x0
    REG6_FIELD2_MASK = 0xf00
    REG6_FIELD2_SW = "rw"
    REG6_FIELD2_HW = "r"
    REG6_FIELD2_ONWRITE = "wot"

    """Register: reg7"""
    REG7_SW = "rw"
    REG7_HW = "r"
    REG7_WIDTH = 12
    REG7_OFFSET = 0x1c
    REG7_RESET = 0xf0

    """ Field: field0 """
    REG7_FIELD0_OFFSET = 0
    REG7_FIELD0_WIDTH = 4
    REG7_FIELD0_RESET = 0x0
    REG7_FIELD0_MASK = 0xf
    REG7_FIELD0_SW = "rw"
    REG7_FIELD0_HW = "r"
    REG7_FIELD0_ONWRITE = "wzs"

    """ Field: field1 """
    REG7_FIELD1_OFFSET = 4
    REG7_FIELD1_WIDTH = 4
    REG7_FIELD1_RESET = 0xf
    REG7_FIELD1_MASK = 0xf0
    REG7_FIELD1_SW = "rw"
    REG7_FIELD1_HW = "r"
    REG7_FIELD1_ONWRITE = "wzc"

    """ Field: field2 """
    REG7_FIELD2_OFFSET = 8
    REG7_FIELD2_WIDTH = 4
    REG7_FIELD2_RESET = 0x0
    REG7_FIELD2_MASK = 0xf00
    REG7_FIELD2_SW = "rw"
    REG7_FIELD2_HW = "r"
    REG7_FIELD2_ONWRITE = "wzt"

    """Register: reg8"""
    REG8_SW = "rw"
    REG8_HW = "r"
    REG8_WIDTH = 8
    REG8_OFFSET = 0x20
    REG8_RESET = 0xf

    """ Field: field0 """
    REG8_FIELD0_OFFSET = 0
    REG8_FIELD0_WIDTH = 4
    REG8_FIELD0_RESET = 0xf
    REG8_FIELD0_MASK = 0xf
    REG8_FIELD0_SW = "rw"
    REG8_FIELD0_HW = "r"
    REG8_FIELD0_ONWRITE = "wclr"

    """ Field: field1 """
    REG8_FIELD1_OFFSET = 4
    REG8_FIELD1_WIDTH = 4
    REG8_FIELD1_RESET = 0x0
    REG8_FIELD1_MASK = 0xf0
    REG8_FIELD1_SW = "rw"
    REG8_FIELD1_HW = "r"
    REG8_FIELD1_ONWRITE = "wset"

    """Register: reg9"""
    REG9_SW = "rw"
    REG9_HW = "r"
    REG9_WIDTH = 8
    REG9_OFFSET = 0x24
    REG9_RESET = 0x0

    """ Field: field0 """
    REG9_FIELD0_OFFSET = 0
    REG9_FIELD0_WIDTH = 4
    REG9_FIELD0_RESET = 0x0
    REG9_FIELD0_MASK = 0xf
    REG9_FIELD0_SW = "rw"
    REG9_FIELD0_HW = "r"

    """ Field: field1 """
    REG9_FIELD1_OFFSET = 4
    REG9_FIELD1_WIDTH = 4
    REG9_FIELD1_RESET = 0x0
    REG9_FIELD1_MASK = 0xf0
    REG9_FIELD1_SW = "rw"
    REG9_FIELD1_HW = "r"

    """Register: reg10"""
    REG10_SW = "rw"
    REG10_HW = "r"
    REG10_WIDTH = 4
    REG10_OFFSET = 0x28
    REG10_RESET = 0x0

    """ Field: field0 """
    REG10_FIELD0_OFFSET = 0
    REG10_FIELD0_WIDTH = 4
    REG10_FIELD0_RESET = 0x0
    REG10_FIELD0_MASK = 0xf
    REG10_FIELD0_SW = "rw"
    REG10_FIELD0_HW = "r"
    REG10_FIELD0_SINGLEPULSE = True

    """Register: reg11"""
    REG11_SW = "rw"
    REG11_HW = "r"
    REG11_WIDTH = 2
    REG11_OFFSET = 0x2c
    REG11_RESET = 0x0

    """ Field: field0 """
    REG11_FIELD0_OFFSET = 0
    REG11_FIELD0_WIDTH = 2
    REG11_FIELD0_RESET = 0x0
    REG11_FIELD0_MASK = 0x3
    REG11_FIELD0_SW = "rw"
    REG11_FIELD0_HW = "r"
    REG11_FIELD0_STATE0 = 0
    REG11_FIELD0_STATE1 = 1
    REG11_FIELD0_STATE2 = 2
    REG11_FIELD0_STATE3 = 3
