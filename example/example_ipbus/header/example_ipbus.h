#ifndef EXAMPLE_IPBUS_H
#define EXAMPLE_IPBUS_H


/* Register: reg0 */
#define REG0_OFFSET 0x0
#define REG0_RESET 0x0

/* Register: reg1 */
#define REG1_OFFSET 0x4
#define REG1_RESET 0x1

/* Register: reg2 */
#define REG2_OFFSET 0x8
#define REG2_RESET 0x0

/* Register: reg3 */
#define REG3_OFFSET 0xc
#define REG3_RESET 0x3

/* Register: reg4 */
#define REG4_OFFSET 0x10
#define REG4_RESET 0x0

/* Register: reg5 */
#define REG5_OFFSET 0x14
#define REG5_RESET 0xffffffff

/* Register: reg6 */
#define REG6_OFFSET 0x18
#define REG6_RESET 0x0

/* Register: reg7 */
#define REG7_OFFSET 0x1c
#define REG7_RESET 0xad7

/* Field: field0 */
#define REG7_FIELD0_OFFSET 0
#define REG7_FIELD0_WIDTH 1
#define REG7_FIELD0_RESET 0x1
#define REG7_FIELD0_MASK 0x1

/* Field: field1 */
#define REG7_FIELD1_OFFSET 1
#define REG7_FIELD1_WIDTH 4
#define REG7_FIELD1_RESET 0xb
#define REG7_FIELD1_MASK 0x1e

/* Field: field2 */
#define REG7_FIELD2_OFFSET 5
#define REG7_FIELD2_WIDTH 1
#define REG7_FIELD2_RESET 0x0
#define REG7_FIELD2_MASK 0x20

/* Field: field3 */
#define REG7_FIELD3_OFFSET 6
#define REG7_FIELD3_WIDTH 15
#define REG7_FIELD3_RESET 0x2b
#define REG7_FIELD3_MASK 0x1fffc0

/* Register: reg8 */
#define REG8_OFFSET 0x20
#define REG8_RESET 0x0

/* Field: field0 */
#define REG8_FIELD0_OFFSET 0
#define REG8_FIELD0_WIDTH 1
#define REG8_FIELD0_RESET 0x0
#define REG8_FIELD0_MASK 0x1

/* Field: field1 */
#define REG8_FIELD1_OFFSET 1
#define REG8_FIELD1_WIDTH 19
#define REG8_FIELD1_RESET 0x0
#define REG8_FIELD1_MASK 0xffffe

/* Field: field2 */
#define REG8_FIELD2_OFFSET 20
#define REG8_FIELD2_WIDTH 1
#define REG8_FIELD2_RESET 0x0
#define REG8_FIELD2_MASK 0x100000

/* Field: field3 */
#define REG8_FIELD3_OFFSET 21
#define REG8_FIELD3_WIDTH 3
#define REG8_FIELD3_RESET 0x0
#define REG8_FIELD3_MASK 0xe00000

/* Register: reg9 */
#define REG9_OFFSET 0x24
#define REG9_RESET 0x1

/* Register: reg10 */
#define REG10_OFFSET 0x28
#define REG10_RESET 0xa

/* Register: reg11 */
#define REG11_OFFSET 0x2c
#define REG11_RESET 0x3

/* Field: field0 */
#define REG11_FIELD0_OFFSET 0
#define REG11_FIELD0_WIDTH 15
#define REG11_FIELD0_RESET 0x3
#define REG11_FIELD0_MASK 0x7fff

/* Field: field1 */
#define REG11_FIELD1_OFFSET 15
#define REG11_FIELD1_WIDTH 1
#define REG11_FIELD1_RESET 0x0
#define REG11_FIELD1_MASK 0x8000

#endif