"""Numbers in the register map: a JSON number is decimal, a string is
hexadecimal after 0x, binary after 0b and decimal without a prefix (#217). The
generated files print the value bust parsed, never the string from the file
(#216)."""

import pytest

from bust.core.bus import Bus
from bust.core.module import Module
from bust.exceptions import FormatError, InvalidRegister
from bust.generators.documentation_generator import DocumentationGenerator
from bust.generators.factory import GeneratorFactory
from bust.generators.header_generator import HeaderGenerator
from bust.validation.config_validator import parse_number


def _module(registers, bus_type="axi"):
    bus = Bus({"type": bus_type, "addr_width": 16, "data_width": 32})
    return Module({"name": "m", "register": registers}, bus, settings=None)


@pytest.mark.parametrize(
    "value, number",
    [
        (16, 16),
        (0, 0),
        ("16", 16),
        ("0016", 16),
        ("0x10", 16),
        ("0X10", 16),
        ("0x1b2", 0x1B2),
        ("0x1B2", 0x1B2),
        ("0b10000", 16),
        ("0B101", 5),
    ],
)
def test_number_forms(value, number):
    assert parse_number(value, "Width") == number


@pytest.mark.parametrize(
    "value, message",
    [
        (-1, "must not be negative"),
        (1.5, "must be a whole number"),
        (16.0, "must be a whole number"),
        (True, "must be a whole number"),
        (None, "must be a whole number"),
        ("-16", "must be a whole number"),
        ("0x", "must be a whole number"),
        ("0b102", "must be a whole number"),
        (" 16", "must be a whole number"),
        ("sixteen", "must be a whole number"),
    ],
)
def test_values_that_are_not_numbers_are_rejected(value, message):
    with pytest.raises(FormatError, match=message):
        parse_number(value, "Width")


@pytest.mark.parametrize("value", ["1B2", "ff", "a"])
def test_hexadecimal_digits_without_prefix_suggest_0x(value):
    with pytest.raises(FormatError, match=f'Write "0x{value}"'):
        parse_number(value, "Reset of register r")


@pytest.mark.parametrize("address", [16, "16", "0x10", "0b10000"])
def test_address_forms_give_the_same_register_offset(address):
    module = _module([{"name": "r", "address": address}])
    assert module.registers[0].address == 0x10


def test_address_without_prefix_is_decimal():
    module = _module([{"name": "r", "address": "10"}], bus_type="ipbus")
    assert module.registers[0].address == 10


def test_address_error_names_the_register():
    with pytest.raises(FormatError, match='Address of register r "1c" has'):
        _module([{"name": "r", "address": "1c"}])


def test_reset_forms_reach_hdl_and_headers_alike():
    module = _module(
        [
            {"name": "a", "type": "vector", "width": 16, "reset": "0x1B2"},
            {"name": "b", "type": "vector", "width": 8, "reset": "10"},
            {"name": "c", "type": "vector", "width": 8, "reset": 255},
        ]
    )
    pkg = GeneratorFactory.generate_regfile_package_vhdl(module)
    assert 'a => 16X"1B2"' in pkg
    assert 'b => 8X"A"' in pkg
    assert 'c => 8X"FF"' in pkg
    headers = HeaderGenerator(module)
    c_header = headers.generate_c_header()
    assert "#define M_A_RESET 0x1b2" in c_header
    assert "#define M_B_RESET 0xa" in c_header
    assert "#define M_C_RESET 0xff" in c_header
    assert "const uint32_t B_RESET = 0xa;" in headers.generate_cpp_header()
    assert "B_RESET = 0xa" in headers.generate_python_header()
    tex = DocumentationGenerator(module).generate_tex_documentation()
    assert r"\texttt{0x1B2}" in tex
    assert r"\texttt{0xA}" in tex


def test_field_reset_reaches_headers_as_parsed():
    module = _module(
        [
            {
                "name": "r",
                "type": "fields",
                "fields": [
                    {
                        "name": "f",
                        "type": "vector",
                        "width": 5,
                        "reset": "16",
                        "enums": [
                            {"name": "X", "value": "0xa"},
                            {"name": "Y", "value": "16"},
                        ],
                    },
                    {"name": "g", "type": "vector", "width": 4, "reset": "0b1010"},
                ],
            }
        ]
    )
    field = module.registers[0].fields[0]
    assert [e.value for e in field.enums] == [10, 16]
    assert 'r => (f => Y, g => 4X"A")' in (
        GeneratorFactory.generate_regfile_package_vhdl(module)
    )
    c_header = HeaderGenerator(module).generate_c_header()
    assert "#define M_R_F_RESET 0x10" in c_header
    assert "#define M_R_G_RESET 0xa" in c_header


def test_ipbus_table_prints_the_parsed_reset():
    module = _module(
        [{"name": "r", "type": "vector", "width": 8, "reset": "10"}], "ipbus"
    )
    assert (
        'parameters="reset=0xa"' in HeaderGenerator(module).generate_ipbus_addr_table()
    )


def test_width_and_position_take_strings():
    module = _module(
        [
            {"name": "v", "type": "vector", "width": "0x8"},
            {
                "name": "r",
                "type": "fields",
                "fields": [
                    {"name": "f", "type": "vector", "width": "3", "position": "4"}
                ],
            },
        ]
    )
    assert module.registers[0].width == 8
    field = module.registers[1].fields[0]
    assert (field.width, field.pos_low, field.pos_high) == (3, 4, 6)


@pytest.mark.parametrize(
    "register, message",
    [
        ({"name": "r", "type": "vector", "width": "8.0"}, "Width of register r"),
        ({"name": "r", "reset": "1B2"}, "Reset of register r"),
        (
            {
                "name": "r",
                "type": "fields",
                "fields": [{"name": "f", "type": "bit", "position": -1}],
            },
            "Position of field f in register r",
        ),
        (
            {
                "name": "r",
                "type": "fields",
                "fields": [{"name": "f", "type": "vector", "width": "x"}],
            },
            "Width of field f in register r",
        ),
        (
            {
                "name": "r",
                "type": "fields",
                "fields": [
                    {
                        "name": "f",
                        "type": "vector",
                        "width": 2,
                        "enums": [{"name": "A", "value": "b"}],
                    }
                ],
            },
            "Value of enum A in field f",
        ),
        (
            {"name": "r", "mode": "pulse", "pulse_cycles": "two"},
            "pulse_cycles of register r",
        ),
    ],
)
def test_errors_name_the_key_and_where_it_is(register, message):
    with pytest.raises(InvalidRegister, match=message):
        _module([register])


def test_bus_widths_take_strings_and_name_the_key():
    bus = Bus({"type": "axi", "addr_width": "0x10", "data_width": "32"})
    assert (bus.addr_width, bus.data_width) == (16, 32)
    with pytest.raises(FormatError, match="data_width of the bus"):
        Bus({"type": "axi", "addr_width": 16, "data_width": "32 bits"})
