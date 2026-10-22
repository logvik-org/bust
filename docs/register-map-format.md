# Register map format

A register map is one JSON file that describes one module: the bus it sits on,
its registers and their fields. bust generates the VHDL, the testbench, the
headers and the documentation from it.

```json
{
  "bus": {
    "type": "axi",
    "addr_width": 16,
    "data_width": 32
  },
  "module": {
    "name": "uart",
    "version": "1.2",
    "description": "UART control and status.",
    "register": [
      {
        "name": "ctrl",
        "address": "0x0",
        "type": "fields",
        "sw": "rw",
        "hw": "r",
        "description": "Transmitter and receiver control.",
        "fields": [
          { "name": "tx_en", "type": "bit", "description": "Enable the transmitter." },
          { "name": "rx_en", "type": "bit", "description": "Enable the receiver." },
          {
            "name": "parity",
            "type": "vector",
            "width": 2,
            "description": "Parity bit.",
            "enums": [
              { "name": "PAR_NONE", "value": 0 },
              { "name": "PAR_EVEN", "value": 1 },
              { "name": "PAR_ODD", "value": 2 }
            ]
          },
          {
            "name": "flush",
            "type": "bit",
            "position": 8,
            "singlepulse": true,
            "description": "Write 1 to empty both FIFOs."
          }
        ]
      },
      {
        "name": "baud_div",
        "address": "0x4",
        "type": "vector",
        "width": 16,
        "reset": "0x1b2",
        "sw": "rw",
        "hw": "r",
        "description": "Clock cycles per bit."
      },
      {
        "name": "status",
        "address": "0x8",
        "type": "fields",
        "sw": "ro",
        "hw": "w",
        "description": "Transmitter and receiver state.",
        "fields": [
          { "name": "tx_busy", "type": "bit", "description": "A byte is being sent." },
          { "name": "rx_level", "type": "vector", "width": 5, "description": "Bytes in the receive FIFO." },
          {
            "name": "overrun",
            "type": "bit",
            "position": 8,
            "hw": "r",
            "hwset": true,
            "onread": "rclr",
            "description": "A received byte was lost. Cleared when read."
          }
        ]
      }
    ]
  }
}
```

The file has two sections:

- `bus`: the bus protocol and its address and data widths.
- `module`: the module's name and its registers.

This page describes every key. In the tables, the Default column says
`required` for a key that must be present. Every other key is optional, and
bust uses the default when the key is left out. The access keys (`sw`, `hw`, `onread` and the
others) decide what software and hardware can do with each field.
[Access modes](access-modes.md) describes what each of them does in hardware.

bust reads and checks the whole file before it writes anything. At the first
error it prints what is wrong and exits with status 1.

## Numbers

Every number in the file, such as an `address`, a `reset` or a `width`, can be
written as a JSON number or as a string:

| Written as | Read as | Example | Value |
|---|---|---|---|
| a JSON number | decimal | `16` | 16 |
| a string | decimal | `"16"` | 16 |
| a string that starts with `0x` | hexadecimal | `"0x10"` | 16 |
| a string that starts with `0b` | binary | `"0b10000"` | 16 |

Plain JSON has no hexadecimal numbers, so a hexadecimal value is a string.
Upper and lower case both work, as in `"0X1B2"` and `"0x1b2"`. A number cannot
be negative, and a fraction, a space or any other character stops bust. So does
a string with hexadecimal digits but no `0x`, because it cannot be decimal:

```text
Could not parse register baud_div: Reset of register baud_div "1B2" has hexadecimal digits but no 0x. Write "0x1B2" for a hexadecimal number.
```

