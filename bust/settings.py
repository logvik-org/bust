"""Settings module for bust.

This module defines the Settings class, which holds the output settings from the
optional `settings` section of a register-map JSON file.
"""

import os
from collections import OrderedDict
from typing import Optional


class Settings:
    """Output settings of a register map.

    Attributes:
        json_path: Path to the JSON configuration file.
        json_name: Filename of the JSON configuration.
        proj_dir: Output directory from the JSON file, or None.
        project_path: Output directory used when no `-o` is given: `proj_dir`,
            else the directory of the JSON file.
        mod_subdir: Whether to write the output into a subdirectory named after
            the module.
        hdl_dir: Directory name for HDL files ("hdl").
        tb_dir: Directory name for testbenches ("tb").
        doc_dir: Directory name for documentation ("doc").
        header_dir: Directory name for headers ("header").
    """

    # bust 0.14 settings that bust 1.0 ignores. They are kept as given so that
    # saving the JSON file again (bust -a, the editor) does not drop them.
    IGNORED_KEYS = (
        "bus_subdir",
        "uvvm_rel_path",
        "ipbus_rel_path",
        "vip_ipbus_rel_path",
        "coverage",
    )

    def __init__(self, json_path: Optional[str], settings: Optional[dict]):
        """Initialize Settings from a JSON file path and its settings section.

        Args:
            json_path: Path to the JSON configuration file, or None.
            settings: The `settings` section of the file, or None when the file
                has none.
        """
        settings = settings or {}
        self.json_path = json_path or ""
        json_dir, self.json_name = os.path.split(self.json_path)

        self.proj_dir: Optional[str] = settings.get("proj_dir")
        # A file in the working directory has no directory part.
        default_dir = json_dir or "."
        self.project_path = default_dir if self.proj_dir is None else self.proj_dir
        self.mod_subdir: bool = settings.get("mod_subdir", True)
        self.ignored = OrderedDict(
            (key, settings[key]) for key in self.IGNORED_KEYS if key in settings
        )

        self.hdl_dir = "hdl"
        self.tb_dir = "tb"
        self.doc_dir = "doc"
        self.header_dir = "header"

    def to_json(self):
        """Export settings as an ordered dictionary.

        Returns:
            OrderedDict with the settings, including any ignored 0.14 settings
            the file had.
        """
        json: OrderedDict[str, object] = OrderedDict()
        if self.proj_dir is not None:
            json["proj_dir"] = self.proj_dir
        json["mod_subdir"] = self.mod_subdir
        json.update(self.ignored)
        return json
