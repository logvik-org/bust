#ifndef PROTOTYPE_H
#define PROTOTYPE_H


/* Register: reg0 */
#define REG0_SW "rw"
#define REG0_HW "r"
#define REG0_WIDTH 3
#define REG0_OFFSET 0x0
#define REG0_RESET 0x0

/* Field: field0 */
#define REG0_FIELD0_OFFSET 0
#define REG0_FIELD0_WIDTH 1
#define REG0_FIELD0_RESET 0x0
#define REG0_FIELD0_MASK 0x1
#define REG0_FIELD0_SW "rw"
#define REG0_FIELD0_HW "r"

/* Field: field1 */
#define REG0_FIELD1_OFFSET 1
#define REG0_FIELD1_WIDTH 2
#define REG0_FIELD1_RESET 0x0
#define REG0_FIELD1_MASK 0x6
#define REG0_FIELD1_SW "rw"
#define REG0_FIELD1_HW "r"

/* Register: reg1 */
#define REG1_SW "ro"
#define REG1_HW "w"
#define REG1_WIDTH 6
#define REG1_OFFSET 0x4
#define REG1_RESET 0x0

/* Field: field0 */
#define REG1_FIELD0_OFFSET 0
#define REG1_FIELD0_WIDTH 4
#define REG1_FIELD0_RESET 0x0
#define REG1_FIELD0_MASK 0xf
#define REG1_FIELD0_SW "ro"
#define REG1_FIELD0_HW "w"

/* Field: field1 */
#define REG1_FIELD1_OFFSET 4
#define REG1_FIELD1_WIDTH 1
#define REG1_FIELD1_RESET 0x0
#define REG1_FIELD1_MASK 0x10
#define REG1_FIELD1_SW "ro"
#define REG1_FIELD1_HW "w"

/* Field: field2 */
#define REG1_FIELD2_OFFSET 5
#define REG1_FIELD2_WIDTH 1
#define REG1_FIELD2_RESET 0x0
#define REG1_FIELD2_MASK 0x20
#define REG1_FIELD2_SW "ro"
#define REG1_FIELD2_HW "w"

/* Register: reg2 */
#define REG2_SW "wo"
#define REG2_HW "r"
#define REG2_WIDTH 1
#define REG2_OFFSET 0x8
#define REG2_RESET 0x0

/* Field: field0 */
#define REG2_FIELD0_OFFSET 0
#define REG2_FIELD0_WIDTH 1
#define REG2_FIELD0_RESET 0x0
#define REG2_FIELD0_MASK 0x1
#define REG2_FIELD0_SW "wo"
#define REG2_FIELD0_HW "r"

/* Register: reg3 */
#define REG3_SW "rw"
#define REG3_HW "na"
#define REG3_WIDTH 8
#define REG3_OFFSET 0xc
#define REG3_RESET 0x0

/* Field: field0 */
#define REG3_FIELD0_OFFSET 0
#define REG3_FIELD0_WIDTH 8
#define REG3_FIELD0_RESET 0x0
#define REG3_FIELD0_MASK 0xff
#define REG3_FIELD0_SW "rw"
#define REG3_FIELD0_HW "na"

/* Register: reg4 */
#define REG4_SW "rw"
#define REG4_HW "r"
#define REG4_WIDTH 9
#define REG4_OFFSET 0x10
#define REG4_RESET 0x0

/* Field: field0 */
#define REG4_FIELD0_OFFSET 0
#define REG4_FIELD0_WIDTH 4
#define REG4_FIELD0_RESET 0x0
#define REG4_FIELD0_MASK 0xf
#define REG4_FIELD0_SW "rw"
#define REG4_FIELD0_HW "rw"

/* Field: field1 */
#define REG4_FIELD1_OFFSET 8
#define REG4_FIELD1_WIDTH 1
#define REG4_FIELD1_RESET 0x0
#define REG4_FIELD1_MASK 0x100
#define REG4_FIELD1_SW "rw"
#define REG4_FIELD1_HW "r"

/* Register: reg5 */
#define REG5_SW "rw"
#define REG5_HW "r"
#define REG5_WIDTH 8
#define REG5_OFFSET 0x14
#define REG5_RESET 0x0

/* Field: field0 */
#define REG5_FIELD0_OFFSET 0
#define REG5_FIELD0_WIDTH 4
#define REG5_FIELD0_RESET 0x0
#define REG5_FIELD0_MASK 0xf
#define REG5_FIELD0_SW "rw"
#define REG5_FIELD0_HW "r"
#define REG5_FIELD0_ONREAD "rclr"

/* Field: field1 */
#define REG5_FIELD1_OFFSET 4
#define REG5_FIELD1_WIDTH 4
#define REG5_FIELD1_RESET 0x0
#define REG5_FIELD1_MASK 0xf0
#define REG5_FIELD1_SW "rw"
#define REG5_FIELD1_HW "r"
#define REG5_FIELD1_ONREAD "rset"

/* Register: reg6 */
#define REG6_SW "rw"
#define REG6_HW "r"
#define REG6_WIDTH 12
#define REG6_OFFSET 0x18
#define REG6_RESET 0xf0

/* Field: field0 */
#define REG6_FIELD0_OFFSET 0
#define REG6_FIELD0_WIDTH 4
#define REG6_FIELD0_RESET 0x0
#define REG6_FIELD0_MASK 0xf
#define REG6_FIELD0_SW "rw"
#define REG6_FIELD0_HW "r"
#define REG6_FIELD0_ONWRITE "woset"

