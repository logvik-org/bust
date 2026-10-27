# SPDX-License-Identifier: Apache-2.0
import json
import os
import shutil
import subprocess
import tempfile

from bust._version import __VERSION__
from bust.schema import SCHEMA_URL, register_map_schema

project = "bust"
author = "Ola Groettvik"
copyright = "Ola Groettvik"
release = __VERSION__
version = release

extensions = ["myst_parser"]
# 5 so the register links in the included example Markdown resolve.
myst_heading_anchors = 5
exclude_patterns = ["_build"]

html_theme = "furo"
html_title = "bust"
html_favicon = "images/favicon.png"
html_static_path = ["_static", "images"]
html_css_files = ["custom.css"]
pygments_style = "friendly"
pygments_dark_style = "monokai"

# The logvik paper, ink and teal, as in the logo. The ohsh docs use the same
# paper and ink.
html_theme_options = {
    "light_logo": "wordmark-light.svg",
    "dark_logo": "wordmark-dark.svg",
    "sidebar_hide_name": True,
    "source_repository": "https://github.com/logvik-org/bust/",
    "source_branch": "master",
    "source_directory": "docs/",
    "light_css_variables": {
        "color-background-primary": "#f2eee3",
        "color-background-secondary": "#e9e3d3",
        "color-background-hover": "#e3ddcb",
        "color-background-border": "#d3cbb4",
        "color-foreground-primary": "#1c2118",
        "color-foreground-secondary": "#4a4d43",
        "color-foreground-muted": "#686b61",
        "color-brand-primary": "#2c6e6a",
        "color-brand-content": "#2c6e6a",
        "color-code-background": "#e9e3d3",
        "color-highlighted-background": "#e3ddcb",
    },
    "dark_css_variables": {
        "color-background-primary": "#1f1e1d",
        "color-background-secondary": "#2a2725",
        "color-background-hover": "#2f2c2a",
        "color-background-border": "#3a3633",
        "color-foreground-primary": "#ece8df",
        "color-foreground-secondary": "#c9c3b6",
        "color-foreground-muted": "#9a948a",
        "color-brand-primary": "#5fa8a0",
        "color-brand-content": "#5fa8a0",
        "color-code-background": "#131312",
        "color-highlighted-background": "#2f2c2a",
    },
}


def _write_schema(app, exception):
    if exception is not None or app.builder.format != "html":
        return
    path = os.path.join(app.outdir, os.path.basename(SCHEMA_URL))
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(register_map_schema(), fp, indent=2)
        fp.write("\n")


# The documentation bust generated for the prototype example, put into the
# built site so the docs can show it. Both come from the committed goldens,
# which the tests keep in step with the generator: the HTML is copied, and the
# PDF is built from the .tex. Read the Docs installs pdflatex for that (see
# .readthedocs.yaml). Elsewhere the PDF is left out when pdflatex is missing.
_EXAMPLE_DOC = os.path.join("..", "example", "example_prototype", "doc", "prototype")


def _add_example_docs(app, exception):
    if exception is not None or app.builder.format != "html":
        return
    examples_dir = os.path.join(app.outdir, "examples")
    os.makedirs(examples_dir, exist_ok=True)
    example = os.path.join(app.confdir, _EXAMPLE_DOC)
    shutil.copy(example + ".html", examples_dir)
    _build_example_pdf(example + ".tex", examples_dir)


def _build_example_pdf(tex, out_dir):
    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        if os.environ.get("READTHEDOCS") == "True":
            raise RuntimeError(
                "pdflatex is missing, so the example PDF cannot be built"
            )
        return
    with tempfile.TemporaryDirectory() as build_dir:
        # The second run resolves the references the first one writes to the
        # .aux file.
        for _ in range(2):
            subprocess.run(
                [
                    pdflatex,
                    "--interaction=batchmode",
                    f"--output-directory={build_dir}",
                    tex,
                ],
                stdout=subprocess.DEVNULL,
                check=True,
                # The same date as the HTML example, which pins it for the goldens.
                env=dict(os.environ, SOURCE_DATE_EPOCH="0", FORCE_SOURCE_DATE="1"),
            )
        name = os.path.splitext(os.path.basename(tex))[0] + ".pdf"
        shutil.copy(os.path.join(build_dir, name), out_dir)


def setup(app):
    app.connect("build-finished", _add_example_docs)
    app.connect("build-finished", _write_schema)
