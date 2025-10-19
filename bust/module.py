"""@package module
Contains the Module class and relevant exceptions

"""

import logging
import json
from collections import OrderedDict
from typing import Dict, Any, List, Optional

from bust.enums import RegisterMode, RegisterType
from bust.exceptions import InvalidAddress, InvalidRegister
from bust.module_vhdl_gen import ModuleVHDLGen
from bust.register import Register
from bust.utils import indent_string
from bust.vhdl_util import is_unique, is_valid_VHDL
from bust.config_wrapper import ConfigWrapper


class Module:
    """! @brief Managing module information

    Contain the name of the module, the bus type and addr and data width specification +
    description of the module.
    """

    def __init__(self, mod: Dict[str, Any], bus: Any, settings: Any) -> None:
        """! @brief"""

        self.logger = logging.getLogger(__name__)

        self.bus = bus
        self.settings = settings
        self.registers: List[Any] = []
        self.addresses: List[int] = []

        self._config = ConfigWrapper(
            mod,
            required_keys=[
                "name",
            ],
            defaults={
                "description": "",
                "version": "",
                "git_hash": None,
                "byte_addressable": bus.bus_type == "axi",
            },
        )

        self.name = self._config.require("name")
        is_valid_VHDL(self.name)

        # Store some config values for easy access
        self.description = self._config.get("description")
        self.version = self._config.get("version")
        self.git_hash = self._config.get("git_hash")  # Currently not used
        self.byte_addressable = self._config.get("byte_addressable")

        self.addr_width = bus.addr_width
        self.data_width = bus.data_width

        for reg in mod["register"]:
            if "stall_cycles" in reg and bus.bus_type != "ipbus":
                raise NotImplementedError(
                    "Stall cycles has not been implemented for other buses than IPBus..."
                )
            self.add_register(reg)

    def add_register(self, reg: Dict[str, Any]) -> None:
        if "address" in reg:
            addr = int(reg["address"], 16)
            if not self.is_address_free(addr):
                raise InvalidAddress(reg["name"], addr)
            if self.is_address_out_of_range(addr):
                raise RuntimeError(
                    "Address " + hex(addr) + " is definitely out of range..."
                )
            self.addresses.append(addr)
            try:
                self.registers.append(Register(reg, addr, self.name, self.data_width))
            except Exception as e:
                self.logger.error(str(e))
                raise InvalidRegister(reg) from e

        else:
            addr = self.get_next_address()
            self.addresses.append(addr)
            self.registers.append(Register(reg, addr, self.name, self.data_width))

    def get_next_address(self) -> int:
        """! @brief Will get the next address based on the byte-addressed scheme"""
        addr = 0
        found_addr = False
        while not found_addr:
            if self.is_address_out_of_range(addr):
                raise RuntimeError(
                    "Address " + hex(addr) + " is definitely out of range..."
                )
            if self.is_address_free(addr):
                self.addresses.append(addr)
                return addr
            else:
                if self.byte_addressable:
                    addr += (
                        self.data_width // 8
                    )  # force integer division to prevent float
                else:
                    addr += 1
        raise RuntimeError("Failed to find available address - this should never happen")

    def is_address_out_of_range(self, addr: int) -> bool:
        """Returns True if address is out of range, False if not"""

        if addr > pow(2, self.addr_width) - 1:
            return True

        return False

    def is_address_free(self, addr: int) -> bool:
        """Returns True if address is not been used in the module, False if it already taken"""
        for address in self.addresses:
            if address == addr:
                return False
        # If loop completes without matching addresses
        return True

    def is_address_byte_based(self, addr: int) -> bool:
        """Returns True if address is divisible by number of bytes in module data width"""

        if addr % (self.data_width / 8) == 0:
            return True
        else:
            return False

    def update_addresses(self) -> None:
        self.addresses = []
        for reg in self.registers:
            addr = self.get_next_address()
            self.addresses.append(addr)
            reg.address = addr

    @property
    def num_ro_regs(self) -> int:
        return sum(1 for reg in self.registers if reg.mode == RegisterMode.RO)

    @property
    def num_rw_regs(self) -> int:
        return sum(1 for reg in self.registers if reg.mode == RegisterMode.RW)

    @property
    def num_pulse_regs(self) -> int:
        return sum(1 for reg in self.registers if reg.mode == RegisterMode.PULSE)

    def has_stall_regs(self) -> bool:
        if len([reg for reg in self.registers if reg.stall]) > 0:
            return True
        else:
            return False

    def __str__(self) -> str:
        string: str = "Name: " + self.name + "\n"
        string += "Address width: " + str(self.addr_width) + "\n"
        string += "Data width: " + str(self.data_width) + "\n"
        string += "Description: " + str(self.description) + "\n\n"
        string += "Registers: \n"
        for i, reg in enumerate(self.registers):
            indented: str = indent_string(str(reg), 1)
            string += indented
        result: str = string
        return result

    def return_JSON(self, include_address: bool = False) -> str:
        """! @brief Returns JSON string"""
        dic = OrderedDict()
        mod = OrderedDict()
        dic["settings"] = self.settings.return_JSON()
        dic["bus"] = self.bus.return_JSON()
        dic["module"] = OrderedDict()

        mod["name"] = self.name
        if self.version is not None:
            mod["version"] = self.version
        mod["description"] = self.description
        if self.git_hash is not None:
            mod["git_hash"] = self.git_hash

        mod["register"] = []

        for _, reg in enumerate(self.registers):
            reg_dic = OrderedDict()

            reg_dic["name"] = reg.name
            reg_dic["mode"] = reg.mode.value
            if reg.mode == RegisterMode.PULSE:
                reg_dic["pulse_cycles"] = reg.pulse_cycles
            reg_dic["type"] = reg.type.value

            if include_address:
                reg_dic["address"] = str(hex(reg.address))

            if (
                reg.type != RegisterType.DEFAULT
                and reg.type != RegisterType.FIELDS
                and reg.type != RegisterType.SL
            ):
                reg_dic["width"] = reg.width

            if reg.type != RegisterType.FIELDS:
                reg_dic["reset"] = reg.reset

            if reg.stall is True:
                reg_dic["stall_cycles"] = reg.stall_cycles

            if reg.type == RegisterType.FIELDS and len(reg.fields) > 0:
                reg_dic["fields"] = []
                for field in reg.fields:
                    reg_dic["fields"].append(field.return_dic())

            reg_dic["description"] = reg.description

            mod["register"].append(reg_dic)

        dic["module"] = mod

        s = json.dumps(dic, indent=4)
        s += "\n"

        return s

    def return_module_pkg_VHDL(self) -> str:
        gen_obj = self._get_vhdl_gen_obj()
        result: str = gen_obj.return_module_pkg_VHDL(self)
        return result

    def return_module_VHDL(self) -> str:
        gen_obj = self._get_vhdl_gen_obj()
        result: str = gen_obj.return_module_VHDL(self)
        return result

    def get_instantiation(self, instance_name: str, intern_out: bool = False) -> str:
        """Also a VHDL method."""
        gen_obj = self._get_vhdl_gen_obj()
        result: str = gen_obj.get_instantiation(self, instance_name, intern_out)
        return result

    def _get_vhdl_gen_obj(self) -> ModuleVHDLGen:
        o = ModuleVHDLGen(
            name=self.name,
            bus_gen=self.bus.get_VHDL_generator(),
            regs=self.registers,
            data_width=self.data_width,
            addr_width=self.addr_width,
        )
        return o
