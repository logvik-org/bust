from bust.enums import RegisterType
from bust.jinja_utils.environment import get_environment


class Header(object):
    """Documentation for Header"""

    def __init__(self, module):
        self.module = module

    def _render_template(self, template_name):
        """Helper method to render templates with common context"""
        # Get standardized Jinja2 environment with all filters
        env = get_environment()

        # Load the template
        template = env.get_template(template_name)

        # Define common context for template rendering
        context = {
            "module": self.module,
            "reg_type_fields": RegisterType.FIELDS,
        }
        result = template.render(context)
        # Ensure final newline is preserved
        if not result.endswith("\n"):
            result += "\n"
        return result

    def return_c_header(self):
        return self._render_template("header/c_header.j2")

    def return_cpp_header(self):
        return self._render_template("header/cpp_header.j2")

    def return_python_header(self):
        return self._render_template("header/python_header.j2")

    def return_ipbus_addr_table(self):
        return self._render_template("ipbus/addr_table.j2")
