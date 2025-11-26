#ifndef EXAMPLE_AXI_H
#define EXAMPLE_AXI_H

#include <cstdint>
#include <string>

namespace EXAMPLE_AXI
{
/* Register: reg0 */
const std::string REG0_MODE = "rw";
const uint32_t REG0_WIDTH = 1;
const uint32_t REG0_OFFSET = 0x0;
const uint32_t REG0_RESET = 0x0;

/* Register: reg1 */
const std::string REG1_MODE = "rw";
const uint32_t REG1_WIDTH = 1;
const uint32_t REG1_OFFSET = 0x4;
const uint32_t REG1_RESET = 0x1;

/* Register: reg2 */
const std::string REG2_MODE = "ro";
const uint32_t REG2_WIDTH = 1;
const uint32_t REG2_OFFSET = 0x8;
const uint32_t REG2_RESET = 0x0;

/* Register: reg3 */
const std::string REG3_MODE = "rw";
const uint32_t REG3_WIDTH = 8;
const uint32_t REG3_OFFSET = 0xc;
const uint32_t REG3_RESET = 0x3;

/* Register: reg4 */
const std::string REG4_MODE = "ro";
const uint32_t REG4_WIDTH = 14;
const uint32_t REG4_OFFSET = 0x10;
const uint32_t REG4_RESET = 0x0;

/* Register: reg5 */
const std::string REG5_MODE = "rw";
const uint32_t REG5_WIDTH = 32;
const uint32_t REG5_OFFSET = 0x14;
const uint32_t REG5_RESET = 0xffffffff;

/* Register: reg6 */
const std::string REG6_MODE = "ro";
const uint32_t REG6_WIDTH = 32;
const uint32_t REG6_OFFSET = 0x18;
const uint32_t REG6_RESET = 0x0;

/* Register: reg7 */
const std::string REG7_MODE = "rw";
const uint32_t REG7_WIDTH = 21;
const uint32_t REG7_OFFSET = 0x1c;
const uint32_t REG7_RESET = 0xad7;

/* Field: field0 */
const uint32_t REG7_FIELD0_OFFSET = 0;
const uint32_t REG7_FIELD0_WIDTH = 1;
const uint32_t REG7_FIELD0_RESET = 0x1;
const uint32_t REG7_FIELD0_MASK = 0x1;

/* Field: field1 */
const uint32_t REG7_FIELD1_OFFSET = 1;
const uint32_t REG7_FIELD1_WIDTH = 4;
const uint32_t REG7_FIELD1_RESET = 0xb;
const uint32_t REG7_FIELD1_MASK = 0x1e;

/* Field: field2 */
const uint32_t REG7_FIELD2_OFFSET = 5;
const uint32_t REG7_FIELD2_WIDTH = 1;
const uint32_t REG7_FIELD2_RESET = 0x0;
const uint32_t REG7_FIELD2_MASK = 0x20;

/* Field: field3 */
const uint32_t REG7_FIELD3_OFFSET = 6;
const uint32_t REG7_FIELD3_WIDTH = 15;
const uint32_t REG7_FIELD3_RESET = 0x2b;
const uint32_t REG7_FIELD3_MASK = 0x1fffc0;

/* Register: reg8 */
const std::string REG8_MODE = "ro";
const uint32_t REG8_WIDTH = 24;
const uint32_t REG8_OFFSET = 0x20;
const uint32_t REG8_RESET = 0x0;

/* Field: field0 */
const uint32_t REG8_FIELD0_OFFSET = 0;
const uint32_t REG8_FIELD0_WIDTH = 1;
const uint32_t REG8_FIELD0_RESET = 0x0;
const uint32_t REG8_FIELD0_MASK = 0x1;

/* Field: field1 */
const uint32_t REG8_FIELD1_OFFSET = 1;
const uint32_t REG8_FIELD1_WIDTH = 19;
const uint32_t REG8_FIELD1_RESET = 0x0;
const uint32_t REG8_FIELD1_MASK = 0xffffe;

/* Field: field2 */
const uint32_t REG8_FIELD2_OFFSET = 20;
const uint32_t REG8_FIELD2_WIDTH = 1;
const uint32_t REG8_FIELD2_RESET = 0x0;
const uint32_t REG8_FIELD2_MASK = 0x100000;

/* Field: field3 */
const uint32_t REG8_FIELD3_OFFSET = 21;
const uint32_t REG8_FIELD3_WIDTH = 3;
const uint32_t REG8_FIELD3_RESET = 0x0;
const uint32_t REG8_FIELD3_MASK = 0xe00000;

/* Register: reg9 */
const std::string REG9_MODE = "pulse";
const uint32_t REG9_WIDTH = 1;
const uint32_t REG9_OFFSET = 0x24;
const uint32_t REG9_RESET = 0x1;

/* Register: reg10 */
const std::string REG10_MODE = "pulse";
const uint32_t REG10_WIDTH = 4;
const uint32_t REG10_OFFSET = 0x28;
const uint32_t REG10_RESET = 0xa;

/* Register: reg11 */
const std::string REG11_MODE = "pulse";
const uint32_t REG11_WIDTH = 16;
const uint32_t REG11_OFFSET = 0x2c;
const uint32_t REG11_RESET = 0x3;

/* Field: field0 */
const uint32_t REG11_FIELD0_OFFSET = 0;
const uint32_t REG11_FIELD0_WIDTH = 15;
const uint32_t REG11_FIELD0_RESET = 0x3;
const uint32_t REG11_FIELD0_MASK = 0x7fff;

/* Field: field1 */
const uint32_t REG11_FIELD1_OFFSET = 15;
const uint32_t REG11_FIELD1_WIDTH = 1;
const uint32_t REG11_FIELD1_RESET = 0x0;
const uint32_t REG11_FIELD1_MASK = 0x8000;

};

#endif
