# Getting started

This page installs bust, describes a small timer module in JSON, generates its
VHDL, headers and testbench, and connects the result to a design.

## Install

bust needs Python 3.9 or newer.

```bash
pip install bust
bust --version
```

## Describe your registers

A register map is one JSON file with a `bus` section and a `module` section.
This one describes a timer with four registers:

```json
{
  "bus": {
    "type": "axi",
    "addr_width": 32,
    "data_width": 32,
    "comp_library": "work"
  },
  "module": {
    "name": "timer",
    "version": "1.0",
    "description": "A timer with a control, a period, a status and an event register.",
    "register": [
      {
        "name": "ctrl",
        "sw": "rw",
        "hw": "r",
        "type": "fields",
        "description": "Timer control.",
        "fields": [
          { "name": "enable", "type": "bit", "description": "Count while 1." },
          {
            "name": "mode",
            "type": "vector",
            "width": 2,
            "description": "What happens when the counter reaches the period.",
            "enums": [
              { "name": "ONESHOT", "value": 0 },
              { "name": "PERIODIC", "value": 1 }
            ]
          }
        ]
      },
      {
        "name": "period",
        "sw": "rw",
        "hw": "r",
        "type": "fields",
        "description": "Number of clock cycles per period.",
        "fields": [
          { "name": "cycles", "type": "vector", "width": 16, "reset": "0x3e8" }
        ]
      },
      {
        "name": "status",
        "sw": "ro",
        "hw": "w",
        "type": "fields",
        "description": "Timer state, written by hardware.",
        "fields": [
          { "name": "count", "type": "vector", "width": 16 },
          { "name": "running", "type": "bit" }
        ]
      },
      {
        "name": "event",
        "sw": "rw",
        "hw": "r",
        "type": "fields",
        "description": "Sticky event flags.",
        "fields": [
          {
            "name": "expired",
            "type": "bit",
            "hwset": true,
            "onwrite": "woclr",
            "description": "Set by hardware when the period ends. Write 1 to clear."
          }
        ]
      }
    ]
  }
}
```

Each register says what software can do with it (`sw`) and what hardware can do
with it (`hw`):

- `ctrl` and `period` are written by software and read by hardware. The `mode`
  field has named values, so bust generates a VHDL enumeration type for it.
- `status` is read-only for software and written by hardware.
- `event.expired` is a sticky flag. Hardware sets it with `hwset`, and software
  clears it by writing 1 (`onwrite: woclr`).

The registers have no addresses, so bust places them one after another from
address 0. [Register map format](register-map-format.md) lists every key, and
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
record ports, `to_hw` and `from_hw`, that carry every field by name. These are
the records bust generated for the timer:

```vhdl
type t_timer_to_hw is record
  ctrl   : t_ctrl_to_hw;     -- enable : std_logic, mode : t_ctrl_mode
  period : t_period_to_hw;   -- cycles : std_logic_vector(15 downto 0)
  event  : t_event_to_hw;    -- expired : std_logic
end record;

type t_timer_from_hw is record
  status : t_status_from_hw; -- count : std_logic_vector(15 downto 0), running : std_logic
  event  : t_event_from_hw;  -- expired.set : std_logic
end record;
```

Instantiate the module and connect your logic through the records:

```vhdl
use work.timer_regfile_pkg.all;

signal timer_to_hw   : t_timer_to_hw;
signal timer_from_hw : t_timer_from_hw;

i_timer_regs : entity work.timer
  generic map (
    G_BASE_ADDRESS => x"4000_0000")
  port map (
    clk      => clk,
    areset_n => areset_n,
    awaddr   => s_axi_awaddr,
    -- ... the other AXI4-Lite signals ...
    to_hw    => timer_to_hw,
    from_hw  => timer_from_hw);

-- Your timer logic reads the control fields by name ...
count_enable <= timer_to_hw.ctrl.enable;
is_periodic  <= timer_to_hw.ctrl.mode = PERIODIC;

-- ... and drives the status fields and the event flag.
timer_from_hw.status.count       <= std_logic_vector(counter);
timer_from_hw.status.running     <= count_enable;
timer_from_hw.event.expired.set  <= period_done;
```

The base address is a generic, so the same module can sit at different
addresses in different designs. [Generated HDL](generated-hdl.md) describes the
files and records in detail, and [Buses](buses.md) covers the ports of each bus.

## Use the headers

The headers give software the same names. From `timer.h`:

```c
#define CTRL_OFFSET 0x0
#define CTRL_MODE_OFFSET 1
#define CTRL_MODE_MASK 0x6
#define CTRL_MODE_PERIODIC 1
```

```c
uint32_t ctrl = read32(TIMER_BASE + CTRL_OFFSET);
ctrl = (ctrl & ~CTRL_MODE_MASK) | (CTRL_MODE_PERIODIC << CTRL_MODE_OFFSET);
write32(TIMER_BASE + CTRL_OFFSET, ctrl);
```

`read32`, `write32` and `TIMER_BASE` stand for whatever your platform uses.
[Headers and documentation](headers-and-docs.md) covers the C++, Python and
IPBus outputs.

## Run the testbench

`timer_tb.vhd` is a self-checking UVVM testbench that resets the module and
checks every register through the bus. It needs UVVM and the bus VIP compiled
into their libraries. [Testbenches](testbenches.md) describes what it checks and
how to run it.

## Change the register map

Edit the JSON and run bust again. Without `-f`, bust asks before it overwrites
each existing file. With `-f` it overwrites them all:

```bash
bust timer.json -o out -f
```

Every generated file is regenerated, including `timer.vhd`, so keep your own
logic in your own files and connect it through `to_hw` and `from_hw`.
