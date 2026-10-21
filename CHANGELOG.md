# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Version
strings use their PEP 440 form, so the first 1.0.0 alpha is `1.0.0a0`.

Releases up to and including 0.14.1 predate this changelog. Their history is in
the git log and on [PyPI](https://pypi.org/project/bust/#history).

## [Unreleased]

### Added
- A logo, shown in the README and the documentation.
- The generic `G_MODULE_ADDR_WIDTH` on the endpoint, the register file and the
  starter top level sets how many low address bits the module decodes, as
  `g_module_addr_width` did in 0.14. The module answers for
  `2**G_MODULE_ADDR_WIDTH` addresses from its base address, and an access to
  one of them where no register sits gets an error response. The default
  decodes just the bits the registers need.
- A new page, Base address and address range, shows how a module decodes an
  address with each setting of `G_BASE_ADDRESS`, `G_CHECK_BASE_ADDRESS` and
  `G_MODULE_ADDR_WIDTH`.
- The generated testbench checks that addresses where no register sits get an
  error response and that writes to them change no register.
- The bust 0.14 options `-u`, `-b`, `-t` and `-m` are accepted again and
  ignored with a warning, so 0.14 command lines in Makefiles keep working.
- `--replace-top` replaces `<module>.vhd` with a fresh starter and keeps the
  old file as `<module>.vhd.bak`. It asks first unless `-f` is given.
- `bust FILE --migrate` migrates a bust 0.14 JSON file without moving a
  register, and connects a 0.14 `<module>.vhd` to the bus endpoint, keeping its
  entity and the user logic (#221).

### Changed
- `<module>.vhd` belongs to the user again, as in bust 0.14. bust writes a
  starter when the file is missing and does not replace it after that, not
  even with `-f`, which says how to replace it instead. The starter has the
  generics and ports of the 1.0.0a1 top wrapper, so existing instantiations
  keep working. Add your own ports and logic to it.
- The generated testbench drives the bus endpoint, such as
  `<module>_axi_endpoint`, instead of `<module>`, which is yours now.
- A bust 0.14 `<module>.vhd`, with user logic between `-- User` comments, no
  longer stops bust with an error. bust leaves it alone, generates the other
  files and warns. Upgrading from 0.14 describes how to connect it to the bus
  endpoint.
- Each name in the C header starts with the module name, such as
  `TIMER_CTRL_OFFSET` instead of `CTRL_OFFSET`, so one source file can include
  the headers of two modules that have a register of the same name. The C++
  and Python headers already kept their names in a namespace and a class
  named after the module, and are unchanged.
- A register without fields is now a member of `to_hw` and `from_hw` by
  itself, as `to_hw.<reg>` instead of `to_hw.<reg>.<reg>`. When it has
  `swmod`, `swacc`, `we`, `wel`, `hwset` or `hwclr`, the member is the record
  of its value and strobes, such as `to_hw.load.value` and `to_hw.load.swmod`.
  Such a register no longer gets a `t_<reg>_to_hw` or `t_<reg>_from_hw` type.
  This is the shape of the 0.14 records, so `ipb_rw_regs.<reg>` becomes
  `to_hw.<reg>`.
- bust writes `debug.log` only when a run stops with an error, so a run that
  succeeds no longer leaves the file in the working directory. A failed run
  adds to the file under a line with the time and the command line, instead
  of replacing it.
- One rule for every number in the register map: a JSON number is decimal,
  and a string is hexadecimal after `0x`, binary after `0b` and decimal
  without a prefix. `address` and `reset` used to read a string without a
  prefix as hexadecimal, so `"10"` meant 0x10 and now means 10. `address` and
  `reset` now take JSON numbers, and `width`, `position`, enum values and the
  bus widths take strings. A string with hexadecimal digits but no `0x`, such
  as `"1B2"`, stops bust with a message that suggests `"0x1B2"`. A value of the
  wrong type is reported with the key and the register instead of a Python
  error.

### Fixed
- `"byte_addressable": "False"`, as bust 0.14 wrote it, was read as true, so a
  word-addressed module from 0.14 became byte-addressed. Its registers without
  an address moved to multiples of the data width in bytes, and addresses set
  by hand that were not such multiples were rejected. bust reads `"True"` and
  `"False"` again, warns that they are deprecated, and `bust FILE -a` saves a
  JSON boolean. Any other value is an error.
- The headers, the LaTeX documentation and the IPBus address table printed a
  `reset` as the JSON file wrote it. A reset without `0x` gave a C header that
  does not compile, such as `1B2`, or a value that differs from the hardware,
  such as `10` for a register that resets to 0x10. They now print the value
  bust parsed, in the headers as `0x` and lower-case digits like the offsets
  and masks.
- A module without a `version` no longer gets an empty `Version:` on the title
  page and in the footer of its documentation. The version is now escaped for
  LaTeX.
- bust reads the bust 0.14 type names `sl` and `slv` again, for registers and
  fields, as `bit` and `vector`. It warns once per file that they are
  deprecated, and `bust FILE -a` saves the file with the new names. Without
  this, no register map written for 0.14 could be read.
- With `G_CHECK_BASE_ADDRESS => false`, the register file looked only at the
  address bits that select a register. An access to an address above the
  registers reached a register instead of getting an error, so a mistyped
  address could hit a pulse register. Set `G_MODULE_ADDR_WIDTH` to the size of
  the address range your interconnect gives the module.

## [1.0.0a1] - 2026-10-16

Second pre-release of bust 1.0.0, for testing. Install it with
`pip install --pre bust` or `pip install bust==1.0.0a1`. The documentation is
now at [bust.readthedocs.io](https://bust.readthedocs.io).

### Changed
- The `settings` section of the JSON file is optional.
- `bust -a -f` saves the JSON file without asking first.
- bust no longer waits for an answer when it would overwrite a file and there
  is no terminal to ask, for example in CI. It stops with an error that
  suggests `-f`.
- An invalid register is reported in one line that names the register and the
  reason, without the generic "Lacking or misspelt JSON keys?" guess and the
  dump of the register.
- The settings `bus_subdir`, `coverage`, `uvvm_rel_path`, `ipbus_rel_path` and
  `vip_ipbus_rel_path` and the bus keys `comp_library` and `reset` have no
  effect in 1.0. bust no longer logs messages about them, and `bust -a` keeps
  them as they are instead of adding or dropping them.
- bust warns about each key it does not read, so a misspelt key such as
  `onwrit` no longer goes unnoticed.
- bust rejects register maps that produced VHDL that does not compile, or a
  register software could not reach: two registers, or two fields of one
  register, whose names differ only in case, a register with the name of its
  module, a `fields` register with no fields, an address that is not a multiple
  of the data width in bytes on a byte-addressed bus, and a `data_width` that is
  not a whole number of bytes.
- A register with a `fields` list is a `fields` register even without
  `"type": "fields"`. Before, its fields were dropped without a warning. A
  `fields` list on a register of another type is an error.
- `true`/`false` keys such as `swmod` or `hwset` must be JSON booleans. A quoted
  `"false"` used to switch the option on.
- The editor (`-c`, `-e`) stops with an error when there is no terminal instead
  of exiting with status 0 without saving.
- bust reports when `pdflatex` fails or finds errors in the documentation.

### Fixed
- `bust FILE` without `-o` failed when `FILE` was in the working directory.
- The IPBus address table was malformed when a description contained `&`, `<`
  or a quote. Descriptions are now escaped, and the file is declared and
  written as UTF-8.
- The C and C++ headers used the same include guard, so a file that included
  both lost the second.
- A register with an empty description produced LaTeX errors.
- `bust -a` exited with status 0 when it could not save the file.
- Names that are VHDL keywords in upper or mixed case, such as an enumerated
  value called `ON`, were accepted and produced VHDL that does not compile. They
  are now rejected like their lower-case spelling.

### Removed
- The 0.14 module paths such as `bust.module`, `bust.register` and
  `bust.header`, which 1.0.0a0 kept as aliases. The code now lives in the
  `bust.core`, `bust.generators` and `bust.validation` packages. bust is a
  command-line tool, and its Python modules are not a supported API.

## [1.0.0a0] - 2026-10-15

First pre-release of bust 1.0.0, for testing. Install it with
`pip install --pre bust` or `pip install bust==1.0.0a0`. A plain
`pip install bust` still installs 0.14.1.

### Added
- A local-bus architecture: every bus is a thin endpoint over one
  protocol-agnostic local bus and register file, so the register-map logic is
  the same for all of them. Each module is generated as
  `<module>_localbus_pkg`, `<module>_regfile_pkg`, `<module>_regfile`,
  `<module>_<bus>_endpoint` and a fixed `<module>` top wrapper. The local-bus
  package is sized from and named after its module, so modules with different
  address or data widths can be compiled into the same VHDL library.
- SBI, Avalon-MM, Wishbone (B4 classic) and APB, alongside AXI4-Lite and IPBus.
- A self-checking UVVM testbench generated for every bus. CI simulates each of
  them with nvc.
- Access modes aligned with SystemRDL: separate software (`sw`) and hardware
  (`hw`) access per field, `onread` and `onwrite` side effects, `singlepulse`,
  and the hardware modifiers `we`, `wel`, `hwset`, `hwclr`, `swmod` and
  `swacc`. Access set on a register is the default for its fields, which can
  override it.
- Enumerated fields, generated as VHDL enumeration types.
- Access-mode combinations the generator cannot render are rejected with an
  error naming the register and field: an enumerated field with `onwrite`,
  `onread`, `hwset`, `hwclr` or `singlepulse`; `swmod`, `swacc` or
  `singlepulse` on a field hardware cannot read; and `singlepulse` together
  with `onread` or on a field hardware writes every cycle.
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
- A `singlepulse` field returns to its reset value one clock after a software
  write, not to 0, so a pulse field with a non-zero reset idles at that value.
  A 0.14 `pulse` register becomes a `singlepulse` field and so still returns to
  its reset value as in 0.14, but after one cycle (see `pulse_cycles` under
  Removed).
- When a hardware update (`hwclr`, `hwset`, or a `we`/`wel` write) and a
  software read side effect (`onread: rclr` or `rset`) hit a field in the same
  clock, the hardware update wins, as it already did over a software write. A
  `hwset` that coincides with an `rclr` read is no longer lost.
- The top-level `<module>` VHDL file is a fixed wrapper that bust regenerates,
  so `-f` overwrites it like any other file. `-F` is kept as an alias of `-f`.
  In 0.14 that file held user logic between `-- User ... Start/End` markers
  and `-f` left it alone. bust now stops with an error, before writing
  anything, instead of overwriting a top-level file that still has those
  markers. Move that logic into your own design, where it connects through the
  `to_hw`/`from_hw` records, then delete or rename the old file.
- The supported buses are described in one data-driven registry table, so
  adding a single-beat bus takes a new table entry plus its endpoint and
  testbench templates.
- IPBus modules must use a `data_width` of 32 and an `addr_width` of at most
  32. Other values are rejected with an error instead of generating VHDL that
  does not compile.
- The IPBus address table lists only registers and fields that software can
  reach, with permissions taken from the fields' effective access.
- bumpversion no longer creates the version tag. The GitHub Release does.

### Removed
- The legacy per-protocol "PIF" generation path. Local-bus generation is the
  only path.
- The `-u`, `-b`, `-t` and `-m` command-line options, which belonged to the PIF
  path.
- The generated ModelSim/QuestaSim TCL simulation scripts. Choosing a simulator
  and flow is left to the user.
- Multi-cycle pulses and IPBus stalls from 0.14. The 1.0 register file drives a
  pulse for one cycle and answers every access in one cycle, so `pulse_cycles`
  other than 1 and `stall_cycles` other than 0 are rejected with an error
  naming the register, instead of being dropped while the LaTeX documentation
  and the IPBus address table still printed them. Remove both keys from 0.14
  JSON. `pulse_cycles: 1` and `stall_cycles: 0` are accepted and have no
  effect.

### Fixed
- An enumerated field with no `reset` and no literal of value 0 resets to its
  first literal in hardware, but the C/C++/Python headers and the LaTeX
  documentation reported a reset of 0. They now report the reset hardware uses.
- The IPBus address table gives each field node its own permission. A
  read-only field in a read-write register was writable through uHAL.
- The interactive editor (`-c`, `-e`) failed to add a register when its address
  was entered by hand.
- `bust --help` and the README named the command `bust.py`. The installed
  command is `bust`.
- `python -m build` and `pip install -e .` failed on the reworked source tree,
  because setuptools also took the new `hdl/` and `sim/` directories for
  packages. The wheel also left out the Jinja2 templates, without which an
  installed bust cannot generate anything.

[Unreleased]: https://github.com/logvik-org/bust/compare/v1.0.0a1...HEAD
[1.0.0a1]: https://github.com/logvik-org/bust/compare/v1.0.0a0...v1.0.0a1
[1.0.0a0]: https://github.com/logvik-org/bust/compare/0d2a394f4710dd007be031b2b05c1bce4f35d56b...v1.0.0a0
