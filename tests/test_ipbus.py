"""IPBus-specific output: the uHAL address table publishes each register's and
each field's effective software access (the headers/docs use the same
register-level access), and the endpoint fits the fixed 32-bit IPBus address to
the module's addr_width."""

import xml.etree.ElementTree as ET

import pytest

from bust.core.bus import Bus
from bust.core.module import Module
from bust.exceptions import FormatError
from bust.generators.documentation_generator import Documentation
from bust.generators.factory import GeneratorFactory
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


def test_addr_table_field_permission_follows_its_own_access():
    """uHAL checks a field node's own permission, so an ro field inside an rw
    register must not inherit the register's write permission."""
    nodes = _addr_table_nodes()
    permissions = {
        (name, field.get("id")): field.get("permission")
        for name, node in nodes.items()
        for field in node
    }
    assert permissions == {
        ("status", "busy"): "r",
        ("status", "level"): "r",
        ("mixed", "flag"): "r",
        ("mixed", "go"): "w",
        ("partial", "visible"): "rw",
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


def test_endpoint_slices_ipbus_address_to_module_width():
    module = _ipbus_module([{"name": "r", "type": "default"}], addr_width=16)

    endpoint = GeneratorFactory.generate_ipb_endpoint_vhdl(module)
    assert "m2s.address <= ipb_in.ipb_addr(15 downto 0);" in endpoint
    assert "G_BASE_ADDRESS       : unsigned(15 downto 0)" in endpoint
    # The sliced address is what the local bus carries and the base check sees.
    localbus_pkg = GeneratorFactory.generate_localbus_package_vhdl(module)
    assert "C_LB_ADDR_WIDTH : natural := 16;" in localbus_pkg
    regfile_pkg = GeneratorFactory.generate_regfile_package_vhdl(module)
    assert "return addr(15 downto C_MODULE_ADDR_WIDTH)" in regfile_pkg


def test_ipbus_addr_width_above_32_rejected():
    with pytest.raises(FormatError, match="at most 32"):
        Bus({"type": "ipbus", "addr_width": 33, "data_width": 32})


def test_addr_width_limit_is_ipbus_only():
    assert Bus({"type": "axi", "addr_width": 64, "data_width": 32}).addr_width == 64


def test_ipbus_data_width_other_than_32_rejected():
    with pytest.raises(FormatError, match="data_width must be 32"):
        Bus({"type": "ipbus", "addr_width": 32, "data_width": 16})


def test_data_width_constraint_is_ipbus_only():
    assert Bus({"type": "axi", "addr_width": 32, "data_width": 64}).data_width == 64
