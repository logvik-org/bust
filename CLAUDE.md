# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Read it before making any changes.

## What bust is

`bust` is an open-source bus tool: a command-line utility that generates VHDL, C/C++/Python headers, LaTeX/PDF documentation, and UVVM-based testbenches from a simple JSON register-map description. It currently supports **AXI4-Lite** (`axi`) and **IPBus** (`ipbus`). The generated VHDL hides all register handling behind VHDL records so the rest of a design references registers by name and access mode.

Maintained by Ola Grøttvik. MIT licensed, hosted at https://github.com/grottviq/bust. Target runtimes: Python 3.9, 3.10, 3.11 (3.9 is the mypy baseline). Python 2.7 is not supported.

## Architecture

`bust` is built around a **local bus abstraction**. Every supported single-beat protocol (AXI4-Lite, IPBus, and future Wishbone/custom buses) is a thin **endpoint** wrapper around one small internal local-bus interface, so the register-map logic stays protocol-agnostic. The generated VHDL stack per module is:

```
localbus_pkg            local-bus records (t_lb_m2s / t_lb_s2m), sized from the module
<module>_regfile_pkg    storage / to_hw / from_hw record families, address-decode helpers
<module>_regfile        storage, access-mode behaviour, hardware updates, read mux, response
<module>_<bus>_endpoint protocol bridge (axi_endpoint / ipb_endpoint) over the local bus
<module>                thin, fixed top wrapper instantiating the endpoint
<module>_tb             self-checking UVVM testbench over the stock VIP (AXI-Lite / vip_ipbus)
```

The hardware side references each field by name through `to_hw`/`from_hw` records. The access-mode system (full spec below) is richer than a read-only/read-write `mode`: separate software (`sw`) and hardware (`hw`) access, software side effects (onread/onwrite/singlepulse), hardware modifiers (we/wel/hwset/hwclr/swmod/swacc), and enumerated field types that generate VHDL enums.

This was built in order: (1) design the HDL for every access-mode combination, (2) verify with UVVM testbenches, (3) implement the Python/Jinja2 generator to match the verified HDL, (4) update headers and documentation. All four are complete for AXI4-Lite and IPBus, and the legacy per-protocol "PIF" generation path has been fully removed: local-bus generation is the only path and is always on. When changing generated HDL, keep the generated testbench in lockstep.

The hand-written, simulation-verified reference HDL still lives in `hdl/prototype/` (local-bus package, `prototype` regfile, local-bus BFM, and self-checking testbenches); the design rationale is in `docs/refactor/local-bus-hdl.md`. These are reference HDL, not generator output, so they are not in the golden-file suite, but the generator is checked structurally and by simulation against them. Run with `cd sim && make sim-prototype`.

## Architecture decisions

### Local bus abstraction

A minimal single-beat transaction interface: address, write data, read data, write enable, read enable, acknowledge. It targets register-map access patterns (single-beat, non-bursting). All supported bus protocols are thin wrappers around it. Burst-capable protocols (AXI4 full, AXI Stream) are a future concern and will use native implementations, not this abstraction.

### Base address as a generic

The base address is exposed as a VHDL generic, never hardcoded:

```vhdl
generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true
);
```

When `G_CHECK_BASE_ADDRESS` is false, the instantiator handles address decoding externally. The base address does not belong in the register-map JSON; it is an instantiation-time generic.

### VHDL records and enumerated types

Generated VHDL uses records throughout (bus interfaces, hardware-side signals, register grouping). Fields with enumerated values generate proper VHDL `type` definitions, not raw `std_logic_vector` constants, enabling compile-time type checking on the hardware side.

## Access mode specification (bust 1.0)

The access mode system bust 1.0 implements. ("legacy" refers to the old `mode`-based format; legacy JSON is still accepted and translated onto `sw`/`hw`, but the legacy generation path is gone.) All keywords are conceptually aligned with SystemRDL 2.0.

**Software access (`sw`)**: `rw` (read+write), `ro` (read only), `wo` (write only), `na` (no access).

**Software side effects**:

