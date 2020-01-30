"""! @package exceptions


"""


class FormatError(Exception):
    """! @brief Raised when input JSON is incorrect


    """


class InvalidAddress(RuntimeError):
    """! @brief Raised when a specified address is already assigned to
    other register

    """

    def __init__(self, reg, addr):
        msg = "\nFAILURE:\n"
        msg += "When specifying address for register " + reg + ", address "
        msg += hex(addr) + " is already assigned to other register"
        super().__init__(msg)


class InvalidRegister(RuntimeError):
    """! @brief Raised when trying to parse a register with lacking or misspelt
    json keys
    """

    def __init__(self, reg):
        msg = "\nFAILURE:\n"
        msg += "Could not parse register. Lacking or misspelt JSON keys?\n"
        msg += str(reg)
        super().__init__(msg)
