"""! @package exceptions


"""

class FormatError(Exception):
    """! @brief Raised when input JSON is incorrect


    """


class ModuleDataBitsExceeded(Exception):
    """! @brief Raised when the specified module data bits are exceeded

    """


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
