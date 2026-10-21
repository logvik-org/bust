# Getting started

This page installs bust, describes a small timer module in JSON, generates its
VHDL, headers and testbench, and connects the result to a design. The same
timer is used on the other pages of this documentation.

## Install

bust needs Python 3.9 or newer.

```bash
pip install bust
bust --version
```

## Describe your registers

A register map is one JSON file with a `bus` section and a `module` section.
Save this one as `timer.json`:

```json
{
  "bus": {
    "type": "axi",
    "addr_width": 32,
    "data_width": 32
  },
  "module": {
    "name": "timer",
    "register": [
      {
        "name": "ctrl", "address": "0x0", "sw": "rw", "hw": "r", "type": "fields",
        "fields": [
          {"name": "enable", "type": "bit"},
          {"name": "mode", "type": "vector", "width": 2,
           "enums": [{"name": "ONESHOT", "value": 0}, {"name": "PERIODIC", "value": 1}]},
          {"name": "start", "type": "bit", "singlepulse": true}
        ]
      },
      {
        "name": "load", "address": "0x4", "sw": "rw", "hw": "r",
        "type": "default", "swmod": true
      },
      {
        "name": "status", "address": "0x8", "sw": "ro", "hw": "w", "type": "fields",
        "fields": [
          {"name": "count", "type": "vector", "width": 16, "we": true},
          {"name": "running", "type": "bit"}
        ]
      },
      {
        "name": "irq", "address": "0xc", "sw": "rw", "hw": "r", "type": "fields",
        "fields": [
          {"name": "expired", "type": "bit", "hwset": true, "onwrite": "woclr"}
        ]
      }
    ]
  }
}
```

Each register says what software can do with it (`sw`) and what hardware can do
with it (`hw`):

- `ctrl` is written by software and read by hardware. `mode` has named values,
  so bust generates a VHDL enumeration type for it. `start` is a
  `singlepulse` field: a software write shows to hardware for one clock cycle.
- `load` is a full-width register. `swmod` gives hardware a one-cycle strobe
  each time software writes it.
- `status` is read-only for software and written by hardware. `count` takes
  the hardware value only while its write enable `we` is high.
- `irq.expired` is a sticky flag. Hardware sets it with `hwset`, and software
  clears it by writing 1 (`onwrite: woclr`).

[Register map format](register-map-format.md) lists every key, and
[Access modes](access-modes.md) describes what each access mode does.

## Generate

```bash
bust timer.json -o out
```

bust writes one directory per module:

```text
out/timer/
├── doc/
│   ├── timer.pdf
│   └── timer.tex
├── hdl/
│   ├── timer.vhd
│   ├── timer_axi_endpoint.vhd
│   ├── timer_localbus_pkg.vhd
│   ├── timer_regfile.vhd
│   └── timer_regfile_pkg.vhd
├── header/
│   ├── timer.h
│   ├── timer.hpp
│   └── timer.py
└── tb/
    └── timer_tb.vhd
```

The PDF needs `pdflatex` on your `PATH`. Add `-p` to skip it.
[Command line](command-line.md) describes every option.

## Use the VHDL

The generated VHDL needs VHDL-2008. Compile the files in this order, into one
library:

1. `timer_localbus_pkg.vhd`
2. `timer_regfile_pkg.vhd`
3. `timer_regfile.vhd`
4. `timer_axi_endpoint.vhd`
5. `timer.vhd`

`timer` is the entity you instantiate. Next to the AXI4-Lite ports it has two
record ports, `to_hw` and `from_hw`, that carry every field by name:

```vhdl
type t_timer_to_hw is record
  ctrl : t_ctrl_to_hw;     -- enable, mode (t_ctrl_mode), start
  load : t_load_load_out;  -- value, swmod
  irq  : t_irq_to_hw;      -- expired
end record;

type t_timer_from_hw is record
  status : t_status_from_hw;  -- count.value, count.we, running
  irq    : t_irq_from_hw;     -- expired.set
end record;
```

Instantiate the module and connect your logic through the records:

```vhdl
use work.timer_regfile_pkg.all;

signal timer_to_hw   : t_timer_to_hw;
signal timer_from_hw : t_timer_from_hw;

i_timer : entity work.timer
  generic map (
    G_BASE_ADDRESS      => x"4000_1000",
    G_MODULE_ADDR_WIDTH => 12)
  port map (
    clk      => clk,
    areset_n => areset_n,
    awaddr   => awaddr,
    -- ... the other AXI4-Lite signals ...
    to_hw    => timer_to_hw,
    from_hw  => timer_from_hw);

-- Your logic reads the control fields by name ...
run      <= timer_to_hw.ctrl.enable;
periodic <= timer_to_hw.ctrl.mode = PERIODIC;

-- ... and drives the status fields and the event flag.
timer_from_hw.status.count.value <= std_logic_vector(count);
timer_from_hw.status.count.we    <= run;
timer_from_hw.status.running     <= '1' when count /= 0 else '0';
timer_from_hw.irq.expired.set    <= '1' when count = 1 else '0';
```

The base address is a generic, so the same module can sit at different
addresses in different designs. `G_MODULE_ADDR_WIDTH => 12` gives the timer a
4 KiB address range, and any address in it without a register gets an error.
[Base address and address range](addressing.md) shows how to choose these
generics for your interconnect. [Generated HDL](generated-hdl.md) shows the
complete timer logic and describes the files and records in detail, and
[Buses](buses.md) covers the ports of each bus.

## Use the headers

The headers give software the same names. From `timer.h`:

```c
#define TIMER_CTRL_OFFSET 0x0
#define TIMER_CTRL_MODE_OFFSET 1
#define TIMER_CTRL_MODE_MASK 0x6
#define TIMER_CTRL_MODE_PERIODIC 1
```

```c
uint32_t ctrl = read32(TIMER_BASE + TIMER_CTRL_OFFSET);
ctrl = (ctrl & ~TIMER_CTRL_MODE_MASK)
     | (TIMER_CTRL_MODE_PERIODIC << TIMER_CTRL_MODE_OFFSET);
write32(TIMER_BASE + TIMER_CTRL_OFFSET, ctrl);
```

`read32`, `write32` and `TIMER_BASE` stand for whatever your platform uses.
[Headers and documentation](headers-and-docs.md) covers the C++, Python and
IPBus outputs.

## Run the testbench

`timer_tb.vhd` is a self-checking UVVM testbench. It drives the module through
the bus and through `from_hw`, and checks the registers it can classify, such
as the read-write, `onwrite` and strobe registers. It needs UVVM and the bus
VIP compiled into their libraries. [Testbenches](testbenches.md) describes what
it checks and how to run it.

## Change the register map

Edit the JSON and run bust again. Without `-f`, bust asks before it overwrites
each existing file. With `-f` it overwrites them all:

```bash
bust timer.json -o out -f
```

Every generated file is regenerated, including `timer.vhd`, so keep your own
logic in your own files and connect it through `to_hw` and `from_hw`.
