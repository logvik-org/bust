from cursesmenu import CursesMenu
from cursesmenu.items import FunctionItem
from collections import OrderedDict
from prettytable import PrettyTable

from uart.utils import JSON_parser
from uart.utils import cont
from uart.utils import is_int
from uart.utils import clear_screen
from uart.utils import write_string_to_file
from uart.module import Module
from uart.bus import Bus


class Editor(object):
    """Documentation for Editor

    """
    def __init__(self, edit, jsonfile, output_dir='output/'):
        self.jsonfile = jsonfile
        self.output_dir = output_dir
        self.recently_saved = False

        if edit:
            # Load the specified JSON file
            try:
                json = JSON_parser(jsonfile)
                self.bus = Bus(json['bus'])
                self.mod = Module(json, self.bus)
                self.recently_saved = True
            except Exception as e:
                print('An unresolvable error has occurred:')
                print(str(e))
                print('Exiting...')
                exit()
        else:
            bus_dic = OrderedDict()
            while True:
                try:
                    # import ipdb; ipdb.set_trace()
                    print('Choose a bus type: ')
                    for i, bus in enumerate(Bus.supported_bus):
                        print(str(i+1) + ': ' + bus)
                    select = int(input('Select by number: '))
                    if select < 1 or select > len(Bus.supported_bus):
                        print(str(i) + ' is not a valid choice...')
                    else:
                        break
                except Exception:
                    print('That is not a valid choice...')
                        
            bus_dic['type'] = 'axi'
            bus_dic['addr_width'] = 32
            bus_dic['data_width'] = 32
            bus_dic['reset'] = 'async'
            self.bus = Bus(bus_dic)
            
            # Get name, addr_width, data_width and description
            mod = OrderedDict()
            mod['name'] = input('Enter a module name: ')
            '''! @todo Add int check'''
            mod['addr_width'] = 32
            mod['data_width'] = 32
            mod['description'] = input('Enter a description for the module: ')
            mod['register'] = []

            
            self.mod = Module(mod, self.bus)

    def show_menu(self):
        self.menu = CursesMenu('uart - Module Editor', self.set_subtitle())

        self.menu.append_item(FunctionItem('Edit name', self.edit_name))
        self.menu.append_item(FunctionItem('Edit base address', self.edit_baseaddr))
        self.menu.append_item(FunctionItem('List registers', self.list_registers))
        self.menu.append_item(FunctionItem('Add new register', self.add_register))
        self.menu.append_item(FunctionItem('Remove register', self.remove_register))
        self.menu.append_item(FunctionItem('Update addresses', self.update_addresses))
        self.menu.append_item(FunctionItem('Save JSON', self.save_JSON))
        self.menu.show()

    def update_menu(self):
        self.menu.subtitle = self.set_subtitle()

    def edit_name(self):
        print('Change the module name from current: ' + self.mod.name)
        self.mod.name = input('Enter new name: ')
        self.recently_saved = False
        self.update_menu()

    def edit_baseaddr(self):
        print('Change the module base address from current: ' + str(hex(self.mod.baseaddr)))
        self.mod.baseaddr = int(input('Enter new base address (in hex): 0x'), 16)
        self.recently_saved = False
        self.update_menu()
        
    def return_registers(self):
        while True:
            clear_screen()
            if len(self.mod.registers) < 1:
                print('No registers created at this point...')
                cont()
                return
            else:
                table = PrettyTable()
                table.field_names = ['#', 'Name', 'Mode', 'Address', 'Type', 'Length', 'Reset', 'Description']
                for i, reg in enumerate(self.mod.registers):
                    table.add_row([i, reg.name, reg.mode, hex(reg.address), reg.sig_type, reg.length,
                                   reg.reset, reg.description])
                return(table)

    def list_registers(self):
        table = self.return_registers()
        if table is None:
            return
        print(table)
        print('\nEnter the register number for register details, or q to quit...')
        while True:
            choice = input('Choice: ')
            if self.valid_register_input(choice):
                break
            else:
                print(choice + ' is not a valid choice')
        if choice == 'q':
            return
        else:
            clear_screen()
            self.print_register(int(choice), table)
            cont()

    def print_register(self, reg_num, table):
        reg = self.mod.registers[reg_num]
        print(table.get_string(start=reg_num, end=(reg_num+1)))

        if len(reg.fields) > 0:
            print('\nFields:')
            table_fields = PrettyTable()
            table_fields.field_names = ['#', 'Name', 'Type', 'Position', 'Length', 'Reset', 'Description']
            for i, field in enumerate(reg.fields):

                table_fields.add_row([i, field.name, field.sig_type, field.get_pos_str(), field.length,
                                      field.reset, field.description])

            print(table_fields)

    def add_register(self):
        reg = OrderedDict()

        print('Input register information: ')
        try:
            reg['name'] = input('Name: ')
            reg['description'] = input('Description: ')
            while True:
                try:
                    mode = int(input('Mode (0 = RW, 1 = RO): '))
                    if mode == 0:
                        reg['mode'] = 'rw'
                        break
                    elif mode == 1:
                        reg['mode'] = 'ro'
                        break
                    else:
                        print(str(mode) + ' is not a valid choice...')
                except Exception:
                    print('That is not a valid choice...')

            fields = []
            while True:
                field_dic = OrderedDict()
                add_fields = input('Do you want to add a field? (Y/n): ')
                if add_fields.upper() == 'N':
                    break
                elif add_fields.upper() == 'Y' or add_fields == '':
                    field_dic['name'] = input('Field name: ')
                    while True:
                        field_dic['type'] = input('Field type (sl/slv): ')
                        if field_dic['type'] != 'sl' and field_dic['type'] != 'slv':
                            print(field_dic['type'] + ' is not a valid choice...')
                        else:
                            break

                    if field_dic['type'] == 'slv':
                        while True:
                            try:
                                field_dic['length'] = int(input('Field length: '))
                                break
                            except Exception:
                                print('That is not an integer...')

                    else:
                        field_dic['length'] = 1

                    while True:
                        field_dic['reset'] = input('Field reset (default=0x0): ')

                        if field_dic['reset'] == '':
                            field_dic['reset'] = '0x0'
                            break
                        else:
                            try:
                                field_dic['reset'] = hex(int(field_dic['reset'], 16))
                                break
                            except Exception:
                                print(field_dic['reset'] + ' is not a valid reset value...')

                    field_dic['description'] = input('Field description: ')

                    fields.append(field_dic)

                else:
                    print(add_fields + ' is not a valid choice...')

            if len(fields) > 0:
                print('Register is of type: "fields"')
                reg['type'] = 'fields'
                reg['fields'] = fields

            else:
                while True:

                    reg['type'] = input('Type (DEFAULT/slv/sl): ')
                    if reg['type'] in ['default', 'slv', 'sl']:
                        break
                    elif reg['type'] == '':
                        reg['type'] = 'default'
                        break
                    else:
                        print(reg['type'] + ' is not a valid register type...')

            if reg['type'] == 'slv':
                while True:
                    try:
                        reg['length'] = int(input('Length: '))
                        break
                    except Exception:
                        print('That is not a valid length...')

            if input('Auto-assign address? (Y/n): ').upper() == 'N':
                while True:
                    try:
                        reg['address'] = input('Address (hex): ')
                        reg['address'] = hex(int(reg['address'], 16))
                        break

                    except Exception:
                        print(reg['address'] + ' is not a valid address...')

            if reg['type'] != 'fields':
                while True:
                    reg['reset'] = input('Reset (default=0x0): ')

                    if reg['reset'] == '':
                        reg['reset'] = '0x0'
                        break
                    else:
                        try:
                            reg['reset'] = hex(int(reg['reset'], 16))
                            break
                        except Exception:
                            print(reg['reset'] + ' is not a valid reset value...')

            table = PrettyTable()
            table.field_names = ['#', 'Name', 'Mode', 'Address', 'Type', 'Length', 'Reset', 'Description']

            # Table values based on what values exists
            table_name = reg['name']
            table_mode = reg['mode']

            if 'address' in reg:
                table_address = reg['address']
            else:
                table_address = 'auto'

            table_type = reg['type']

            if reg['type'] == 'fields':
                table_length = 'auto'
            elif 'length' in reg:
                table_length = reg['length']
            else:
                table_length = self.mod.bus.data_width

            if reg['type'] == 'fields':
                table_reset = 'auto'
            elif 'reset' in reg:
                table_reset = reg['reset']
            else:
                table_reset = 'auto'

            table_description = reg['description']

            table.add_row([len(self.mod.registers), table_name, table_mode, table_address, table_type,
                           table_length, table_reset, table_description])

            print(table)

            if 'fields' in reg:
                print('\nFields:')
                table_fields = PrettyTable()
                table_fields.field_names = ['#', 'Name', 'Type', 'Length', 'Reset', 'Description']
                for i, field in enumerate(reg['fields']):

                    table_fields.add_row([i, field['name'], field['type'], field['length'],
                                          field['reset'], field['description']])

                print(table_fields)

            if input('Confirm creation of register? (Y/n): ').upper() != 'N':
                self.mod.add_register(reg)

                self.recently_saved = False
                self.update_menu()
            else:
                return

        except KeyboardInterrupt:
            print('\nAdding register aborted!')
            cont()

        except Exception as e:
            print('\nAdding register failed!')
            print(str(e))
            cont()

    def remove_register(self):
        table = self.return_registers()
        if table is None:
            return
        print(table)
        print('\nEnter the register number for removal, or q to quit...')
        while True:
            choice = input('Choice: ')
            if self.valid_register_input(choice):
                break
            else:
                print(choice + ' is not a valid choice')
        if choice == 'q':
            return
        else:
            clear_screen()
            self.print_register(int(choice), table)

            if input('Are you sure you want to delete this register? (y/N): ').upper() == 'Y':
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
        print('Saving ' + self.jsonfile + ' ...')

        # Get JSON with addresses
        json = self.mod.print_JSON(True)
        try:
            write_string_to_file(json, self.jsonfile, None)
        except Exception:
            print('Saving failed...')
            cont()
            return

        self.recently_saved = True
        cont()
        self.update_menu()

    def set_subtitle(self):
        if self.recently_saved:
            s = ' - SAVED'
        else:
            s = ' - NOT SAVED'
        string = self.mod.name
        string += ' / ' + str(self.mod.addr_width)
        string += ' / ' + str(self.mod.data_width)
        string += ' / ' + str(hex(self.mod.baseaddr))
        string += s
        return string

    def valid_register_input(self, s):
        if s == 'q':
            return True
        elif is_int(s):
            index = int(s)
            for i, reg in enumerate(self.mod.registers):
                if index == i:
                    return True
        return False
