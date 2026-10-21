"""Settings module for bust.

This module defines the Settings class, which says where bust writes the output
of a register map.
"""

import logging
import os
from typing import Optional

from bust.exceptions import FormatError

logger = logging.getLogger(__name__)


class Settings:
    """Output location of a register map.

    bust writes into `<output directory>/<module name>/`. The output directory
    is `-o DIR`, or else the directory of the JSON file.

    Attributes:
        json_path: Path to the JSON configuration file.
        json_name: Filename of the JSON configuration.
        project_path: Output directory used when no `-o` is given, the
            directory of the JSON file.
        hdl_dir: Directory name for HDL files ("hdl").
        tb_dir: Directory name for testbenches ("tb").
        doc_dir: Directory name for documentation ("doc").
        header_dir: Directory name for headers ("header").
    """

    def __init__(self, json_path: Optional[str], settings: Optional[dict]):
        """Initialize Settings from a JSON file path and its settings section.

        Args:
            json_path: Path to the JSON configuration file, or None.
            settings: The bust 0.14 `settings` section of the file, or None
                when the file has none. bust 1.0 does not read it.

        Raises:
            FormatError: If the section would put the output somewhere other
                than bust 1.0 does.
        """
        if settings:
            if "proj_dir" in settings or settings.get("mod_subdir") is False:
                raise FormatError(
                    "bust no longer reads proj_dir and mod_subdir in the settings "
                    "section. It writes into <output directory>/<module name>/, "
                    "and -o sets the output directory. Remove the settings "
                    "section and run bust with -o instead."
                )
            logger.warning(
                "The settings section is ignored. Remove it, or run bust with "
                "--migrate."
            )
        self.json_path = json_path or ""
        json_dir, self.json_name = os.path.split(self.json_path)
        # A file in the working directory has no directory part.
        self.project_path = json_dir or "."

        self.hdl_dir = "hdl"
        self.tb_dir = "tb"
        self.doc_dir = "doc"
        self.header_dir = "header"
