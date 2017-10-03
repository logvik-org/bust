"""! @package utils


"""
import re
import json


spacesInTab = 2

def indentString(string, tabs=1, breakLine=False):
    """! @brief adds indent spaces to all lines in string
    """
   
    indent = spacesInTab*tabs * (" ")
    # Add indent to every line and recreate string
    string = [ indent + line for line in re.split(r"\n", string) ]
    string = "\n".join(string)

    # Remove last string if it only contains indent
    string = fixLastIndentOnlyLine(string, tabs)
    
    if breakLine:
        string += '\n'
    return string

def jsonParser(filename='module.json'):
    with open(filename) as json_data:
        d = json.load(json_data)
        return d

def fixLastIndentOnlyLine(string, tabs):
    """! @brief Will edit the last line if it only contains indentation to an empty string
    """
    stringList = re.split(r"\n", string)
    if stringList[-1] == (spacesInTab*tabs*(" ")):
        stringList[-1] = ''
        
    string = "\n".join(stringList)
    return string

