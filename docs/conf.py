# SPDX-License-Identifier: Apache-2.0
from bust._version import __VERSION__

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
html_static_path = ["_static"]
html_css_files = ["custom.css"]
pygments_style = "friendly"
pygments_dark_style = "monokai"

# The same paper-and-ink palette as the ohsh docs, with a teal accent for bust.
html_theme_options = {
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
        "color-brand-primary": "#0f6b63",
        "color-brand-content": "#0f6b63",
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
        "color-brand-primary": "#5cc2b6",
        "color-brand-content": "#5cc2b6",
        "color-code-background": "#131312",
        "color-highlighted-background": "#2f2c2a",
    },
}
