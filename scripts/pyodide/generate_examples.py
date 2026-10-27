"""Generate every example register map with bust as Pyodide runs it.

run.mjs installs bust without its dependencies and imports this module. Only
the core dependencies are present, so generation fails if it needs any other.
"""

import glob
import os

import bust


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
            path = os.path.join(output_dir, relative_path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fp:
                fp.write(content)
