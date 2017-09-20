"""! @package utils


"""
import re
import json


spacesInTab = 2

def indentString(string, tabs=1):
    """! @brief adds indent spaces to all lines in string
    """
   
    indent = spacesInTab*tabs * (" ")
    # Add indent to every line and recreate string
    string = [ indent + line for line in re.split(r"\n", string) ]
    string = "\n".join(string)
    return string

def jsonParser(filename='module.json'):
    with open(filename) as json_data:
        d = json.load(json_data)
        return d
