# Generated HDL

For each register map, bust writes a small set of VHDL files. Your design
instantiates one entity, named after the module, connects the bus to it, and
reads and drives the registers through two records, `to_hw` and `from_hw`.

The examples on this page use a timer module on AXI4-Lite. Every VHDL snippet
is bust's output for this register map, trimmed:

```json
{
  "settings": {
    "mod_subdir": true
  },
  "bus": {
    "type": "axi",
    "addr_width": 32,
    "data_width": 32
  },
  "module": {
    "name": "timer",
    "register": [
      {
        "name": "ctrl", "sw": "rw", "hw": "r", "type": "fields",
        "fields": [
          {"name": "enable", "type": "bit"},
          {"name": "mode", "type": "vector", "width": 2,
           "enums": [{"name": "ONESHOT", "value": 0}, {"name": "PERIODIC", "value": 1}]},
          {"name": "start", "type": "bit", "singlepulse": true}
        ]
      },
      {"name": "load", "sw": "rw", "hw": "r", "type": "default", "swmod": true},
      {
        "name": "status", "sw": "ro", "hw": "w", "type": "fields",
        "fields": [
          {"name": "count", "type": "vector", "width": 16, "we": true},
          {"name": "running", "type": "bit"}
        ]
      },
      {
        "name": "irq", "sw": "rw", "hw": "r", "type": "fields",
        "fields": [
          {"name": "expired", "type": "bit", "hwset": true, "onwrite": "woclr"}
        ]
      }
    ]
  }
}
```

The [register map format](register-map-format.md) page describes the JSON, and
[Access modes](access-modes.md) describes what `sw`, `hw` and the modifiers do.

## Files

For a module named `<module>`, bust writes these files:

| File | Contents |
|------|----------|
| `<module>_localbus_pkg.vhd` | The local-bus records `t_lb_m2s` and `t_lb_s2m`, sized for this module. |
| `<module>_regfile_pkg.vhd` | Register addresses, enumeration types, and the `to_hw` and `from_hw` record types you connect to. |
| `<module>_regfile.vhd` | The register file: storage, access-mode behaviour, hardware updates, the read mux and the bus response. |
| `<module>_<bus>_endpoint.vhd` | The bus endpoint. It translates the bus protocol to the local bus and instantiates the register file. |
| `<module>.vhd` | The top wrapper, the entity you instantiate. It contains only the endpoint. |
| `<module>_tb.vhd` | A self-checking UVVM testbench for the top wrapper. See [Testbenches](testbenches.md). |

`<bus>` is `axi`, `ipb`, `sbi`, `avalon`, `wishbone` or `apb`. The
[Buses](buses.md) page lists the ports of each endpoint. The top wrapper has
the same generics and ports as its endpoint.

### Where the files go

The VHDL lands in `hdl/` and the testbench in `tb/`, next to the `header/` and
`doc/` directories of the [headers and documentation](headers-and-docs.md). For
the timer:

```text
timer/
├── doc/
├── hdl/
│   ├── timer.vhd
│   ├── timer_axi_endpoint.vhd
│   ├── timer_localbus_pkg.vhd
│   ├── timer_regfile.vhd
│   └── timer_regfile_pkg.vhd
├── header/
└── tb/
    └── timer_tb.vhd
```

The `timer/` directory is there because `mod_subdir` is `true`, which is also
the default. With `"mod_subdir": false`, the four directories go straight into
the output directory. You choose the output directory with `-o`.
[Command line](command-line.md) describes the default.

### Compile order

Compile the files in this order, all into the same library:

1. `<module>_localbus_pkg.vhd`
2. `<module>_regfile_pkg.vhd`
3. `<module>_regfile.vhd`
4. `<module>_<bus>_endpoint.vhd`
5. `<module>.vhd`
6. `<module>_tb.vhd`, for simulation only

