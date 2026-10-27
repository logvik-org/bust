<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/logo-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/images/logo-light.png">
    <img alt="bust: single source of truth" src="https://raw.githubusercontent.com/logvik-org/bust/master/docs/images/logo-light.png" width="480">
  </picture>
</p>

[![Tests](https://github.com/logvik-org/bust/actions/workflows/python_tests.yml/badge.svg)](https://github.com/logvik-org/bust/actions/workflows/python_tests.yml)
[![VHDL simulation](https://github.com/logvik-org/bust/actions/workflows/vhdl_sim.yml/badge.svg)](https://github.com/logvik-org/bust/actions/workflows/vhdl_sim.yml)
[![Docs](https://readthedocs.org/projects/bust/badge/?version=latest)](https://bust.readthedocs.io)
[![PyPI](https://img.shields.io/pypi/v/bust.svg)](https://pypi.org/project/bust/)
[![Python](https://img.shields.io/pypi/pyversions/bust.svg)](https://pypi.org/project/bust/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/logvik-org/bust/blob/master/LICENSE)

**bust** generates the register file of a register map from a JSON for FPGA or ASIC modules. From one file it writes the VHDL register file with its bus endpoint, a self-checking UVVM testbench, C, C++ and Python headers, and documentation.

## Features

- Six buses: [AXI4-Lite](https://developer.arm.com/documentation/ihi0022/latest/),
  [IPBus](https://ipbus.web.cern.ch/), SBI (the UVVM simple bus interface),
  [Avalon-MM](https://www.intel.com/content/www/us/en/docs/programmable/683091/current/introduction-to-the-interface-specifications.html),
  [Wishbone](https://wishbone-interconnect.readthedocs.io/) and
  [APB](https://developer.arm.com/documentation/ihi0024/latest/).
- Your design reaches every field by name through the `to_hw` and `from_hw` VHDL records, and enumerated fields become VHDL enumeration types.
- Separate software and hardware access per field, with SystemRDL-style side effects:
  - clear or set on read,
  - set, clear or toggle on write,
  - single-cycle pulses,
  - hardware set and clear, write enables and access strobes.
- A self-checking UVVM testbench for every module, on every bus.
- The base address is a VHDL generic, so one module can sit at any or even multiple addresses.
- C, C++ and Python headers, an IPBus address table for uHAL and documentation from the same file.

## Installation

bust needs Python 3.9 or newer.

```bash
pip install bust
```

## Usage

```bash
bust FILE [-o DIR] [[[-f] [-d | -p] [-i]] | [-a] | [-c | -e]]
bust --version
bust -h | --help
```

A minimal register map with one control register with two fields:

```json
{
  "bus": { "type": "axi", "addr_width": 32, "data_width": 32 },
  "module": {
    "name": "blinky",
    "version": "1.0",
    "description": "LED control.",
    "register": [
      {
        "name": "ctrl", "address": "0x0", "sw": "rw", "hw": "r", "type": "fields",
        "description": "LED control.",
        "fields": [
          { "name": "enable", "type": "bit", "description": "Turn the LED on." },
          { "name": "rate", "type": "vector", "width": 4, "description": "Blink rate." }
        ]
      }
    ]
  }
}
```

```bash
bust blinky.json -o out -p
```

This writes `out/blinky/` with the VHDL in `hdl/`, the testbench in `tb/`, the headers in `header/` and the documentation in `doc/`, as HTML, Markdown and LaTeX, plus a PDF when `pdflatex` is installed. `hdl/blinky.vhd` is a starter top level that is yours to edit: bust writes it once and leaves it alone after that. Your logic reads `to_hw.ctrl.enable` and `to_hw.ctrl.rate` from `blinky_axi_endpoint`, which bust regenerates on every run.

## How bust is tested

- The generated files for the example register maps are kept in the repository. Every change is compared with them.
- Every change to the generated VHDL is simulated with `nvc` and `UVVM`. This runs the generated testbench on all six buses, a register map with every class of access mode combination.
- Hand-written reference VHDL and testbenches for all six buses run against the generated VHDL.

## Documentation

The full documentation is at [bust.readthedocs.io](https://bust.readthedocs.io):

- [Getting started](https://bust.readthedocs.io/en/latest/getting-started.html)
- [Register map format](https://bust.readthedocs.io/en/latest/register-map-format.html)
- [Access modes](https://bust.readthedocs.io/en/latest/access-modes.html)
- [Buses](https://bust.readthedocs.io/en/latest/buses.html)
- [Development](https://bust.readthedocs.io/en/latest/development.html)

Release notes are in the [changelog](https://github.com/logvik-org/bust/blob/master/CHANGELOG.md).
Report bugs and ideas as [GitHub issues](https://github.com/logvik-org/bust/issues).

## License

Licensed under the **Apache License 2.0**. See [LICENSE](https://github.com/logvik-org/bust/blob/master/LICENSE) and [NOTICE](https://github.com/logvik-org/bust/blob/master/NOTICE).

## Author

**Ola Groettvik** - [GitHub](https://github.com/olagrottvik)

### AI assistance

bust is mainly a hand-written tool. Some of the code is written with AI assistance. The author reviewed every change, and no change is merged before it passes the checks under `How bust is tested` above.
