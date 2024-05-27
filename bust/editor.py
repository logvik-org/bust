"""@package editor
Contains the Editor class

"""
from cursesmenu import CursesMenu
from cursesmenu.items import FunctionItem
from collections import OrderedDict
from prettytable import PrettyTable

from bust.utils import json_parser
from bust.utils import cont
from bust.utils import is_int
from bust.utils import clear_screen
from bust.utils import write_string_to_file
from bust.utils import get_list_choice
from bust.utils import get_int
from bust.utils import add_line_breaks
from bust.module import Module
from bust.bus import Bus
from bust.register import Register
from bust.field import Field
from bust.vhdl import get_identifier
from bust.settings import Settings


class Editor(object):
    """A console-based menu system for creating and editing module descripting JSON files"""

    def __init__(self, edit, jsonfile, output_dir="output/"):
        """Constructor

        Either reconstructs a module object from JSON, or create a new based on user input
        """
        self.jsonfile = jsonfile
        self.output_dir = output_dir
        self.recently_saved = False

        if edit:
            # Load the specified JSON file
            try:
                json = json_parser(jsonfile)
                self.settings = Settings(jsonfile, json["settings"])
                self.bus = Bus(json["bus"])
                self.mod = Module(json["module"], self.bus, self.settings)
                self.recently_saved = True
            except Exception as e:
                print("An unresolvable error has occurred:")
                print(str(e))
                print("Exiting...")
                exit()
        else:
            bus_dic = OrderedDict()
            bus_dic["type"] = get_list_choice("Choose a bus type: ", Bus.supported_bus)
            bus_dic["addr_width"] = 32
            bus_dic["data_width"] = 32
            bus_dic["reset"] = "async"
            self.bus = Bus(bus_dic)

            # Get name, addr_width, data_width and description
            mod = OrderedDict()
            mod["name"] = get_identifier("Enter a module name: ")

            """! @todo Add int check"""
            mod["addr_width"] = 32
            mod["data_width"] = 32
            mod["description"] = input("Enter a description for the module: ")
            mod["register"] = []

            self.settings = Settings(None, None)
            self.mod = Module(mod, self.bus, self.settings)

    def show_menu(self):
        self.menu = CursesMenu("bust - Module Editor", self.set_subtitle())

        self.menu.append_item(FunctionItem("Edit name", self.edit_name))
        self.menu.append_item(FunctionItem("List registers", self.list_registers))
        self.menu.append_item(FunctionItem("Add new register", self.add_register))
        self.menu.append_item(FunctionItem("Remove register", self.remove_register))
        self.menu.append_item(FunctionItem("Update addresses", self.update_addresses))
        self.menu.append_item(FunctionItem("Save JSON", self.save_JSON))
        self.menu.show()

    def update_menu(self):
        self.menu.subtitle = self.set_subtitle()

    def edit_name(self):
        print("Change the module name from current: " + self.mod.name)
        self.mod.name = get_identifier("Enter a new name: ")
        self.recently_saved = False
        self.update_menu()

    def return_registers(self):
        while True:
            clear_screen()
            if len(self.mod.registers) < 1:
                print("No registers created at this point...")
                cont()
                return
            else:
                table = PrettyTable()
                table.field_names = [
                    "#",
                    "Name",
                    "Mode",
                    "Address",
                    "Type",
                    "Length",
                    "Reset",
                    "Description",
                ]
                for i, reg in enumerate(self.mod.registers):
                    table.add_row(
                        [
                            i,
                            reg.name,
                            reg.mode,
                            hex(reg.address),
                            reg.sig_type,
                            reg.length,
                            reg.reset,
                            add_line_breaks(reg.description, 25),
                        ]
                    )
                return table

    def list_registers(self):
        table = self.return_registers()
        if table is None:
            return
        print(table)
        print("\nEnter the register number for register details, or q to quit...")
        while True:
            choice = input("Choice: ")
            if self.valid_register_input(choice):
                break
            else:
                print(choice + " is not a valid choice")
        if choice == "q":
            return
        else:
            clear_screen()
            self.print_register(int(choice), table)
            cont()

    def print_register(self, reg_num, table):
        reg = self.mod.registers[reg_num]
        print(table.get_string(start=reg_num, end=(reg_num + 1)))

        if len(reg.fields) > 0:
            print("\nFields:")
            table_fields = PrettyTable()
            table_fields.field_names = [
                "#",
                "Name",
                "Type",
                "Position",
                "Length",
                "Reset",
                "Description",
            ]
            for i, field in enumerate(reg.fields):

                table_fields.add_row(
                    [
                        i,
                        field.name,
                        field.sig_type,
                        field.get_pos_str(),
                        field.length,
                        field.reset,
                        add_line_breaks(field.description, 25),
                    ]
                )

            print(table_fields)

    def add_register(self):
        """Adds a register to the module object

        Get user input to create a register that may or may not consists of individual fields
        """
        reg = OrderedDict()
        reg_names = [regs.name for regs in self.mod.registers]
        print("Input register information: ")
        try:
            reg["name"] = get_identifier("Name: ", reg_names)
            reg["description"] = input("Description: ")
            reg["mode"] = get_list_choice(
                "Choose register mode: ", Register.supported_modes, "lower", 0
            )

            fields = []

            width_consumed = 0
            while True:
                field_dic = OrderedDict()
                add_fields = input("Do you want to add a field? (Y/n): ")
                field_names = [field["name"] for field in fields]
                if add_fields.upper() == "N":
                    break
                elif add_fields.upper() == "Y" or add_fields == "":
                    field_dic["name"] = get_identifier("Field name: ", field_names)
                    field_dic["type"] = get_list_choice(
                        "Field type: ", Field.supported_types
                    )

                    if field_dic["type"] == "slv":
                        max_width = self.mod.data_width - width_consumed

                        field_dic["length"] = get_int(
                            "Field length: ",
                            10,
                            1,
                            max_width,
                            "The minimum width of a field is 1!",
                            "The maximum width of this field cannot extend"
                            + " the module data width minus the width already"
                            + " consumed by other fields: "
                            + str(max_width),
                        )
                        width_consumed += field_dic["length"]

                    else:
                        width_consumed += 1
                        field_dic["length"] = 1

                    max_reset = 2 ** field_dic["length"] - 1
                    field_dic["reset"] = hex(
                        get_int(
                            "Field reset in hex (default=0x0): ",
                            16,
                            0x0,
                            max_reset,
                            "The minimum reset value is 0x0",
                            "The maximum reset value is based on the field width, "
                            + "and is "
                            + str(hex(max_reset)),
                            0x0,
                        )
                    )

                    field_dic["description"] = input("Field description: ")

                    fields.append(field_dic)
                    # Check if all available data bits are use
                    if width_consumed == self.mod.data_width:
                        print(
                            "All available bits ("
                            + str(self.mod.data_width)
                            + ") is consumed.\n"
                            + "No more fields can be added to this register.\n"
                        )
                        break
                    elif width_consumed > self.mod.data_width:
                        raise RuntimeError("More bits used by fields than available...")

                else:
                    print(add_fields + " is not a valid choice...")

            if len(fields) > 0:
                reg["type"] = "fields"
                reg["fields"] = fields

            else:
                reg["type"] = get_list_choice(
                    "Register type: ", Register.supported_types, None, 0
                )

            # Make sure reg length is set to help calculate max reset later
            # Registers of field type will get an auto reset based on the field resets
            if reg["type"] == "default":
                reg["length"] = self.mod.data_width
            elif reg["type"] == "sl":
                reg["length"] = 1
            elif reg["type"] == "slv":
                while True:
                    try:
                        reg["length"] = int(input("Length: "))
                        break
                    except Exception:
                        print("That is not a valid length...")

            if input("Auto-assign address? (Y/n): ").upper() == "N":
                # Make sure the address is not out of range and that it is free
                max_address = 2**self.mod.addr_width - 1

                while True:
                    reg["address"] = get_int(
                        "Address in hex: ",
                        16,
                        0x0,
                        max_address,
                        "The minimum address is 0x0",
                        "The maximum address is based on the module address width, "
                        + "and is "
                        + str(hex(max_address)),
                        0x0,
                    )
                    # Perform an extra check of address range, although redundant
                    if self.mod.is_address_out_of_range(reg["address"]):
                        print("Address is out of range...")
                        continue

                    # Check if the address has not been taken
                    if not self.mod.is_address_free(reg["address"]):
                        print(
                            "The chosen address is already assigned to another register..."
                        )
                        continue

                    # Check whether the address is not byte-addressed, and give the user a choice to continue
                    if not self.mod.is_address_byte_based(reg["address"]):
                        choice = input(
                            "The selected address is not byte-based. Continue? (y/N): "
                        )
                        if not choice.upper() == "Y":
                            continue
                    break

            if reg["type"] != "fields":

                max_reset = 2 ** reg["length"] - 1
                reg["reset"] = hex(
                    get_int(
                        "Register reset in hex (default=0x0): ",
                        16,
                        0x0,
                        max_reset,
                        "The minimum reset value is 0x0",
                        "The maximum reset value is based on the register width, "
                        + "and is "
                        + str(hex(max_reset)),
                        0x0,
                    )
                )

            table = PrettyTable()
            table.field_names = [
                "#",
                "Name",
                "Mode",
                "Address",
                "Type",
                "Length",
                "Reset",
                "Description",
            ]

            # Table values based on what values exists
            table_name = reg["name"]
            table_mode = reg["mode"]

            if "address" in reg:
                table_address = reg["address"]
            else:
                table_address = "auto"

            table_type = reg["type"]

            if reg["type"] == "fields":
                table_length = "auto"
            elif "length" in reg:
                table_length = reg["length"]
            else:
                table_length = self.mod.bus.data_width

            if reg["type"] == "fields":
                table_reset = "auto"
            elif "reset" in reg:
                table_reset = reg["reset"]
            else:
                table_reset = "auto"

            table_description = add_line_breaks(reg["description"], 25)

            table.add_row(
                [
                    len(self.mod.registers),
                    table_name,
                    table_mode,
                    table_address,
                    table_type,
                    table_length,
                    table_reset,
                    table_description,
                ]
            )

            print(table)

            if "fields" in reg:
                print("\nFields:")
                table_fields = PrettyTable()
                table_fields.field_names = [
                    "#",
                    "Name",
                    "Type",
                    "Length",
                    "Reset",
                    "Description",
                ]
                for i, field in enumerate(reg["fields"]):

                    table_fields.add_row(
                        [
                            i,
                            field["name"],
                            field["type"],
                            field["length"],
                            field["reset"],
                            field["description"],
                        ]
                    )

                print(table_fields)

            if input("Confirm creation of register? (Y/n): ").upper() != "N":
                self.mod.add_register(reg)

                self.recently_saved = False
                self.update_menu()
            else:
                return

        except KeyboardInterrupt:
            print("\nAdding register aborted!")
            cont()

        except Exception as e:
            print("\nAdding register failed!")
            print(str(e))
            cont()

    def remove_register(self):
        table = self.return_registers()
        if table is None:
            return
        print(table)
        print("\nEnter the register number for removal, or q to quit...")
        while True:
            choice = input("Choice: ")
            if self.valid_register_input(choice):
                break
            else:
                print(choice + " is not a valid choice")
        if choice == "q":
            return
        else:
            clear_screen()
            self.print_register(int(choice), table)

            if (
                input("Are you sure you want to delete this register? (y/N): ").upper()
                == "Y"
            ):
                del self.mod.registers[int(choice)]
                self.recently_saved = False

        self.update_menu()

    def update_addresses(self):
        self.mod.update_addresses()
        print("Addresses are updated..")
        self.recently_saved = False
        self.update_menu()
        cont()

    def save_JSON(self):
        print("Saving " + self.jsonfile + " ...")

        # Get JSON with addresses
        json = self.mod.return_JSON(True)
        try:
            write_string_to_file(json, self.jsonfile, ".")
        except Exception as e:
            print("Saving failed...")
            print(e)
            cont()
            return

        self.recently_saved = True
        cont()
        self.update_menu()

    def set_subtitle(self):
        if self.recently_saved:
            s = " - SAVED"
        else:
            s = " - NOT SAVED"
        string = self.mod.name
        string += " / " + str(self.mod.addr_width)
        string += " / " + str(self.mod.data_width)
        # string += " / " + str(hex(self.mod.baseaddr))
        string += s
        return string

    def valid_register_input(self, s):
        """Returns boolean determining if a choice of register is valid

        The input is first checked against the quit-character, and then checked if it matches any
        valid indexes of the mod.registers list.
        """
        if s.upper() == "Q":
            return True
        elif is_int(s):
            index = int(s)
            for i, reg in enumerate(self.mod.registers):
                if index == i:
                    return True
        return False
