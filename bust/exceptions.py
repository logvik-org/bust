"""! @package exceptions


"""


def error(msg):
    return "\nERROR:\n{}".format(msg)


class FormatError(Exception):
    """! @brief Raised when input JSON is incorrect."""


class InvalidAddress(RuntimeError):
    """! @brief Raised when a specified address is already assigned to
    other register.

    """

    def __init__(self, reg, addr):
        msg = "When specifying address for register " + reg + ", address "
        msg += hex(addr) + " is already assigned to other register"
        super().__init__(error(msg))


class InvalidRegister(RuntimeError):
    """! @brief Raised when trying to parse a register with lacking or misspelt
    json keys.
    """

    def __init__(self, reg):
        msg = "Could not parse register. Lacking or misspelt JSON keys?\n"
        msg += str(reg)
        super().__init__(error(msg))


class InvalidBusType(RuntimeError):
    """@brief Raised when trying to parse an unspecified or unsupported bus type."""

    def __init__(self, bus_type):
        msg = "Bus type is not valid: {}".format(bus_type)
        super().__init__(error(msg))


class InvalidResetMode(RuntimeError):
    """@brief Raised when an invalid reset mode is set."""

    def __init__(self, reset):
        msg = "Bus reset mode must be either:\n"
        msg += "- 'async' - asynchronous (default)\n"
        msg += "- 'sync'  - synchronous\n"
        msg += "but was: " + reset
        super().__init__(error(msg))


class ModuleDataBitsExceeded(Exception):
    """! @brief Raised when the specified module data bits are exceeded."""

    def __init__(self, register, reglength, mod_data_length):
        msg = "Register length exceeded module data length by "
        msg += str(reglength - mod_data_length)
        msg += " in register " + register + "\n"
        msg += "Module length: " + str(mod_data_length) + "\n"
        msg += "Register length: " + str(reglength)

        super().__init__(msg)


class UndefinedRegisterType(RuntimeError):
    """! @brief Raised when trying to parse a register type that is not supported."""

    def __init__(self, regtype):
        msg = "Could not parse register type: " + regtype
        super().__init__(msg)


class UndefinedFieldType(RuntimeError):
    """! @brief Raised when trying to parse an field type that is not supported."""

    def __init__(self, sig_type):
        msg = "Could not parse field type: " + sig_type
        super().__init__(msg)


class InvalidRegisterFormat(RuntimeError):
    """! @brief Raised when register has some unspecified format error."""

    def __init__(self, msg):
        msg = "Invalid register format: " + msg
        super().__init__(msg)


class InvalidFieldFormat(RuntimeError):
    """! @brief Raised when field format is wrong."""

    def __init__(self, msg):
        msg = "Invalid field format: " + msg
        super().__init__(msg)


class InvalidStallValue(RuntimeError):
    """! @brief Raised when stall value is wrong."""

    def __init__(self, val):
        msg = "Invalid stall value: {}. Must be between 2 and 255.".format(val)
        super().__init__(msg)
