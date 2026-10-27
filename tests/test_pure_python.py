"""bust runs in the browser under Pyodide, which installs only pure Python
wheels from PyPI. Every runtime dependency must stay pure Python."""

import email
from importlib import metadata
from typing import Dict, List

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

# Pyodide ships its own build of MarkupSafe, the one Jinja2 needs. MarkupSafe
# also runs without its C speedups, so it works everywhere else too.
PYODIDE_BUILDS = {"markupsafe"}


def runtime_requirements(name: str) -> List[Requirement]:
    requirements = [Requirement(line) for line in metadata.requires(name) or []]
    return [
        requirement
        for requirement in requirements
        if requirement.marker is None or requirement.marker.evaluate({"extra": ""})
    ]


def runtime_dependencies() -> Dict[str, metadata.Distribution]:
    """Every distribution bust needs at run time, by canonical name."""
    found: Dict[str, metadata.Distribution] = {}
    pending = runtime_requirements("bust")
    while pending:
        name = canonicalize_name(pending.pop().name)
        if name not in found:
            found[name] = metadata.distribution(name)
            pending.extend(runtime_requirements(name))
    return found


def is_pure_python(distribution: metadata.Distribution) -> bool:
    wheel = email.message_from_string(distribution.read_text("WHEEL") or "")
    tags = wheel.get_all("Tag") or []
    return wheel["Root-Is-Purelib"] == "true" and all(
        tag.endswith("-none-any") for tag in tags
    )


def test_the_walk_reaches_indirect_dependencies():
    dependencies = runtime_dependencies()
    assert {"jinja2", "markupsafe", "textual", "rich"} <= dependencies.keys()


def test_every_runtime_dependency_is_pure_python():
    impure = [
        name
        for name, distribution in sorted(runtime_dependencies().items())
        if name not in PYODIDE_BUILDS and not is_pure_python(distribution)
    ]
    assert impure == [], (
        f"{', '.join(impure)} is not pure Python, so bust cannot install it "
        "in the browser under Pyodide"
    )
