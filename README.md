# axi_slave_gen

Utility for simply creating and modifying AXI Slave modules.

## Concept

The main goal of the project is to able to automatically create and modify AXI slave modules based on a simple definition format. By employing VHDL records the handling of the registers can be completely hidden in a module seperate from the rest of the designers logic. All referring to the registers are done via a record which specifies if the register is read-only or read-write, and also includes the name. All AXI-specific signals are also wrapped in records. This increases the readability of the design as a whole.


### Philosophy
  * Information hiding
  * Naming of registers
  * Seperate read-only and rw registers
  * Easy modification
  

## Getting Started

It is highly recommended to employ virtual environments while tinkering with this project. See below for short howto.

### Requirements

The utility require Python 3. The requirements for running the utility, and a few more, are listed in `requirements.txt`. To install them in your virtual environment run the following command:

`$ pip install -r requirements.txt`

If you are contributing and have added a module to the project, update the requirements by running:

`$ pip freeze > requirements.txt`

### Run

Start the project by simply running the main file:

`$ python art.py`

### Virtual Environment

To create a virtual environment with Python3:

```bash
$ pip install virtualenv
$ cd axi_slave_gen
$ virtualenv env
$ virtualenv -p /usr/bin/python3 env
```

To activate the virtual environment:

```
$ source env/bin/activate
```

When running `python` or `pip` commands, these will now refer to Python 3.

## Contributing

If you have ideas on how to improve the project, please review [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Authors

* [Ola Grøttvik](https://github.com/olagrottvik) - *Initial work

## License

This project is licensed under the MIT license - see [LICENSE](LICENSE) for details.
