# Local bus HDL design (step 1)

*Historical design record from the local-bus refactor; kept for provenance.*

Status (at the time): design foundation for the HDL refactor. This is hand-written prototype
HDL and its verification. The Python/Jinja2 generator is **not** touched at this
stage (that is step 3, after this HDL is verified).

## Architecture

Three VHDL units per module replace today's single per-protocol PIF:

```
<bus> protocol wrapper  ->  local bus (t_lb_m2s / t_lb_s2m)  ->  <module>_regfile
```

- `<module>_regfile` owns address decode, base-address check, register storage,
  software read/write semantics, and the hardware-side record ports. It speaks
  only the local bus. One per module, reused by every protocol.
- Protocol endpoints (`<module>_axi_endpoint`, `<module>_ipb_endpoint`) own only
  the handshake and instantiate the regfile. Each endpoint is combinational glue
  that adds no register stage of its own, so the regfile's single registered
  cycle is the whole latency: the response lands exactly one clock after the
  request. AXI's five-channel handshake and IPBus's strobe logic live here and
  nowhere else.

The current AXI and IPBus PIFs already share their whole register core through
common Jinja macros (`statement_read_reg`, `statement_write_reg`,
`process_pulse`) and differ only in the handshake. The regfile is that shared
core promoted to a real entity.

## Local bus contract

```vhdl
constant C_LB_ADDR_WIDTH : natural := 32;
constant C_LB_DATA_WIDTH : natural := 32;

type t_lb_m2s is record
  address : std_logic_vector(C_LB_ADDR_WIDTH - 1 downto 0);
  wdata   : std_logic_vector(C_LB_DATA_WIDTH - 1 downto 0);
  wen     : std_logic;     -- write request
  ren     : std_logic;     -- read request
end record;
type t_lb_s2m is record
  rdata   : std_logic_vector(C_LB_DATA_WIDTH - 1 downto 0);
  ack     : std_logic;     -- transaction complete (1 cycle)
  err     : std_logic;     -- invalid address / error, mutually exclusive with ack
end record;
```

`C_LB_ADDR_WIDTH`/`C_LB_DATA_WIDTH` are fixed at 32 in the prototype; promoting
them to generics is part of the deferred generator work.

Single outstanding transaction, "hold until acknowledged":

- The master asserts exactly one of `wen` / `ren` with a valid `address` (and
  `wdata` for writes) and **holds the request stable until it observes a
  response**.
- The regfile completes the beat by pulsing exactly one of `ack` or `err` for
  one cycle. `ack` and `err` are mutually exclusive.

There is deliberately **no separate stall/wait signal**. A slow or
variable-latency target (for example a register backed by RAM) stalls the
master simply by asserting its response later; withholding `ack`/`err` *is* the
stall mechanism. This covers every protocol in scope:

- **AXI4-Lite** has no stall wire; the slave back-pressures by delaying
  `RVALID`/`BVALID`, i.e. the wrapper delays its response channel until the
  regfile answers.
- **IPBus** "stall" in the legacy PIF is implemented purely by delaying `ipb_ack`
  (`process_stall` counts wait cycles, then asserts ack). The local bus
  expresses the same thing directly.
- **Wishbone (classic)** inserts wait states by delaying `ACK`.

A dedicated stall signal only earns its place on a *pipelined / multi-outstanding*
bus that decouples request acceptance from response. That is out of scope for
this single-beat abstraction (burst-capable protocols use native
implementations), and can be added later without disturbing single-beat users.

`address`/`data` are fixed at 32 bits in the prototype. Making them
configurable is a generator-time concern, deferred with the rest of the
generator work.

### Addressing

The local bus carries a **byte address** so the regfile decode stays
protocol-agnostic: each wrapper forwards the incoming address unchanged and the
regfile slices the module window from it (low bits select the register, upper
bits check the base), exactly as the legacy AXI and IPBus PIFs did. No wrapper shifts
or rewrites the address. IPBus is the one port of fixed width: `ipb_addr` is
always 32 bits, so the generated IPBus endpoint slices it to the module's
`addr_width` (higher bits are decoded upstream) and an `addr_width` above 32 is
rejected. This is an internal-bus convention only, not a restriction on the
register map.

bust must support whatever addressing scheme the register map declares, with
**byte-addressing and word-addressing** being the two common cases, and the
map need not be contiguous: a user can leave unused address ranges between
registers (sparse maps, reserved windows, register blocks aligned to a stride).
The generator translates the declared scheme and offsets into the byte offsets
the regfile decodes, so a word-addressed map and a byte-addressed map both
reduce to byte-offset compares internally. Because decode compares the full
register offset (not a packed index), gaps between registers cost nothing and
an access to an unused offset inside the module window returns `err`.

