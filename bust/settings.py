"""Settings module for bust.

This module defines the Settings class, which says where bust writes the output
of a register map.
"""

import os
from typing import Optional


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

    def __init__(self, json_path: Optional[str]):
        """Initialize Settings from a JSON file path.

        Args:
            json_path: Path to the JSON configuration file, or None.
        """
        self.json_path = json_path or ""
        json_dir, self.json_name = os.path.split(self.json_path)
        # A file in the working directory has no directory part.
        self.project_path = json_dir or "."

        self.hdl_dir = "hdl"
        self.tb_dir = "tb"
        self.doc_dir = "doc"
        self.header_dir = "header"
