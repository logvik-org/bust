# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Releases up to and including 0.14.1 predate this changelog. Their history is in
the git log and on [PyPI](https://pypi.org/project/bust/#history).

## [Unreleased]

### Added
- `bust.generate_files` returns every output file as `{path: content}`, without writing to disk or running `pdflatex`. The command line writes that result.
- `doc/<module>.html`, the documentation as one self-contained HTML page with inline SVG bit diagrams, links between the register list and the registers, a sidebar and a print stylesheet.

### Changed
- bust builds the PDF only when `pdflatex` is on `PATH`. Without it, bust writes the `.tex` and `.html` files and prints one line saying the PDF was skipped.
- `<module>_regfile_pkg` merges `base_match` and `above_registers` into one function, `is_in_range`.

### Removed
- Support for bust 0.14 register maps. `mode`, `pulse_cycles`, `stall_cycles`, `settings`, `bus.comp_library`, `bus.reset`, `module.git_hash`, `sl`/`slv` and `"True"`/`"False"` for `byte_addressable` are now errors that point to `bust FILE --migrate`.
- The ignored options `-u`, `-b`, `-t` and `-m`, and `-F`, an alias for `-f`.
- 0.14 conversion in the editor, the 0.14 `<module>.vhd` warning, and `RegisterMode` in the Python API.
- The Upgrading from 0.14 page. `--migrate` is described on the command line page.

## [1.0.0]

First release of bust 1.0, a rewrite of bust 0.14. Install it with
`pip install bust`. This section lists the changes since 0.14.1. Upgrading from
0.14 in the documentation describes how to move a project over, and
`bust FILE --migrate` does most of the work.

### Added
- A local-bus architecture: every bus is a thin endpoint over one
  protocol-agnostic local bus and register file, so the register-map logic is
  the same for all of them. Each module is generated as
  `<module>_localbus_pkg`, `<module>_regfile_pkg`, `<module>_regfile` and
  `<module>_<bus>_endpoint`. The local-bus package is sized from and named
  after its module, so modules with different address or data widths can be
  compiled into the same VHDL library.
- SBI, Avalon-MM, Wishbone (B4 classic) and APB, alongside AXI4-Lite and IPBus.
- A self-checking UVVM testbench generated for every bus. It drives the bus
  endpoint, such as `<module>_axi_endpoint`, and checks every register, the
  error response and read data of addresses where no register sits, accesses
  that software cannot make, and the hash and version registers. CI simulates
  each bus with nvc.
- Access modes aligned with SystemRDL: separate software (`sw`) and hardware
  (`hw`) access per field, `onread` and `onwrite` side effects, `singlepulse`,
  and the hardware modifiers `we`, `wel`, `hwset`, `hwclr`, `swmod` and
  `swacc`. Access set on a register is the default for its fields, which can
  override it.
- Enumerated fields, generated as VHDL enumeration types.
- The generics `G_BASE_ADDRESS`, `G_CHECK_BASE_ADDRESS` and
  `G_MODULE_ADDR_WIDTH` on the register file, every endpoint and the starter
  top level. `G_BASE_ADDRESS` sets the base address when the module is
  instantiated, and `G_CHECK_BASE_ADDRESS => false` leaves address decoding to
  the instantiating design. `G_MODULE_ADDR_WIDTH` sets how many low address
  bits the module decodes, as `g_module_addr_width` did in 0.14. The module
  answers for `2**G_MODULE_ADDR_WIDTH` addresses from its base address, and an
  access to one of them where no register sits gets an error response. The
  default decodes just the bits the registers need.
- The generic `G_UNMAPPED_READ_DATA` is the data a read gets from an address
  where no register sits. It defaults to 0.
- The generic `G_ERR_ON_BAD_ACCESS`. When true, a write to a register software
  cannot write and a read of one it cannot read get an error response, and
  such a read returns `G_UNMAPPED_READ_DATA`. It defaults to false.
- Every output carries the `version` of the module and a 32-bit hash of the
  register map. The hash changes exactly when something that hardware or
  software depends on changes, and descriptions do not count.
- The register types `hash` and `version`, read-only constants that hold the
  register map hash and the `version` of the module, so that software can
  check at run time which register map the hardware holds.
- bust reads register maps written in JSON5, with comments, trailing commas and
  hexadecimal numbers without quotes such as `0x1c`.
- `--replace-top` replaces `<module>.vhd` with a fresh starter and keeps the
  old file as `<module>.vhd.bak`. It asks first unless `-f` is given.
- A release pipeline: publishing a GitHub Release runs the tests and the VHDL
  simulations, builds the package, publishes it to TestPyPI, installs and
  smoke-tests it from there, and then publishes the same files to PyPI with
  Trusted Publishing.

### Changed
- Relicensed from MIT to the Apache License 2.0.
- `<module>.vhd` belongs to the user, as in bust 0.14. bust writes a starter
  when the file is missing and does not replace it after that, not even with
  `-f`, which says how to replace it instead.
- Hardware connects through the `to_hw` and `from_hw` records. A register
  without fields is a member by itself, as `to_hw.<reg>`. When it has `swmod`,
  `swacc`, `we`, `wel`, `hwset` or `hwclr`, the member is the record of its
  value and strobes, such as `to_hw.load.value` and `to_hw.load.swmod`.
- The names in `<module>_regfile_pkg` that a design uses carry the module name,
  such as `C_<MODULE>_<REG>_OFFSET` and `t_<module>_<reg>_to_hw`, so one file
  can use the packages of several modules with `.all`.
- The generated VHDL follows the default style of vsg, the VHDL Style Guide,
  with constants and generics in upper case. `vsg.yaml` holds the rules, and
  the tests check the generated examples against them.
- Each name in the C header starts with the module name, such as
  `TIMER_CTRL_OFFSET` instead of `CTRL_OFFSET`, so one source file can include
  the headers of two modules that have a register of the same name. The C++
  and Python headers keep their names in a namespace and a class named after
  the module.
- The generated Python header is formatted as black formats it.
- Each generated VHDL, C, C++ and Python file starts with
  `Generated by bust v<version> <date> <time>`. `SOURCE_DATE_EPOCH` sets the
  time, for output that does not change between runs.
- bust no longer reads the `settings` section. It always writes into
  `<output directory>/<module>/`, where the output directory is `-o DIR` or
  the directory of the JSON file.
- One rule for every number in the register map: a JSON number is decimal,
  and a string is hexadecimal after `0x`, binary after `0b` and decimal
  without a prefix. `address` and `reset` now take JSON numbers, and `width`,
  `position`, enum values and the bus widths take strings.
- `true`/`false` keys such as `swmod` or `hwset` must be JSON booleans.
- bust checks the register map against its JSON Schema before anything else,
  and lists every problem in one run instead of stopping at the first.
- bust warns about each key it does not read, with a suggestion for a misspelt
  key such as `onwrit`.
- A register with a `fields` list is a `fields` register even without
  `"type": "fields"`. Before, its fields were dropped without a warning. A
  `fields` list on a register of another type is an error.
- bust no longer warns about a name longer than 16 characters.
- The editor behind `-c` and `-e` is completely reworked.
- `bust FILE -a` changes only the addresses in the file, and works on JSON5
  files. `bust -a -f` saves without asking first.
- bust no longer waits for an answer when it would overwrite a file and there
  is no terminal to ask, for example in CI. It stops with an error that
  suggests `-f`. `-F` is kept as an alias of `-f`.
- The IPBus address table lists only registers and fields that software can
  reach, with permissions taken from the fields' effective access.
- bust writes `debug.log` only when a run stops with an error, and adds to the
  file under a line with the time and the command line instead of replacing
  it.
- bust reports when `pdflatex` fails or finds errors in the documentation.

### Removed
- The per-protocol "PIF" generation path.
- The generated ModelSim/QuestaSim TCL simulation scripts. Choosing a simulator
  and flow is left to the user.
- Multi-cycle pulses and IPBus stalls. The 1.0 register file drives a pulse for
  one cycle and answers every access in one cycle, so `pulse_cycles` other
  than 1 and `stall_cycles` other than 0 are rejected with an error naming the
  register. `pulse_cycles: 1` and `stall_cycles: 0` are accepted and have no
  effect.
- The dependencies `curses-menu` and `prettytable`, which only the old editor
  used.

### Fixed
- The IPBus address table gives each field node its own permission. A
  read-only field in a read-write register was writable through uHAL.
- The IPBus address table was malformed when a description contained `&`, `<`
  or a quote. Descriptions are now escaped, and the file is declared and
  written as UTF-8.
- The headers, the LaTeX documentation and the IPBus address table printed a
  `reset` as the JSON file wrote it, which could give a C header that does not
  compile. They now print the value bust parsed.
- The C and C++ headers used the same include guard.
- A register with an empty description, or a description with characters
  LaTeX cannot print such as emoji, produced LaTeX errors. A `` `code` `` span
  in a description is set in typewriter type.
- A module without a `version` no longer gets an empty `Version:` on the title
  page and in the footer of its documentation. The version is escaped for
  LaTeX.
- `bust FILE` without `-o` failed when `FILE` was in the working directory.
- `bust -a` exited with status 0 when it could not save the file.
- Names that are VHDL keywords in upper or mixed case, such as an enumerated
  value called `ON`, were accepted and produced VHDL that does not compile. They
  are now rejected like their lower-case spelling.
- `bust --help` and the README named the command `bust.py`. The installed
  command is `bust`.

[Unreleased]: https://github.com/logvik-org/bust/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/logvik-org/bust/compare/v0.14.1...v1.0.0
