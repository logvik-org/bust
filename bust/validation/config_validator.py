"""Configuration validation utilities for bust.

This module provides a utility class for managing configuration dictionaries
with support for required key validation, default fallback values, and simple
access patterns with clear error reporting.
"""

import logging

logger = logging.getLogger(__name__)


def warn_unknown_keys(config, known_keys, where):
    """Warn about each key bust does not read, so a misspelt key is not lost silently.

    Args:
        config (dict): A section of the register-map JSON.
        known_keys (Iterable[str]): The keys bust reads in that section.
        where (str): The section, for the message (for example "register ctrl").
    """
    for key in config:
        if key not in known_keys:
            logger.warning(f"Unknown key '{key}' in {where} is ignored")


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
