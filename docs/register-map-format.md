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
        "type": "vector",
        "width": 16,
        "reset": "0x1b2",
        "sw": "rw",
        "hw": "r",
        "description": "Clock cycles per bit."
      },
      {
        "name": "status",
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

The file has up to three sections:

- `bus`: the bus protocol and its address and data widths.
- `module`: the module's name and its registers.
- `settings` (optional): where bust writes its output.

This page describes every key. The access keys (`sw`, `hw`, `onread` and the
others) decide what software and hardware can do with each field.
[Access modes](access-modes.md) describes what each of them does in hardware.

bust reads and checks the whole file before it writes anything. At the first
error it prints what is wrong and exits with status 1.

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
| `addr_width` | integer | required | Width of the bus address in bits. |
| `data_width` | integer | required | Width of the bus data in bits. No register can be wider. |
| `comp_library` | string | none | Accepted so that bust 0.14 files still load. It has no effect. |

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

bust does not limit the widths of the other buses. On a byte-addressed bus,
use a `data_width` that is a multiple of 8, because bust places registers
`data_width / 8` bytes apart. [Buses](buses.md) describes the ports and the
timing of each protocol.

`bust -a` also writes a `reset` key into `bus`, which names the reset style of
the bus. bust ignores it when it reads the file.

## Module

| Key | Type | Default | Meaning |
|---|---|---|---|
| `name` | string | required | Module name. It names the generated files and VHDL units, such as `uart_regfile` and `uart_regfile_pkg`. See [Names](#names). |
| `register` | list | required | The registers, see [Registers](#registers). |
| `version` | string | `""` | Shown in the LaTeX documentation. |
| `description` | string | `""` | Shown in the LaTeX documentation. |
| `byte_addressable` | boolean | from the bus | How far apart bust places registers that have no address. See [Addresses](#addresses). |
| `git_hash` | string | none | Accepted and ignored. |

## Registers

Each entry in `register` is one register.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `name` | string | required | Register name. See [Names](#names). |
| `type` | string | `"default"` | `default`, `vector`, `bit` or `fields`. See [Register types](#register-types). |
| `address` | string | next free address | Hexadecimal address. See [Addresses](#addresses). |
| `width` | integer | `data_width` | Width of a `vector` register. |
| `reset` | string | `"0x0"` | Hexadecimal reset value of a register without fields. See [Reset values](#reset-values). |
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

A register without fields counts as one field with the same name as the
register. It takes the register's `reset` and access keys. bust generated this
record for `baud_div` in the example:

```vhdl
type t_baud_div_to_hw is record
  baud_div : std_logic_vector(15 downto 0);
end record;
```

Your logic reads it as `to_hw.baud_div.baud_div`.

bust ignores a `width` on a `default` or `bit` register and prints a warning:

```text
User-specified width of default register does not match the expected width (32). Ignoring configured width.
```

A register with fields needs `"type": "fields"` and at least one field.
Without the `type`, bust treats the register as `default` and ignores its
`fields` list.

### Addresses

`address` is a hexadecimal string such as `"0x1c"`. The `0x` is optional, so
`"10"` means 0x10. A JSON number is not accepted. The address must fit in
`addr_width` bits.

A register without an `address` gets the lowest free address. bust goes
through the list in order and places each such register at the first address
that no earlier register uses. It steps by `data_width / 8` on byte-addressed
buses and by 1 on IPBus. With AXI4-Lite and 32-bit data, the registers of the
example land at 0x0, 0x4 and 0x8.

You can give some registers an address and leave it out on others. A register
with an address that an earlier register already took stops bust:

```text
When specifying address for register status, address 0x4 is already assigned to other register
```

So either give every register an address, or list the registers with fixed
addresses first.

`bust -a` gives every register a new address, in list order, and writes the
addresses into the JSON file. It replaces addresses you set by hand. See
[Command line](command-line.md).

`byte_addressable` in `module` overrides the step: `false` steps by 1 and
`true` by `data_width / 8`. It only changes the addresses bust picks. The bus
endpoint still compares the address exactly as the bus master drives it.

bust does not check that an address is a multiple of `data_width / 8`. The
generated register file compares the whole address, so software has to use the
exact address of each register. An access to any other address, including a
byte address inside a register, gets the bus's error response. See
[Access modes](access-modes.md#unmapped-addresses).

The base address of the module is not part of the register map. You set it
with the `G_BASE_ADDRESS` generic when you instantiate the module. See
[Generated HDL](generated-hdl.md).

### Reset values

`reset` is a hexadecimal string, written like `address`: `"0x1b2"`, `"1B2"`.
A JSON number is not accepted. The value must fit in the register's width,
otherwise bust stops:

```text
Failed to parse register baud_div: InvalidRegisterFormat: Invalid register format: Reset value does not match register: baud_div
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

A field named `in`, for example, stops bust:

```text
Error in parsing identifier: in - identifier cannot be identical to VHDL keyword.
```

bust warns, but goes on, when a name is longer than 16 characters or mixes
uppercase and lowercase letters. The headers turn names into uppercase
constants, such as `CTRL_PARITY_MASK`.

Register names must be unique in the module, field names in their register
and enumeration names in their field. VHDL ignores case, so `ctrl` and `CTRL`
are the same name. A register cannot have the same name as the module, because
both would declare a type `t_<name>_regs`.

## Fields

A `fields` register lists its fields under `fields`. Each entry is one field.

| Key | Type | Default | Meaning |
|---|---|---|---|
| `name` | string | required | Field name. See [Names](#names). |
| `type` | string | required | `bit` for a `std_logic`, `vector` for a `std_logic_vector`. |
| `width` | integer | `1` | Width of a `vector` field. A `bit` field is always 1 bit wide, and bust ignores a different `width` with a warning. |
| `position` | integer | next free bit | Lowest bit of the field. See [Bit positions](#bit-positions). |
| `reset` | string | `"0x0"` | Hexadecimal reset value, written like a register's `reset`. |
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
Failed to parse register ctrl: InvalidFieldFormat: Invalid field format: Field 'flush' in register 'ctrl': position 2 overlaps bits already in use (next free bit is 4).
```

A `fields` register is as wide as its highest field bit plus one, 9 bits for
`ctrl`. It cannot be wider than `data_width`:

```text
Failed to parse register ctrl: ModuleDataBitsExceeded: Register width exceeded module data width by 1 in register ctrl
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
- `value`: the encoding, a JSON integer. It must fit in the field's width and
  be unique in the field.

bust reads no other keys from an entry, so an entry cannot have a
description. The values need not be in order or contiguous, and not every
encoding needs a name. `parity` leaves 3 unnamed.

Without a `reset`, an enumerated field resets to the entry with value 0. When
no entry has value 0, it resets to the first entry in the list. A `reset` must
be the value of one of the entries:

```text
Failed to parse register ctrl: InvalidFieldFormat: Invalid field format: Reset value 0x3 of enumerated field parity in reg ctrl matches no declared enum value
```

The other checks give these errors:

```text
Failed to parse register ctrl: InvalidFieldFormat: Invalid field format: Enum 'PAR_ODD' value 4 does not fit field parity (width 2) in reg ctrl
Failed to parse register ctrl: InvalidFieldFormat: Invalid field format: Duplicate enum value 1 in field parity in reg ctrl
Failed to parse register ctrl: InvalidFieldFormat: Invalid field format: Duplicate enum name 'PAR_EVEN' in field parity in reg ctrl
```

`enums` belongs on a field. On a register without fields, bust ignores it, so
give such a register `"type": "fields"` and one field.
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

Give the boolean keys as JSON `true` or `false`, not as strings. A value that
is not in the table stops bust and lists the valid ones:

```text
Failed to parse register ctrl: ValueError: Invalid SwAccess: 'rx'. Did you mean one of these? ['rw', 'ro', 'wo', 'na']
```

## Settings

Most files need no `settings` section. It decides where bust writes its
output:

```json
"settings": {
  "proj_dir": "build",
  "mod_subdir": false
}
```

| Key | Type | Default | Meaning |
|---|---|---|---|
| `proj_dir` | string | the directory of the JSON file | Output directory, used when you run bust without `-o`. A relative path is relative to the directory you run bust from, not to the JSON file. A leading `~` is expanded. |
| `mod_subdir` | boolean | `true` | Put the output in a subdirectory named after the module, inside the output directory. With `false`, bust writes straight into the output directory. |

With neither key and no `-o`, `bust uart.json` writes `uart/hdl`, `uart/tb`,
`uart/header` and `uart/doc` next to `uart.json`.

bust also accepts `bus_subdir`, `coverage`, `uvvm_rel_path`, `ipbus_rel_path`
and `vip_ipbus_rel_path`, so that bust 0.14 files still load, and ignores
them.

## Keys bust does not know

bust ignores keys it does not know. A misspelt key, such as `onwrit` instead of
`onwrite`, is dropped without an error. If a field does not behave as you
expect, check the spelling of its keys.

## Files from bust 0.14

bust 1.0 reads JSON files written for bust 0.14. A 0.14 register has a `mode`
instead of access keys, and bust translates it:

| `mode` | Becomes |
|---|---|
| `rw`, or no `mode` | `"sw": "rw", "hw": "r"` |
| `ro` | `"sw": "ro", "hw": "w"` |
| `pulse` | `"sw": "wo", "hw": "r", "singlepulse": true` |

A `pulse` register therefore returns to its reset value one clock cycle after
a software write. The register types `default`, `vector`, `bit` and `fields`
are the same in both versions. The fields of a `mode` register can set their
own access keys, but a register cannot have `mode` together with access keys
of its own:

```text
Failed to parse register baud_div: InvalidRegisterFormat: Invalid register format: Register baud_div sets the legacy 'mode' key together with bust 1.0 access-mode keys (sw/hw/...); use one schema, not both
```

In bust 1.0 a pulse lasts one clock cycle, and the register file has no
configurable stall. `pulse_cycles: 1` and `stall_cycles: 0` are accepted and
have no effect. Other values stop bust:

```text
Failed to parse register go: InvalidRegisterFormat: Invalid register format: Register 'go': pulse_cycles=2 is not supported in bust 1.0. A pulse register drives the written value for one clock cycle and then returns to its reset value. Remove pulse_cycles.
Failed to parse register st: InvalidRegisterFormat: Invalid register format: Register 'st': stall_cycles is not supported in bust 1.0, because registers live in the generated register file and always answer in one cycle. Remove stall_cycles.
```

The 0.14 settings `bus_subdir`, `coverage`, `uvvm_rel_path`, `ipbus_rel_path`
and `vip_ipbus_rel_path` are ignored, see [Settings](#settings).
[Upgrading from 0.14](upgrading.md) lists everything else that changed.
