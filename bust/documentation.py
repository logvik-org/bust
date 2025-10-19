"""Documentation generation module for bust.

This module provides the Documentation class for automatically generating
LaTeX documentation from module definitions. The generated documentation
includes register maps, bit field descriptions, and access modes.
"""

from bust._version import __VERSION__
from bust.enums import RegisterType
from bust.jinja_utils.environment import get_environment


class Documentation(object):
    """Generates documentation for bus slave modules.

    The Documentation class creates LaTeX documentation with complete register
    specifications including addresses, bit positions, access modes, and
    descriptions.

    Attributes:
        module: Module instance to document.
    """

    def __init__(self, module):
        """Initialize Documentation generator.

        Args:
            module: Module instance to generate documentation for.
        """
        self.module = module

    def _render_template(self, template_name, version=None):
        """Render a Jinja2 template with module context.

        Args:
            template_name: Path to template file relative to templates directory.
            version: Version string to include (default: current bust version).

        Returns:
            Rendered template content as string with trailing newline.
        """
        if version is None:
            version = __VERSION__

        # Get standardized Jinja2 environment with all filters
        env = get_environment()

        # Load the template
        template = env.get_template(template_name)

        # Define common context for template rendering
        context = {
            "module": self.module,
            "version": version,
            "reg_type_fields": RegisterType.FIELDS,
        }
        result = template.render(context)

        # Ensure final newline is preserved
        if not result.endswith("\n"):
            result += "\n"
        return result

    def return_tex_documentation(self, test_version=None):
        """Generate LaTeX documentation for the module.

        Creates a complete LaTeX document with register map tables showing
        addresses, names, modes, bit positions, and descriptions.

        Args:
            test_version: Version string for testing (default: None, uses bust version).

        Returns:
            LaTeX document source code as string.
        """
        return self._render_template("latex/documentation.j2", test_version)
