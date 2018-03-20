#ifndef EXAMPLE_MODULE_RO_H
#define EXAMPLE_MODULE_RO_H

#define EXAMPLE_MODULE_RO_BASEADDR 0xffaa0000

/* Register: reg0 */
#define REG0_OFFSET 0x0
#define REG0_RESET 0x1

/* Register: reg1 */
#define REG1_OFFSET 0x4
#define REG1_RESET 0xF

/* Register: reg2 */
#define REG2_OFFSET 0x8
#define REG2_RESET 0x0

/* Register: reg3 */
#define REG3_OFFSET 0xc
#define REG3_RESET 0x0

/* Field: field0 */
#define REG3_FIELD0_OFFSET 0
#define REG3_FIELD0_WIDTH 1
#define REG3_FIELD0_RESET 0x0

/* Field: field1 */
#define REG3_FIELD1_OFFSET 1
#define REG3_FIELD1_WIDTH 19
#define REG3_FIELD1_RESET 0x0

/* Field: field2 */
#define REG3_FIELD2_OFFSET 20
#define REG3_FIELD2_WIDTH 1
#define REG3_FIELD2_RESET 0x0

/* Field: field3 */
#define REG3_FIELD3_OFFSET 21
#define REG3_FIELD3_WIDTH 3
#define REG3_FIELD3_RESET 0x0

#endif