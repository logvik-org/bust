from cursesmenu import CursesMenu
from cursesmenu.items import FunctionItem
from utils import jsonParser
from utils import cont
from utils import isInt
from utils import clearScreen
from exceptions import UndefinedEntryType
from module import Module
from module import Bus
from collections import OrderedDict
from prettytable import PrettyTable


class Editor(object):
    """Documentation for Editor

    """
    def __init__(self, edit, jsonfile, outputDir='output/', bus=None):

        self.jsonfile = jsonfile
        self.outputDir = outputDir
        self.recently_saved = False
        if bus is None:
            bus = {'bus_type': 'axi', 'data_width': 32, 'addr_width': 32}
        self.bus = Bus(bus)
        if edit:
            # Load the specified JSON file
            try:
                self.mod = Module(jsonParser(jsonfile), self.bus)
                self.recently_saved = True
            except Exception as e:
                print(str(e))
        else:
            # Get name, addrWidth, dataWidth and description
            print('Please enter some general information about your module.')
            print('All values can be changed at a later stage.')
            mod = OrderedDict()
            mod['name'] = input('Enter a module name: ')
            '''! @todo Add int check'''
            mod['addr_width'] = int(input("Enter the module's address width: "))
            mod['data_width'] = int(input("Enter the module's data width: "))
            mod['description'] = input('Enter a description for the module: ')
            mod['register'] = []
            # import ipdb; ipdb.set_trace()
            self.mod = Module(mod, self.bus)

    def showMenu(self):
        self.menu = CursesMenu('art - Module Editor', self.setSubtitle())

        self.menu.append_item(FunctionItem('Edit name', self.editName))
        self.menu.append_item(FunctionItem('List registers', self.listRegisters))
        self.menu.append_item(FunctionItem('Add new register', self.addRegister))
        self.menu.append_item(FunctionItem('Save JSON', self.saveJSON))
        self.menu.show()

    def updateMenu(self):
        self.menu.subtitle = self.setSubtitle()

    def editName(self):
        print('Change the module name from current: ' + self.mod.name)
        self.mod.name = input('Enter new name: ')
        self.recently_saved = False
        self.updateMenu()

    def listRegisters(self):
        while True:
            clearScreen()
            if len(self.mod.registers) < 1:
                print('No registers created at this point...')
            else:
                table = PrettyTable()
                table.field_names = ['#', 'Name', 'Mode', 'Address', 'Type', 'Reset', 'Description']
                for i, reg in enumerate(self.mod.registers):
                    table.add_row([i, reg.name, reg.mode, hex(reg.address), reg.regtype,
                                   reg.reset, reg.description])
                print(table)

                print('\nEnter the register number for register details, or q to quit...')
                while True:
                    choice = input('Choice: ')
                    if self.validInput(choice):
                        break
                    else:
                        print(choice + ' is not a valid choice')
                if choice == 'q':
                    return
                else:
                    clearScreen()
                    self.printRegister(int(choice), table)

    def printRegister(self, regNum, table):
        reg = self.mod.registers[regNum]
        print(table.get_string(start=regNum, end=(regNum+1)))
        print('\nFields:')
        if len(reg.entries) > 0:
            table_fields = PrettyTable()
            table_fields.field_names = ['#', 'Name', 'Type', 'Position', 'Length', 'Reset', 'Description']
            for i, field in enumerate(reg.entries):

                # Get the position of the field
                if field['type'] == 'sl':
                    pos = str(field['pos_low'])
                elif field['type'] == 'slv':
                    pos = str(field['pos_high']) + ':' + str(field['pos_low'])
                else:
                    raise UndefinedEntryType("Unknown field type: " + field['type'])

                table_fields.add_row([i, field['name'], field['type'], pos, field['length'],
                                      field['reset'], field['description']])

            print(table_fields)

        cont()

    def addRegister(self):
        self.recently_saved = False
        self.updateMenu()

    def saveJSON(self):
        print('Saving ' + self.jsonfile + ' in ' + self.outputDir + ' ...')
        self.recently_saved = True
        print('This does not really save the JSON-file yet...')
        cont()
        self.updateMenu()

    def setSubtitle(self):
        if self.recently_saved:
            s = ' - SAVED'
        else:
            s = ' - NOT SAVED'
        return self.mod.name + ' / ' + str(self.mod.addrWidth) + ' / ' + str(self.mod.dataWidth) + s
    
    def validInput(self, s):
        if s == 'q':
            return True
        elif isInt(s):
            index = int(s)
            for i,reg in enumerate(self.mod.registers):
                if index == i:
                    return True
        return False


