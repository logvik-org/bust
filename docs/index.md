# bust

<p align="center">
  <img class="only-light" alt="bust: single source of truth" src="_static/logo-light.svg" width="480">
  <img class="only-dark" alt="bust: single source of truth" src="_static/logo-dark.svg" width="480">
</p>

**bust** generates the register file of an FPGA or ASIC module from a JSON
register map. From one file it writes the VHDL register file with its bus
endpoint, a self-checking UVVM testbench, C, C++ and Python headers, an IPBus
address table and LaTeX documentation.

bust supports six buses: AXI4-Lite, IPBus, SBI, Avalon-MM, Wishbone and APB.

```bash
pip install bust
bust my_module.json -o out
```

## Why bust

**Your design sees registers by name.** The generated module hands every field
to your logic through two VHDL records, `to_hw` and `from_hw`. You write
`to_hw.ctrl.enable`, not a bit slice of a data bus, and enumerated fields
arrive as VHDL enumeration types.

**One register map, every bus.** Each bus is a thin endpoint in front of the
same register file. Moving a module from AXI4-Lite to Avalon-MM changes one
word in the JSON and leaves your logic untouched.

**Access modes beyond read and write.** Fields can clear on read, set or clear
on write, pulse for one cycle, or be set and cleared by hardware, with the
same keywords as SystemRDL. bust generates the logic and the checks for each.

**Software and documentation stay in step.** The headers, the IPBus address
table and the documentation come from the same file as the VHDL, so they
cannot drift apart.

**Tested output.** Every generated module comes with a testbench that checks
its registers through the bus, and the bust repository simulates the generated
testbench of every bus in CI.

## Documentation

- [Getting started](getting-started.md): install bust, describe a module,
  generate it and connect it to your design.
- [Register map format](register-map-format.md): every key of the JSON file.
- [Access modes](access-modes.md): what software and hardware can do with each
  field.
- [Buses](buses.md): the ports and protocol details of each bus.
- [Generated HDL](generated-hdl.md): the generated files, the records and how
  to instantiate the module.
- [Headers and documentation](headers-and-docs.md): the C, C++ and Python
  headers, the IPBus address table and the LaTeX documentation.
- [Testbenches](testbenches.md): what the testbench checks and how to run it.
- [Command line](command-line.md): every option of the `bust` command.
- [Upgrading from 0.14](upgrading.md): what changed in 1.0 and what to update.

```{toctree}
:hidden:

Home <self>
```

```{toctree}
:hidden:
:caption: User guide

getting-started
register-map-format
access-modes
buses
generated-hdl
headers-and-docs
testbenches
command-line
upgrading
```

```{toctree}
:hidden:
:caption: Project

development
Changelog <https://github.com/logvik-org/bust/blob/master/CHANGELOG.md>
GitHub <https://github.com/logvik-org/bust>
PyPI <https://pypi.org/project/bust/>
```
