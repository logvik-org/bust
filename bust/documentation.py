import os
from jinja2 import Environment, FileSystemLoader
from pylatexenc.latexencode import utf8tolatex
from bust._version import __VERSION__
from bust.enums import RegisterType


class Documentation(object):
    """Class for auto-generation of module documentation"""

    def __init__(self, module):
        self.module = module

    def _render_template(self, template_name, version=None):
        """Helper method to render a Jinja2 template with common context."""
        if version is None:
            version = __VERSION__

        # Setup Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(
            loader=FileSystemLoader(template_dir, followlinks=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        from bust.jinja_utils.filters import hex_format, utf8tolatex

        env.filters["hex_format"] = hex_format
        env.filters["utf8tolatex"] = utf8tolatex

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
        """Generate LaTeX documentation for the module using Jinja2 templates."""
        return self._render_template("latex/documentation.j2", test_version)
