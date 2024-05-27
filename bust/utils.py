"""! @package utils


"""
import re
import json
import os
from functools import reduce
import logging

spaces_in_tab = 2

logger = logging.getLogger(__name__)


def indent_string(string, tabs=1, break_line=False):
    """! @brief adds indent spaces to all lines in string"""

    indent = spaces_in_tab * tabs * (" ")
    # Add indent to every line and recreate string
    string = [indent + line for line in re.split(r"\n", string)]

    # Remove indent in empty lines
    for i, s in enumerate(string):
        if s == indent:
            string[i] = ""
    string = "\n".join(string)

    # Remove last string if it only contains indent
    string = fix_last_indent_only_line(string, tabs)

    if break_line:
        string += "\n"
    return string


def json_parser(filename="module.json"):
    with open(filename) as json_data:
        d = json.load(json_data)
        return d


def fix_last_indent_only_line(string, tabs):
    """! @brief Will edit the last line if it only contains indentation to an
    empty string
    """
    string_list = re.split(r"\n", string)
    if string_list[-1] == (spaces_in_tab * tabs * (" ")):
        string_list[-1] = ""

    string = "\n".join(string_list)
    return string


def compare_JSON(json1, json2, raise_error=False):
    """! @brief Will compare two JSON strings, and return False if they differ. An
    extra argument can be used to force the function to raise an error with the line
    the difference was observed.
    """
    for linenumber, (line1, line2) in enumerate(
        zip(json1.splitlines(), json2.splitlines())
    ):
        if line1 != line2:
            if raise_error:
                raise Exception("JSON differs at line: " + str(linenumber))
            return False

    return True


def write_string_to_file(string, output_file, output_dir, force_overwrite=False):
    """! @brief Write string to file"""

    # Make sure output directory exists
    if not os.path.isdir(output_dir):
        raise RuntimeError("Output dir does not exist: {}".format(output_dir))

    joined = os.path.join(output_dir, output_file)

    # Check if file exist
    if os.path.isfile(joined):
        if (
            not force_overwrite
            and input("Do you want to overwrite " + joined + "? (y/N):").upper() != "Y"
        ):
            logger.warning("Did not write " + joined)
            return

    logger.debug("Writing string to " + joined)

    with open(joined, "w") as strfile:
        strfile.write(string)


def update_module_top_level(existing_file, new_top_level):
    # Check if file exists at all...
    if os.path.isfile(existing_file):
        # Read the file and get the user edited parts...
        string_list = analyze_top_level_file(existing_file)
        string = restore_user_in_top_level(string_list, new_top_level)
        if (
            input("Preview updated top-level before writing to file? (y/N): ").upper()
            == "Y"
        ):
            print(string)

        if (
            input("Are you sure want to update " + existing_file + "? (Y/n): ").upper()
            == "N"
        ):
            raise Exception("Cancelled update. Will keep existing top-level module.")
        else:
            return string
    else:
        logger.warning("Top-level file does not exist. Cannot update...")
        return new_top_level


def analyze_top_level_file(existing_file):
    string_list = [""] * 5
    list_num = 0
    with open(existing_file) as infile:
        copy = False
        for line in infile:
            if line.strip() == "-- User Libraries Start":
                copy = True
                list_num = 0
            elif line.strip() == "-- User Libraries End":
                copy = False
            elif line.strip() == "-- User Generics Start":
                copy = True
                list_num = 1
            elif line.strip() == "-- User Generics End":
                copy = False
            elif line.strip() == "-- User Ports Start":
                copy = True
                list_num = 2
            elif line.strip() == "-- User Ports End":
                copy = False
            elif line.strip() == "-- User Architecture Start":
                copy = True
                list_num = 3
            elif line.strip() == "-- User Architecture End":
                copy = False
            elif line.strip() == "-- User Logic Start":
                copy = True
                list_num = 4
            elif line.strip() == "-- User Logic End":
                copy = False
            elif copy:
                string_list[list_num] = string_list[list_num] + line

    return string_list


def restore_user_in_top_level(user, new_top_level):

    new_top_lines = splitkeepsep(new_top_level, "\n")

    top_lines_with_user = []
    last_was_marker = False
    for line in new_top_lines:
        if not last_was_marker:
            top_lines_with_user.append(line)
        last_was_marker = False
        if line.strip() == "-- User Libraries Start":
            top_lines_with_user += splitkeepsep(user[0], "\n")
            last_was_marker = True
        if line.strip() == "-- User Generics Start":
            top_lines_with_user += splitkeepsep(user[1], "\n")
            last_was_marker = True
        if line.strip() == "-- User Ports Start":
            top_lines_with_user += splitkeepsep(user[2], "\n")
            last_was_marker = True
        if line.strip() == "-- User Architecture Start":
            top_lines_with_user += splitkeepsep(user[3], "\n")
            last_was_marker = True
        if line.strip() == "-- User Logic Start":
            top_lines_with_user += splitkeepsep(user[4], "\n")
            last_was_marker = True

    return "".join(top_lines_with_user)


def splitkeepsep(s, sep):
    return reduce(
        lambda acc, elem: acc[:-1] + [acc[-1] + elem] if elem == sep else acc + [elem],
        re.split("(%s)" % re.escape(sep), s),
        [],
    )


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


def get_int(
    msg,
    base=10,
    range_min=None,
    range_max=None,
    range_min_msg=None,
    range_max_msg=None,
    default=None,
):
    while True:
        try:
            s = input(msg)
            if s == "" and default is not None:
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
                    print(str(i + 1) + ": " + element.upper() + " - default")
                else:
                    print(str(i + 1) + ": " + element)
            tmp = input("Select by number: ")
            if default is not None and tmp == "":
                select = default + 1
            else:
                select = int(tmp)
            if select < 1 or select > len(ls):
                print(str(select) + " is not a valid choice...")
            else:
                if case == "lower":
                    return ls[select - 1].lower()
                elif case == "upper":
                    return ls[select - 1].upper()
                else:
                    return ls[select - 1]
        except Exception as e:
            print("That is not a valid choice...")


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def add_line_breaks(string, min_length):
    """! @brief Adds line breaks on the next space after the minimum length of a line"""
    requirement = min_length
    replace = False
    positions = []
    for i, char in enumerate(string):
        if i > requirement:
            replace = True
        if replace and char == " ":
            positions.append(i)
            requirement = i + min_length
            replace = False
    for rep in positions:
        string = string[:rep] + "\n" + string[rep + 1 :]

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