bust also reads the file as [JSON5](https://json5.org/), whatever its name. A
JSON5 file can have comments, trailing commas, keys without quotes and
hexadecimal numbers without quotes, such as `"address": 0x1c`. `bust -a` and
the [editor](command-line.md#interactive-editor) keep the comments when they
save a JSON5 file.

## Bus

```json
"bus": {
  "type": "axi",
  "addr_width": 16,
  "data_width": 32
}
```

| Key | Type | Default | Meaning |
|---|---|---|---|
| `type` | string | required | The bus protocol, from the table below. |
| `addr_width` | [number](#numbers) | required | Width of the bus address in bits. |
| `data_width` | [number](#numbers) | required | Width of the bus data in bits. No register can be wider. |

| `type` | Protocol | An address selects |
|---|---|---|
| `axi` | AXI4-Lite | a byte |
| `ipbus` | IPBus | a 32-bit word |
| `sbi` | SBI | a byte |
| `avalon` | Avalon-MM | a byte |
| `wishbone` | Wishbone B4 classic | a byte |
| `apb` | AMBA APB | a byte |

Write the type in lowercase. Any other value stops bust:

```text
Bus type is not valid: AXI
```

IPBus carries 32-bit data and 32-bit addresses, so an `ipbus` module needs a
`data_width` of 32 and an `addr_width` of at most 32. Other values stop bust
with an error such as:

```text
Bus type ipbus carries 32-bit data, so data_width must be 32 (got 16)
```

On every bus, `data_width` must be a whole number of bytes, because bust
places registers `data_width / 8` bytes apart on a byte-addressed bus. bust
does not limit the widths further. [Buses](buses.md) describes the ports and
the timing of each protocol.

## Module

| Key | Type | Default | Meaning |
|---|---|---|---|
| `name` | string | required | Module name. It names the generated files and VHDL units, such as `uart_regfile` and `uart_regfile_pkg`. See [Names](#names). |
| `register` | list | required | The registers, see [Registers](#registers). |
| `version` | string | `""` | The version of the register map. Every generated file carries it, see [Version and hash](#version-and-hash). Printable ASCII characters other than `"`, `\`, `;` and `=`. |
| `description` | string | `""` | Shown in the LaTeX documentation. |
| `byte_addressable` | boolean | from the bus | `true` if an address counts bytes, `false` if it counts data words. See [Byte and word addresses](#byte-and-word-addresses). |
| `hash_register` | boolean or number | `false` | Adds a read-only register that holds the hash. `true` puts it at the lowest free register offset, a number at that register offset. See [Version and hash](#version-and-hash). |
| `git_hash` | string | none | Accepted and ignored. |

### Version and hash

bust gives software and hardware two ways to tell which register map they
are built from. `version` is the text you give in the JSON file, such as
`"1.2"`. bust does not check or change it, so raise it yourself when the
register map changes. The hash is a 32-bit number that bust computes from the
register map on every run, so it changes whenever the register map changes,
with nothing for you to keep up to date.

The hash covers the module name, the data width, `byte_addressable` and, for
each register and field, the name, register offset, bit position, width, type,
reset, access modes and enumeration values. Descriptions, `version`, the bus
type and `addr_width` do not count. Neither does the bust version, so a newer
bust gives the same hash for the same register map. The value is the first 32
bits of the SHA-256 of these values written as JSON.

Both appear in every output:

| Output | Version | Hash |
|---|---|---|
| `<module>_regfile_pkg` | `C_<MODULE>_REGMAP_VERSION`, a `string` | `C_<MODULE>_REGMAP_HASH`, a 32-bit `std_logic_vector` |
| C header | `<MODULE>_REGMAP_VERSION` | `<MODULE>_REGMAP_HASH` |
| C++ and Python headers | `REGMAP_VERSION` | `REGMAP_HASH` |
| IPBus address table | `regmap_version=` in the `parameters` of the top node | `regmap_hash=` in the same `parameters` |
| LaTeX documentation | Title page and page footer | Under the module description |

### The hash register

To let software check at run time which register map the hardware holds, set
`hash_register`. bust then adds a register named `regmap_hash` with `sw` `ro`
and `hw` `na` whose value is the hash. It is a constant, so it costs no
flip-flops. Software reads it and compares it with `REGMAP_HASH` in its
header. A difference means the software and the hardware come from different
register maps.

```json
"module": {
    "name": "uart",
    "version": "1.2",
    "hash_register": "0x0",
    "register": []
}
```

The register appears in the headers, the IPBus address table, the
documentation and the generated testbench like any other register, and it
comes after the registers of the JSON file. The hash covers the register,
apart from its value.

Give it a register offset, as in `"hash_register": "0x0"`, so that it stays in
one place while the register map changes. bust takes that register offset
before it places the other registers. With `true`, it gets the lowest free
register offset after the other registers are placed, so it moves when you add
a register without an `address`.

`regmap_hash` is then a reserved name, and `hash_register` needs a
`data_width` of at least 32 bits.

## Registers

Each entry in `register` is one register.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `name` | string | required | Register name. See [Names](#names). |
| `type` | string | `"default"` | `default`, `vector`, `bit` or `fields`. See [Register types](#register-types). |
| `address` | [number](#numbers) | next free address | Register offset. See [Addresses](#addresses). |
| `width` | [number](#numbers) | `data_width` | Width of a `vector` register. |
| `reset` | [number](#numbers) | `0` | Reset value of a register without fields. See [Reset values](#reset-values). |
| `description` | string | `""` | Shown in the LaTeX documentation and the IPBus address table. |
| `fields` | list | none | The fields of a `fields` register. See [Fields](#fields). |
| access keys | | | Defaults for the register's fields. See [Access keys](#access-keys). |

### Register types

| `type` | The register holds |
|---|---|
| `default` | one `std_logic_vector` of `data_width` bits |
| `vector` | one `std_logic_vector` of `width` bits, from bit 0 |
| `bit` | one `std_logic`, at bit 0 |
| `fields` | the fields listed under `fields` |

A register without fields works like one field that spans the register. It
takes the register's `reset` and access keys, and `to_hw` and `from_hw` hold
its value directly, with no record of its own. bust generated this member of
`to_hw` for `baud_div` in the example:

```vhdl
baud_div : std_logic_vector(15 downto 0);
```

Your logic reads it as `to_hw.baud_div`.

bust ignores a `width` on a `default` or `bit` register and prints a warning:

```text
User-specified width of default register does not match the expected width (32). Ignoring configured width.
```

A register with a `fields` list is a `fields` register, so you can leave out
`"type": "fields"`. It needs at least one field. A `fields` list on a register
of another type stops bust.

### Addresses

`address` is the register offset, the register's distance from the module's
base address. See [Base address and address range](addressing.md). It is a
[number](#numbers), such as `"0x1c"` or `28`. The address must fit in
`addr_width` bits.

Give every register an address when you can. The register map then says where
each register is, and adding, removing or reordering registers does not move
the others.

`address` is optional, though. A register without an `address` gets the lowest
free address. bust goes through the list in order and places each such
register at the first address that no earlier register uses. It steps by
`data_width / 8` when addresses count bytes and by 1 when they count data
words. See [Byte and word addresses](#byte-and-word-addresses). With AXI4-Lite
and 32-bit data, these registers get the addresses in the table:

```json
"register": [
  { "name": "ctrl", "address": "0x0" },
  { "name": "status" },
  { "name": "irq", "address": "0x10" },
  { "name": "debug" }
]
```

| Register | `address` | Address |
|---|---|---|
| `ctrl` | `"0x0"` | 0x0 |
| `status` | left out | 0x4 |
| `irq` | `"0x10"` | 0x10 |
| `debug` | left out | 0x8 |

`debug` comes after `irq` in the list, but 0x8 is the lowest address that no
earlier register uses.

A register with an address that an earlier register already took stops bust.
With `"address": "0x4"` on `irq`, `status` would already have taken 0x4:

```text
When specifying address for register irq, address 0x4 is already assigned to other register
```

So either give every register an address, or list the registers with an
address before the registers without one.

`bust -a` gives every register a new address, in list order, and writes the
addresses into the JSON file. It replaces addresses you set by hand. See
[Command line](command-line.md).

The generated register file compares the whole address, so software has to use
the exact address of each register. An access to any other address, including
a byte address inside a register, gets the bus's error response. See
[Access modes](access-modes.md#unmapped-addresses).

The base address of the module is not part of the register map. You set it
with the `G_BASE_ADDRESS` generic when you instantiate the module. See
[Generated HDL](generated-hdl.md).

### Byte and word addresses

An address counts either bytes or data words. `byte_addressable` in `module`
says which:

| `byte_addressable` | An address counts | bust places registers | An address you set |
|---|---|---|---|
| `true` | bytes | `data_width / 8` apart | must be a multiple of `data_width / 8` |
| `false` | data words | 1 apart | can be any address |

The default follows the bus: `false` on IPBus, whose addresses count 32-bit
words, and `true` on every other bus. Set `false` on another bus when the
master or the interconnect drives word addresses, as many Wishbone designs and
some bridges from IPBus do. The endpoint compares the address exactly as the
master drives it, so `byte_addressable` must match what the master drives.
With 32-bit data, the third register of a module is at `0x8` with `true` and
at `0x2` with `false`.

With `true`, an address that is not a multiple of `data_width / 8` stops bust:

```text
Address 0x6 of register baud_div is not a multiple of 4, the data width in bytes
```

### Reset values

`reset` is a [number](#numbers), such as `"0x1b2"` or `434`. The value must
fit in the register's width, otherwise bust stops:

```text
Could not parse register baud_div: Invalid register format: Reset value does not match register: baud_div
```

Leave `reset` out of a `fields` register and give each field its own `reset`.
bust builds the register's reset value from its fields.

### Names

Module, register, field and enumeration names become VHDL identifiers, so they
must follow the VHDL rules for basic identifiers:

- start with a letter,
- contain only letters, digits and underscores,
- not end with an underscore or contain two underscores in a row,
- not be a VHDL reserved word, such as `signal`, `in` or `register`.

A field named `in`, for example, stops bust. Reserved words count in any case,
so `IN` is rejected too:

```text
Could not parse register ctrl: Invalid identifier: in - identifier cannot be identical to VHDL keyword.
```

bust warns, but goes on, when a name is longer than 16 characters or mixes
uppercase and lowercase letters. The headers turn names into uppercase
constants, such as `CTRL_PARITY_MASK`.

Register names must be unique in the module, field names in their register
and enumeration names in their field. VHDL ignores case, so `ctrl` and `CTRL`
are the same name, and bust stops when two names differ only in case. A
register cannot have the same name as the module, because both would declare a
type `t_<name>_regs`.

## Fields

A `fields` register lists its fields under `fields`. Each entry is one field.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `name` | string | required | Field name. See [Names](#names). |
| `type` | string | required | `bit` for a `std_logic`, `vector` for a `std_logic_vector`. |
| `width` | [number](#numbers) | `1` | Width of a `vector` field. A `bit` field is always 1 bit wide, and bust ignores a different `width` with a warning. |
| `position` | [number](#numbers) | next free bit | Lowest bit of the field. See [Bit positions](#bit-positions). |
| `reset` | [number](#numbers) | `0` | Reset value of the field. |
| `description` | string | `""` | Shown in the LaTeX documentation and the IPBus address table. |
| `enums` | list | none | Named values. See [Enumerations](#enumerations). |
| access keys | | from the register | See [Access keys](#access-keys). |

### Bit positions

Fields fill the register from bit 0 upwards, in the order you list them. Each
field starts at the bit after the previous one, unless it has a `position`. A
`position` can leave a gap, but it cannot go back, so list the fields from the
lowest bit to the highest. In the example, `flush` sits at bit 8 and bits 4 to
7 of `ctrl` are unused:

| Field | Bits |
|---|---|
| `tx_en` | 0 |
| `rx_en` | 1 |
| `parity` | 3:2 |
| `flush` | 8 |

A `position` below the next free bit stops bust:

```text
Could not parse register ctrl: Invalid field format: Field 'flush' in register 'ctrl': position 2 overlaps bits already in use (next free bit is 4).
```

A `fields` register is as wide as its highest field bit plus one, 9 bits for
`ctrl`. It cannot be wider than `data_width`:

```text
Could not parse register ctrl: Register width exceeded module data width by 1 in register ctrl
Module width: 32
Register width: 33
```

Bits that no field covers read as 0, and writes to them have no effect.

## Enumerations

A field with an `enums` list has named values. bust generates a VHDL
enumeration type for it, and the headers get a constant for each value.

```json
{
  "name": "parity",
  "type": "vector",
  "width": 2,
  "enums": [
    { "name": "PAR_NONE", "value": 0 },
    { "name": "PAR_EVEN", "value": 1 },
    { "name": "PAR_ODD", "value": 2 }
  ]
}
```

Each entry has two keys:

- `name`: the name of the value. It becomes a VHDL enumeration literal, so it
  follows the [name rules](#names) and must be unique in the field.
- `value`: the encoding, a [number](#numbers). It must fit in the field's width and
  be unique in the field.

bust reads no other keys from an entry and warns about any other key, such as
a `description`. The values need not be in order or contiguous, and not every
encoding needs a name. `parity` leaves 3 unnamed.

Without a `reset`, an enumerated field resets to the entry with value 0. When
no entry has value 0, it resets to the first entry in the list. A `reset` must
be the value of one of the entries:

```text
Could not parse register ctrl: Invalid field format: Reset value 0x3 of enumerated field parity in reg ctrl matches no declared enum value
```

The other checks give these errors:

```text
Could not parse register ctrl: Invalid field format: Enum 'PAR_ODD' value 4 does not fit field parity (width 2) in reg ctrl
Could not parse register ctrl: Invalid field format: Duplicate enum value 1 in field parity in reg ctrl
Could not parse register ctrl: Invalid field format: Duplicate enum name 'PAR_EVEN' in field parity in reg ctrl
```

`enums` belongs on a field. On a register without fields, bust ignores it with
a warning, so give such a register `"type": "fields"` and one field.
[Access modes](access-modes.md#enumerated-fields) describes the generated type,
how software writes are decoded, and which access keys an enumerated field
cannot have.

## Access keys

| Key | Values | Default |
|---|---|---|
| `sw` | `rw`, `ro`, `wo`, `na` | `rw` |
| `hw` | `r`, `w`, `rw`, `na` | `r` |
| `onread` | `rclr`, `rset` | none |
| `onwrite` | `woset`, `woclr`, `wot`, `wzs`, `wzc`, `wzt`, `wclr`, `wset` | none |
| `singlepulse` | `true`, `false` | `false` |
| `we`, `wel` | `true`, `false` | `false` |
| `hwset`, `hwclr` | `true`, `false` | `false` |
| `swmod`, `swacc` | `true`, `false` | `false` |

Each key can sit on a field, or on its register as the default for all the
register's fields. A key on the field wins over the same key on the register.
[Access modes](access-modes.md) describes what each key does, how
[inheritance](access-modes.md#inheritance) works, and which combinations bust
rejects.

Give the boolean keys as JSON `true` or `false`. A string such as `"false"`
stops bust. `null` counts as `false`. A value that is not in the table stops
bust and lists the valid ones:

```text
Could not parse register ctrl: Invalid SwAccess: 'rx'. Did you mean one of these? ['rw', 'ro', 'wo', 'na']
```

## Settings

bust 1.0 has no `settings` section. Without `-o`, `bust uart.json` writes
`uart/hdl`, `uart/tb`, `uart/header` and `uart/doc` next to `uart.json`, and
`-o DIR` puts the `uart/` directory in `DIR` instead.

bust ignores a `settings` section left from bust 0.14 and warns about it. A
`proj_dir` or `"mod_subdir": false` in it stops bust, because the output would
land somewhere else. `bust FILE --migrate` removes the section and says which
`-o` to use.

## Keys bust does not know

bust warns about each key it does not read, and otherwise ignores it. A
misspelt key such as `onwrit` gives:

```text
Unknown key 'onwrit' in field tx_en of register ctrl is ignored
```

`bust -a` and the [editor](command-line.md#interactive-editor) keep unknown
keys when they save the file.

## Files from bust 0.14

bust 1.0 reads JSON files written for bust 0.14. A 0.14 register has a `mode`
instead of access keys, and bust translates it:

| `mode` | Becomes |
|---|---|
| `rw`, or no `mode` | `"sw": "rw", "hw": "r"` |
| `ro` | `"sw": "ro", "hw": "w"` |
| `pulse` | `"sw": "wo", "hw": "r", "singlepulse": true` |

A `pulse` register therefore returns to its reset value one clock cycle after
a software write.

bust 0.14 called the `bit` and `vector` types `sl` and `slv`, for registers and
fields. bust 1.0 still reads these names and warns once per file that they are
deprecated:

```text
The bust 0.14 type names 'sl' and 'slv' are deprecated. Use 'bit' and 'vector' instead (17 registers and fields).
```

`bust FILE --migrate` saves the file with the new names. The types `default` and
`fields` are the same in both versions.

bust 0.14 wrote `byte_addressable` as the string `"True"` or `"False"`. bust
1.0 reads both and warns that they are deprecated, and `bust FILE --migrate` saves
`true` or `false`:

```text
byte_addressable "False" is the deprecated bust 0.14 form. Use false, without quotes.
```

bust 0.14 read an `address` or a `reset` as hexadecimal even without `0x`, so
`"10"` meant 0x10. bust 1.0 reads a string without a prefix as decimal, so
`"10"` is 10. Add `0x` to such values before you run bust 1.0. The values 0 to
9 are the same either way. A value with a hexadecimal letter, such as `"1c"`,
stops bust with a message that suggests `"0x1c"`. bust 0.14 and its editor
wrote `0x` themselves, so only values typed by hand can lack it.

The fields of a `mode` register can set their own access keys, but a register
cannot have `mode` together with access keys of its own:

```text
Could not parse register baud_div: Invalid register format: Register baud_div sets the legacy 'mode' key together with bust 1.0 access-mode keys (sw/hw/...); use one schema, not both
```

In bust 1.0 a pulse lasts one clock cycle, and the register file has no
configurable stall. `pulse_cycles: 1` and `stall_cycles: 0` are accepted and
have no effect. Other values stop bust:

```text
Could not parse register go: Invalid register format: Register 'go': pulse_cycles=2 is not supported in bust 1.0. A pulse register drives the written value for one clock cycle and then returns to its reset value. Remove pulse_cycles.
Could not parse register st: Invalid register format: Register 'st': stall_cycles is not supported in bust 1.0, because registers live in the generated register file and always answer in one cycle. Remove stall_cycles.
```

bust no longer reads the 0.14 `settings` section, see [Settings](#settings).
[Upgrading from 0.14](upgrading.md) lists everything else that changed.
