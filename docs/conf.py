# SPDX-License-Identifier: Apache-2.0
import json
import os

from bust._version import __VERSION__
from bust.schema import SCHEMA_URL, register_map_schema

project = "bust"
author = "Ola Groettvik"
copyright = "Ola Groettvik"
release = __VERSION__
version = release

extensions = ["myst_parser"]
myst_heading_anchors = 3
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


def setup(app):
    app.connect("build-finished", _write_schema)
