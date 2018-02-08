#ifndef EXAMPLE_MODULE_H
#define EXAMPLE_MODULE_H

#define EXAMPLE_MODULE_BASEADDR 0xffaa0000

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

/* Field: field1 */
#define REG7_FIELD1_OFFSET 1
#define REG7_FIELD1_WIDTH 4
#define REG7_FIELD1_RESET 0xb

/* Field: field2 */
#define REG7_FIELD2_OFFSET 5
#define REG7_FIELD2_WIDTH 1
#define REG7_FIELD2_RESET 0x0

/* Field: field3 */
#define REG7_FIELD3_OFFSET 6
#define REG7_FIELD3_WIDTH 15
#define REG7_FIELD3_RESET 0x2b

/* Register: reg8 */
#define REG8_OFFSET 0x20
#define REG8_RESET 0x0

/* Field: field0 */
#define REG8_FIELD0_OFFSET 0
#define REG8_FIELD0_WIDTH 1
#define REG8_FIELD0_RESET 0x0

/* Field: field1 */
#define REG8_FIELD1_OFFSET 1
#define REG8_FIELD1_WIDTH 19
#define REG8_FIELD1_RESET 0x0

/* Field: field2 */
#define REG8_FIELD2_OFFSET 20
#define REG8_FIELD2_WIDTH 1
#define REG8_FIELD2_RESET 0x0

/* Field: field3 */
#define REG8_FIELD3_OFFSET 21
#define REG8_FIELD3_WIDTH 3
#define REG8_FIELD3_RESET 0x0

#endif