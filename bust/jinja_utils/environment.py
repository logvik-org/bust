"""
Centralized Jinja2 environment setup to eliminate code duplication across modules.
"""

import os
from jinja2 import Environment, FileSystemLoader


def get_environment(additional_filters=None):
    """
    Create and configure a standardized Jinja2 environment with common settings.

    Args:
        additional_filters (dict, optional): Additional filters to register beyond common ones

    Returns:
        Environment: Configured Jinja2 environment with:
            - Template directory set to bust/templates
            - trim_blocks=True and lstrip_blocks=True for clean output
            - Common filters registered (hex_format, utf8tolatex, indent_all)
            - Additional filters if provided
    """
    # Get template directory relative to this module
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

    # Create environment with standard settings
    env = Environment(
        loader=FileSystemLoader(template_dir, followlinks=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Register common filters used across modules
    from bust.jinja_utils.filters import hex_format, utf8tolatex, indent_all

    env.filters["hex_format"] = hex_format
    env.filters["utf8tolatex"] = utf8tolatex
    env.filters["indent_all"] = indent_all

    # Register any additional filters provided
    if additional_filters:
        env.filters.update(additional_filters)

    return env
