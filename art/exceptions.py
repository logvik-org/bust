"""! @package exceptions


"""

class FormatError(Exception):
    """! @brief Raised when input JSON is incorrect


    """


class ModuleDataBitsExceeded(Exception):
    """! @brief Raised when the specified module data bits are exceeded

    """
    def __init__(self, register, reglength, mod_data_length):
        msg = "\nFAILURE:\n"
        msg += "In register " + register + "\n"
        msg += "Register length exceeded module data length by "
        msg += str(reglength-mod_data_length)
        super().__init__(msg)


class UndefinedRegisterType(RuntimeError):
    """! @brief Raised when trying to parse a register type that is not supported

    """
    def __init__(self, regtype):
        msg = "\nFAILURE:\n"
        msg += "Could not parse register type: " + regtype
        super().__init__(msg)

class UndefinedEntryType(RuntimeError):
    """! @brief Raised when trying to parse an entry type that is not supported

    """
    def __init__(self, entrytype):
        msg = "\nFAILURE:\n"
        msg += "Could not parse entry type: " + entrytype
        super().__init__(msg)