| Keyword | Description |
|---------|-------------|
| `onread: rclr` | Field clears to 0 after software reads |
| `onread: rset` | Field sets to all 1s after software reads |
| `onwrite: woset` | Write 1 sets bits, write 0 has no effect |
| `onwrite: woclr` | Write 1 clears bits, write 0 has no effect |
| `onwrite: wot` | Write 1 toggles bits |
| `onwrite: wzs` | Write 0 sets bits |
| `onwrite: wzc` | Write 0 clears bits |
| `onwrite: wzt` | Write 0 toggles bits |
| `onwrite: wclr` | Write any value clears field |
| `onwrite: wset` | Write any value sets field |
| `singlepulse: true` | Field self-clears one clock after SW write; HW sees a single-cycle pulse |

**Hardware access (`hw`)**: `r`, `w`, `rw`, `na`.

**Hardware modifiers**:

| Keyword | Generated signal | Description |
|---------|------------------|-------------|
| `we: true` | `<field>_we` | HW write-enable; HW updates field only when asserted |
| `wel: true` | `<field>_wel` | Write-enable active low |
| `hwset: true` | `<field>_set` | Hardware can set field to all 1s |
| `hwclr: true` | `<field>_clr` | Hardware can clear field to 0 |
| `swmod: true` | `<field>_swmod` | Pulse when software modifies field |
| `swacc: true` | `<field>_swacc` | Pulse when software accesses field |

**Inheritance**: access modes set at register level act as defaults, overridable per field. Unspecified field properties inherit from the register default.

```json
{
  "name": "CTRL", "sw": "rw", "hw": "r",
  "fields": [
    { "name": "MODE",   "sw": "ro" },
    { "name": "ENABLE", "onwrite": "woset" }
  ]
}
```

`MODE` overrides `sw` to read-only. `ENABLE` inherits `sw: rw` and adds write-set behaviour.

**Enumerated values** generate VHDL enum types:

```json
{
  "name": "MODE", "width": 2, "sw": "rw", "hw": "r",
  "enums": [
    { "name": "IDLE", "value": 0 }, { "name": "SINGLE", "value": 1 },
    { "name": "BURST", "value": 2 }, { "name": "STREAM", "value": 3 }
  ]
}
```

## Explicitly deferred: do not implement

Tracked in GitHub issues for future versions. Do not implement these in the current refactor even if they seem straightforward. They are deferred deliberately, not forgotten, and each needs architectural thought first:

`precedence` (hw/sw simultaneous write arbitration), `counter` fields, `intr` (interrupt aggregation), `nonsticky` interrupt behaviour, queue/FIFO/LIFO interfaces, array registers, RAM interface generation, `addrmap` hierarchy and multi-instance address maps.

JSON schema note: design the schema to accommodate a future `addrmap` hierarchy (multiple register-map instances at different base addresses) even though bust 1.0 does not implement it. Do not hardcode the assumption of a single address space.

## Bus support

- **Current (bust 1.0)**: AXI4-Lite, IPBus.
- **Planned**: Wishbone, custom buses via Jinja2 templates. All current and future single-beat protocols use the local bus abstraction internally.

## Commands

```bash
pip install -r requirements.txt        # install deps (includes dev tools: pytest, mypy, sphinx)
pip install -e ".[dev]"                # editable install with dev extras

python -m bust example/example_axi.json -o /tmp/out   # run the generator
bust --version                               # console-script entry point

pytest                                 # run the full test suite
pytest tests/test_suite.py::Test_Suite::test_localbus_hdl   # run a single test
mypy bust                              # type-check (CI runs this; must pass)
black bust tests                       # format (excludes example/)
pre-commit run --all-files             # trailing-ws, eof, tabs, crlf, black, flake8(script/)
```

CI (`.github/workflows/python_tests.yml`) runs `mypy bust` then `pytest` across Python 3.9/3.10/3.11. Both must be green.

## Generation pipeline

`bust/__main__.py` is the orchestrator and the clearest map of the flow:

```
json_parser(file) -> Settings -> Bus -> Module(json, bus, settings)
                                          -> Header / Documentation
                                          -> generate_output(...)  (bust/generation.py)
```

`generate_output` creates the project directory tree (controlled by `Settings`) and writes every artifact: the local-bus VHDL stack and testbench, language headers, and documentation. The CLI flags (`-f/-F/-d/-p/-i/-a/-c/-e`) toggle artifacts and overwrite behaviour; local-bus generation is always on. The docopt usage string at the top of `__main__.py` is the source of truth for the interface.

