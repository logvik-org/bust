from bust._version import __VERSION__
from bust.enums import RegisterType
from bust.jinja_utils.environment import get_environment


class Documentation:
    """Class for auto-generation of module documentation"""

    def __init__(self, module):
        self.module = module

    def _render_template(self, template_name, version=None):
        """Helper method to render a Jinja2 template with common context."""
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
        """Generate LaTeX documentation for the module using Jinja2 templates."""
        return self._render_template("latex/documentation.j2", test_version)
