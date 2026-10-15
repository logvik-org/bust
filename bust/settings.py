"""Settings module for bust.

This module defines the Settings class which manages project-wide configuration
including file paths, directory structure, and external dependencies like UVVM
and IPBus. Settings are typically loaded from the JSON configuration file.
"""

import os
import logging
from collections import OrderedDict
from typing import Optional, cast


class Settings:
    """Manages project settings and path configurations.

    The Settings class encapsulates all project-level configuration including
    output directory structure, paths to external dependencies (UVVM, IPBus),
    and project organization preferences.

    Attributes:
        json_path: Path to the JSON configuration file.
        json_name: Filename of the JSON configuration.
        project_path: Root directory for project output.
        mod_subdir: Whether to create module subdirectories.
        bus_subdir: Whether to create bus subdirectories.
        uvvm_rel_path: Relative path to UVVM library (for testbenches).
        ipbus_rel_path: Relative path to IPBus library.
        vip_ipbus_rel_path: Relative path to IPBus VIP library.
        coverage: Whether to enable coverage in testbenches.
        hdl_dir: Directory name for HDL files ("hdl").
        script_dir: Directory name for scripts ("scripts").
        tb_dir: Directory name for testbenches ("tb").
        doc_dir: Directory name for documentation ("doc").
        header_dir: Directory name for headers ("header").
        sim_dir: Directory name for simulation ("sim").

    Class Attributes:
        default_val: Dictionary of default values for optional settings.
    """

    default_val = {
        "mod_subdir": True,
        "bus_subdir": True,
        "uvvm_rel_path": None,
        "ipbus_rel_path": None,
        "vip_ipbus_rel_path": None,
        "coverage": False,
    }

    def __init__(self, json_path, settings):
        """Initialize Settings from JSON file and settings dictionary.

        Args:
            json_path: Path to JSON configuration file (or None for defaults).
            settings: Dictionary containing settings, or None for defaults.
        """
        self.logger = logging.getLogger(__name__)

        if json_path is None and settings is None:
            self.logger.info("No input to Settings. Using default settings.")
            self.json_path = ""
            self.proj_dir = cast(Optional[str], None)
            self.project_path = ""
            self.json_name = ""
            self.mod_subdir = self.default_val["mod_subdir"]
            self.bus_subdir = self.default_val["bus_subdir"]
            self.uvvm_rel_path = cast(Optional[str], None)
            self.ipbus_rel_path = cast(Optional[str], None)
            self.vip_ipbus_rel_path = cast(Optional[str], None)
            self.coverage = self.default_val["coverage"]
        else:

            self.json_path = json_path
            json_dir, file_name = os.path.split(json_path)

            self.json_name = file_name

            self.proj_dir = cast(Optional[str], settings.get("proj_dir"))
            if self.proj_dir is None:
                self.project_path = json_dir
            else:
                self.project_path = self.proj_dir

            if "mod_subdir" not in settings:
                self.logger.info(
                    "Module subdir setting not specified. Choosing default: True"
                )
                self.mod_subdir = self.default_val["mod_subdir"]
            else:
                self.mod_subdir = settings["mod_subdir"]

            if "bus_subdir" not in settings:
                self.logger.info(
                    "Bus subdir setting not specified. Choosing default: True"
                )
                self.bus_subdir = self.default_val["bus_subdir"]
            else:
                self.bus_subdir = settings["bus_subdir"]

            if "uvvm_rel_path" not in settings:
                self.logger.info(
                    "UVVM path is not specified. No testbench can be generated!"
                )
                self.uvvm_rel_path = cast(Optional[str], None)
            else:
                self.uvvm_rel_path = cast(Optional[str], settings["uvvm_rel_path"])

            if "ipbus_rel_path" not in settings:
                self.logger.debug(
                    "ipbus path is not specified. No testbench can be generated for ipbus!"
                )
                self.ipbus_rel_path = cast(Optional[str], None)
            else:
                self.ipbus_rel_path = cast(Optional[str], settings["ipbus_rel_path"])

            if "vip_ipbus_rel_path" not in settings:
                self.logger.debug(
                    "vip_ipbus path is not specified. No testbench can be generated for ipbus!"
                )
                self.vip_ipbus_rel_path = cast(Optional[str], None)
            else:
                self.vip_ipbus_rel_path = cast(
                    Optional[str], settings["vip_ipbus_rel_path"]
                )

            if "coverage" not in settings:
                self.logger.info("Coverage is not specified. Choosing default: False")
                self.coverage = self.default_val["coverage"]
            else:
                self.coverage = settings["coverage"]

        self.hdl_dir = "hdl"
        self.tb_dir = "tb"
        self.doc_dir = "doc"
        self.header_dir = "header"

    def to_json(self):
        """Export settings as an ordered dictionary.

        Returns:
            OrderedDict with settings, omitting None values for optional paths.
        """
        json: OrderedDict[str, object] = OrderedDict()
        if self.proj_dir is not None:
            json["proj_dir"] = self.proj_dir
        json["mod_subdir"] = self.mod_subdir
        json["bus_subdir"] = self.bus_subdir
        if self.uvvm_rel_path is not None:
            json["uvvm_rel_path"] = self.uvvm_rel_path
        if self.ipbus_rel_path is not None:
            json["ipbus_rel_path"] = self.ipbus_rel_path
        if self.vip_ipbus_rel_path is not None:
            json["vip_ipbus_rel_path"] = self.vip_ipbus_rel_path
        json["coverage"] = self.coverage
        return json