The `prototype` demo uses byte-addressing with contiguous word-aligned
offsets (`0x00`, `0x04`, ...) as one concrete instance of that scheme; it is the
demo's choice, not a constraint of the local bus.

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

## Records and types

Registers and fields are expressed as **nested records** (`regs.<reg>.<field>`),
both for the hardware-side ports and for the regfile's internal storage. A
module with many registers stays one record signal instead of a flat list of
signals, and the hardware references each field by name with its modifiers
attached. Three record families, all nested register -> field:

- `t_<module>_regs` (internal) holds one member per field that stores state.
  The regfile keeps a single signal of this type.
- `t_<module>_<reg>_to_hw` (regfile -> hardware): `hw: r`/`rw` field values.
- `t_<module>_<reg>_from_hw` (hardware -> regfile): per-field input records that
  pair each value with its modifier strobes, so a field's enable or set/clear
  lives next to its value: `from_hw.reg4.field0.we`, `from_hw.reg4.field1.set`.

The register-definition package also carries the field documentation (name,
bit range, access modes, meaning) as comments next to each record member, so a
designer can understand a field from the package alone. Fields with enumerated
values will generate VHDL `type` definitions (deferred to a later pass).

## Access modes covered in this pass (core access)

`sw` and `hw` are independent per field. Storage exists for any field that is
software-writable or hardware-writable.

| `sw` | software write         | software read           |
| ---- | ---------------------- | ----------------------- |
| `rw` | on `wen` + address hit | drives stored value     |
| `ro` | none                   | drives stored value     |
| `wo` | on `wen` + address hit | reads 0                 |
| `na` | none                   | reads 0                 |

| `hw` | hardware port | regfile behavior                       |
| ---- | ------------- | -------------------------------------- |
| `r`  | value out     | exposes stored value                   |
| `w`  | value in      | stores hardware value (see `we`/`wel`) |
| `rw` | in + out      | stores hardware value and exposes it   |
| `na` | none          | software-only register                 |

| modifier | field record member         | effect                                          |
| -------- | --------------------------- | ----------------------------------------------- |
| `we`     | `from_hw.<reg>.<field>.we`  | hardware value is captured only while `we = 1`  |
| `wel`    | `from_hw.<reg>.<field>.wel` | same, active low: captured only while `wel = 0` |
| `hwset`  | `from_hw.<reg>.<field>.set` | a pulse forces the field to all 1s              |
| `hwclr`  | `from_hw.<reg>.<field>.clr` | a pulse forces the field to 0                   |

`we`, `wel`, `hwset` and `hwclr` are all standard SystemRDL field properties;
`wel` is named after the SystemRDL property (active-low write enable) rather
than a `_n` suffix for that reason.

### Hardware/software write precedence (provisional)

When several sources can drive the same field in one cycle, the regfile applies
a single documented order (provisional, since `precedence` is on the deferred
list). The clocked storage process expresses it as an `if`/`elsif` chain per
field, so it reads top to bottom:

| priority     | source             | applies when                       |
| ------------ | ------------------ | ---------------------------------- |
| 1 (highest)  | `hwclr`            | `from_hw.<reg>.<field>.clr = '1'`  |
| 2            | `hwset`            | `from_hw.<reg>.<field>.set = '1'`  |
| 3            | hardware `we`/`wel`| the field's write enable asserted  |
| 4 (lowest)   | software write     | a bus write hits the field         |

An `onread` side effect ranks with the software write. The generated regfile
assigns a register's onread effects before its hardware updates, so a `hwset`
in the same cycle as an `rclr` read leaves the field set instead of losing the
event.

## Software side effects (onread / onwrite)

A field may transform itself on a software access instead of just storing the
bus data. These live in the same single storage process that owns the field, so
there is still one driver of `regs`.

`onread` effects act when a software read is serviced. The read returns the
value *before* the effect; storage updates on the same clock edge. The read-side
effect reuses the read mux's "first cycle of the transaction" guard (response
not yet asserted), so it fires exactly once per read.

| `onread` | effect after the read |
| -------- | --------------------- |
| `rclr`   | field clears to 0     |
| `rset`   | field sets to all 1s  |

`onwrite` effects replace the plain store on a software write, combining the
stored value `f` with the write data `w`:

