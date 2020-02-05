"""! @package exceptions


"""

def error(msg):
    return "\nERROR:\n{}".format(msg)


class FormatError(Exception):
    """! @brief Raised when input JSON is incorrect


    """


class InvalidAddress(RuntimeError):
    """! @brief Raised when a specified address is already assigned to
    other register

    """

    def __init__(self, reg, addr):
        msg = "When specifying address for register " + reg + ", address "
        msg += hex(addr) + " is already assigned to other register"
        super().__init__(error(msg))


class InvalidRegister(RuntimeError):
    """! @brief Raised when trying to parse a register with lacking or misspelt
    json keys
    """

    def __init__(self, reg):
        msg = "Could not parse register. Lacking or misspelt JSON keys?\n"
        msg += str(reg)
        super().__init__(error(msg))

class InvalidBusType(RuntimeError):
    """ @brief Raised when trying to parse an unspecified or unsupported bus type

    """
    def __init__(self, bus_type):
        msg = "Bus type is not valid: {}".format(bus_type)
        super().__init__(error(msg))


class InvalidResetMode(RuntimeError):
    """Documentation for InvalidResetMode

    """
    def __init__(self, reset):
        msg = "Bus reset mode must be either:\n"
        msg += "- 'async' - asynchronous (default)\n"
        msg += "- 'sync'  - synchronous\n"
        msg += "but was: " + reset
        super().__init__(error(msg))
