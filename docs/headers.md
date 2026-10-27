# Software headers

Next to the VHDL, bust writes headers that give software the addresses and bit positions of the registers, and for IPBus an address table. This page describes what each file holds and how to use it.

## Files

bust writes the headers to `header/`, in the output directory of the module described in [Command line](command-line.md#output-directory).

| File           | Content                                     | Written                                          |
|----------------|---------------------------------------------|--------------------------------------------------|
| `<module>.h`   | C header with `#define` constants            | Unless you give `-i`                             |
| `<module>.hpp` | C++ header with constants in a namespace     | Unless you give `-i`                             |
| `<module>.py`  | Python module with constants in a class      | Unless you give `-i`                             |
| `<module>.xml` | IPBus address table for uHAL                 | For the `ipbus` bus type, unless you give `-i`   |

## Constant names

The C, C++ and Python headers define the same constants. Each name starts with
the register name in upper case, followed by the field name for a field
property. In the C header, every name also starts with the module name, as
`<MODULE>_<REG>_OFFSET`, because C has no namespaces. The C++ and Python
headers put the names in a namespace and a class named after the module
instead.
Two names belong to the module rather than a register: `REGMAP_VERSION` and
`REGMAP_HASH`.

| Constant                     | Value                                                                                                                                                  |
|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| `<REG>_OFFSET`               | Address of the register, relative to the base address of the module, in hex. The unit is the address unit of the bus: bytes, or 32-bit words for IPBus. |
| `<REG>_WIDTH`                | Number of bits the register uses, up to and including its highest field bit.                                                                           |
| `<REG>_RESET`                | Reset value of the whole register.                                                                                                                     |
| `<REG>_SW`, `<REG>_HW`       | Software and hardware access, as a string such as `"rw"` or `"r"`. For a register with fields, `rw` means that some field can be read and some field can be written. |
| `<REG>_<FIELD>_OFFSET`       | Lowest bit of the field.                                                                                                                               |
| `<REG>_<FIELD>_WIDTH`        | Number of bits in the field.                                                                                                                           |
| `<REG>_<FIELD>_RESET`        | Reset value of the field.                                                                                                                              |
| `<REG>_<FIELD>_MASK`         | The bits of the field, in their place in the register.                                                                                                 |
| `<REG>_<FIELD>_SW`, `_HW`    | Software and hardware access of the field.                                                                                                             |
| `<REG>_<FIELD>_ONREAD`       | `"rclr"` or `"rset"`. Only for a field with `onread`.                                                                                                  |
| `<REG>_<FIELD>_ONWRITE`      | The `onwrite` keyword, such as `"woclr"`. Only for a field with `onwrite`.                                                                             |
| `<REG>_<FIELD>_SINGLEPULSE`  | `1` in C, `true` in C++ and `True` in Python. Only for a `singlepulse` field.                                                                         |
| `<REG>_<FIELD>_<VALUE>`      | One constant for each value of an enumerated field.                                                                                                    |
| `REGMAP_VERSION`             | The `version` of the module, as a string.                                                                                                              |
| `REGMAP_HASH`                | The 32-bit hash of the register map. See [Version and hash](register-map-format.md#version-and-hash).                                                  |

A register without fields has no field constants. Its `ONREAD`, `ONWRITE` and
`SINGLEPULSE` constants are named after the register alone, as in
`REG9_SINGLEPULSE` in the AXI4-Lite example of the repository
(`EXAMPLE_AXI_REG9_SINGLEPULSE` in C).

`_OFFSET` is an address for a register and a bit position for a field. The
hardware modifiers (`we`, `wel`, `hwset`, `hwclr`, `swmod`, `swacc`) only
concern the hardware side, so the headers leave them out.
[Access modes](access-modes.md) describes the access keywords.

The examples below come from `prototype.h`, `prototype.hpp` and `prototype.py`
of the prototype example in the repository, trimmed to one register. In that
module, `reg11` has one enumerated field, `field0`, with the values `STATE0` to
`STATE3`.

### C

The C header holds only comments and `#define` lines, with an include guard
named after the module:

```c
#ifndef PROTOTYPE_H
#define PROTOTYPE_H

/* Register map version and content hash */
#define PROTOTYPE_REGMAP_VERSION "1.0"
#define PROTOTYPE_REGMAP_HASH 0x593FA68E

/* Register: reg11 */
#define PROTOTYPE_REG11_WIDTH 2
#define PROTOTYPE_REG11_OFFSET 0x2c
#define PROTOTYPE_REG11_RESET 0x0
#define PROTOTYPE_REG11_SW "rw"
#define PROTOTYPE_REG11_HW "r"

/* Field: field0 */
#define PROTOTYPE_REG11_FIELD0_OFFSET 0
#define PROTOTYPE_REG11_FIELD0_WIDTH 2
#define PROTOTYPE_REG11_FIELD0_RESET 0x0
#define PROTOTYPE_REG11_FIELD0_MASK 0x3
#define PROTOTYPE_REG11_FIELD0_SW "rw"
#define PROTOTYPE_REG11_FIELD0_HW "r"
#define PROTOTYPE_REG11_FIELD0_STATE0 0
#define PROTOTYPE_REG11_FIELD0_STATE1 1
#define PROTOTYPE_REG11_FIELD0_STATE2 2
#define PROTOTYPE_REG11_FIELD0_STATE3 3

#endif
```

Add `<MODULE>_<REG>_OFFSET` to the base address of the module to get the
address of a register. Use `_MASK` and `_OFFSET` of a field to read or change it:

```c
#include <stdint.h>
#include "prototype.h"

uint32_t value = read32(PROTOTYPE_BASE + PROTOTYPE_REG11_OFFSET);
uint32_t state = (value & PROTOTYPE_REG11_FIELD0_MASK) >> PROTOTYPE_REG11_FIELD0_OFFSET;

if (state == PROTOTYPE_REG11_FIELD0_STATE0) {
    value = (value & ~PROTOTYPE_REG11_FIELD0_MASK)
            | (PROTOTYPE_REG11_FIELD0_STATE2 << PROTOTYPE_REG11_FIELD0_OFFSET);
    write32(PROTOTYPE_BASE + PROTOTYPE_REG11_OFFSET, value);
}
```

`read32`, `write32` and `PROTOTYPE_BASE` stand for whatever your platform uses.
The module name in each constant keeps the headers of two modules apart, so
one source file can include both.

### C++

The C++ header has the same constants as `const` values in a namespace named
after the module, in upper case. Numbers are `uint32_t` and access strings are
`std::string`:

```cpp
#ifndef PROTOTYPE_HPP
#define PROTOTYPE_HPP

#include <cstdint>
#include <string>

namespace PROTOTYPE
{
/* Register map version and content hash */
const std::string REGMAP_VERSION = "1.0";
const uint32_t REGMAP_HASH = 0x593FA68E;

/* Register: reg11 */
const uint32_t REG11_WIDTH = 2;
const uint32_t REG11_OFFSET = 0x2c;
const uint32_t REG11_RESET = 0x0;
const std::string REG11_SW = "rw";
const std::string REG11_HW = "r";

/* Field: field0 */
const uint32_t REG11_FIELD0_OFFSET = 0;
const uint32_t REG11_FIELD0_WIDTH = 2;
const uint32_t REG11_FIELD0_RESET = 0x0;
const uint32_t REG11_FIELD0_MASK = 0x3;
const std::string REG11_FIELD0_SW = "rw";
const std::string REG11_FIELD0_HW = "r";
const uint32_t REG11_FIELD0_STATE0 = 0;
const uint32_t REG11_FIELD0_STATE1 = 1;
const uint32_t REG11_FIELD0_STATE2 = 2;
const uint32_t REG11_FIELD0_STATE3 = 3;
};

#endif
```

Refer to them as `PROTOTYPE::REG11_OFFSET`.

### Python

The Python module has the constants as attributes of a class named
`<MODULE>_H`. It is formatted as black formats it, with upper-case hex digits,
so black leaves it unchanged in a project that uses black:

```python
class PROTOTYPE_H:
    """Register map version and content hash"""

    REGMAP_VERSION = "1.0"
    REGMAP_HASH = 0x593FA68E

    """Register: reg11"""
    REG11_WIDTH = 2
    REG11_OFFSET = 0x2C
    REG11_RESET = 0x0
    REG11_SW = "rw"
    REG11_HW = "r"

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
```

Import the class and use it as a namespace:

```python
from prototype import PROTOTYPE_H as regs

value = read32(base + regs.REG11_OFFSET)
state = (value & regs.REG11_FIELD0_MASK) >> regs.REG11_FIELD0_OFFSET
```

## IPBus address table

For a module with the `ipbus` bus type, bust also writes `header/<module>.xml`,
an address table for the IPBus software library
[uHAL](https://github.com/ipbus/ipbus-software).
It has one top-level node named after the module, one node for each register,
and one child node for each field. The `parameters` of the top-level node hold
the `version` of the module and the hash of the register map. This excerpt comes from `example_ipbus.xml`
in the repository:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<node id="example_ipbus" parameters="regmap_version=1.0;regmap_hash=0xFCD085B6">
    <node id="reg6" address="0x00000018" permission="r" description="Default RO register" parameters="reset=0x0"/>
    <node id="reg7" address="0x0000001C" permission="rw" description="RW register that have multiple fields" parameters="reset=0xad7">
        <node id="field0" mask="0x1" permission="rw" description="std_logic that resets to 0x1" parameters="reset=0x1"/>
        <node id="field1" mask="0x1e" permission="rw" description="std_logic_vector[3:0] that resets to 0xb is not a valid reset value" parameters="reset=0xb"/>
        <node id="field2" mask="0x20" permission="rw" description="std_logic that resets to 0x1" parameters="reset=0x0"/>
        <node id="field3" mask="0x1fffc0" permission="rw" description="std_logic_vector[14:0] that resets to 0x2b" parameters="reset=0x2b"/>
    </node>
</node>
```

| Attribute     | On             | Value                                                                                   |
|---------------|----------------|-----------------------------------------------------------------------------------------|
| `id`          | Register, field | The name from the JSON file.                                                           |
| `address`     | Register        | The address of the register in 32-bit words, relative to the module.                   |
| `mask`        | Field           | The bits of the field in the register, as `<REG>_<FIELD>_MASK` in the headers.         |
| `permission`  | Register, field | `rw`, `r` or `w`, from the software access. See below.                                 |
| `description` | Register, field | The description from the JSON file, with `&`, `<`, `>` and quotes escaped.             |
| `parameters`  | Module          | `regmap_version=` and the version, `;`, and `regmap_hash=` and the hash.               |
| `parameters`  | Register, field | `reset=` and the reset value.                                                          |

The permission comes from the software access:

| Software access | `permission` |
|-----------------|--------------|
| `rw`            | `rw`         |
| `ro`            | `r`          |
| `wo`            | `w`          |
| `na`            | No node      |

Each field gets the permission of its own `sw`, so a read-only field in a
read-write register is read-only through uHAL. A register gets the permission
of the summary its fields give, the same value as `<REG>_SW` in the headers.
Registers and fields that software cannot access get no node, since uHAL cannot
reach them.

The addresses start at 0 for the module. To place the module in your system,
refer to the file from your top-level address table, at the base address of the
module:

```xml
<node id="example_ipbus" module="file://example_ipbus.xml" address="0x00001000"/>
```
