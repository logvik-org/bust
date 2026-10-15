[![Tests](https://github.com/logvik-org/bust/actions/workflows/python_tests.yml/badge.svg)](https://github.com/logvik-org/bust/actions/workflows/python_tests.yml)
[![VHDL simulation](https://github.com/logvik-org/bust/actions/workflows/vhdl_sim.yml/badge.svg)](https://github.com/logvik-org/bust/actions/workflows/vhdl_sim.yml)
[![Docs](https://readthedocs.org/projects/bust/badge/?version=latest)](https://bust.readthedocs.io)
[![PyPI](https://img.shields.io/pypi/v/bust.svg)](https://pypi.org/project/bust/)
[![Python](https://img.shields.io/pypi/pyversions/bust.svg)](https://pypi.org/project/bust/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/logvik-org/bust/blob/master/LICENSE)

# bust

**bust** generates the register file of an FPGA module from a JSON register
map. From one file it writes the VHDL register file with its bus endpoint, a
self-checking UVVM testbench, C, C++ and Python headers, an IPBus address table
and LaTeX documentation.

## Features

- Six buses: [AXI4-Lite](https://developer.arm.com/documentation/ihi0022/latest/),
  [IPBus](https://ipbus.web.cern.ch/), SBI (the UVVM simple bus interface),
  [Avalon-MM](https://www.intel.com/content/www/us/en/docs/programmable/683091/current/introduction-to-the-interface-specifications.html),
  [Wishbone](https://wishbone-interconnect.readthedocs.io/) and
  [APB](https://developer.arm.com/documentation/ihi0024/latest/). Each is a thin
  endpoint in front of the same register file.
- Your design reaches every field by name through the `to_hw` and `from_hw`
  VHDL records, and enumerated fields become VHDL enumeration types.
- Separate software and hardware access per field, with SystemRDL-style side
  effects: clear or set on read, set, clear or toggle on write, single-cycle
  pulses, hardware set and clear, write enables and access strobes.
- The base address is a VHDL generic, so one module can sit at any address.
- A self-checking UVVM testbench for every module, on every bus.
- C, C++ and Python headers, an IPBus address table for uHAL and LaTeX/PDF
  documentation from the same file.

## Installation

bust needs Python 3.9 or newer.

```bash
pip install bust
```

## Usage

```bash
bust FILE [-o DIR] [[[-F | -f] [-d | -p] [-i]] | [-a] | [-c | -e]]
bust --version
bust -h | --help
```

A minimal register map with one control register:

```json
{
  "bus": { "type": "axi", "addr_width": 32, "data_width": 32, "comp_library": "work" },
  "module": {
    "name": "blinky",
    "version": "1.0",
    "description": "LED control.",
    "register": [
      {
        "name": "ctrl", "sw": "rw", "hw": "r", "type": "fields",
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

This writes `out/blinky/` with the VHDL in `hdl/`, the testbench in `tb/`, the
headers in `header/` and the LaTeX documentation in `doc/`. Your logic reads
`to_hw.ctrl.enable` and `to_hw.ctrl.rate` from the generated `blinky` entity.

## Documentation

The full documentation is at [bust.readthedocs.io](https://bust.readthedocs.io):

- [Getting started](https://bust.readthedocs.io/en/latest/getting-started.html)
- [Register map format](https://bust.readthedocs.io/en/latest/register-map-format.html)
- [Access modes](https://bust.readthedocs.io/en/latest/access-modes.html)
- [Buses](https://bust.readthedocs.io/en/latest/buses.html)
- [Upgrading from 0.14](https://bust.readthedocs.io/en/latest/upgrading.html)
- [Development](https://bust.readthedocs.io/en/latest/development.html)

Release notes are in the [changelog](https://github.com/logvik-org/bust/blob/master/CHANGELOG.md).
Report bugs and ideas as [GitHub issues](https://github.com/logvik-org/bust/issues).

## License

Licensed under the **Apache License 2.0**. See [LICENSE](https://github.com/logvik-org/bust/blob/master/LICENSE) and
[NOTICE](https://github.com/logvik-org/bust/blob/master/NOTICE).

## Author

**Ola Groettvik** - [GitHub](https://github.com/olagrottvik)

### AI assistance

bust started as a hand-written tool. Most of the work on 1.0 was done with AI
assistance, with all changes reviewed and tested by the author.
