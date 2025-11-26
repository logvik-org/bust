from bust.enums import RegisterType
from bust.jinja_utils.environment import render_template


class Header:
    """Generates header files (C, C++, Python) for register definitions."""

    def __init__(self, module):
        self.module = module

    def _render_template(self, template_name):
        """Helper method to render templates with common context"""
        return render_template(
            template_name,
            {
                "module": self.module,
                "reg_type_fields": RegisterType.FIELDS,
            },
        )

    def return_c_header(self):
        return self._render_template("header/c_header.j2")

    def return_cpp_header(self):
        return self._render_template("header/cpp_header.j2")

    def return_python_header(self):
        return self._render_template("header/python_header.j2")

    def return_ipbus_addr_table(self):
        return self._render_template("ipbus/addr_table.j2")
