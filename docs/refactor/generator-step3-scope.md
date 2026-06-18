# Step 3 scope: generator for the local-bus HDL

Status: scoping. Step 1 (prototype HDL) and step 2 (UVVM verification) are merged
on `refactor/local-bus`. This document scopes the work to make the Python/Jinja2
generator emit that verified architecture. No generator code is changed yet.

## Goal

Replace the current per-protocol PIF emission with the verified local-bus
architecture, for the v1 buses (AXI4-Lite, IPBus), keeping `mypy bust` clean and
the golden-file suite green against regenerated reference output.

## Current vs target

### Emitted file set

| Today (per-protocol PIF) | Target (local bus) |
| --- | --- |
| `<mod>.vhd` (top entity) | `<mod>.vhd` (top entity, instantiates endpoint) |
| `<mod>_<bus>_pif.vhd` (decode + storage + handshake fused) | `<mod>_regfile.vhd` (protocol-agnostic) + `<mod>_<bus>_endpoint.vhd` (handshake only) |
| `<mod>_pif_pkg.vhd` (records) | `<mod>_regfile_pkg.vhd` (records + enum types) |
| `axi_pkg.vhd` (AXI only) | `localbus_pkg.vhd` (shared) + any per-bus pkg |

The hand-written prototype files in `hdl/prototype/` are the reference for each of
these. `localbus_pkg.vhd` is module-independent and can be emitted verbatim (or
shipped as a static library file).

### Access-mode model: the main gap

The current domain model is far behind the v1 spec in CLAUDE.md.

| Concept | Today | v1 target |
| --- | --- | --- |
| Register mode | `RegisterMode` = `rw/ro/pulse` | per-field `sw` (`rw/ro/wo/na`) and `hw` (`r/w/rw/na`) with register-level defaults + field override |
| Field access | none (name/type/width/reset only) | full sw/hw access + modifiers |
| Software side effects | none | `onread` (rclr/rset), `onwrite` (woset/woclr/wot/wzs/wzc/wzt/wclr/wset) |
| HW modifiers | none | `we`, `wel`, `hwset`, `hwclr`, `swmod`, `swacc` |
| Pulse | `mode: pulse` + `pulse_cycles` (register-level, N-cycle) | `singlepulse` (field-level, 1-cycle, self-clearing) |
| Enumerated fields | none | `enums` -> generated VHDL enum type |
| IPBus stall | `stall_cycles` (register-level) | expressed via delayed `ack` on the local bus |

The prototype demo module (`reg0..reg11` in `local-bus-hdl.md`) is the concrete
reference for every one of these.

## Workstreams (rough dependency order)

1. **JSON schema + domain model** (largest, blocks everything)
   - Extend `Field` with `sw`, `hw`, `onread`, `onwrite`, `singlepulse`, `we`,
     `wel`, `hwset`, `hwclr`, `swmod`, `swacc`, `enums`.
   - Add register-level defaults with field-level inheritance/override.
   - New enums in `bust/core/enums.py` (SwAccess, HwAccess, OnRead, OnWrite, ...);
     keep `from_string` validation style.
   - Validation: legal sw/hw/effect combinations, enum value/width consistency,
     reset constraints (e.g. clear-type fields), modifier compatibility.
   - Compatibility layer translating legacy `mode: rw/ro/pulse` + `stall_cycles` +
     `pulse_cycles` onto the new sw/hw model (decided: translate, not hard-cut).

2. **Regfile generator + package** (`generators/vhdl/`, `templates/vhdl/`)
   - New `module_regfile.vhd.j2` emitting the two-process storage/read structure,
     the precedence chain, onread/onwrite, pulses, enum convert at the bus boundary.
   - New `regfile_pkg.j2`: nested `t_<mod>_regs`, `t_<mod>_<reg>_to_hw`,
     `t_<mod>_<reg>_from_hw`, enum `type` defs, reset constants.
   - Macro reuse: today's `statement_read_reg`, `statement_write_reg`,
     `process_pulse` macros are the seam to generalize; the prototype regfile shows
     the target per-access-mode emission.