| `onwrite` | new value     | meaning                    |
| --------- | ------------- | -------------------------- |
| `woset`   | `f or w`      | write 1 sets bits          |
| `woclr`   | `f and not w` | write 1 clears bits        |
| `wot`     | `f xor w`     | write 1 toggles bits       |
| `wzs`     | `f or not w`  | write 0 sets bits          |
| `wzc`     | `f and w`     | write 0 clears bits        |
| `wzt`     | `f xor not w` | write 0 toggles bits       |
| `wclr`    | all 0s        | any write clears the field |
| `wset`    | all 1s        | any write sets the field   |

A clear-type field (`woclr`/`wzc`/`wclr`) cannot be set by software, so in the
demo those fields reset to all 1s to make the clearing observable.

## Software-access pulses and singlepulse

These surface software activity to hardware as single-cycle strobes:

| keyword       | to-hw signal                | pulses when                           |
| ------------- | --------------------------- | ------------------------------------- |
| `swmod`       | `to_hw.<reg>.<field>.swmod` | software modifies the field (a write) |
| `swacc`       | `to_hw.<reg>.<field>.swacc` | software reads or writes the field    |
| `singlepulse` | `to_hw.<reg>.<field>` value | the value itself, one cycle after a write, then back at its reset value |

`swmod`/`swacc` ride alongside the field value in the hardware-side record, so a
field with a pulse becomes a small record (`value` + strobe), just as a
hardware-input field pairs its value with `we`/`wel`. A `singlepulse` field
needs no extra strobe: its storage returns to its reset value every cycle, so a
software write surfaces as a one-cycle pulse on the value and then the field is
back at its reset value.

## Enumerated values

A field with enumerated values generates a VHDL enumeration type rather than raw
`std_logic_vector` constants, so hardware- and software-side assignments are
checked against the named states at compile time. The regfile stores the field
as the enum type and converts to/from bits only at the bus boundary (the read
mux and the software-write path).

| keyword | generated type             | encoding                              |
| ------- | -------------------------- | ------------------------------------- |
| `enums` | `t_<module>_<reg>_<field>` | literal position is the encoded value |

