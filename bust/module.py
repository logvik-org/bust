"""@package module
Contains the Module class and relevant exceptions

"""

import json
from collections import OrderedDict

from bust.exceptions import InvalidAddress, InvalidRegister
from bust.module_vhdl_gen import ModuleVHDLGen
from bust.register import Register
from bust.utils import add_line_breaks, indent_string
from bust.vhdl import is_unique, is_valid_VHDL


class Module:
    """! @brief Managing module information

    Contain the name of the module, the bus type and addr and data width specification +
    description of the module.
    """

    def __init__(self, mod, bus, settings):
        """! @brief"""

        self.bus = bus
        self.settings = settings
        self.registers = []
        self.addresses = []

        is_valid_VHDL(mod["name"])
        self.name = mod["name"]
        self.description = mod["description"]
        self.description_with_breaks = add_line_breaks(mod["description"], 25)
        if "version" in mod:
            self.version = mod["version"]
        else:
            self.version = None
        self.git_hash = None  # not used

        self.addr_width = bus.addr_width
        self.data_width = bus.data_width

        if "byte_addressable" in mod:
            if mod["byte_addressable"] == "True":
                self.byte_addressable = True
            else:
                self.byte_addressable = False
        else:
            if self.bus.bus_type == "axi":  # axi usually is byte addressable
                self.byte_addressable = True
            else:
                self.byte_addressable = False

        for reg in mod["register"]:
            if "stall_cycles" in reg and bus.bus_type != "ipbus":
                raise NotImplementedError(
                    "Stall cycles has not been implemented for other buses than IPBus..."
                )
            self.add_register(reg)

    def get_version(self):
        if self.version is None:
            return ""
        else:
            return "Version: {}".format(self.version)

    def add_register(self, reg):
        if self.register_valid(reg):
            if "address" in reg:
                addr = int(reg["address"], 16)
                if self.is_address_free(addr):
                    if self.is_address_out_of_range(addr):
                        raise RuntimeError(
                            "Address " + hex(addr) + " is definitely out of range..."
                        )
                    self.addresses.append(addr)
                    self.registers.append(Register(reg, addr, self.data_width))
                else:
                    raise InvalidAddress(reg["name"], addr)
            else:
                addr = self.get_next_address()
                self.addresses.append(addr)
                self.registers.append(Register(reg, addr, self.data_width))
        else:
            raise InvalidRegister(reg)

    def get_next_address(self):
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

    def is_address_out_of_range(self, addr):
        """Returns True if address is out of range, False if not"""

        if addr > pow(2, self.addr_width) - 1:
            return True

        return False

    def is_address_free(self, addr):
        """Returns True if address is not been used in the module, False if it already taken"""
        for address in self.addresses:
            if address == addr:
                return False
        # If loop completes without matching addresses
        return True

    def is_address_byte_based(self, addr):
        """Returns True if address is divisible by number of bytes in module data width"""

        if addr % (self.data_width / 8) == 0:
            return True
        else:
            return False

    def update_addresses(self):
        self.addresses = []
        for reg in self.registers:
            addr = self.get_next_address()
            self.addresses.append(addr)
            reg.address = addr

    def register_valid(self, reg):
        """Returns True if register is semi-valid. May raise exceptions which must be catched"""

        # Check if all required register keys exists
        if not (
            {"name", "mode", "type", "description"}.issubset(reg)
            or {"name", "mode", "fields", "description"}.issubset(reg)
        ):
            return False

        """Check if name is valid VHDL, if not it will raise an exception which must be
        catched in calling function"""
        is_valid_VHDL(reg["name"])

        """Get a list of the currently used reg names and compare the chosen reg names to this list
        If it is already taken it will raise an exception which must be catched in calling function"""
        reg_names = [r.name for r in self.registers]
        is_unique(reg["name"], reg_names)

        return True

    def count_ro_regs(self):
        return len([reg for reg in self.registers if reg.mode == "ro"])

    def count_rw_regs(self):
        return len([reg for reg in self.registers if reg.mode == "rw"])

    def count_pulse_regs(self):
        return len([reg for reg in self.registers if reg.mode == "pulse"])

    def has_stall_regs(self):
        if len([reg for reg in self.registers if reg.stall]) > 0:
            return True
        else:
            return False

    def __str__(self):
        string = "Name: " + self.name + "\n"
        string += "Address width: " + str(self.addr_width) + "\n"
        string += "Data width: " + str(self.data_width) + "\n"
        string += "Description: " + self.description + "\n\n"
        string += "Registers: \n"
        for i, reg in enumerate(self.registers):
            string += indent_string(str(reg), 1)
        return string

    def return_JSON(self, include_address=False):
        """! @brief Returns JSON string"""
        dic = OrderedDict()
        mod = OrderedDict()
        dic["settings"] = self.settings.return_JSON()
        dic["bus"] = self.bus.return_JSON()
        dic["module"] = OrderedDict()

        mod["name"] = self.name
        mod["description"] = self.description
        if self.version is not None:
            mod["version"] = self.version
        if self.git_hash is not None:
            mod["git_hash"] = self.git_hash

        mod["register"] = []

        for _, reg in enumerate(self.registers):
            reg_dic = OrderedDict()

            reg_dic["name"] = reg.name
            reg_dic["mode"] = reg.mode
            if reg.mode == "pulse":
                reg_dic["pulse_cycles"] = reg.pulse_cycles
            reg_dic["type"] = reg.sig_type

            if include_address:
                reg_dic["address"] = str(hex(reg.address))

            if (
                reg.sig_type != "default"
                and reg.sig_type != "fields"
                and reg.sig_type != "sl"
            ):
                reg_dic["length"] = reg.length

            if reg.sig_type != "fields":
                reg_dic["reset"] = reg.reset

            if reg.sig_type == "fields" and len(reg.fields) > 0:
                reg_dic["fields"] = []
                for field in reg.fields:
                    reg_dic["fields"].append(field.return_dic())

            reg_dic["description"] = reg.description

            mod["register"].append(reg_dic)

        dic["module"] = mod

        s = json.dumps(dic, indent=4)
        s += "\n"

        return s

    def return_module_pkg_VHDL(self):
        gen_obj = self._get_vhdl_gen_obj()
        return gen_obj.return_module_pkg_VHDL()

    def return_module_VHDL(self):
        gen_obj = self._get_vhdl_gen_obj()
        return gen_obj.return_module_VHDL()

    def get_instantiation(self, instance_name, intern_out=False):
        """Also a VHDL method."""
        gen_obj = self._get_vhdl_gen_obj()
        return gen_obj.get_instantiation(instance_name, intern_out)

    def _get_vhdl_gen_obj(self):
        o = ModuleVHDLGen(
            name=self.name,
            bus_gen=self.bus.get_VHDL_generator(),
            regs=self.registers,
            data_width=self.data_width,
            addr_width=self.addr_width,
        )
        return o
