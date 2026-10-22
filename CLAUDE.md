# CLAUDE.md

Guidance for Claude Code in this repository.

## What bust is

bust is a command-line tool that reads a JSON register map and generates, for
each module, a VHDL register file behind a bus endpoint, a self-checking UVVM
testbench, C/C++/Python headers, an IPBus address table (IPBus only) and LaTeX
documentation. The buses are AXI4-Lite (`axi`), IPBus (`ipbus`), SBI (`sbi`),
Avalon-MM (`avalon`), Wishbone (`wishbone`) and APB (`apb`). It runs on Python
3.9 to 3.14 and is licensed under Apache 2.0.

The user documentation in `docs/` (published on Read the Docs) is the reference
for behaviour: the JSON format (`register-map-format.md`), the access modes
(`access-modes.md`), the buses, addressing (`addressing.md`), the generated HDL
and the command line. A change
to behaviour updates the matching page in the same PR.

## Commands

```bash
pip install -e ".[dev,docs]"
pytest                                          # full suite
mypy bust                                       # must stay clean
pre-commit run --all-files                      # black and whitespace checks
BUST_UPDATE_GOLDENS=1 pytest tests/test_suite.py  # rewrite the golden files
sphinx-build -W --keep-going -b html docs docs/_build/html
python -m bust example/example_axi.json -o /tmp/out -p
cd sim && make build && make sim-axi            # nvc + UVVM in Docker
```

## Code layout

- `bust/__main__.py`: the CLI. Its docopt usage string is the interface. The
  flow is `json_parser` -> `Settings` -> `Bus` -> `Module` -> `generate_output`
  (`bust/generation.py`).
- `bust/core/`: the domain model. `bus.py` holds the bus registry
  (`BUS_CONFIG`), `module.py` the register list, address assignment and
  validation, `register.py` and `field.py` the access-mode model and the helpers
  templates render from, `legacy_schema.py` the translation of the 0.14 `mode`
  format. No generation code here.
- `bust/generators/`: code emission. Domain objects reach generators only
  through `GeneratorFactory` in `factory.py`.
- `bust/templates/`: the Jinja2 templates. All emitted text lives here, so most
  output changes are template changes. `vhdl/testbench/localbus_tb/` holds the
  test body shared by every bus.
- `bust/editing/`: `JsonSource` edits the text of a JSON or JSON5 file one
  value at a time, and `RegisterMapDocument` applies JSON Patch operations
  that it checks through `Bus` and `Module`. `bust/schema.py` is the JSON
  Schema of the register map. `bust/editor/`, the Textual editor behind `-c`
  and `-e` (the optional `editor` extra), works only through these, and
  `bust -a` saves through `RegisterMapDocument` too. `session.py` holds the
  editor logic without Textual, `app.py` and `screens.py` the screens.
- `bust/validation/`, `bust/utils/` and `bust/jinja_utils/`.
- Each JSON section has a set of the keys bust reads (`REGISTER_KEYS`,
  `FIELD_KEYS`, `MODULE_KEYS` in `bust/core/`, and the key tuple in `Bus`).
  `bust/validation/schema_check.py` checks the file against `bust/schema.py`
  before `Bus` and `Module` are built, reports every problem with its path and
  line, and warns about any other key. A new key goes into its set and into
  the schema, and `tests/test_schema.py` checks that the two agree. The
  checker supports only the JSON Schema keywords in its `CHECKED_KEYWORDS`,
  and `tests/test_schema_check.py` fails if the schema uses another one. bust no
  longer reads the 0.14 `settings` section, and `--migrate` removes the 0.14
  keys.

## Generated VHDL

Each module becomes `<module>_localbus_pkg`, `<module>_regfile_pkg`,
`<module>_regfile`, `<module>_<bus>_endpoint` and `<module>_tb`, which bust
regenerates on every run, and the `<module>` top level, which belongs to the
user. bust writes a starter `<module>.vhd` only when it is missing and replaces
it only for `--replace-top`. Every bus is a thin endpoint over one local bus
(`t_lb_m2s` / `t_lb_s2m`), so the register logic exists once, in `regfile.j2`.
The generated testbench drives `<module>_<bus>_endpoint`.

