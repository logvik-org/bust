"""Configuration validation utilities for bust.

This module provides a utility class for managing configuration dictionaries
with support for required key validation, default fallback values, and simple
access patterns with clear error reporting.
"""

import re
from typing import Any

from bust.exceptions import FormatError


def parse_number(value: Any, what: str) -> int:
    """Read a whole number from the register map.

    A JSON number is decimal. A string is hexadecimal after `0x`, binary after
    `0b` and decimal without a prefix.

    Args:
        value: The value from the JSON file.
        what (str): The key and where it is, for the message (for example
            "Address of register ctrl").

    Returns:
        int: The number, never negative.

    Raises:
        FormatError: If the value is not a whole number of 0 or more.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        if value < 0:
            raise FormatError(f"{what} must not be negative (got {value})")
        return value
    if isinstance(value, str):
        text = value.lower()
        if re.fullmatch(r"0x[0-9a-f]+", text):
            return int(text[2:], 16)
        if re.fullmatch(r"0b[01]+", text):
            return int(text[2:], 2)
        if re.fullmatch(r"[0-9]+", text):
            return int(text)
        if not text.startswith(("0x", "0b")) and re.fullmatch(r"[0-9a-f]+", text):
            raise FormatError(
                f'{what} "{value}" has hexadecimal digits but no 0x. Write '
                f'"0x{value}" for a hexadecimal number.'
            )
    raise FormatError(
        f'{what} must be a whole number such as 16, "0x10" or "0b10000" '
        f"(got {value!r})"
    )


class ConfigWrapper:
    """A utility class to wrap and manage configuration dictionaries.

    This wrapper ensures that all required keys are present and allows easy
    access to config values with fallback to defaults.

    Attributes:
        _config (dict): The user-provided configuration dictionary.
        _required (list): A list of required keys that must be present in the config.
        _defaults (dict): A dictionary of default values for optional config keys.
    """

    def __init__(self, config_dict, required_keys=None, defaults=None):
        """Initialize the ConfigWrapper.

        Args:
            config_dict (dict): The main configuration dictionary.
            required_keys (list, optional): A list of keys that must exist in config_dict.
            defaults (dict, optional): A dictionary of default values for optional keys.

        Raises:
            KeyError: If any of the required keys are missing from config_dict.
        """
        self._config = config_dict
        self._required = required_keys or []
        self._defaults = defaults or {}

        self._validate_required_keys()

    def _validate_required_keys(self):
        """Check that all required keys are present in the config.

        Raises:
            KeyError: If any required key is missing.
        """
        missing = [key for key in self._required if key not in self._config]
        if missing:
            raise KeyError(f"Missing required config keys: {', '.join(missing)}")

    def get(self, key):
        """Retrieve the value for a key, checking config first, then defaults.

        Args:
            key (str): The key to retrieve.

        Returns:
            The value associated with the key.

        Raises:
            KeyError: If the key is not present in config or defaults.
        """
        if key in self._config:
            return self._config[key]
        elif key in self._defaults:
            return self._defaults[key]
        raise KeyError(f"Config key '{key}' not found in config or defaults.")

    def require(self, key):
        """Retrieve a required key, raising an error if it is missing.

        Args:
            key (str): The key to retrieve.

        Returns:
            The value associated with the key.

        Raises:
            KeyError: If the key is not present in config.
        """
        if key not in self._config:
            raise KeyError(f"Missing required config key: {key}")
        return self.get(key)

    def is_set(self, key):
        """Return True if the key was explicitly set in the config."""
        return key in self._config
