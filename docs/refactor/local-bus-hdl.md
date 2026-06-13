# Local bus HDL design (step 1)

Status: approved design foundation for the HDL refactor. This is hand-written
prototype HDL and its verification. The Python/Jinja2 generator is **not**
touched at this stage (that is step 3, after this HDL is verified).

## Architecture

Three VHDL units per module replace today's single per-protocol PIF:

```
<bus> protocol wrapper  ->  local bus (t_lb_m2s / t_lb_s2m)  ->  <module>_regfile
```

- `<module>_regfile` owns address decode, base-address check, register storage,
  software read/write semantics, and the hardware-side record ports. It speaks
  only the local bus. One per module, reused by every protocol.
- Protocol wrappers (`<module>_axi_pif`, `<module>_ipb_pif`) own only the
  handshake and instantiate the regfile. AXI's five-channel FSM and IPBus's
  strobe/stall logic live here and nowhere else.

The current AXI and IPBus PIFs already share their whole register core through
common Jinja macros (`statement_read_reg`, `statement_write_reg`,
`process_pulse`) and differ only in the handshake. The regfile is that shared
core promoted to a real entity.

## Local bus contract

```vhdl
type t_lb_m2s is record
  address : std_logic_vector(C_ADDR_WIDTH-1 downto 0);
  wdata   : std_logic_vector(C_DATA_WIDTH-1 downto 0);
  wen     : std_logic;     -- single-cycle write request
  ren     : std_logic;     -- single-cycle read request
end record;
type t_lb_s2m is record
  rdata   : std_logic_vector(C_DATA_WIDTH-1 downto 0);
  ack     : std_logic;     -- transaction complete (1 cycle)
  err     : std_logic;     -- invalid address / error, mutually exclusive with ack
  waitreq : std_logic;     -- regfile not ready (stall); wrapper holds the beat
end record;
```

`wait` is a VHDL reserved word, hence `waitreq`. `C_ADDR_WIDTH`/`C_DATA_WIDTH`
above are the parameterizable target form; the prototype in
`hdl/local_bus/localbus_pkg.vhd` fixes both at 32. Making them configurable is a
generator-time concern, deferred with the rest of the generator work.

Timing: the wrapper asserts `wen` or `ren` for one cycle with `address` (and
`wdata` for writes). When `waitreq = '0'` the regfile answers with exactly one
of `ack` or `err` on the following cycle. AXI maps `err` to `rresp`/`bresp` and
absorbs `waitreq` into its response channels; IPBus maps `err` to `ipb_err` and
`waitreq` to its stall extension. `waitreq` is what keeps the IPBus stall
feature expressible without leaking it into the AXI wrapper.

## Base address

Lives on the regfile as generics, never in the register-map JSON:

```vhdl
generic (
  G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
  G_CHECK_BASE_ADDRESS : boolean := true
);
```

With `G_CHECK_BASE_ADDRESS = false` the upper-bit compare is dropped and the
instantiator handles decode externally. Wrappers pass both generics through.

## Access modes covered in this pass (core access)

`sw` and `hw` are independent per field. Storage exists for any field that is
software-writable or hardware-writable.

| `sw` | software write | software read (drives `rdata`) |
|------|----------------|--------------------------------|
| `rw` | on `wen` + address hit | yes |
| `ro` | none | yes |
| `wo` | on `wen` + address hit | drives 0 |
| `na` | none | drives 0 |

| `hw` | hardware port | regfile behavior |
|------|---------------|------------------|
| `r`  | value out | exposes stored value |
| `w`  | value in | stores hardware value (see `we`/`wel`) |
| `rw` | both | stores hardware value and exposes it |
| `na` | none | software-only register |

| Modifier | Signal | Effect |
|----------|--------|--------|
| `we`    | `<field>_we`  | hardware write taken only when `we = '1'` |
| `wel`   | `<field>_wel` | same, active low |
| `hwset` | `<field>_set` | force field to all 1s |
| `hwclr` | `<field>_clr` | force field to 0 |

### Hardware/software write precedence (provisional)

`precedence` is on the deferred list, so this pass fixes a single documented
order and applies it uniformly: `hwclr` > `hwset` > hardware `we`/`wel` write >
software write. In the clocked process this is achieved by ordering the
assignments so the highest-priority one is written last.

## Hardware-side records

Grouped per register and split by direction so wrappers stay trivial:

- `t_<module>_<reg>_to_hw` (regfile -> hardware): `hw: r`/`rw` field values.
- `t_<module>_<reg>_from_hw` (hardware -> regfile): `hw: w`/`rw` values plus the
  `_we`/`_wel`/`_set`/`_clr` strobes.

## Reset

The regfile takes one native synchronous reset with documented polarity
(active-high in the prototype). Each protocol wrapper adapts its own reset (AXI
async active-low, IPBus sync active-high) to it, removing the reset-convention
divergence that exists between the two current PIFs.

## Verification (step 2)

The regfile is verified directly over the local bus with a small local-bus BFM,
independent of UVVM AXI/IPBus VIP. The prototype testbench
(`hdl/local_bus/tb/regs_demo_regfile_tb.vhd`) is self-checking plain VHDL-2008
so it runs on bare `nvc` without the UVVM image. Protocol wrappers, once added,
get a thin handshake-conformance test on top.

## Prototype demo module

`regs_demo` exercises the full core-access matrix:

| Register | Offset | Field | Bits | sw | hw | modifiers |
|----------|--------|-------|------|----|----|-----------|
| CTRL    | 0x00 | ENABLE | 0     | rw | r  | |
| CTRL    | 0x00 | MODE   | 2..1  | rw | r  | |
| STATUS  | 0x04 | STATE  | 3..0  | ro | w  | we |
| STATUS  | 0x04 | FLAG   | 4     | ro | w  | (continuous) |
| STATUS  | 0x04 | ALARM  | 5     | ro | w  | wel |
| CMD     | 0x08 | TRIGGER| 0     | wo | r  | |
| SCRATCH | 0x0C | VAL    | 7..0  | rw | na | |
| HWCTRL  | 0x10 | LEVEL  | 3..0  | rw | rw | we |
| HWCTRL  | 0x10 | GATE   | 8     | rw | r  | hwset, hwclr |

## Deferred (unchanged)

`onread`/`onwrite` effects, `swmod`/`swacc`, enum types, per-field
`singlepulse`, and everything already on the project do-not-implement list. The
local bus and record shapes above are intended to absorb these later without
re-cutting the seam.
