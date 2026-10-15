# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases up to and including 0.14.1 predate this changelog. Their history is in
the git log and on [PyPI](https://pypi.org/project/bust/#history).

## [Unreleased]

### Added
- A local-bus architecture: every bus is a thin endpoint over one
  protocol-agnostic local bus and register file, so the register-map logic is
  the same for all of them. Each module is generated as `localbus_pkg`,
  `<module>_regfile_pkg`, `<module>_regfile`, `<module>_<bus>_endpoint` and a
  fixed `<module>` top wrapper.
- SBI, Avalon-MM, Wishbone (B4 classic) and APB, alongside AXI4-Lite and IPBus.
- A self-checking UVVM testbench generated for every bus. CI simulates each of
  them with nvc.
- Access modes aligned with SystemRDL: separate software (`sw`) and hardware
  (`hw`) access per field, `onread` and `onwrite` side effects, `singlepulse`,
  and the hardware modifiers `we`, `wel`, `hwset`, `hwclr`, `swmod` and
  `swacc`. Access set on a register is the default for its fields, which can
  override it.
- Enumerated fields, generated as VHDL enumeration types.
- The `G_BASE_ADDRESS` generic sets the base address when the module is
  instantiated, and `G_CHECK_BASE_ADDRESS => false` leaves address decoding to
  the instantiating design.
- Python 3.12, 3.13 and 3.14 support. CI tests 3.9 to 3.14 and the 3.15
  pre-release.
- `scripts/smoke-test.sh`, which checks an installed bust against the committed
  example outputs. CI runs it on the built wheel.
- A release pipeline: publishing a GitHub Release runs the tests and the VHDL
  simulations, builds the package, publishes it to TestPyPI, installs and
  smoke-tests it from there, and then publishes the same files to PyPI with
  Trusted Publishing.

### Changed
- Relicensed from MIT to the Apache License 2.0. The package metadata gives the
  license as the SPDX expression `Apache-2.0`, and the wheel includes `LICENSE`
  and `NOTICE`.
- JSON that uses the old `mode` keyword is still accepted and translated to
  `sw` and `hw` access.
- The top-level `<module>` VHDL file is a fixed wrapper that bust regenerates,
  so `-f` overwrites it like any other file. `-F` is kept as an alias of `-f`.
- The supported buses are described in one data-driven registry table, so
  adding a single-beat bus takes a new table entry plus its endpoint and
  testbench templates.
- bumpversion no longer creates the version tag. The GitHub Release does.

### Removed
- The legacy per-protocol "PIF" generation path. Local-bus generation is the
  only path.
- The `-u`, `-b`, `-t` and `-m` command-line options, which belonged to the PIF
  path.
- The generated ModelSim/QuestaSim TCL simulation scripts. Choosing a simulator
  and flow is left to the user.

### Fixed
- `python -m build` and `pip install -e .` failed on the reworked source tree,
  because setuptools also took the new `hdl/` and `sim/` directories for
  packages. The wheel also left out the Jinja2 templates, without which an
  installed bust cannot generate anything.

[Unreleased]: https://github.com/logvik-org/bust/compare/0d2a394f4710dd007be031b2b05c1bce4f35d56b...HEAD
