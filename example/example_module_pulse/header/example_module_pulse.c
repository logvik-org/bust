#ifndef EXAMPLE_MODULE_PULSE_H
#define EXAMPLE_MODULE_PULSE_H

#define EXAMPLE_MODULE_PULSE_BASEADDR 0xffaa0000

/* Register: reg0 */
#define REG0_OFFSET 0x0
#define REG0_RESET 0x0

/* Register: reg1 */
#define REG1_OFFSET 0x4
#define REG1_RESET 0x1

/* Register: reg2 */
#define REG2_OFFSET 0xc
#define REG2_RESET 0x3

/* Register: reg3 */
#define REG3_OFFSET 0x14
#define REG3_RESET 0xffffffff

/* Register: reg4 */
#define REG4_OFFSET 0x1c
#define REG4_RESET 0xad7

/* Field: field0 */
#define REG4_FIELD0_OFFSET 0
#define REG4_FIELD0_WIDTH 1
#define REG4_FIELD0_RESET 0x1

/* Field: field1 */
#define REG4_FIELD1_OFFSET 1
#define REG4_FIELD1_WIDTH 4
#define REG4_FIELD1_RESET 0xb

/* Field: field2 */
#define REG4_FIELD2_OFFSET 5
#define REG4_FIELD2_WIDTH 1
#define REG4_FIELD2_RESET 0x0

/* Field: field3 */
#define REG4_FIELD3_OFFSET 6
#define REG4_FIELD3_WIDTH 15
#define REG4_FIELD3_RESET 0x2b

#endif