/* Field: field1 */
#define REG6_FIELD1_OFFSET 4
#define REG6_FIELD1_WIDTH 4
#define REG6_FIELD1_RESET 0xf
#define REG6_FIELD1_MASK 0xf0
#define REG6_FIELD1_SW "rw"
#define REG6_FIELD1_HW "r"
#define REG6_FIELD1_ONWRITE "woclr"

/* Field: field2 */
#define REG6_FIELD2_OFFSET 8
#define REG6_FIELD2_WIDTH 4
#define REG6_FIELD2_RESET 0x0
#define REG6_FIELD2_MASK 0xf00
#define REG6_FIELD2_SW "rw"
#define REG6_FIELD2_HW "r"
#define REG6_FIELD2_ONWRITE "wot"

/* Register: reg7 */
#define REG7_SW "rw"
#define REG7_HW "r"
#define REG7_WIDTH 12
#define REG7_OFFSET 0x1c
#define REG7_RESET 0xf0

/* Field: field0 */
#define REG7_FIELD0_OFFSET 0
#define REG7_FIELD0_WIDTH 4
#define REG7_FIELD0_RESET 0x0
#define REG7_FIELD0_MASK 0xf
#define REG7_FIELD0_SW "rw"
#define REG7_FIELD0_HW "r"
#define REG7_FIELD0_ONWRITE "wzs"

/* Field: field1 */
#define REG7_FIELD1_OFFSET 4
#define REG7_FIELD1_WIDTH 4
#define REG7_FIELD1_RESET 0xf
#define REG7_FIELD1_MASK 0xf0
#define REG7_FIELD1_SW "rw"
#define REG7_FIELD1_HW "r"
#define REG7_FIELD1_ONWRITE "wzc"

/* Field: field2 */
#define REG7_FIELD2_OFFSET 8
#define REG7_FIELD2_WIDTH 4
#define REG7_FIELD2_RESET 0x0
#define REG7_FIELD2_MASK 0xf00
#define REG7_FIELD2_SW "rw"
#define REG7_FIELD2_HW "r"
#define REG7_FIELD2_ONWRITE "wzt"

/* Register: reg8 */
#define REG8_SW "rw"
#define REG8_HW "r"
#define REG8_WIDTH 8
#define REG8_OFFSET 0x20
#define REG8_RESET 0xf

/* Field: field0 */
#define REG8_FIELD0_OFFSET 0
#define REG8_FIELD0_WIDTH 4
#define REG8_FIELD0_RESET 0xf
#define REG8_FIELD0_MASK 0xf
#define REG8_FIELD0_SW "rw"
#define REG8_FIELD0_HW "r"
#define REG8_FIELD0_ONWRITE "wclr"

/* Field: field1 */
#define REG8_FIELD1_OFFSET 4
#define REG8_FIELD1_WIDTH 4
#define REG8_FIELD1_RESET 0x0
#define REG8_FIELD1_MASK 0xf0
#define REG8_FIELD1_SW "rw"
#define REG8_FIELD1_HW "r"
#define REG8_FIELD1_ONWRITE "wset"

/* Register: reg9 */
#define REG9_SW "rw"
#define REG9_HW "r"
#define REG9_WIDTH 8
#define REG9_OFFSET 0x24
#define REG9_RESET 0x0

/* Field: field0 */
#define REG9_FIELD0_OFFSET 0
#define REG9_FIELD0_WIDTH 4
#define REG9_FIELD0_RESET 0x0
#define REG9_FIELD0_MASK 0xf
#define REG9_FIELD0_SW "rw"
#define REG9_FIELD0_HW "r"

/* Field: field1 */
#define REG9_FIELD1_OFFSET 4
#define REG9_FIELD1_WIDTH 4
#define REG9_FIELD1_RESET 0x0
#define REG9_FIELD1_MASK 0xf0
#define REG9_FIELD1_SW "rw"
#define REG9_FIELD1_HW "r"

/* Register: reg10 */
#define REG10_SW "rw"
#define REG10_HW "r"
#define REG10_WIDTH 4
#define REG10_OFFSET 0x28
#define REG10_RESET 0x0

/* Field: field0 */
#define REG10_FIELD0_OFFSET 0
#define REG10_FIELD0_WIDTH 4
#define REG10_FIELD0_RESET 0x0
#define REG10_FIELD0_MASK 0xf
#define REG10_FIELD0_SW "rw"
#define REG10_FIELD0_HW "r"
#define REG10_FIELD0_SINGLEPULSE 1

/* Register: reg11 */
#define REG11_SW "rw"
#define REG11_HW "r"
#define REG11_WIDTH 2
#define REG11_OFFSET 0x2c
#define REG11_RESET 0x0

/* Field: field0 */
#define REG11_FIELD0_OFFSET 0
#define REG11_FIELD0_WIDTH 2
#define REG11_FIELD0_RESET 0x0
#define REG11_FIELD0_MASK 0x3
#define REG11_FIELD0_SW "rw"
#define REG11_FIELD0_HW "r"
#define REG11_FIELD0_STATE0 0
#define REG11_FIELD0_STATE1 1
#define REG11_FIELD0_STATE2 2
#define REG11_FIELD0_STATE3 3

#endif