The files refer to each other through `work`, so the library name is up to
you. The `comp_library` key of the `bus` object does not change the generated
HDL. The files use VHDL-2008 syntax, so compile with VHDL-2008 enabled. With
[GHDL](https://github.com/ghdl/ghdl), into a library called `periph`:

```bash
for f in timer_localbus_pkg timer_regfile_pkg timer_regfile timer_axi_endpoint timer; do
  ghdl -a --std=08 --work=periph timer/hdl/$f.vhd
done
```

An IPBus module also needs the IPBus package compiled into a library called
`ipbus` first, see [IPBus](buses.md#ipbus).

## The local bus

bust keeps all register-map logic in one register file per module and connects
it to your bus through a thin endpoint. Between the two is the local bus, a
minimal single-beat interface. The register file is the same VHDL whichever
bus you choose, so every bus gets the same access-mode behaviour. Changing the
bus replaces the endpoint and the ports of the top wrapper, and the register
file stays the same.

The local bus is two records in `<module>_localbus_pkg`:

```vhdl
package timer_localbus_pkg is

  constant C_LB_ADDR_WIDTH : natural := 32;
  constant C_LB_DATA_WIDTH : natural := 32;

  type t_lb_m2s is record
    address : std_logic_vector(C_LB_ADDR_WIDTH - 1 downto 0);
    wdata   : std_logic_vector(C_LB_DATA_WIDTH - 1 downto 0);
    wen     : std_logic;
    ren     : std_logic;
  end record;

  type t_lb_s2m is record
    rdata : std_logic_vector(C_LB_DATA_WIDTH - 1 downto 0);
    ack   : std_logic;
    err   : std_logic;
  end record;
```

The widths are the `addr_width` and `data_width` of the register map.

| Member | Direction | Meaning |
|--------|-----------|---------|
| `address` | endpoint to register file | The address the bus master drove, unchanged. A byte address on every bus except IPBus, where it is a word address. |
| `wdata` | endpoint to register file | Write data. |
| `wen` | endpoint to register file | Write request. |
| `ren` | endpoint to register file | Read request. |
| `rdata` | register file to endpoint | Read data, valid with `ack`. |
| `ack` | register file to endpoint | The access completed. |
| `err` | register file to endpoint | The address did not decode, see [errors](buses.md#errors). |

A transfer works like this:

- The endpoint raises one of `wen` or `ren`, with `address` and `wdata`, and
  holds them until it sees `ack` or `err`.
- The register file answers with a one-cycle pulse on `ack` or `err` in the
  clock cycle after the request. There is one transfer at a time and no bursts.
- A request that is still held in the cycle of the answer is not serviced
  again, so every transfer takes at least two clock cycles.

There is no separate wait or stall signal. A target that needs more time
answers later, and the endpoint waits. The generated register file always
answers in one cycle.

The register file entity takes the local bus, the clock and a reset whose
polarity the endpoint sets to match its bus:

```vhdl
entity timer_regfile is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := 32x"0";
    G_CHECK_BASE_ADDRESS : boolean := true;
    -- Reset polarity. The regfile normalizes internally so the rest of the
    -- logic is polarity-agnostic.
    G_RESET_ACTIVE_LOW   : boolean := false
  );
  port (
    clk     : in  std_logic;
    reset   : in  std_logic;
    lb_m2s  : in  t_lb_m2s;
    lb_s2m  : out t_lb_s2m;
    to_hw   : out t_timer_to_hw;
    from_hw : in  t_timer_from_hw
  );
end entity timer_regfile;
```

The register file resets synchronously, on a rising edge of `clk` while the
reset is asserted.

## The register-file package

`<module>_regfile_pkg` holds everything your design needs to talk to the
registers. Use it in any file that connects to the module:

```vhdl
use work.timer_regfile_pkg.all;
```

| Name | What it is |
|------|------------|
| `C_ADDR_<REG>` | The address of each register within the module, `addr_width` bits wide. |
| `C_MODULE_ADDR_WIDTH` | The number of low address bits that select a register. |
| `t_<reg>_<field>` | The enumeration type of an enumerated field. |
| `to_slv`, `to_<reg>_<field>` | Conversions between an enumeration type and its bits. |
| `t_<module>_to_hw` | Everything the hardware reads, one member per register. |
| `t_<reg>_to_hw` | The fields of one register that the hardware reads. |
| `t_<reg>_<field>_out` | One field's value together with its `swmod` or `swacc` strobe. |
| `t_<module>_from_hw` | Everything the hardware drives, one member per register. |
| `t_<reg>_from_hw` | The fields of one register that the hardware drives. |
| `t_<reg>_<field>_in` | One field's value together with its `we`, `wel`, `set` or `clr` input. |
| `t_<module>_regs`, `t_<reg>_regs`, `C_<MODULE>_REGS_RESET`, `base_match`, `sel_is`, `is_mapped` | The register file's internal storage, its reset value and its address decoding. Your design does not need them. |

Register and field names keep the case you gave them in the JSON. The
`C_ADDR_` constants use the register name in upper case.

The timer's addresses and its enumeration type:

```vhdl
  constant C_ADDR_CTRL : std_logic_vector(31 downto 0) := 32x"00";
  constant C_ADDR_LOAD : std_logic_vector(31 downto 0) := 32x"04";
  constant C_ADDR_STATUS : std_logic_vector(31 downto 0) := 32x"08";
  constant C_ADDR_IRQ : std_logic_vector(31 downto 0) := 32x"0C";

  constant C_MODULE_ADDR_WIDTH : natural := 4;

  type t_ctrl_mode is (ONESHOT, PERIODIC);
  function to_slv(v : t_ctrl_mode) return std_logic_vector;
  function to_ctrl_mode(s : std_logic_vector(1 downto 0)) return t_ctrl_mode;
```

### Hardware reads: `to_hw`

`to_hw` has one member per register that has at least one field with `hw: r`
or `hw: rw`, and that member has one member per such field:

```vhdl
  type t_ctrl_to_hw is record
    enable : std_logic;
    mode : t_ctrl_mode;
    start : std_logic;
  end record;
  type t_load_load_out is record
    value : std_logic_vector(31 downto 0);
    swmod : std_logic;
  end record;

  type t_load_to_hw is record
    load : t_load_load_out;
  end record;
  type t_irq_to_hw is record
    expired : std_logic;
  end record;

  type t_timer_to_hw is record
    ctrl : t_ctrl_to_hw;
    load : t_load_to_hw;
    irq : t_irq_to_hw;
  end record;
```

| Field | Member in `to_hw.<reg>.<field>` |
|-------|---------------------------------|
| A bit field | `std_logic` |
| A vector field | `std_logic_vector(width - 1 downto 0)` |
| An enumerated field | Its enumeration type, such as `t_ctrl_mode` |
| A field with `swmod` or `swacc` | A record with `value` and the strobe, such as `to_hw.load.load.swmod` |

A register without fields, such as `load` of type `default`, counts as one
field with the register's name, so its value is `to_hw.load.load`. Here it is
`to_hw.load.load.value`, because the field has `swmod`. `status` is missing
because hardware cannot read it.

### Hardware drives: `from_hw`

`from_hw` has one member per register that has at least one field the hardware
writes (`hw: w` or `hw: rw`) or sets or clears (`hwset`, `hwclr`):

```vhdl
  type t_status_count_in is record
    value : std_logic_vector(15 downto 0);
    we : std_logic;
  end record;

  type t_status_from_hw is record
    count : t_status_count_in;
    running : std_logic;
  end record;
  type t_irq_expired_in is record
    set : std_logic;
  end record;

  type t_irq_from_hw is record
    expired : t_irq_expired_in;
  end record;

  type t_timer_from_hw is record
    status : t_status_from_hw;
    irq : t_irq_from_hw;
  end record;
```

| Field | Member in `from_hw.<reg>.<field>` |
|-------|-----------------------------------|
| `hw: w` or `rw` without modifiers | The value itself. The register file stores it every clock cycle. |
| With `we` or `wel` | A record with `value` and `we` or `wel`. |
| With `hwset` or `hwclr` | A record with `set` or `clr`, after `value` if the hardware also writes the field. |

A module whose fields the hardware never reads has no `to_hw` port, and one
whose fields the hardware never drives has no `from_hw` port.

## Instantiate the module

Instantiate the top wrapper, connect the bus ports, and declare one signal of
each record type. The timer's AXI4-Lite ports connect one to one:

```vhdl
use work.timer_regfile_pkg.all;

architecture rtl of my_design is

  signal timer_to_hw   : t_timer_to_hw;
  signal timer_from_hw : t_timer_from_hw;

  signal count : unsigned(15 downto 0) := (others => '0');

begin

  i_timer : entity work.timer
    generic map (
      G_BASE_ADDRESS       => x"4000_1000",
      G_CHECK_BASE_ADDRESS => true)
    port map (
      clk      => clk,
      areset_n => areset_n,
      awaddr   => awaddr,
      awvalid  => awvalid,
      awready  => awready,
      wdata    => wdata,
      wvalid   => wvalid,
      wready   => wready,
      bresp    => bresp,
      bvalid   => bvalid,
      bready   => bready,
      araddr   => araddr,
      arvalid  => arvalid,
      arready  => arready,
      rdata    => rdata,
      rresp    => rresp,
      rvalid   => rvalid,
      rready   => rready,
      to_hw    => timer_to_hw,
      from_hw  => timer_from_hw);
```

Your logic then reads `timer_to_hw` and drives `timer_from_hw`, field by field
and by name:

```vhdl
  p_count : process (clk) is
  begin
    if rising_edge(clk) then
      if timer_to_hw.ctrl.start = '1' or timer_to_hw.load.load.swmod = '1' then
        count <= unsigned(timer_to_hw.load.load.value(15 downto 0));
      elsif timer_to_hw.ctrl.enable = '1' then
        if count /= 0 then
          count <= count - 1;
        elsif timer_to_hw.ctrl.mode = PERIODIC then
          count <= unsigned(timer_to_hw.load.load.value(15 downto 0));
        end if;
      end if;
    end if;
  end process p_count;

  timer_from_hw.status.count.value <= std_logic_vector(count);
  timer_from_hw.status.count.we    <= timer_to_hw.ctrl.enable;
  timer_from_hw.status.running     <= '1' when count /= 0 else '0';
  timer_from_hw.irq.expired.set    <= '1' when count = 1 else '0';

  irq <= timer_to_hw.irq.expired;
```

Drive every member of `from_hw`. A `we`, `wel`, `set` or `clr` input you leave
undriven stays `'U'` in simulation.

## Base address

The top wrapper, the endpoint and the register file have the same two
generics:

```vhdl
entity timer is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := 32x"0";
    G_CHECK_BASE_ADDRESS : boolean := true
  );
```

`G_BASE_ADDRESS` is `addr_width` bits wide. The register file splits each
address in two. The low `C_MODULE_ADDR_WIDTH` bits select the register. With
`G_CHECK_BASE_ADDRESS` set to `true`, the bits above must equal the same bits
of `G_BASE_ADDRESS`, and any other address gets an
[error response](buses.md#errors).

The base address must be aligned to the module's window of
`2**C_MODULE_ADDR_WIDTH` addresses, so its low `C_MODULE_ADDR_WIDTH` bits must
be zero. Otherwise the register file stops the simulation with an assertion
failure. The timer has `C_MODULE_ADDR_WIDTH = 4`, a window of 16 bytes, so
`x"4000_1000"` works and puts `load` at `0x4000_1004`. Accesses to
`0x4000_1010` and to `0x0000_1004` both get an error.

With `G_CHECK_BASE_ADDRESS` set to `false`, the register file ignores
`G_BASE_ADDRESS` and the upper address bits. The module then answers at every
address whose low bits select a register, so `0x0000_1004` and `0x4000_1004`
both reach `load`. Use this when your interconnect already decodes the
module's address range and forwards only accesses meant for it.

The base address is a generic, not a key in the JSON, because it describes
where you place the module, not the module itself. You can instantiate one
register map several times at different addresses, and you can move a module
without generating it again. The C, C++ and Python headers give register
offsets for the same reason, and your software adds the base address.

## Several modules in one design

Every generated design unit is named after its module, including the local-bus
package. Each module's `<module>_localbus_pkg` is sized from that module's own
`addr_width` and `data_width`, so modules with different widths can share one
library. A timer with 32-bit addresses and data and a GPIO module with 16-bit
addresses and data can both be compiled into `periph`. Compile each module's
files in the order above. The order between the modules does not matter.

The per-register type names, such as `t_ctrl_to_hw`, carry the register name
but not the module name. If two modules both have a register called `ctrl`, a
file that uses both packages with `.all` cannot refer to `t_ctrl_to_hw`
directly. Use the module-level types, `t_timer_to_hw` and `t_gpio_to_hw`, or
a selected name:

```vhdl
signal gpio_ctrl : work.gpio_regfile_pkg.t_ctrl_to_hw;
```

## Regenerating

bust owns every file it writes, including the top wrapper `<module>.vhd`. Run
bust again after you change the register map, and all files are regenerated.
bust asks before it overwrites an existing file, and `-f` overwrites without
asking. Keep your own logic in your own files, connected through `to_hw` and
`from_hw` as above, never in the generated ones.

bust 0.14 kept user logic in the top-level file between `-- User ... Start`
and `-- User ... End` markers. bust stops with an error, before it writes
anything, if the top-level file it would replace still has those markers.
[Upgrading](upgrading.md) describes how to move that logic out.
