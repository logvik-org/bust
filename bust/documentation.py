"""Documentation generation module for bust.

This module is a backward compatibility shim. Import from bust.generators.documentation_generator instead.
"""

# Re-export from new location for backward compatibility
from bust.generators.documentation_generator import (
    DocumentationGenerator,
    Documentation,
)

__all__ = ["DocumentationGenerator", "Documentation"]
