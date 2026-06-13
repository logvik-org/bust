# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Read it before making any changes.

## What bust is

`bust` is an open-source bus tool: a command-line utility that generates VHDL, C/C++/Python headers, LaTeX/PDF documentation, and UVVM-based testbenches from a simple JSON register-map description. It currently supports **AXI4-Lite** (`axi`) and **IPBus** (`ipbus`). The generated VHDL hides all register handling behind VHDL records so the rest of a design references registers by name and access mode.

Maintained by Ola Grøttvik. MIT licensed, hosted at https://github.com/grottviq/bust. Target runtimes: Python 3.9, 3.10, 3.11 (3.9 is the mypy baseline). Python 2.7 is not supported.

## Status: major refactor in progress

**The codebase is undergoing a significant architectural refactor. Do not treat the existing code as the target architecture.** Many parts of the current implementation will be replaced. When in doubt, ask before assuming the existing approach should be preserved. The sections below labeled "current implementation" describe what exists today; the sections labeled "target" describe where it is going.

### What is being refactored and why

1. **HDL architecture**: a local bus abstraction is being introduced. All single-beat transaction protocols (AXI4-Lite, IPBus, Wishbone, custom buses) will be implemented as wrappers around a simple internal local bus interface. This keeps the register-map logic protocol-agnostic and makes adding new bus protocols much easier.
2. **Access mode system**: a richer access mode system aligned with SystemRDL 2.0 concepts (see the spec below). The current per-protocol HDL does not support this.
3. **Python and Jinja2 generator**: updated to reflect the new HDL architecture and access mode system. This work comes **after** the HDL is designed and verified. Do not modify the generator ahead of the HDL work.

### Order of operations (do not skip ahead)

1. Design the HDL for all access mode combinations.
2. Verify with UVVM testbenches.
3. Update the Python/Jinja2 generator to match the verified HDL.
4. Update documentation.

The testbench is generated alongside the HDL and must be updated in lockstep with any HDL change. Do not modify HDL without a corresponding testbench update.

## Target architecture decisions

### Local bus abstraction

A minimal single-beat transaction interface: address, write data, read data, write enable, read enable, acknowledge. It targets register-map access patterns (single-beat, non-bursting). All supported bus protocols become thin wrappers around it. Burst-capable protocols (AXI4 full, AXI Stream) are a future concern and will use native implementations, not this abstraction.

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

## Access mode specification (v1)

The access mode system bust v1 will support. Implement exactly this, no more, no less. All keywords are conceptually aligned with SystemRDL 2.0.

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

JSON schema note: design the schema to accommodate a future `addrmap` hierarchy (multiple register-map instances at different base addresses) even though v1 does not implement it. Do not hardcode the assumption of a single address space.

## Bus support

- **Current (v1)**: AXI4-Lite, IPBus.
- **Planned**: Wishbone, custom buses via Jinja2 templates. All current and future single-beat protocols use the local bus abstraction internally.

## Commands

```bash
pip install -r requirements.txt        # install deps (includes dev tools: pytest, mypy, sphinx)
pip install -e ".[dev]"                # editable install with dev extras

python -m bust example/example_axi.json -o /tmp/out   # run the generator
bust --version                               # console-script entry point

pytest                                 # run the full test suite
pytest tests/test_suite.py::Test_Suite::test_pif       # run a single test
mypy bust                              # type-check (CI runs this; must pass)
black bust tests                       # format (excludes example/)
pre-commit run --all-files             # trailing-ws, eof, tabs, crlf, black, flake8(script/)
```

CI (`.github/workflows/python_tests.yml`) runs `mypy bust` then `pytest` across Python 3.9/3.10/3.11. Both must be green.

## Current implementation: generation pipeline

`bust/__main__.py` is the orchestrator and the clearest map of the flow:

```
json_parser(file) -> Settings -> Bus -> Module(json, bus, settings)
                                          -> Header / Documentation / Testbench
                                          -> generate_output(...)  (bust/generation.py)
```

`generate_output` creates the project directory tree (controlled by `Settings`) and writes every artifact. The CLI flags (`-f/-F/-u/-d/-p/-b/-t/-i/-m/-a/-c/-e`) toggle which artifacts are produced and overwrite behavior. The docopt usage string at the top of `__main__.py` is the source of truth for the interface.