## Package layout

The package uses a layered structure. **The flat top-level modules in `bust/` (e.g. `bust/bus.py`, `bust/module.py`, `bust/header.py`, `bust/utils.py`, `bust/generator_factory.py`) are backward-compatibility shims** that only re-export from the new locations. Write and import new code from the real homes below. Only touch a shim to keep its re-export list in sync.

- **`bust/core/`**: domain model, no generation logic. `Bus`, `Module`, `Register`, `Field`, and `enums` (`RegisterMode`, `RegisterType`, `SwAccess`, `HwAccess`, `OnRead`, `OnWrite`). `Module` owns the register list, address assignment (`update_addresses`), and validation. `Register`/`Field` carry the access-mode model and the per-register/field helpers the templates render from.
- **`bust/generators/`**: all code emission.
  - `factory.py` `GeneratorFactory` is the seam that decouples `core` domain objects from generator implementations. **Domain classes never import generators; everything goes through this factory.** Call its static methods (`generate_localbus_package_vhdl`, `generate_regfile_package_vhdl`, `generate_regfile_vhdl`, `generate_axi_endpoint_vhdl`, `generate_ipb_endpoint_vhdl`, `generate_module_top_vhdl`, `generate_localbus_axi_testbench_vhdl`, `generate_localbus_ipbus_testbench_vhdl`) rather than instantiating generators directly.
  - `vhdl/module_generator.py` is the (stateless) VHDL emitter for the local-bus stack and testbenches.
  - `header_generator.py` (C/C++/Python/IPBus-XML), `documentation_generator.py` (LaTeX).
- **`bust/validation/`**: `config_validator.py` (`ConfigWrapper`, JSON key validation) and `vhdl_validator.py` (`is_valid_VHDL`).
- **`bust/utils/`**: `file_utils.py` (write/overwrite helpers), `formatting.py` (`indent_string`), `json_utils.py` (`json_parser`).
- **`bust/jinja_utils/`**: `environment.py` (`get_environment` / `render_template`) and `filters.py`. All text output is rendered from Jinja2 templates.
- **`bust/templates/`**: the `.j2` templates, organized by artifact (`vhdl/module/` for the local-bus stack, `vhdl/testbench/` for the UVVM testbenches incl. the shared `localbus_tb/` body fragments, `header/`, `ipbus/`, `latex/`). **This is where the emitted text lives**, so most output changes happen here, not in Python.
- **`bust/editor.py`**: interactive curses-menu editor for creating/editing JSON configs (`-c` / `-e` flags).

## Testing model: golden files

`tests/test_suite.py` is **not** unit-style. It regenerates output from `example/example_axi.json` and `example/example_ipbus.json` and asserts byte-for-byte equality against the committed reference files under `example/example_axi/` and `example/example_ipbus/` (subdirs `hdl/`, `tb/`, `header/`, `doc/`). `tests/test_regfile_package.py` does the same for the new-format `example/example_prototype.json` (which exercises every access mode) plus structural checks against the hand-written prototype.

Consequence: **any change to a generator or template that alters output will fail the suite until you regenerate and commit the corresponding `example/.../` reference files** (for all affected examples: axi, ipbus, and prototype). Treat the example output trees as fixtures that must be updated alongside generator/template changes. The doc test pins the version string, so keep generated reference docs consistent with it. `test_doc` needs `pylatexenc` (the `utf8tolatex` filter); where it is unavailable it is skipped/expected-to-fail and runs in CI instead.

## VHDL simulation (`sim/`)

bust does **not** emit simulator-specific run scripts; choosing a simulator and flow is left to the user. The `sim/` infrastructure exists only to verify that bust itself works and that the generated example designs simulate. It runs the generated example testbenches (and the hand-written prototype testbenches) with the open-source **nvc** simulator inside Docker (UVVM + IPBus firmware + vip_ipbus pre-compiled into the image). No local VHDL toolchain needed.

```bash
cd sim && make build          # build the nvc+UVVM image (once)
make sim-axi                  # run example_axi testbench (exit 0 = PASS)
make sim-ipbus                # run example_ipbus testbench
make wave-axi                 # simulate + capture FST + open GTKWave
```

