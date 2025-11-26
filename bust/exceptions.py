"""Exception classes for bust.

This module defines custom exception types used throughout the bust tool
for error handling during configuration parsing, register validation, and
VHDL generation.
"""


class FormatError(Exception):
    """Raised when input JSON configuration has incorrect format."""


class InvalidAddress(RuntimeError):
    """Raised when a register address conflicts with an existing assignment.

    This exception is raised when attempting to assign a register to an
    address that is already occupied by another register in the module.
    """

    def __init__(self, reg, addr):
        """Initialize InvalidAddress exception.

        Args:
            reg: Name of the register with conflicting address.
            addr: The conflicting address value.
        """
        msg = "When specifying address for register " + reg + ", address "
        msg += hex(addr) + " is already assigned to other register"
        super().__init__(msg)


class InvalidRegister(RuntimeError):
    """Raised when register configuration has missing or invalid keys.

    This exception indicates that a register definition in the JSON
    configuration is missing required keys or has invalid values.
    """

    def __init__(self, reg):
        """Initialize InvalidRegister exception.

        Args:
            reg: Register configuration dictionary.
        """
        name = reg.get("name", "<unknown>")
        msg = f"Could not parse register {name}. Lacking or misspelt JSON keys?\n{reg}"
        super().__init__(msg)


class InvalidBusType(RuntimeError):
    """Raised when bus type is not supported.

    This exception is raised when the configuration specifies a bus type
    that is not in the supported bus types list.
    """

    def __init__(self, bus_type):
        """Initialize InvalidBusType exception.

        Args:
            bus_type: The invalid bus type string.
        """
        msg = "Bus type is not valid: {}".format(bus_type)
        super().__init__(msg)


class InvalidResetMode(RuntimeError):
    """Raised when reset mode is not 'async' or 'sync'."""

    def __init__(self, reset):
        """Initialize InvalidResetMode exception.

        Args:
            reset: The invalid reset mode string.
        """
        msg = "Bus reset mode must be either:\n"
        msg += "- 'async' - asynchronous (default)\n"
        msg += "- 'sync'  - synchronous\n"
        msg += "but was: " + reset
        super().__init__(msg)


class ModuleDataBitsExceeded(Exception):
    """Raised when register width exceeds module data width.

    This exception is raised when a register's total bit width (including
    all fields) exceeds the module's configured data bus width.
    """

    def __init__(self, register, regwidth, mod_data_width):
        """Initialize ModuleDataBitsExceeded exception.

        Args:
            register: Name of the register that exceeds width.
            regwidth: Actual width of the register in bits.
            mod_data_width: Maximum allowed width (module data width).
        """
        msg = "Register width exceeded module data width by "
        msg += str(regwidth - mod_data_width)
        msg += " in register " + register + "\n"
        msg += "Module width: " + str(mod_data_width) + "\n"
        msg += "Register width: " + str(regwidth)

        super().__init__(msg)


class UndefinedRegisterType(RuntimeError):
    """Raised when register type is not recognized.

    This exception is raised when parsing a register with an unsupported
    or misspelled type value.
    """

    def __init__(self, regtype):
        """Initialize UndefinedRegisterType exception.

        Args:
            regtype: The unrecognized register type string.
        """
        msg = "Could not parse register type: " + regtype
        super().__init__(msg)


class UndefinedFieldType(RuntimeError):
    """Raised when field type is not recognized.

    This exception is raised when parsing a field with an unsupported
    or misspelled type value.
    """

    def __init__(self, type):
        """Initialize UndefinedFieldType exception.

        Args:
            type: The unrecognized field type string.
        """
        msg = "Could not parse field type: " + type
        super().__init__(msg)


class InvalidRegisterFormat(RuntimeError):
    """Raised when register configuration has a format error.

    This is a generic exception for various register format issues such
    as invalid reset values or unsupported combinations of settings.
    """

    def __init__(self, msg):
        """Initialize InvalidRegisterFormat exception.

        Args:
            msg: Description of the format error.
        """
        msg = "Invalid register format: " + msg
        super().__init__(msg)


class InvalidFieldFormat(RuntimeError):
    """Raised when field configuration has a format error.

    This exception indicates issues with field configuration such as
    invalid reset values or bit widths.
    """

    def __init__(self, msg):
        """Initialize InvalidFieldFormat exception.

        Args:
            msg: Description of the format error.
        """
        msg = "Invalid field format: " + msg
        super().__init__(msg)


class InvalidStallValue(RuntimeError):
    """Raised when stall_cycles value is out of valid range.

    Stall cycles must be either 0 (disabled) or between 2 and 255
    (inclusive) for IPBus registers.
    """

    def __init__(self, val):
        """Initialize InvalidStallValue exception.

        Args:
            val: The invalid stall cycles value.
        """
        msg = "Invalid stall value: {}. Must be between 2 and 255.".format(val)
        super().__init__(msg)
