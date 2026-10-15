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
(`access-modes.md`), the buses, the generated HDL and the command line. A change
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
- `bust/validation/`, `bust/utils/`, `bust/jinja_utils/`, and `bust/editor.py`
  (the curses editor behind `-c` and `-e`). The editor still writes only the
  0.14 `mode` schema.
- Each JSON section has a set of the keys bust reads (`REGISTER_KEYS`,
  `FIELD_KEYS`, `MODULE_KEYS` in `bust/core/`, and the key tuples in `Bus` and
  `Settings`). bust warns about any other key, so a new key goes into its set.
  Keys bust 0.14 used that 1.0 ignores stay accepted (`IGNORED_KEYS`) and are
  written back unchanged by `-a`.

## Generated VHDL

Each module becomes `<module>_localbus_pkg`, `<module>_regfile_pkg`,
`<module>_regfile`, `<module>_<bus>_endpoint`, the `<module>` top wrapper and
`<module>_tb`. Every bus is a thin endpoint over one local bus (`t_lb_m2s` /
`t_lb_s2m`), so the register logic exists once, in `regfile.j2`.

- Generated HDL and its testbench change together, in the same PR.
- The base address is the `G_BASE_ADDRESS` generic (with
  `G_CHECK_BASE_ADDRESS`), never a JSON key.
- Hardware connects through the `to_hw` and `from_hw` records. Enumerated fields
  are VHDL enumeration types.
- Same-cycle precedence is fixed: `hwclr` > `hwset` > hardware write with
  `we`/`wel` > software write or `onread` effect > hardware write without
  `we`/`wel`.
- Output is VHDL-2008 and must simulate with nvc.
- A new single-beat bus needs a `BUS_CONFIG` entry, endpoint and testbench
  templates, factory methods, goldens and a sim target.

## Tests

- `tests/test_suite.py` regenerates the outputs of the `example/*.json` files
  and compares them byte for byte with `example/<name>/`. After an output
  change, run the golden update, review the diff and commit it. The LaTeX
  goldens pin the version string `1.0.0-dev`.
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
