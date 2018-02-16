"""! @package utils


"""
import re
import json
import os

spaces_in_tab = 2


def indent_string(string, tabs=1, break_line=False):
    """! @brief adds indent spaces to all lines in string
    """

    indent = spaces_in_tab * tabs * (" ")
    # Add indent to every line and recreate string
    string = [indent + line for line in re.split(r"\n", string)]
    string = "\n".join(string)

    # Remove last string if it only contains indent
    string = fix_last_indent_only_line(string, tabs)

    if break_line:
        string += '\n'
    return string


def JSON_parser(filename='module.json'):
    with open(filename) as json_data:
        d = json.load(json_data)
        return d


def fix_last_indent_only_line(string, tabs):
    """! @brief Will edit the last line if it only contains indentation to an 
    empty string
    """
    string_list = re.split(r"\n", string)
    if string_list[-1] == (spaces_in_tab * tabs * (" ")):
        string_list[-1] = ''

    string = "\n".join(string_list)
    return string


def compare_JSON(json1, json2, raise_error=False):
    """! @brief Will compare two JSON strings, and return False if they differ. An
    extra argument can be used to force the function to raise an error with the line
    the difference was observed.
    """
    for linenumber, (line1, line2) in enumerate(zip(json1.splitlines(),
                                                    json2.splitlines())):
        if (line1 != line2):
            if raise_error:
                raise Exception("JSON differs at line: " + str(linenumber))
            return False

    return True


def write_string_to_file(string, output_file, output_dir):
    """! @brief Write string to file

    """

    # Create output directory if it does not exist
    if output_dir is not None:
        os.makedirs(output_dir, 0o777, True)
        joined = os.path.join(output_dir, output_file)
    else:
        joined = output_file

    print('Writing string to ' + joined)

    with open(joined, 'w') as strfile:
        strfile.write(string)


def cont():
        try:
            input("Press enter to continue...")
        except SyntaxError:
            pass


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


def get_int(msg, base=10, range_min=None, range_max=None, range_min_msg=None, range_max_msg=None,
            default=None):
    while True:
        try:
            s = input(msg)
            if s == '' and default is not None:
                i = default
            else:
                i = int(s, base)
            if range_min is not None and i < range_min:
                if range_min_msg is None:
                    print("Integer must be at least " + str(range_min))
                else:
                    print(range_min_msg)
            elif range_max is not None and i > range_max:
                if range_max_msg is None:
                    print("Integer can't be larger than " + str(range_max))
                else:
                    print(range_max_msg)
            else:
                return i
        except Exception:
            print("That is not a valid integer...")


def get_list_choice(msg, ls, case=None, default=None):
    while True:
        try:
            print(msg)
            for i, element in enumerate(ls):
                if default is not None and i == default:
                    print(str(i+1) + ': ' + element.upper() + ' - default')
                else:
                    print(str(i+1) + ': ' + element)
            tmp = input('Select by number: ')
            if default is not None and tmp == '':
                select = default+1
            else:
                select = int(tmp)
            if select < 1 or select > len(ls):
                print(str(select) + ' is not a valid choice...')
            else:
                if case == 'lower':
                    return ls[select-1].lower()
                elif case == 'upper':
                    return ls[select-1].upper()
                else:
                    return ls[select-1]
        except Exception as e:
            print('That is not a valid choice...')


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def add_line_breaks(string, min_length):
    """! @brief Adds line breaks on the next space after the minimum length of a line"""
    requirement = min_length
    replace = False
    positions = []
    for i, char in enumerate(string):
        if i > requirement:
            replace = True
        if replace and char == ' ':
            positions.append(i)
            requirement = i + min_length
            replace = False
    for rep in positions:
        string = string[:rep] + '\n' + string[rep + 1:]

    return string


def is_mixed(string):
    upper = False
    lower = False
    for letter in string:
        if letter.isupper():
            upper = True
        elif letter.islower():
            lower = True

    return upper and lower
