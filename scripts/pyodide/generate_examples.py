"""Generate every example register map with bust as Pyodide runs it.

run.mjs installs bust without its dependencies and imports this module. Only
the core dependencies are present, so generation fails if it needs any other.
"""

import glob
import os

import bust
from bust.utils.file_utils import write_string_to_file


def generate_examples(example_dir: str, output_dir: str) -> None:
    """Write what ``bust FILE -o output_dir -p`` writes for each example."""
    json_paths = sorted(glob.glob(os.path.join(example_dir, "*.json")))
    if not json_paths:
        raise FileNotFoundError(f"No register maps in {example_dir}")
    for json_path in json_paths:
        print(f"Generating {json_path}")
        with open(json_path, encoding="utf-8", newline="") as fp:
            files = bust.generate_files(fp.read())
        for relative_path, content in files.items():
            directory, filename = os.path.split(os.path.join(output_dir, relative_path))
            os.makedirs(directory, exist_ok=True)
            write_string_to_file(content, filename, directory, True)
