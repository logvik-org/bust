class ConfigWrapper:
    def __init__(self, config_dict, defaults=None):
        self._config = config_dict
        self._defaults = defaults or {}

    def get(self, key):
        if key in self._config:
            return self._config[key]
        elif key in self._defaults:
            return self._defaults[key]
        raise KeyError(f"Config key '{key}' not found in config or defaults.")

    def require(self, key):
        if key not in self._config:
            raise KeyError(f"Missing required config key: {key}")
        return self.get(key)