The prototype's `reg11.field0` is a 2-bit enum `(STATE0, STATE1, STATE2,
STATE3)` whose positions are the encoded values 0..3.

## Reset

The regfile takes one native synchronous reset whose polarity is selected by a
generic, since some FPGA families prefer active-low resets:

```vhdl
G_RESET_ACTIVE_LOW : boolean := false
```

The reset is normalized to active-high internally so the rest of the logic is
polarity-agnostic. Each protocol wrapper adapts its own reset (AXI async
active-low, IPBus sync active-high) to it, removing the reset-convention
divergence between the two current PIFs.

## Read of non-readable fields

Reading a mapped register whose addressed fields are all software-unreadable
(`sw: wo`/`na`) returns 0 with a normal `ack`. `err` is reserved for
address-decode failures (unmapped offset, wrong base). This matches SystemRDL
(a read of a `wo` field yields 0), the common AXI-Lite / IPBus behavior, and the
legacy bus PIFs, and keeps generic driver patterns (read-back, read-modify-write)
working. A stricter "error on read of non-readable" mode is not part of bust 1.0.

## Verification (step 2)

The regfile is verified directly over the local bus with a UVVM bus functional
model (`hdl/prototype/localbus_bfm_pkg.vhd`): a config record, scope and
`msg_id_panel` per call, `check_value`-based response checking, and a bounded
wait for `ack`/`err`. The testbench
(`hdl/prototype/tb/prototype_regfile_tb.vhd`) drives the BFM and covers software
read/write per access mode, `we`/`wel` capture and gating, the `hwclr > hwset`
precedence, hardware `we` overriding a software write, `wo` reading back 0, the
onread (rclr/rset) and onwrite (woset/woclr/wot/wzs/wzc/wzt/wclr/wset) side
effects, the `swmod`/`swacc`/`singlepulse` single-cycle pulses (counted by a
monitor so their width is checked), the enumerated `reg11.field0` round-tripping
through its named type, and `err` on both unmapped-offset and wrong-base-address
transactions for reads and writes. It runs on `nvc` against the project's pre-compiled UVVM.

## Protocol endpoints

Each `<bus>` endpoint owns only the handshake and instantiates the regfile,
serializing one transaction at a time onto the single-outstanding local bus and
adapting its own reset to the regfile's polarity generic.

The endpoints add **no register stage of their own**: the request is forwarded
combinationally onto the local bus and the regfile's response (`ack`/`err`/
`rdata`) is forwarded combinationally back. The regfile registers its response
(and contains a one-cycle guard that acks a held request exactly once), so that
single registered cycle is the whole latency: the bus response lands exactly one
clock after the request. Transaction separation comes from that regfile guard,
not from the request/select line going low, so the sub-cycle inter-transaction
gap never has to be sampled.

The AXI4-Lite endpoint prototype (`hdl/prototype/prototype_axi_endpoint.vhd`)
accepts AW+W (or AR) and drives `wen`/`ren` with the full byte address in the
same cycle, and presents `BVALID`/`RVALID` combinationally on the cycle the
regfile acks, so the response is one clock after the address handshake
(`err` -> `SLVERR`, `ack` -> `OKAY`). AXI is the one protocol whose response
channels must stay valid until the master accepts them, so the response is
latched into a hold register only when `BREADY`/`RREADY` is low on the ack
cycle: that register is for back-pressure, not added latency. AXI's async
active-low reset is passed to the regfile via `G_RESET_ACTIVE_LOW`. It is
verified with the stock Bitvis AXI-Lite VIP
(`hdl/prototype/tb/prototype_axi_endpoint_tb.vhd`, `make sim-prototype-axi`).

The IPBus endpoint prototype (`hdl/prototype/prototype_ipb_endpoint.vhd`) is the
thinnest, since IPBus is itself a single-beat hold-until-ack protocol: a strobe
drives one local-bus transaction (`wen`/`ren`) and the regfile's response is
forwarded straight back as `ipb_ack`/`ipb_err`, one clock after the strobe. The
address is forwarded unchanged and the regfile slices the module window from it
(as every endpoint and the legacy PIFs do), and its sync active-high reset passes
straight through. It is verified with the stock `vip_ipbus` VIP
(`hdl/prototype/tb/prototype_ipb_endpoint_tb.vhd`, `make sim-prototype-ipbus`).

The SBI endpoint prototype (`hdl/prototype/prototype_sbi_endpoint.vhd`) bridges
the Simple Bus Interface: the master raises `cs` with `wena`/`rena` and holds
until the slave asserts `ready`. The request drives one local-bus transaction and
`ready` is the regfile's response forwarded combinationally (a one-cycle beat).
SBI has no error line, so `ack` and `err` both surface as a single `ready` beat,
matching the regfile reserving `err` for address-decode failures; on a decode
error `rdata` is forced to 0. SBI carries no reset, so a sync active-high reset
passes straight through, and the master drives a byte address directly onto the
local bus. It is verified with the stock Bitvis SBI VIP
(`hdl/prototype/tb/prototype_sbi_endpoint_tb.vhd`, `make sim-prototype-sbi`).

The Avalon-MM endpoint prototype (`hdl/prototype/prototype_avalon_endpoint.vhd`)
is the dual of the SBI one: Avalon-MM stalls with `waitrequest`, so
`waitrequest` is just `not (ack or err)` (high = "not ready", the accept beat is
a single-cycle `waitrequest` low with `readdata` valid), for a
waitrequest-controlled read without `readdatavalid`. With no command asserted,
`ack`/`err` are low so `waitrequest` defaults high. The endpoint does not
implement the optional Avalon-MM `response` signal, so decode errors complete as
a normal beat with `readdata` 0 (as on SBI). Its sync active-high reset passes
straight through and the master drives a byte address. It is verified with the
stock Bitvis Avalon-MM VIP
(`hdl/prototype/tb/prototype_avalon_endpoint_tb.vhd`, `make sim-prototype-avalon`).

The Wishbone endpoint prototype (`hdl/prototype/prototype_wishbone_endpoint.vhd`)
bridges a Wishbone B4 classic cycle: a qualified cycle (`cyc_i` and `stb_i`)
drives one local-bus transaction (`we_i` selects write vs read) and `ack_o` or
`err_o` is the regfile's response forwarded combinationally, one clock later,
with `dat_o` valid. Structurally it mirrors the IPBus endpoint. Wishbone has a
native `err_o`, so a regfile decode error maps to `err_o` (rather than folding
into the response as on SBI), with `dat_o` forced to 0. UVVM ships no Wishbone
VIP, so it is verified with a small hand-written classic-cycle master BFM in the
testbench
(`hdl/prototype/tb/prototype_wishbone_endpoint_tb.vhd`, `make sim-prototype-wishbone`).

The APB endpoint prototype (`hdl/prototype/prototype_apb_endpoint.vhd`) bridges
the AMBA APB two-phase protocol: a SETUP cycle (`psel` high, `penable` low) is
followed by ACCESS cycles (`psel` and `penable` high) until the slave raises
`pready`. Because APB holds `psel` across the whole transfer, the endpoint drives
the local-bus request from the SETUP cycle and holds it (a `busy` flag) until the
regfile answers, so the regfile's single registered cycle surfaces as `pready` in
the **first** ACCESS cycle: a zero-wait-state transfer (the APB two-cycle
minimum). The `busy` flag keeps the request asserted for exactly one transaction
(the regfile's response guard blocks a re-service in the ack cycle) and clears on
ack, and the response (`pready`/`prdata`/`pslverr`) is forwarded combinationally.
A variable-latency register simply stretches the ACCESS phase with wait states.
APB has a native `pslverr`, so a decode error maps to `pslverr` (with `prdata`
forced to 0). APB's reset (`presetn`) is active-low, handed to the regfile via
`G_RESET_ACTIVE_LOW`. UVVM ships no APB VIP, so it is verified with a hand-written
APB master BFM in the testbench
(`hdl/prototype/tb/prototype_apb_endpoint_tb.vhd`, `make sim-prototype-apb`).

## Prototype demo module

`prototype` exercises the core-access matrix, the onread/onwrite software side
effects, the swmod/swacc/singlepulse pulses, and an enumerated-value field. It
uses deliberately generic register/field names (`reg0..reg11`, `field0..`) so
the structure and naming scheme can be reviewed without semantic distraction:

| Register | Offset | Field  | Bits  | `sw` | `hw` | modifiers       |
| -------- | ------ | ------ | ----- | ---- | ---- | --------------- |
| reg0     | 0x00   | field0 | 0     | rw   | r    |                 |
| reg0     | 0x00   | field1 | 2..1  | rw   | r    |                 |
| reg1     | 0x04   | field0 | 3..0  | ro   | w    | we              |
| reg1     | 0x04   | field1 | 4     | ro   | w    | (continuous)    |
| reg1     | 0x04   | field2 | 5     | ro   | w    | wel             |
| reg2     | 0x08   | field0 | 0     | wo   | r    |                 |
| reg3     | 0x0C   | field0 | 7..0  | rw   | na   |                 |
| reg4     | 0x10   | field0 | 3..0  | rw   | rw   | we              |
| reg4     | 0x10   | field1 | 8     | rw   | r    | hwset, hwclr    |
| reg5     | 0x14   | field0 | 3..0  | rw   | r    | onread rclr     |
| reg5     | 0x14   | field1 | 7..4  | rw   | r    | onread rset     |
| reg6     | 0x18   | field0 | 3..0  | rw   | r    | onwrite woset   |
| reg6     | 0x18   | field1 | 7..4  | rw   | r    | onwrite woclr   |
| reg6     | 0x18   | field2 | 11..8 | rw   | r    | onwrite wot     |
| reg7     | 0x1C   | field0 | 3..0  | rw   | r    | onwrite wzs     |
| reg7     | 0x1C   | field1 | 7..4  | rw   | r    | onwrite wzc     |
| reg7     | 0x1C   | field2 | 11..8 | rw   | r    | onwrite wzt     |
| reg8     | 0x20   | field0 | 3..0  | rw   | r    | onwrite wclr    |
| reg8     | 0x20   | field1 | 7..4  | rw   | r    | onwrite wset    |
| reg9     | 0x24   | field0 | 3..0  | rw   | r    | swmod           |
| reg9     | 0x24   | field1 | 7..4  | rw   | r    | swacc           |
| reg10    | 0x28   | field0 | 3..0  | rw   | r    | singlepulse     |
| reg11    | 0x2C   | field0 | 1..0  | rw   | r    | enum STATE0..STATE3 |

With this the prototype covers the full bust 1.0 access-mode spec: software access and
side effects, hardware access and modifiers, the software-access pulses, and
enum types. The next step is the generator work (step 3), emitting this HDL from
the register-map JSON.

## Deferred (unchanged)

Everything on the project do-not-implement list (precedence arbitration,
counters, interrupts, nonsticky interrupt behaviour, queue/FIFO/LIFO interfaces,
array registers, RAM interface generation, addrmap hierarchy). The local bus and
record shapes above are intended to absorb these later without re-cutting the
seam.
