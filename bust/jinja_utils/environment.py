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
    from bust.jinja_utils.filters import (
        hex_format,
        utf8tolatex,
        indent_all,
        get_vhdl_type,
        get_reset_value,
    )

    env.filters["hex_format"] = hex_format
    env.filters["utf8tolatex"] = utf8tolatex
    env.filters["indent_all"] = indent_all
    env.filters["get_vhdl_type"] = get_vhdl_type
    env.filters["get_reset_value"] = get_reset_value

    # Register any additional filters provided
    if additional_filters:
        env.filters.update(additional_filters)

    return env


def render_template(template_name, context, ensure_newline=True):
    """
    Render a Jinja2 template with common settings and optional newline handling.

    This helper function centralizes the template rendering logic to eliminate
    code duplication across generator classes.

    Args:
        template_name (str): Path to the template relative to templates/ directory
        context (dict): Context variables to pass to the template
        ensure_newline (bool, optional): If True, ensures result ends with newline.
            Defaults to True.

    Returns:
        str: Rendered template content

    Example:
        >>> result = render_template("header/c_header.j2", {"module": my_module})
    """
    env = get_environment()
    template = env.get_template(template_name)
    result = template.render(context)
    
    if ensure_newline and not result.endswith("\n"):
        result += "\n"
    
    return result
