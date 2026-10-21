# Upgrading from 0.14

bust 1.0 reads your 0.14 JSON files, but it generates a different set of VHDL
files. This page lists what you need to change. The [changelog](https://github.com/logvik-org/bust/blob/master/CHANGELOG.md)
has the full list of changes.

```bash
pip install --upgrade bust
```

## Migrate with --migrate

`bust FILE --migrate` makes the JSON changes listed in
[Check your JSON files](#check-your-json-files) that need no decision, and
connects a bust 0.14 `<module>.vhd` to the bust 1.0 endpoint as described in
[Connect your top-level file](#connect-your-top-level-file). It lists the
changes and asks first, unless you add `-f`, and keeps each old file with the
suffix `.0_14`. Give it the same `-o` as your other runs, then generate the
bust 1.0 files:

```bash
bust timer.json -o out --migrate
bust timer.json -o out
```

bust lists any line it could not change, such as one that passes a whole 0.14
register record to another entity. Change those by hand.

## Connect your top-level file

`<module>.vhd` is still your file. bust writes it only when it does not exist,
and never replaces it, not even with `-f`. In 0.14 it held your logic between
`-- User ... Start` and `-- User ... End` comments and instantiated
`<module>_ipb_pif` or `<module>_axi_pif`. bust 1.0 leaves such a file alone,
generates the other files, and warns:

```text
out/timer/hdl/timer.vhd is a bust 0.14 top level, so bust leaves it alone. To connect it to timer_ipb_endpoint, run bust with --migrate.
```

To connect it by hand, change the architecture of `<module>.vhd`. The entity, with its
0.14 generics and ports, can stay as it is, so the instantiations of
`<module>` in your design do not change.

1. Replace `use work.<module>_pif_pkg.all;` with
   `use work.<module>_regfile_pkg.all;`.
2. Replace the signals `ipb_rw_regs`, `ipb_ro_regs` and `ipb_pulse_regs`, or
   the `axi_` ones, with `to_hw` and `from_hw`.
3. Replace the instance of `<module>_ipb_pif` or `<module>_axi_pif` with an
   instance of `<module>_ipb_endpoint` or `<module>_axi_endpoint`.
4. In your logic, rename the register records as in the table below.

For an IPBus module with 16-bit addresses, steps 2 and 3 give:

```vhdl
  signal to_hw   : t_timer_to_hw;
  signal from_hw : t_timer_from_hw;
  ...
  i_bus : entity work.timer_ipb_endpoint
    generic map (
      G_BASE_ADDRESS       => unsigned(g_ipb_baseaddr(15 downto 0)),
      G_CHECK_BASE_ADDRESS => g_check_baseaddr,
      G_MODULE_ADDR_WIDTH  => g_module_addr_width)
    port map (
      clk     => ipb_clk,
      reset   => ipb_reset,
      ipb_in  => ipb_in,
      ipb_out => ipb_out_i,
      to_hw   => to_hw,
      from_hw => from_hw);
```

`g_module_addr_width` of 0 meant "just the bits the registers need" in 0.14.
In 1.0 a value below `C_MODULE_ADDR_WIDTH`, 0 included, stops the simulation,
so map `C_MODULE_ADDR_WIDTH` instead if your design uses 0. Better, set the
width of the module's address range, such as 16.
[Base address and address range](addressing.md) describes the three generics.

| bust 0.14 | bust 1.0 |
|---|---|
| `ipb_rw_regs.<reg>` or `axi_rw_regs.<reg>` | `to_hw.<reg>` |
| `ipb_pulse_regs.<reg>` or `axi_pulse_regs.<reg>` | `to_hw.<reg>` |
| `ipb_ro_regs.<reg>` or `axi_ro_regs.<reg>` | `from_hw.<reg>` |

A field keeps its name below its register, as in `to_hw.<reg>.<field>`.
[Generated HDL](generated-hdl.md) describes the records.

To start over from the bust 1.0 starter instead, run bust with
`--replace-top`. It keeps your 0.14 file as `<module>.vhd.bak`. The starter
has the bust 1.0 generics and ports, so the instantiations then change:

| bust 0.14 | bust 1.0 starter |
|---|---|
| `g_ipb_baseaddr` or `g_axi_baseaddr`, a 32-bit `std_logic_vector` | `G_BASE_ADDRESS`, an `unsigned` of `addr_width` bits |
| `g_check_baseaddr` | `G_CHECK_BASE_ADDRESS` |
| `g_module_addr_width` | `G_MODULE_ADDR_WIDTH` |
| `ipb_clk`, `ipb_reset` | `clk`, `reset` |

## Update your compile order

The generated files have new names. For a module called `<module>`:

| bust 0.14 | bust 1.0 |
|---|---|
| `axi_pkg.vhd` (AXI4-Lite only) | `<module>_localbus_pkg.vhd` |
| `<module>_pif_pkg.vhd` | `<module>_regfile_pkg.vhd` |
| `<module>_axi_pif.vhd` or `<module>_ipb_pif.vhd` | `<module>_regfile.vhd` and `<module>_axi_endpoint.vhd` or `<module>_ipb_endpoint.vhd` |
| `<module>.vhd` | `<module>.vhd`, still yours |
| `tb/<module>_axi_pif_tb.vhd` or `tb/<module>_ipb_pif_tb.vhd` | `tb/<module>_tb.vhd` |
| `scripts/` (ModelSim/Questa scripts) | not generated |

Delete the old generated files from your project and compile the new ones in
the order given in [Generated HDL](generated-hdl.md). The generated VHDL needs
VHDL-2008.

bust no longer writes simulator scripts. [Testbenches](testbenches.md) describes
what the testbench needs, so you can add it to your own simulation flow.

## Check your JSON files

The old `mode` key still works. bust translates it to software (`sw`) and
hardware (`hw`) access, as described in
[Register map format](register-map-format.md). You can keep your files as they
are, or move to `sw` and `hw` to use the new [access modes](access-modes.md).

A few keys need changes:

- **`sl` and `slv`.** The types `sl` and `slv` are now `bit` and `vector`, for
  registers and fields. bust reads the old names and warns that they are
  deprecated, and `bust FILE -a` saves the file with the new names.
- **`byte_addressable`.** bust 0.14 wrote it as the string `"True"` or
  `"False"`. bust 1.0 reads both and warns that they are deprecated, and
  `bust FILE -a` saves `true` or `false`. A word-addressed AXI4-Lite module
  from 0.14 stays word-addressed.
- **Hexadecimal values without `0x`.** bust 0.14 read an `address` or a
  `reset` as hexadecimal even without `0x`, so `"10"` meant 0x10. bust 1.0
  reads a string without a prefix as decimal, so `"10"` is now 10. Add `0x` to
  such values. The values 0 to 9 are the same either way, and a value with a
  letter, such as `"1c"`, stops bust with a message that suggests `"0x1c"`.
  bust 0.14 and its editor wrote `0x` themselves, so only values typed by hand
  can lack it. [Numbers](register-map-format.md#numbers) gives the rule.
- **`pulse_cycles` and `stall_cycles`.** A pulse now lasts one clock cycle, and
  every access is answered in one cycle. Remove both keys. bust rejects
  `pulse_cycles` other than 1 and `stall_cycles` other than 0 with an error
  that names the register. A `pulse` register still returns to its reset value
  after the pulse, as in 0.14.
- **IPBus widths.** An IPBus module needs `data_width` 32 and an `addr_width` of
  at most 32.
- **Keys that no longer do anything.** bust no longer reads the `settings`
  section or the bus keys `comp_library` and `reset`, and warns about them. A
  `proj_dir` or `"mod_subdir": false` stops bust, because the output would land
  somewhere else. Remove them and use `-o` for the output directory.
  `--migrate` removes them and says which `-o` to use. The generated files
  refer to each other through `work`, so you choose the library when you
  compile them.
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
- On IPBus, bust 0.14 returned `0xDEADBEEF` with the error for a read where no
  register sits. bust 1.0 returns the generic `G_UNMAPPED_READ_DATA`, which is
  0 unless you set it, on every bus.

## Update your software

Code that includes the generated headers needs these changes:

- Each name in the C header starts with the module name, so `REG0_OFFSET` in
  `example_axi.h` becomes `EXAMPLE_AXI_REG0_OFFSET`. The C++ and Python names
  are unchanged, in the namespace and the class named after the module.
- `<REG>_MODE` is gone. `<REG>_SW` and `<REG>_HW` give the software and
  hardware access instead. [Headers and documentation](headers-and-docs.md)
  lists every constant.
- The C `#define` lines no longer end in a semicolon, so the constants work in
  expressions.

## Command-line options

The options `-u`, `-b`, `-t` and `-m` have no effect any more. They controlled
files that bust 1.0 no longer generates or always generates. bust accepts them
with a warning, so a 0.14 command line in a Makefile still runs, but remove them
when you can. `-F` is kept as another name for `-f`.
[Command line](command-line.md) lists the options.

## Python imports

If you imported bust as a Python library, the 0.14 modules such as
`bust.module`, `bust.register` and `bust.header` are gone. bust is a command-line
tool, and its Python modules are not a supported interface.

## License

bust 1.0 is licensed under the Apache License 2.0. Version 0.14 and earlier
were released under the MIT license.
