# Step 3 scope: generator for the local-bus HDL

Status: scoping. Step 1 (prototype HDL) and step 2 (UVVM verification) are merged
on `refactor/local-bus`. This document scopes the work to make the Python/Jinja2
generator emit that verified architecture. No generator code is changed yet.

## Goal

Replace the current per-protocol PIF emission with the verified local-bus
architecture, for the bust 1.0 buses (AXI4-Lite, IPBus), keeping `mypy bust` clean and
the golden-file suite green against regenerated reference output.

## Current vs target

### Emitted file set

| Today (per-protocol PIF) | Target (local bus) |
| --- | --- |
| `<mod>.vhd` (top entity) | `<mod>.vhd` (top entity, instantiates endpoint) |
| `<mod>_<bus>_pif.vhd` (decode + storage + handshake fused) | `<mod>_regfile.vhd` (protocol-agnostic) + `<mod>_<bus>_endpoint.vhd` (handshake only) |
| `<mod>_pif_pkg.vhd` (records) | `<mod>_regfile_pkg.vhd` (records + enum types) |
| `axi_pkg.vhd` (AXI only) | `localbus_pkg.vhd` (shared, emitted once) + any per-bus pkg |

The hand-written prototype files in `hdl/prototype/` are the reference for each of
these. `localbus_pkg.vhd` is module-independent; see "Resolved decisions" for how
it is emitted in multi-module designs.

### Access-mode model: the main gap

The current domain model is far behind the bust 1.0 spec in CLAUDE.md.

| Concept | Today | 1.0 target |
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

   **Template architecture.** One template per emitted file is the spine
   (`module.j2`, `module_regfile.vhd.j2`, `regfile_pkg.j2`, one endpoint template
   per bus, `localbus_pkg.j2`). A shared macro library under
   `templates/vhdl/macros/` holds only the fragments that genuinely repeat: the
   per-access-mode emission (`read_field`, `write_field`, `onread_clear`,
   `singlepulse`, `enum_convert`, ...). The boundary is deliberate: macros emit
   protocol-agnostic access-mode logic, defined once and used by the regfile;
   per-file templates own structure and protocol (entity/port/architecture
   skeletons). This keeps the regfile bus-agnostic and makes a new bus "add one
   endpoint template," never "touch the access-mode macros." This mirrors today's
   convention (`pif.j2` includes `axi.j2`/`ipbus.j2`, which import the
   `statement_*`/`process_*` macros), just disciplined around the access-mode
   matrix where copy-paste would otherwise explode across protocols. Avoid both a
   single-file monolith and a sprawl of tiny includes.

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
   - Keep `example/example_axi.json` and `example/example_ipbus.json` as the simple
     examples (they also exercise the legacy-schema translation path) and add a new
     comprehensive example per bus mirroring the prototype demo module
     (reg0..reg11), per resolved decision 3.
   - Regenerate the full `example/example_{axi,ipbus}/` trees and the new
     comprehensive trees, and commit as the new golden reference. The doc test pins
     `0.14.0-dev` (bump deliberately if needed).
   - The sim CI (`vhdl_sim.yml`) runs the regenerated `example/**/*.vhd`, so the
     generated HDL is simulated end-to-end, not just diffed.

## Resolved decisions

1. **Legacy schema: translate old -> new.** Keep `mode: rw/ro/pulse` (and
   `stall_cycles`, `pulse_cycles`) accepted by mapping them onto the new sw/hw
   model internally, so existing user JSON keeps working. The model carries the
   new access-mode representation; a compatibility layer normalizes legacy input
   before the model is built. Validation must cover both input shapes.

2. **Bus scope: AXI4-Lite + IPBus only.** Matches CLAUDE.md bust 1.0. The other four
   endpoints (SBI/Avalon/Wishbone/APB) stay as verified reference HDL for a later
   pass; the model/regfile work is bus-agnostic so adding them later is template +
   testbench work only.

3. **Examples: keep the simple examples and add a comprehensive one.** Retain the
   current `example_{axi,ipbus}.json` (which also exercise the legacy-schema
   translation path) and add a new full-coverage example per bus mirroring the
   prototype demo module (reg0..reg11). All trees are regenerated as goldens.

4. **Template architecture: one template per file + a shared access-mode macro
   library.** Per-file templates own structure and protocol; a single
   `templates/vhdl/macros/` library owns the per-access-mode logic, used by the
   regfile and reused across buses. Not a monolith, not a sprawl of tiny includes.
   See workstream 2 for the macro boundary.

5. **`localbus_pkg.vhd`: emit once into a shared location.** The package is
   module-independent and identical across modules, so it is not emitted per
   module (N identical copies in `work` would collide). It is emitted once into a
   shared output location and compiled into its own VHDL library (not `work`);
   modules reference it via that library. This requires the output-tree layout
   (and `generate_output` / `Settings`) to gain a shared/common area rather than
   being strictly one-directory-per-module.

6. **Byte/word addressing: exact match, minus the module offset.** The generated
   VHDL does not know or care whether a map is byte- or word-addressable. Register
   addresses in the package are the literal values to match; the incoming address
   must equal them exactly, with no shifting or unit conversion. The only
   adjustment is subtracting the module base/offset address before the compare.
   `byte_addressable` therefore stays a generation-time concern (how the package
   constants are computed), not something the emitted HDL reasons about.

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

1. Model + schema + validation + unit tests (no template changes yet).
2. Regfile pkg + regfile templates; diff generated output against the prototype
   `prototype_regfile*.vhd` for a matching input.
3. Endpoint + top-level templates; same prototype diff for AXI and IPBus.
4. Downstream artifacts (TB, headers, docs).
5. Extend examples, regenerate goldens, green the suite + sim CI.
