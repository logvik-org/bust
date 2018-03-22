class EXAMPLE_MODULE_PULSE_H():
    def __init__(self):
    
        self.EXAMPLE_MODULE_PULSE_BASEADDR = 0xffaa0000

        """ Register: reg0 """
        self.REG0_OFFSET = 0x0
        self.REG0_RESET = 0x0

        """ Register: reg1 """
        self.REG1_OFFSET = 0x4
        self.REG1_RESET = 0x1

        """ Register: reg2 """
        self.REG2_OFFSET = 0xc
        self.REG2_RESET = 0x3

        """ Register: reg3 """
        self.REG3_OFFSET = 0x14
        self.REG3_RESET = 0xffffffff

        """ Register: reg4 """
        self.REG4_OFFSET = 0x1c
        self.REG4_RESET = 0xad7

        """ Field: field0 """
        self.REG4_FIELD0_OFFSET = 0
        self.REG4_FIELD0_WIDTH = 1
        self.REG4_FIELD0_RESET = 0x1

        """ Field: field1 """
        self.REG4_FIELD1_OFFSET = 1
        self.REG4_FIELD1_WIDTH = 4
        self.REG4_FIELD1_RESET = 0xb

        """ Field: field2 """
        self.REG4_FIELD2_OFFSET = 5
        self.REG4_FIELD2_WIDTH = 1
        self.REG4_FIELD2_RESET = 0x0

        """ Field: field3 """
        self.REG4_FIELD3_OFFSET = 6
        self.REG4_FIELD3_WIDTH = 15
        self.REG4_FIELD3_RESET = 0x2b