`sim/README.md` documents the library layering, the `nvc --relaxed` flag gotcha, and how to add a new testbench target (`run_sim.sh` + `sim/Makefile` + `.github/workflows/vhdl_sim.yml`). The sim CI (`vhdl_sim.yml`) triggers only on changes under `sim/**`, `example/**/*.vhd`, or `hdl/**/*.vhd`.

## Conventions

- **Versioning**: managed by `bumpversion` (config in `.bumpversion.cfg`). The version should be kept in sync between `pyproject.toml` and `bust/_version.py` (`__VERSION__`); use bumpversion to update both. Do not edit version strings by hand.
- **mypy**: configured in `pyproject.toml` with most warnings on but untyped-def enforcement off. Keep `mypy bust` clean.
- **Docstrings**: Google convention (pydocstyle), ignoring D100/D104/D107; test files are exempt.
- **black** formats everything except `example/` (generator output, not hand-written).

---

# Claude coding guidelines

## Comments

- Only comment things that are not obvious from the code itself.
- Never describe *what* the code does if reading it is enough. Comment *why* instead: intent, tradeoffs, or non-obvious constraints.
- No section headers that restate the structure (`// Initialize variables`, `// Main logic`).
- No docstrings that just echo the function name (`/// Returns the user`).
- No inline comments at the end of every line.
- A well-named function or variable is better than a comment explaining a poorly-named one.

**Bad:**

```python
# Loop through all users and check if they are active
for user in users:
    if user.active:  # Check if user is active
        send_email(user)  # Send email to the user
```

**Good:**

```python
for user in active_users:
    send_email(user)
```

## Naming

- Names should be precise and self-documenting.
- Avoid generic names: `data`, `result`, `info`, `temp`, `obj`, `handle`, `process_*`, `do_*`.
- Booleans: `is_`, `has_`, `should_`, `can_` prefixes.
- Functions: verb phrases that say what they return or do, like `fetch_user_by_id`, not `get_user_data`.

## DRY and reuse

- Before writing a utility, check whether it already exists in the codebase.
- If the same logic appears more than once, extract it.
- Prefer extending or composing existing abstractions over adding parallel ones.
- When editing a file, look at its imports and existing helpers before writing new ones.
- When working across multiple files, track what has already been defined and reference it.

## Structure and scope

- Functions should do one thing. If a function needs a comment to explain each of its phases, it should be split.
- Keep functions short enough to read without scrolling.
- Avoid deeply nested conditionals. Early returns and guard clauses first.
- Don't add parameters or return values "for future use".

## Output hygiene

- No "I've created...", "Here's the updated...", "This implementation..." preambles in code output.
- No `TODO: implement` stubs unless explicitly asked.
- No placeholder logic that silently does nothing.
- Don't add logging or error handling boilerplate unless the project already uses it or it was asked for.
- No default `try/except Exception: pass` swallowing errors silently.

## Commit messages

- One line. No body, no bullet list of changes, no "This commit..." preamble.
- 72 characters max.
- Imperative mood: `Fix`, `Add`, `Remove`, `Rename`, `Extract`, not `Fixed`, `Adding`, `This adds`.
- Say what changed and where, not why the change was needed (that belongs in code comments or a PR description if at all).
- Never pad with phrases like `as requested`, `per review`, `minor updates`, `various fixes`, `cleanup`.

**Bad:**

```
Refactor user authentication module

- Updated the login function to handle edge cases
- Fixed a bug where users could not log in with special characters
- Added better error messages for improved user experience
- This was done as part of the ongoing cleanup effort
```

**Good:**

```
Fix login failure for usernames with special characters
```

## Punctuation

- Never use em-dashes. Rewrite the sentence.
- Semicolons in code: only where the language requires them. Never use them to join two statements that should be on separate lines.
- Semicolons in prose/comments: avoid. If a sentence needs a semicolon, split it into two.

## When context about the codebase is incomplete

- Assume conventions already in use in the file are intentional. Match them.
- If you are uncertain whether a utility already exists, say so rather than duplicating.
- Prefer minimal, well-scoped changes over wholesale rewrites.
- Ask before refactoring things that weren't in scope.
