"""Header file generation module for bust.

This module provides the HeaderGenerator class for generating register map header files
in various programming languages (C, C++, Python) and formats (IPBus address
tables). These headers allow software to access hardware registers with named
constants and proper address mappings.
"""

from bust.core.enums import RegisterType
from bust.jinja_utils.environment import render_template


class HeaderGenerator:
    """Generates header files for register map access in various languages.

    The HeaderGenerator class creates language-specific header files that define
    constants for register addresses, bit positions, and masks. This enables
    type-safe access to hardware registers from software.

    Attributes:
        module: Module instance containing register definitions.
    """

    def __init__(self, module):
        """Initialize Header generator for a module.

        Args:
            module: Module instance containing register map to export.
        """
        self.module = module

    def _render_template(self, template_name):
        """Render a Jinja2 template with module context.

        Args:
            template_name: Path to template file relative to templates directory.

        Returns:
            Rendered template content as string with trailing newline.
        """
        return render_template(
            template_name,
            {
                "module": self.module,
                "reg_type_fields": RegisterType.FIELDS,
            },
        )

    def generate_c_header(self):
        """Generate C header file with register definitions.

        Returns:
            C header file content as string with #define statements for
            register addresses, bit positions, and masks.
        """
        return self._render_template("header/c_header.j2")

    def generate_cpp_header(self):
        """Generate C++ header file with register definitions.

        Returns:
            C++ header file content as string with constexpr definitions
            for register addresses, bit positions, and masks.
        """
        return self._render_template("header/cpp_header.j2")

    def generate_python_header(self):
        """Generate Python module with register definitions.

        Returns:
            Python source file content as string with class and constant
            definitions for register addresses and bit positions.
        """
        return self._render_template("header/python_header.j2")

    def generate_ipbus_addr_table(self):
        """Generate IPBus XML address table.

        Returns:
            XML address table content as string in IPBus format, mapping
            register names to addresses for IPBus access.
        """
        return self._render_template("ipbus/addr_table.j2")


# Backward compatibility alias
Header = HeaderGenerator
