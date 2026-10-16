# Upgrading from 0.14

bust 1.0 reads your 0.14 JSON files, but it generates a different set of VHDL
files and the top-level file no longer holds your logic. This page lists what
you need to change. The [changelog](https://github.com/logvik-org/bust/blob/master/CHANGELOG.md)
has the full list of changes.

```bash
pip install --upgrade bust
```

## Move your logic out of the top-level file

In 0.14, `<module>.vhd` held your own logic between `-- User ... Start` and
`-- User ... End` comments, and `bust -f` left the file alone. In 1.0,
`<module>.vhd` is a fixed wrapper that bust regenerates on every run.

Before you run bust 1.0 on an existing project:

1. Move the code between the `-- User ... Start/End` comments into a file of
   your own, for example a new entity that instantiates `<module>`.
2. Connect it to the registers through the `to_hw` and `from_hw` record ports
   of `<module>`. [Generated HDL](generated-hdl.md) shows how.
3. Delete or rename the old `<module>.vhd`.

If an old top-level file with those comments is still there, bust stops before
it writes anything and exits with status 1:

```text
An error occurred during output generation...
LegacyTopLevelFile: Refusing to overwrite out/timer/hdl/timer.vhd: it has the '-- User ... Start/End' sections of a bust 0.14 top level, so it may hold your own logic. In bust 1.0 timer.vhd is a fixed wrapper that bust regenerates, and hardware logic connects through the to_hw/from_hw records outside the generated files. Move your logic out of this file, then delete or rename it to proceed. No files were written.
```

## Update your compile order

The generated files have new names. For a module called `<module>`, with `axi`
or `ipb` for the bus:

| bust 0.14 | bust 1.0 |
|---|---|
| `axi_pkg.vhd` (AXI4-Lite only) | `<module>_localbus_pkg.vhd` |
| `<module>_pif_pkg.vhd` | `<module>_regfile_pkg.vhd` |
| `<module>_axi_pif.vhd` or `<module>_ipb_pif.vhd` | `<module>_regfile.vhd` and `<module>_axi_endpoint.vhd` or `<module>_ipb_endpoint.vhd` |
| `<module>.vhd` | `<module>.vhd`, now a fixed wrapper |
| `tb/<module>_axi_pif_tb.vhd` or `tb/<module>_ipb_pif_tb.vhd` | `tb/<module>_tb.vhd` |
| `scripts/` (ModelSim/Questa scripts) | not generated |

Delete the old files from your project and compile the new ones in the order
given in [Generated HDL](generated-hdl.md). The generated VHDL needs VHDL-2008.

bust no longer writes simulator scripts. [Testbenches](testbenches.md) describes
what the testbench needs, so you can add it to your own simulation flow.

## Check your JSON files

The old `mode` key still works. bust translates it to software (`sw`) and
hardware (`hw`) access, as described in
[Register map format](register-map-format.md). You can keep your files as they
are, or move to `sw` and `hw` to use the new [access modes](access-modes.md).

A few keys need changes:

- **`pulse_cycles` and `stall_cycles`.** A pulse now lasts one clock cycle, and
  every access is answered in one cycle. Remove both keys. bust rejects
  `pulse_cycles` other than 1 and `stall_cycles` other than 0 with an error
  that names the register. A `pulse` register still returns to its reset value
  after the pulse, as in 0.14.
- **IPBus widths.** An IPBus module needs `data_width` 32 and an `addr_width` of
  at most 32.
- **Keys that no longer do anything.** bust ignores the settings
  `bus_subdir`, `coverage`, `uvvm_rel_path`, `ipbus_rel_path` and
  `vip_ipbus_rel_path`, and the bus keys `comp_library` and `reset`. You can
  leave them in your files. The generated files refer to each other through
  `work`, so you choose the library when you compile them.
- **Stricter checks.** bust 1.0 stops on register maps that 0.14 accepted but
  that produce VHDL that does not compile or a register software cannot reach,
  such as two registers whose names differ only in case, or an address that is
  not a multiple of the data width in bytes. It also warns about keys it does
  not read.

## Behaviour that changed

- A hardware update (`hwset`, `hwclr` or a write with `we`/`wel`) wins over a
  software read side effect such as `onread: rclr` in the same clock cycle, as
  it already did over a software write. A `hwset` that coincides with a
  clear-on-read is no longer lost.
- The IPBus address table gives each field its own permission, so a read-only
  field in a read-write register is read-only through uHAL.
- For an enumerated field without a `reset` and without a value 0, the headers
  and the documentation now give the reset that the hardware uses, which is
  the first value.

## Command-line options

The options `-u`, `-b`, `-t` and `-m` are gone. They controlled files that bust
1.0 no longer generates or always generates. `-F` is kept as another name for
`-f`. [Command line](command-line.md) lists the options.

## Python imports

If you imported bust as a Python library, the 0.14 modules such as
`bust.module`, `bust.register` and `bust.header` are gone. bust is a command-line
tool, and its Python modules are not a supported interface.

## License

bust 1.0 is licensed under the Apache License 2.0. Version 0.14 and earlier
were released under the MIT license.
