"""IPBus-specific output: the uHAL address table publishes each register's
effective software access, and the headers/docs use the same register-level
access."""

import xml.etree.ElementTree as ET

import pytest

from bust.core.bus import Bus
from bust.core.module import Module
from bust.generators.documentation_generator import Documentation
from bust.generators.header_generator import Header

_ACCESS_REGISTERS = [
    {
        "name": "status",
        "type": "fields",
        "fields": [
            {"name": "busy", "type": "bit", "sw": "ro", "hw": "w"},
            {"name": "level", "type": "vector", "width": 4, "sw": "ro", "hw": "w"},
        ],
    },
    {
        "name": "mixed",
        "type": "fields",
        "fields": [
            {"name": "flag", "type": "bit", "sw": "ro", "hw": "w"},
            {"name": "go", "type": "bit", "sw": "wo", "hw": "r"},
        ],
    },
    {"name": "cmd", "sw": "wo", "hw": "r", "type": "vector", "width": 8},
    {
        "name": "hwonly",
        "sw": "na",
        "hw": "w",
        "type": "fields",
        "fields": [{"name": "f", "type": "vector", "width": 4}],
    },
    {
        "name": "partial",
        "type": "fields",
        "fields": [
            {"name": "visible", "type": "bit"},
            {"name": "hidden", "type": "bit", "sw": "na", "hw": "w"},
        ],
    },
]


def _ipbus_module(registers, addr_width=32):
    bus = Bus({"type": "ipbus", "addr_width": addr_width, "data_width": 32})
    return Module({"name": "m", "register": registers}, bus, settings=None)


def _addr_table_nodes():
    xml = Header(_ipbus_module(_ACCESS_REGISTERS)).generate_ipbus_addr_table()
    return {node.get("id"): node for node in ET.fromstring(xml)}


def test_addr_table_permission_follows_field_access():
    nodes = _addr_table_nodes()
    permissions = {name: node.get("permission") for name, node in nodes.items()}
    assert permissions == {
        "status": "r",
        "mixed": "rw",
        "cmd": "w",
        "partial": "rw",
    }


def test_addr_table_omits_software_unreachable_fields():
    nodes = _addr_table_nodes()
    assert "hwonly" not in nodes
    assert [field.get("id") for field in nodes["partial"]] == ["visible"]


def test_headers_use_effective_register_access():
    module = _ipbus_module(_ACCESS_REGISTERS)
    c_header = Header(module).generate_c_header()
    assert '#define STATUS_SW "ro"' in c_header
    assert '#define STATUS_HW "w"' in c_header
    assert '#define MIXED_SW "rw"' in c_header
    assert '#define MIXED_HW "rw"' in c_header
    assert '#define HWONLY_SW "na"' in c_header
    assert 'STATUS_SW = "ro"' in Header(module).generate_python_header()
    assert 'STATUS_SW = "ro";' in Header(module).generate_cpp_header()


def test_doc_uses_effective_register_access():
    pytest.importorskip("pylatexenc")
    tex = Documentation(_ipbus_module(_ACCESS_REGISTERS)).generate_tex_documentation()
    assert "{status - RO/W}" in tex
    assert "{mixed - RW/RW}" in tex