- Generated HDL and its testbench change together, in the same PR.
- The base address is the `G_BASE_ADDRESS` generic (with
  `G_CHECK_BASE_ADDRESS` and the module address width `G_MODULE_ADDR_WIDTH`),
  never a JSON key. Use the terms of `docs/addressing.md`: a module answers for
  an address range that starts at its base address, and a register sits at its
  register offset in that range. "Offset" alone is ambiguous, so write
  "register offset".
- Hardware connects through the `to_hw` and `from_hw` records. Enumerated fields
  are VHDL enumeration types.
- Same-cycle precedence is fixed: `hwclr` > `hwset` > hardware write with
  `we`/`wel` > software write or `onread` effect > hardware write without
  `we`/`wel`.
- Output is VHDL-2008 and must simulate with nvc.
- Output follows the vsg default style with the settings in `vsg.yaml`, and
  `tests/test_vsg.py` checks the examples and `hdl/prototype/` with the vsg
  version pinned in `pyproject.toml`. Templates line up columns with the
  `align` filter and break long calls with `wrap`
  (`bust/jinja_utils/filters.py`).
- A new single-beat bus needs a `BUS_CONFIG` entry, endpoint and testbench
  templates, factory methods, goldens and a sim target.

## Tests

- `tests/test_suite.py` regenerates the outputs of the `example/*.json` files
  and compares them byte for byte with `example/<name>/`. After an output
  change, run the golden update, review the diff and commit it. The LaTeX
  goldens pin the version string `1.0.0-dev`, and `tests/conftest.py` pins
  the version and time in the `Generated by bust` line of every file.
- `hdl/prototype/` holds hand-written reference HDL and testbenches. The sim
  runs the hand-written testbenches against the generated HDL as well, which is
  the one check that does not come from the generator itself.
- `tests/test_cli.py` runs `bust` as a subprocess with stdin closed, as CI does.

## Simulation and CI

`sim/` runs the testbenches with nvc and UVVM in Docker. A new target goes into
`sim/scripts/run_sim.sh`, `sim/Makefile` and `.github/workflows/vhdl_sim.yml`.
`python_tests.yml` runs mypy and pytest on Python 3.9 to 3.14 (plus 3.15 as an
experimental leg), builds the docs with `-W`, and builds and smoke-tests the
wheel. `vhdl_sim.yml` runs on changes under `sim/`, `hdl/` and the example VHDL,
and `pre-commit.yml` on every PR. Actions are pinned to commit SHAs with a
`# vX.Y.Z` comment.

## Versions and releases

The version is set only in `bust/_version.py` (`__VERSION__`) and follows PEP
440. The release procedure is in `docs/development.md`. The maintainer merges to
`master` and publishes releases: never do either, or push a tag, without their
explicit approval.

## Out of scope

These are deferred and tracked in GitHub issues. Do not implement them without
an agreed design: the `precedence` property, `counter` fields, `intr` and
`nonsticky` interrupts, FIFO and queue interfaces, array registers, RAM
interfaces, and an `addrmap` hierarchy with multiple instances. Keep the JSON
format open to a future `addrmap` level. Burst protocols (full AXI4,
AXI-Stream) would get native implementations, not the local bus.

## Conventions

- `CHANGELOG.md` follows Keep a Changelog. Add user-facing changes under
  `## [Unreleased]`.
- black formats everything except `example/`. Docstrings use the Google
  convention.
- Docs and changelog prose: plain sentences, no em-dashes, no semicolons.
- The images in `docs/images/` come from `scripts/make_logo.py`, and the
  address figure in `docs/addressing.md` from `scripts/make_address_figure.py`.
  Change the script and rerun it rather than editing the output.
