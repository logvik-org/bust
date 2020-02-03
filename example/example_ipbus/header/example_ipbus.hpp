#ifndef EXAMPLE_IPBUS_H
#define EXAMPLE_IPBUS_H

#include <cstdint>

namespace EXAMPLE_IPBUS
{
/* Register: reg0 */
static const uint32_t REG0_OFFSET = 0x0;
static const uint32_t REG0_RESET = 0x0;

/* Register: reg1 */
static const uint32_t REG1_OFFSET = 0x4;
static const uint32_t REG1_RESET = 0x1;

/* Register: reg2 */
static const uint32_t REG2_OFFSET = 0x8;
static const uint32_t REG2_RESET = 0x0;

/* Register: reg3 */
static const uint32_t REG3_OFFSET = 0xc;
static const uint32_t REG3_RESET = 0x3;

/* Register: reg4 */
static const uint32_t REG4_OFFSET = 0x10;
static const uint32_t REG4_RESET = 0x0;

/* Register: reg5 */
static const uint32_t REG5_OFFSET = 0x14;
static const uint32_t REG5_RESET = 0xffffffff;

/* Register: reg6 */
static const uint32_t REG6_OFFSET = 0x18;
static const uint32_t REG6_RESET = 0x0;

/* Register: reg7 */
static const uint32_t REG7_OFFSET = 0x1c;
static const uint32_t REG7_RESET = 0xad7;

/* Field: field0 */
static const uint32_t REG7_FIELD0_OFFSET = 0;
static const uint32_t REG7_FIELD0_WIDTH = 1;
static const uint32_t REG7_FIELD0_RESET = 0x1;
static const uint32_t REG7_FIELD0_MASK = 0x1;

/* Field: field1 */
static const uint32_t REG7_FIELD1_OFFSET = 1;
static const uint32_t REG7_FIELD1_WIDTH = 4;
static const uint32_t REG7_FIELD1_RESET = 0xb;
static const uint32_t REG7_FIELD1_MASK = 0x1e;

/* Field: field2 */
static const uint32_t REG7_FIELD2_OFFSET = 5;
static const uint32_t REG7_FIELD2_WIDTH = 1;
static const uint32_t REG7_FIELD2_RESET = 0x0;
static const uint32_t REG7_FIELD2_MASK = 0x20;

/* Field: field3 */
static const uint32_t REG7_FIELD3_OFFSET = 6;
static const uint32_t REG7_FIELD3_WIDTH = 15;
static const uint32_t REG7_FIELD3_RESET = 0x2b;
static const uint32_t REG7_FIELD3_MASK = 0x1fffc0;

/* Register: reg8 */
static const uint32_t REG8_OFFSET = 0x20;
static const uint32_t REG8_RESET = 0x0;

/* Field: field0 */
static const uint32_t REG8_FIELD0_OFFSET = 0;
static const uint32_t REG8_FIELD0_WIDTH = 1;
static const uint32_t REG8_FIELD0_RESET = 0x0;
static const uint32_t REG8_FIELD0_MASK = 0x1;

/* Field: field1 */
static const uint32_t REG8_FIELD1_OFFSET = 1;
static const uint32_t REG8_FIELD1_WIDTH = 19;
static const uint32_t REG8_FIELD1_RESET = 0x0;
static const uint32_t REG8_FIELD1_MASK = 0xffffe;

/* Field: field2 */
static const uint32_t REG8_FIELD2_OFFSET = 20;
static const uint32_t REG8_FIELD2_WIDTH = 1;
static const uint32_t REG8_FIELD2_RESET = 0x0;
static const uint32_t REG8_FIELD2_MASK = 0x100000;

/* Field: field3 */
static const uint32_t REG8_FIELD3_OFFSET = 21;
static const uint32_t REG8_FIELD3_WIDTH = 3;
static const uint32_t REG8_FIELD3_RESET = 0x0;
static const uint32_t REG8_FIELD3_MASK = 0xe00000;

/* Register: reg9 */
static const uint32_t REG9_OFFSET = 0x24;
static const uint32_t REG9_RESET = 0x1;

/* Register: reg10 */
static const uint32_t REG10_OFFSET = 0x28;
static const uint32_t REG10_RESET = 0xa;

/* Register: reg11 */
static const uint32_t REG11_OFFSET = 0x2c;
static const uint32_t REG11_RESET = 0x3;

/* Field: field0 */
static const uint32_t REG11_FIELD0_OFFSET = 0;
static const uint32_t REG11_FIELD0_WIDTH = 15;
static const uint32_t REG11_FIELD0_RESET = 0x3;
static const uint32_t REG11_FIELD0_MASK = 0x7fff;

/* Field: field1 */
static const uint32_t REG11_FIELD1_OFFSET = 15;
static const uint32_t REG11_FIELD1_WIDTH = 1;
static const uint32_t REG11_FIELD1_RESET = 0x0;
static const uint32_t REG11_FIELD1_MASK = 0x8000;

};

#endif