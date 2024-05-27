![Workflow status](https://github.com/olagrottvik/bust/actions/workflows/python_tests.yml/badge.svg)

# bust bus tool

Utility for simply creating and modifying VHDL bus slave modules.

## Concept

The main goal of the project is to able to automatically create and modify VHDL bus slave modules based on a simple definition format.
By employing VHDL records the handling of the registers can be completely hidden in a module separate from the rest of the design.
All referring to the registers are done via a record that specifies if the register is read-only or read-write, and also includes the name.
All bus-specific signals are also wrapped in records. This increases the readability of the design as a whole.

## Bus support

bust currently supports these bus standards:

- [AXI4-lite](https://en.wikipedia.org/wiki/Advanced_eXtensible_Interface#AXI4-Lite)
- [IPBus](https://ipbus.web.cern.ch/ipbus/)

## Requirements

bust is thoroughly tested with python 3.9.18 but should work with the following versions:

- python 3.6.8
- python 3.7
- python 3.8
- python 3.9
- python 3.10
- python 3.11

bust does NOT support python 2.7 and neither should you!

## Getting Started

Install the latest relase by using pip:

`pip install bust`

### Usage

`bust.py FILE [-o DIR]`

`bust.py --version`

`bust.py -h | --help`

## Examples

The examples folder contains JSON files for the bus types supported.
The files are human-readable to the point that you can create your own from this template alone.
The folder also contains the output files generated based on the JSON files.

### Simulation
Simulation scripts are made solely for Modelsim/Questasim. For any other simulators, you need to compile everything yourselves.
All testbenches require UVVM - which can be cloned from their [Github page](https://github.com/UVVM/UVVM).

### IPBus
IPBus requires the bus package file from the [IPBus firmware repo](https://github.com/ipbus/ipbus-firmware) and the custom [IPBus BFM repo](https://github.com/olagrottvik/vip_ipbus).

See the example files for how you point to the specific folders.

## Latest Development Version (Bleeding Edge)

The latest development version can be found in the [dev branch](https://github.com/olagrottvik/bust/tree/dev) on Github. Clone the repo and check out the branch.

`git clone https://github.com/olagrottvik/bust.git`

`cd bust`

`git checkout dev`

`pip install -r requirements.txt`

`python -m bust`



## Release Notes

Release notes can be found on the [Releases page](https://github.com/olagrottvik/bust/releases).


## Contributing

If you have ideas on how to improve the project, please review [CONTRIBUTING.md](CONTRIBUTING.md) for details. Note that we also have a [Code of Conduct](CODE_OF_CONDUCT.md).


## License

This project is licensed under the MIT license - see [LICENSE](LICENSE) for details.
