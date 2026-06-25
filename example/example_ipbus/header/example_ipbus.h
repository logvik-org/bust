#ifndef EXAMPLE_IPBUS_H
#define EXAMPLE_IPBUS_H


/* Register: reg0 */
#define REG0_SW "rw"
#define REG0_HW "r"
#define REG0_WIDTH 1
#define REG0_OFFSET 0x0
#define REG0_RESET 0x0

/* Register: reg1 */
#define REG1_SW "rw"
#define REG1_HW "r"
#define REG1_WIDTH 1
#define REG1_OFFSET 0x4
#define REG1_RESET 0x1

/* Register: reg2 */
#define REG2_SW "ro"
#define REG2_HW "w"
#define REG2_WIDTH 1
#define REG2_OFFSET 0x8
#define REG2_RESET 0x0

/* Register: reg3 */
#define REG3_SW "rw"
#define REG3_HW "r"
#define REG3_WIDTH 8
#define REG3_OFFSET 0xc
#define REG3_RESET 0x3

/* Register: reg4 */
#define REG4_SW "ro"
#define REG4_HW "w"
#define REG4_WIDTH 14
#define REG4_OFFSET 0x10
#define REG4_RESET 0x0

/* Register: reg5 */
#define REG5_SW "rw"
#define REG5_HW "r"
#define REG5_WIDTH 32
#define REG5_OFFSET 0x14
#define REG5_RESET 0xffffffff

/* Register: reg6 */
#define REG6_SW "ro"
#define REG6_HW "w"
#define REG6_WIDTH 32
#define REG6_OFFSET 0x18
#define REG6_RESET 0x0

/* Register: reg7 */
#define REG7_SW "rw"
#define REG7_HW "r"
#define REG7_WIDTH 21
#define REG7_OFFSET 0x1c
#define REG7_RESET 0xad7

/* Field: field0 */
#define REG7_FIELD0_OFFSET 0
#define REG7_FIELD0_WIDTH 1
#define REG7_FIELD0_RESET 0x1
#define REG7_FIELD0_MASK 0x1
#define REG7_FIELD0_SW "rw"
#define REG7_FIELD0_HW "r"

/* Field: field1 */
#define REG7_FIELD1_OFFSET 1
#define REG7_FIELD1_WIDTH 4
#define REG7_FIELD1_RESET 0xb
#define REG7_FIELD1_MASK 0x1e
#define REG7_FIELD1_SW "rw"
#define REG7_FIELD1_HW "r"

/* Field: field2 */
#define REG7_FIELD2_OFFSET 5
#define REG7_FIELD2_WIDTH 1
#define REG7_FIELD2_RESET 0x0
#define REG7_FIELD2_MASK 0x20
#define REG7_FIELD2_SW "rw"
#define REG7_FIELD2_HW "r"

/* Field: field3 */
#define REG7_FIELD3_OFFSET 6
#define REG7_FIELD3_WIDTH 15
#define REG7_FIELD3_RESET 0x2b
#define REG7_FIELD3_MASK 0x1fffc0
#define REG7_FIELD3_SW "rw"
#define REG7_FIELD3_HW "r"

/* Register: reg8 */
#define REG8_SW "ro"
#define REG8_HW "w"
#define REG8_WIDTH 24
#define REG8_OFFSET 0x20
#define REG8_RESET 0x0

/* Field: field0 */
#define REG8_FIELD0_OFFSET 0
#define REG8_FIELD0_WIDTH 1
#define REG8_FIELD0_RESET 0x0
#define REG8_FIELD0_MASK 0x1
#define REG8_FIELD0_SW "ro"
#define REG8_FIELD0_HW "w"

/* Field: field1 */
#define REG8_FIELD1_OFFSET 1
#define REG8_FIELD1_WIDTH 19
#define REG8_FIELD1_RESET 0x0
#define REG8_FIELD1_MASK 0xffffe
#define REG8_FIELD1_SW "ro"
#define REG8_FIELD1_HW "w"

/* Field: field2 */
#define REG8_FIELD2_OFFSET 20
#define REG8_FIELD2_WIDTH 1
#define REG8_FIELD2_RESET 0x0
#define REG8_FIELD2_MASK 0x100000
#define REG8_FIELD2_SW "ro"
#define REG8_FIELD2_HW "w"

/* Field: field3 */
#define REG8_FIELD3_OFFSET 21
#define REG8_FIELD3_WIDTH 3
#define REG8_FIELD3_RESET 0x0
#define REG8_FIELD3_MASK 0xe00000
#define REG8_FIELD3_SW "ro"
#define REG8_FIELD3_HW "w"

/* Register: reg9 */
#define REG9_SW "wo"
#define REG9_HW "r"
#define REG9_WIDTH 1
#define REG9_OFFSET 0x24
#define REG9_RESET 0x1
#define REG9_SINGLEPULSE 1

/* Register: reg10 */
#define REG10_SW "wo"
#define REG10_HW "r"
#define REG10_WIDTH 4
#define REG10_OFFSET 0x28
#define REG10_RESET 0xa
#define REG10_SINGLEPULSE 1

/* Register: reg11 */
#define REG11_SW "wo"
#define REG11_HW "r"
#define REG11_WIDTH 16
#define REG11_OFFSET 0x2c
#define REG11_RESET 0x3

/* Field: field0 */
#define REG11_FIELD0_OFFSET 0
#define REG11_FIELD0_WIDTH 15
#define REG11_FIELD0_RESET 0x3
#define REG11_FIELD0_MASK 0x7fff
#define REG11_FIELD0_SW "wo"
#define REG11_FIELD0_HW "r"
#define REG11_FIELD0_SINGLEPULSE 1

/* Field: field1 */
#define REG11_FIELD1_OFFSET 15
#define REG11_FIELD1_WIDTH 1
#define REG11_FIELD1_RESET 0x0
#define REG11_FIELD1_MASK 0x8000
#define REG11_FIELD1_SW "wo"
#define REG11_FIELD1_HW "r"
#define REG11_FIELD1_SINGLEPULSE 1

#endif
