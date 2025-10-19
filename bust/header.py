from jinja2 import Environment, FileSystemLoader
import os
from bust.enums import RegisterMode, RegisterType


class Header(object):
    """Documentation for Header"""

    def __init__(self, module):
        self.module = module

    def _render_template(self, template_name):
        """Helper method to render templates with common context"""
        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(
            loader=FileSystemLoader(template_dir, followlinks=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

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