3. **Endpoint generators** (`templates/vhdl/.../endpoint/`)
   - AXI4-Lite and IPBus endpoints from the verified combinational prototypes.
   - Top-level `<mod>.vhd` instantiates the chosen endpoint; `G_BASE_ADDRESS` /
     `G_CHECK_BASE_ADDRESS` generics pass through (today's `g_<bus>_baseaddr` /
     `g_check_baseaddr` already exist and map cleanly).

4. **Downstream artifacts** (depend on the model, not the HDL)
   - Testbench generator: UVVM sequencer + local-bus BFM usage; component list /
     TCL script updated for the new file set.
   - Headers (C/C++/Python/IPBus-XML): mostly address/field metadata; enums and
     wo/na read-back semantics may affect field exposure.
   - LaTeX docs: new access-mode columns (sw/hw/effects), enum tables.

5. **Golden fixtures + tests**
   - Extend `example/example_axi.json` and `example/example_ipbus.json` to exercise
     the v1 access modes (mirror the prototype demo module).
   - Regenerate the full `example/example_{axi,ipbus}/` trees and commit as the new
     golden reference. The doc test pins `0.14.0-dev` (bump deliberately if needed).
   - The sim CI (`vhdl_sim.yml`) runs the regenerated `example/**/*.vhd`, so the
     generated HDL is simulated end-to-end, not just diffed.

## Resolved decisions

1. **Legacy schema: translate old -> new.** Keep `mode: rw/ro/pulse` (and
   `stall_cycles`, `pulse_cycles`) accepted by mapping them onto the new sw/hw
   model internally, so existing user JSON keeps working. The model carries the
   new access-mode representation; a compatibility layer normalizes legacy input
   before the model is built. Validation must cover both input shapes.

2. **Bus scope: AXI4-Lite + IPBus only.** Matches CLAUDE.md v1. The other four
   endpoints (SBI/Avalon/Wishbone/APB) stay as verified reference HDL for a later
   pass; the model/regfile work is bus-agnostic so adding them later is template +
   testbench work only.

3. **Examples: keep the simple examples and add a comprehensive one.** Retain the
   current `example_{axi,ipbus}.json` (which also exercise the legacy-schema
   translation path) and add a new full-coverage example per bus mirroring the
   prototype demo module (reg0..reg11). All trees are regenerated as goldens.

## Open questions (non-blocking, recommendation given)

1. **Byte/word address translation (deferred in step 1).** Today `Module` carries
   `byte_addressable` (True for AXI, False for IPBus) and assigns integer addresses
   in byte or word units; the prototype regfile decodes byte offsets against
   `C_MODULE_ADDR_WIDTH`. Recommendation: the generator emits byte offsets into the
   regfile and the endpoint forwards the raw address (matches the prototype and the
   v1 PIFs), so word-addressed maps reduce to byte offsets at generation time.

2. **`localbus_pkg.vhd`: emit vs ship static.** It is module-independent.
   Recommendation: emit it verbatim into the module output tree so generated
   projects stay self-contained, sourced from a single canonical template.

## Risks / notes

- The golden-file suite is byte-exact; every template/model change churns the
  `example/.../` trees. Land the model first, then regenerate once per stable
  template state to avoid repeated fixture churn.
- `mypy bust` must stay clean; the new enums and inheritance logic are the main
  typing surface.
- HDL must stay in lockstep with its testbench (CLAUDE.md): generated TB updates
  ride with every generated-HDL change.
- Do not regress the verified handshake: generated endpoints must match the
  combinational prototypes (1-cycle response), so a generated-vs-prototype diff is
  a useful guard during development.

## Suggested sequencing

1. Resolve the open questions above (especially 1-3).
2. Model + schema + validation + unit tests (no template changes yet).
3. Regfile pkg + regfile templates; diff generated output against the prototype
   `prototype_regfile*.vhd` for a matching input.
4. Endpoint + top-level templates; same prototype diff for AXI and IPBus.
5. Downstream artifacts (TB, headers, docs).
6. Extend examples, regenerate goldens, green the suite + sim CI.