## Current implementation: package layout

The package uses a layered structure. **The flat top-level modules in `bust/` (e.g. `bust/bus.py`, `bust/module.py`, `bust/header.py`, `bust/utils.py`, `bust/generator_factory.py`) are backward-compatibility shims** that only re-export from the new locations. Write and import new code from the real homes below. Only touch a shim to keep its re-export list in sync.

- **`bust/core/`**: domain model, no generation logic. `Bus`, `Module`, `Register`, `Field`, and `enums` (`RegisterMode`, `RegisterType`). `Module` owns the register list, address assignment (`update_addresses`), and validation.
- **`bust/generators/`**: all code emission.
  - `factory.py` `GeneratorFactory` is the seam that decouples `core` domain objects from generator implementations. **Domain classes never import generators; everything goes through this factory.** Call its static methods (`generate_module_vhdl`, `generate_bus_pif_vhdl`, `generate_bus_package_vhdl`, `generate_module_package_vhdl`, `create_bus_generator`) rather than instantiating generators directly.
  - `vhdl/bus_generator.py`, `vhdl/module_generator.py` are the VHDL emitters.
  - `header_generator.py` (C/C++/Python/IPBus-XML), `testbench_generator.py` (UVVM testbench + TCL sim script + component list), `documentation_generator.py` (LaTeX).
- **`bust/validation/`**: `config_validator.py` (`ConfigWrapper`, JSON key validation) and `vhdl_validator.py` (`is_valid_VHDL`).
- **`bust/utils/`**: `file_utils.py` (write/overwrite, plus `update_module_top_level` which preserves user edits between markers in the top-level entity), `formatting.py` (`indent_string`), `json_utils.py` (`json_parser`).
- **`bust/jinja_utils/`**: `environment.py` (`get_environment` / `render_template`) and `filters.py`. All text output is rendered from Jinja2 templates.
- **`bust/templates/`**: the `.j2` templates, organized by artifact (`vhdl/`, `header/`, `ipbus/`, `latex/`, `tcl/`, `uvvm/`). **This is where the emitted text lives**, so most output changes happen here, not in Python.
- **`bust/editor.py`**: interactive curses-menu editor for creating/editing JSON configs (`-c` / `-e` flags).

## Testing model: golden files

`tests/test_suite.py` is **not** unit-style. It regenerates output from `example/example_axi.json` and `example/example_ipbus.json` and asserts byte-for-byte equality against the committed reference files under `example/example_axi/` and `example/example_ipbus/` (subdirs `hdl/`, `tb/`, `scripts/`, `header/`, `doc/`).

Consequence: **any change to a generator or template that alters output will fail the suite until you regenerate and commit the corresponding `example/.../` reference files.** Treat the example output tree as a fixture that must be updated alongside generator/template changes. The doc test pins the version string `"0.14.0-dev"`, so keep generated reference docs consistent with that.

## VHDL simulation (`sim/`)

Optional infrastructure for simulating the generated example testbenches with the open-source **nvc** simulator inside Docker (UVVM + IPBus firmware + vip_ipbus pre-compiled into the image). No local VHDL toolchain needed. (The bundled simulation scripts emitted by bust itself target Modelsim/Questasim; other simulators require manual compilation setup.)

```bash
cd sim && make build          # build the nvc+UVVM image (once)
make sim-axi                  # run example_axi testbench (exit 0 = PASS)
make sim-ipbus                # run example_ipbus testbench
make wave-axi                 # simulate + capture FST + open GTKWave
```

`sim/README.md` documents the library layering, the `nvc --relaxed` flag gotcha, and how to add a new testbench target (`run_sim.sh` + `sim/Makefile` + `.github/workflows/vhdl_sim.yml`). The sim CI (`vhdl_sim.yml`) triggers only on changes under `sim/**` or `example/**/*.vhd`.

## Conventions

- **Versioning**: managed by `bumpversion` (config in `.bumpversion.cfg`). The version lives in both `pyproject.toml` and `bust/_version.py` (`__VERSION__`) and is bumped together. Do not edit version strings by hand.
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
