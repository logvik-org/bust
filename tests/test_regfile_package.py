"""Verify the generated local-bus regfile package.

Two guards: a golden-file comparison against the committed reference (regression),
and a structural comparison against the hand-written, simulation-verified prototype
package in `hdl/prototype/` (the generator must reproduce the verified HDL)."""

import glob
import json
import os
import re
import shutil
import subprocess

import pytest

from bust.core.bus import Bus
from bust.core.module import Module
from bust.generators.factory import GeneratorFactory
from bust.generators.vhdl.address_checks import AddressChecks
from bust.generation import generate_output
from bust.settings import Settings
from bust.utils.json_utils import json_parser

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_EXAMPLE = os.path.join(_REPO_ROOT, "example", "example_prototype.json")
_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_regfile_pkg.vhd"
)
_PROTOTYPE = os.path.join(_REPO_ROOT, "hdl", "prototype", "prototype_regfile_pkg.vhd")
_ENTITY_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_regfile.vhd"
)
_AXI_ENDPOINT_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_axi_endpoint.vhd"
)
_IPB_ENDPOINT_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_ipb_endpoint.vhd"
)
_MODULE_TOP_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype.vhd"
)
_AXI_TB_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_tb.vhd"
)
_IPBUS_TB_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_ipbus_tb.vhd"
)
_IPBUS_TOP_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_ipbus.vhd"
)


def _build_module():
    with open(_EXAMPLE) as fp:
        cfg = json.load(fp)
    return Module(cfg["module"], Bus(cfg["bus"]), settings=None)


def _build_ipbus_module():
    """The prototype register map driven over an IPBus interface.

    Reuses the example's bus config (widths, library) and only swaps the type, so
    the IPBus setup tracks the JSON rather than hard-coding values.
    """
    with open(_EXAMPLE) as fp:
        cfg = json.load(fp)
    bus = Bus(dict(cfg["bus"], type="ipbus"))
    return Module(cfg["module"], bus, settings=None)


def _structural_lines(text):
    """Declaration lines with comments, blanks, and whitespace normalized away.

    Reset-aggregate and is_mapped lines are dropped: the verified prototype and the
    generator express the same values differently (`(others => '1')` vs `4X"F"`,
    wrapped vs single-line boolean), which is functional, not structural. Enum
    decode `when ... =>` arms are kept so the generated conversion logic is
    checked."""
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"--.*$", "", raw).strip()
        line = re.sub(r"\s+", " ", line)
        is_reset_aggregate = "=>" in line and not line.startswith("when")
        if (
            not line
            or is_reset_aggregate
            or re.match(r"(return |or )?reg_addr_match", line)
        ):
            continue
        lines.append(line)
    return lines


def test_localbus_package_matches_golden():
    generated = GeneratorFactory.generate_localbus_package_vhdl(_build_module())
    golden = os.path.join(
        _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_localbus_pkg.vhd"
    )
    with open(golden) as fp:
        assert generated == fp.read()


def test_regfile_package_matches_golden():
    generated = GeneratorFactory.generate_regfile_package_vhdl(_build_module())
    with open(_GOLDEN) as fp:
        assert generated == fp.read()


def test_regfile_package_matches_verified_prototype():
    generated = GeneratorFactory.generate_regfile_package_vhdl(_build_module())
    with open(_PROTOTYPE) as fp:
        assert _structural_lines(generated) == _structural_lines(fp.read())


def test_regfile_entity_matches_golden():
    generated = GeneratorFactory.generate_regfile_vhdl(_build_module())
    with open(_ENTITY_GOLDEN) as fp:
        assert generated == fp.read()


def test_axi_endpoint_matches_golden():
    generated = GeneratorFactory.generate_axi_endpoint_vhdl(_build_module())
    with open(_AXI_ENDPOINT_GOLDEN) as fp:
        assert generated == fp.read()


def test_ipb_endpoint_matches_golden():
    generated = GeneratorFactory.generate_ipb_endpoint_vhdl(_build_module())
    with open(_IPB_ENDPOINT_GOLDEN) as fp:
        assert generated == fp.read()


def test_module_top_matches_golden():
    generated = GeneratorFactory.generate_module_top_vhdl(_build_module())
    with open(_MODULE_TOP_GOLDEN) as fp:
        assert generated == fp.read()


def test_axi_testbench_matches_golden():
    generated = GeneratorFactory.generate_localbus_axi_testbench_vhdl(_build_module())
    with open(_AXI_TB_GOLDEN) as fp:
        assert generated == fp.read()


def test_ipbus_testbench_matches_golden():
    generated = GeneratorFactory.generate_localbus_ipbus_testbench_vhdl(
        _build_ipbus_module()
    )
    with open(_IPBUS_TB_GOLDEN) as fp:
        assert generated == fp.read()


def test_ipbus_module_top_matches_golden():
    generated = GeneratorFactory.generate_module_top_vhdl(_build_ipbus_module())
    with open(_IPBUS_TOP_GOLDEN) as fp:
        assert generated == fp.read()


def _prototype_header(method):
    from bust.generators.header_generator import HeaderGenerator

    return getattr(HeaderGenerator(_build_module()), method)()


def test_prototype_headers_match_golden():
    """The generated headers express the bust 1.0 access-mode system and match the
    committed prototype goldens (onread/onwrite/singlepulse/enum included)."""
    hdr = os.path.join(_REPO_ROOT, "example", "example_prototype", "header")
    for filename, method in (
        ("prototype.h", "generate_c_header"),
        ("prototype.hpp", "generate_cpp_header"),
        ("prototype.py", "generate_python_header"),
    ):
        with open(os.path.join(hdr, filename)) as fp:
            assert _prototype_header(method) == fp.read(), filename


def test_prototype_c_header_surfaces_access_modes():
    """Side effects and enums reach the C header, not just sw/hw access."""
    out = _prototype_header("generate_c_header")
    assert '#define PROTOTYPE_REG5_FIELD0_ONREAD "rclr"' in out
    assert '#define PROTOTYPE_REG6_FIELD0_ONWRITE "woset"' in out
    assert "#define PROTOTYPE_REG10_FIELD0_SINGLEPULSE 1" in out
    assert "#define PROTOTYPE_REG11_FIELD0_STATE3 3" in out
    assert "_MODE" not in out  # legacy mode macro is gone


def test_register_without_fields_is_a_bare_member_of_to_hw_and_from_hw():
    """A register without fields has no record of its own: to_hw.<reg> is its
    value, or its value-and-strobe record when it has strobes."""
    bus = Bus({"type": "axi", "addr_width": 32, "data_width": 32})
    module = Module(
        {
            "name": "m",
            "register": [
                {"name": "level", "type": "vector", "width": 8, "sw": "rw", "hw": "r"},
                {"name": "kick", "type": "bit", "sw": "rw", "hw": "r", "swmod": True},
                {"name": "count", "type": "vector", "width": 4, "sw": "ro", "hw": "w"},
                {
                    "name": "load",
                    "type": "vector",
                    "width": 4,
                    "sw": "rw",
                    "hw": "rw",
                    "we": True,
                },
                {
                    "name": "ctrl",
                    "type": "fields",
                    "sw": "rw",
                    "hw": "r",
                    "fields": [{"name": "go", "type": "bit"}],
                },
            ],
        },
        bus,
        settings=None,
    )
    pkg = GeneratorFactory.generate_regfile_package_vhdl(module)
    assert "    level : std_logic_vector(7 downto 0);" in pkg
    assert "    kick : t_m_kick_kick_out;" in pkg
    assert "    count : std_logic_vector(3 downto 0);" in pkg
    assert "    load : t_m_load_load_in;" in pkg
    assert "    ctrl : t_m_ctrl_to_hw;" in pkg
    assert "type t_m_level_to_hw" not in pkg
    assert "type t_m_count_from_hw" not in pkg

    regfile = GeneratorFactory.generate_regfile_vhdl(module)
    assert "  to_hw.level <= regs.level.level;" in regfile
    assert (
        "  to_hw.kick <= (value => regs.kick.kick, swmod => swmod_kick_kick);"
        in regfile
    )
    assert "  to_hw.ctrl <= (go => regs.ctrl.go);" in regfile
    assert "rdata(3 downto 0) <= from_hw.count;" in regfile
    assert "regs.count" not in regfile
    assert "if from_hw.load.we = '1' then" in regfile


def test_module_addr_width_generic_reaches_the_regfile():
    """G_MODULE_ADDR_WIDTH, the module address width, is declared on the top
    wrapper, the endpoint and the regfile, and defaults to C_<MODULE>_MODULE_ADDR_WIDTH.
    """
    module = _build_module()
    default = "G_MODULE_ADDR_WIDTH  : natural := C_PROTOTYPE_MODULE_ADDR_WIDTH"
    for generate in (
        GeneratorFactory.generate_module_top_vhdl,
        GeneratorFactory.generate_axi_endpoint_vhdl,
        GeneratorFactory.generate_regfile_vhdl,
    ):
        hdl = generate(module)
        assert default in hdl
    assert "G_MODULE_ADDR_WIDTH  => G_MODULE_ADDR_WIDTH" in (
        GeneratorFactory.generate_module_top_vhdl(module)
    )
    regfile = GeneratorFactory.generate_regfile_vhdl(module)
    assert "above_registers(lb_m2s.address, G_MODULE_ADDR_WIDTH)" in regfile
    assert "and is_mapped(reg_offset);" in regfile
    assert (
        "if mapped and (is_sw_writable(reg_offset) or not G_ERR_ON_BAD_ACCESS) then"
        in regfile
    )


def test_testbench_checks_unmapped_offsets():
    """The prototype's registers use offsets 0x00..0x2C (6 select bits), so the
    testbench sets G_MODULE_ADDR_WIDTH to 8 and checks 0x30, 0x1, which is one
    byte into reg0, 0x40, which aliases reg0 by its low bits, and 0x100, which
    has another base address."""
    module = _build_module()
    checks = AddressChecks(module)
    assert checks.module_addr_width == 8
    assert [u.hex for u in checks.unmapped_addresses] == [
        "0x30",
        "0x1",
        "0x40",
        "0x100",
    ]
    tb = GeneratorFactory.generate_localbus_axi_testbench_vhdl(module)
    assert "G_MODULE_ADDR_WIDTH  => 8," in tb
    assert 'bus_write_unmapped(f_addr(32x"40"), 32x"0"' in tb
    assert "v_config.expected_response := SLVERR;" in tb
    assert "unchanged by the unmapped writes" in tb


def test_example_c_headers_compile_in_one_file(tmp_path):
    """Each C name starts with the module name, so the example headers, which
    share register names such as reg0, can be included in one source file."""
    cc = shutil.which("cc")
    if cc is None:
        pytest.skip("no C compiler")
    headers = sorted(
        glob.glob(os.path.join(_REPO_ROOT, "example", "*", "header", "*.h"))
    )
    assert len(headers) > 1
    source = tmp_path / "all_headers.c"
    source.write_text(
        "".join(f'#include "{header}"\n' for header in headers)
        + "int main(void) { return EXAMPLE_AXI_REG0_OFFSET + PROTOTYPE_REG0_OFFSET; }\n"
    )
    result = subprocess.run(
        [cc, "-Wall", "-Werror", "-fsyntax-only", str(source)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_axi_and_ipbus_testbenches_share_the_test_body():
    """Both testbenches drive the same bus-neutral self-check sequence; only the
    bus stimulus (procedures, signals, reset) differs."""
    axi = GeneratorFactory.generate_localbus_axi_testbench_vhdl(_build_module())
    ipbus = GeneratorFactory.generate_localbus_ipbus_testbench_vhdl(
        _build_ipbus_module()
    )
    for marker in (
        'bus_check(f_addr(C_PROTOTYPE_REG7_OFFSET), 32x"00000A5A", "reg7 applies onwrite effects");',
        'bus_check(f_addr(C_PROTOTYPE_REG4_OFFSET), 32x"0000000A", "reg4 reflects hwclr");',
        "reg10.field0 singlepulse lasts exactly one cycle",
    ):
        assert marker in axi
        assert marker in ipbus
    assert "axilite_write" in axi and "ipbus_write" in ipbus
    assert "ipbus_write" not in axi and "axilite_write" not in ipbus


def test_testbench_register_categories():
    """The generated testbench covers plain-rw, enum, write-zero, and the onread/
    onwrite software side-effect registers."""
    module = _build_module()
    by_name = {r.name: r for r in module.registers}
    assert [r.name for r in module.registers if r.is_simple_readback] == [
        "reg0",
        "reg3",
        "reg9",
    ]
    assert by_name["reg11"].is_enum_readback
    assert by_name["reg11"].enum_selftest_value_vhdl == '32x"00000003"'  # STATE3
    assert by_name["reg2"].reads_back_zero  # sw write-only
    assert by_name["reg10"].reads_back_zero  # singlepulse

    assert [r.name for r in module.registers if r.is_onread_readback] == ["reg5"]
    assert [r.name for r in module.registers if r.is_onwrite_readback] == [
        "reg6",
        "reg7",
        "reg8",
    ]
    assert [r.name for r in module.registers if r.is_hw_driven_readback] == ["reg1"]

    # Predicted readbacks match the simulation-verified hand-written testbench.
    assert by_name["reg5"].onread_post_read_value_vhdl == '32x"000000F0"'
    assert by_name["reg7"].onwrite_expected_value_vhdl == '32x"00000A5A"'
    assert by_name["reg8"].onwrite_expected_value_vhdl == '32x"000000F0"'
    # reg1 = field2(5)|field1(4)|field0(3:0) = 1|1|0101 = 0x35.
    assert by_name["reg1"].hw_driven_expected_value_vhdl == '32x"00000035"'

    # to_hw value checks ride along with the plain rw round-trip on hw-readable
    # registers; reg3 (hw na) contributes none.
    assert [f.name for f in by_name["reg0"].to_hw_fields] == ["field0", "field1"]
    assert by_name["reg3"].to_hw_fields == []
    assert by_name["reg0"].fields[1].all_ones_literal == '2x"3"'

    # reg4 exercises hw we override + hwset + hwclr; the scenario must reproduce
    # the simulation-verified value sequence 0x105 -> 0x10A -> 0x10A -> 0x00A.
    assert [r.name for r in module.registers if r.is_hw_modify_register] == ["reg4"]
    assert [s["expected"] for s in by_name["reg4"].hw_modify_steps] == [
        '32x"00000105"',
        '32x"0000010A"',
        '32x"0000010A"',
        '32x"0000000A"',
    ]

    # reg9/reg10 emit to_hw strobes counted by the generated monitor process.
    assert [r.name for r in module.strobe_registers] == ["reg9", "reg10"]
    assert [f.name for f in by_name["reg9"].swmod_fields] == ["field0"]
    assert [f.name for f in by_name["reg9"].swacc_fields] == ["field1"]
    assert [f.name for f in by_name["reg10"].singlepulse_fields] == ["field0"]


def test_sparse_enum_encodes_by_value_not_position():
    """to_slv must follow each enum's declared value, not its literal position;
    a sparse enum (A=0, D=3) round-trips only if D encodes to "11"."""
    cfg = {
        "name": "m",
        "description": "",
        "byte_addressable": True,
        "register": [
            {
                "name": "r0",
                "type": "fields",
                "sw": "rw",
                "hw": "r",
                "fields": [
                    {
                        "name": "f",
                        "type": "vector",
                        "width": 2,
                        "sw": "rw",
                        "hw": "r",
                        "enums": [{"name": "A", "value": 0}, {"name": "D", "value": 3}],
                    }
                ],
            }
        ],
    }
    bus = Bus({"type": "axi", "data_width": 32, "addr_width": 32, "reset": "async"})
    pkg = GeneratorFactory.generate_regfile_package_vhdl(
        Module(cfg, bus, settings=None)
    )
    assert 'when D => slv := "11";' in pkg
    assert "'pos(v)" not in pkg


def test_selftest_value_covers_non_nibble_width():
    """The self-test literal uses ceil(width/4) hex digits, so non-nibble data
    widths are not truncated."""
    from bust.core.register import Register

    reg = Register(
        {"name": "r", "type": "vector", "width": 18, "mode": "rw"}, 0, "m", 18
    )
    assert reg.selftest_value_vhdl == '18x"3FFFF"'


def _one_register_module(bus):
    return Module(
        {"name": "m", "register": [{"name": "r", "type": "default", "mode": "rw"}]},
        bus,
        settings=None,
    )


def test_module_top_instantiates_axi_endpoint():
    out = GeneratorFactory.generate_module_top_vhdl(_one_register_module(_axi_bus()))
    assert "entity m is" in out
    assert "i_endpoint : entity work.m_axi_endpoint" in out
    assert "awaddr" in out and "rready" in out


def test_module_top_instantiates_ipb_endpoint():
    bus = Bus(
        {"type": "ipbus", "addr_width": 32, "data_width": 32, "comp_library": "bust"}
    )
    out = GeneratorFactory.generate_module_top_vhdl(_one_register_module(bus))
    assert "entity m is" in out
    assert "i_endpoint : entity work.m_ipb_endpoint" in out
    assert "ipb_in" in out and "ipb_out" in out
    assert "use ipbus.ipbus.all;" in out


def _axi_bus():
    return Bus(
        {"type": "axi", "addr_width": 32, "data_width": 32, "comp_library": "bust"}
    )


def test_constant_only_module_omits_empty_record_families():
    """A field that holds no state and is not hw-driven must not produce empty
    storage / from_hw records (an empty VHDL record is illegal)."""
    reg = {
        "name": "stat",
        "sw": "ro",
        "hw": "r",
        "type": "fields",
        "fields": [{"name": "id", "type": "vector", "width": 8}],
    }
    module = Module({"name": "ronly", "register": [reg]}, _axi_bus(), settings=None)
    out = GeneratorFactory.generate_regfile_package_vhdl(module)

    assert not re.search(r"is record\s+end record", out)
    assert "type t_ronly_regs is record" not in out
    assert "C_RONLY_REGS_RESET" not in out
    assert "type t_ronly_from_hw is record" not in out
    assert "type t_ronly_to_hw is record" in out
    assert "return reg_addr_match(reg_offset, C_RONLY_STAT_OFFSET);" in out


def test_constant_only_entity_uses_literals_not_regs():
    """The entity must not reference the `regs` signal for a module whose fields
    hold no state (the storage record is omitted); reads/outputs use the constant."""
    reg = {
        "name": "stat",
        "sw": "ro",
        "hw": "r",
        "type": "fields",
        "fields": [{"name": "id", "type": "vector", "width": 8, "reset": "0xAB"}],
    }
    module = Module({"name": "ronly", "register": [reg]}, _axi_bus(), settings=None)
    out = GeneratorFactory.generate_regfile_vhdl(module)

    assert "signal regs " not in out
    assert "regs." not in out
    assert 'rdata(7 downto 0) <= 8X"AB";' in out
    assert 'to_hw.stat <= (id => 8X"AB");' in out


def test_non_fields_registers_normalize_to_implicit_field():
    """A bit/vector/default register stands for one full-width field named after
    it, so the field-based regfile generator works on legacy register maps."""
    registers = [
        {"name": "flag", "type": "bit", "mode": "rw"},
        {"name": "word", "type": "vector", "width": 12, "mode": "rw"},
        {"name": "whole", "type": "default", "mode": "rw"},
    ]
    module = Module(
        {"name": "legacy", "register": registers}, _axi_bus(), settings=None
    )

    flag, word, whole = module.registers
    assert flag.fields == []  # legacy generator still sees no fields
    assert [f.name for f in flag.effective_fields] == ["flag"]
    assert [f.name for f in word.effective_fields] == ["word"]
    assert [f.name for f in whole.effective_fields] == ["whole"]

    pkg = GeneratorFactory.generate_regfile_package_vhdl(module)
    assert "field0" not in pkg
    assert "flag : std_logic;" in pkg
    assert "word : std_logic_vector(11 downto 0);" in pkg
    # default register spans the full module data width (32).
    assert "whole : std_logic_vector(31 downto 0);" in pkg
    # The whole stack generates without referencing a non-existent member.
    GeneratorFactory.generate_regfile_vhdl(module)
    GeneratorFactory.generate_axi_endpoint_vhdl(module)


def _generate_only_localbus(out_dir, gen_localbus):
    cfg_path = os.path.join(_REPO_ROOT, "example", "example_axi.json")
    cfg = json_parser(cfg_path)
    settings = Settings(cfg_path, cfg.get("settings"))
    bus = Bus(cfg["bus"])
    module = Module(cfg["module"], bus, settings)
    gen_settings = {
        "dir": str(out_dir),
        "force_ow": True,
        "gen_doc": False,
        "gen_pdf": False,
        "gen_header": False,
        "gen_localbus": gen_localbus,
    }
    generate_output(settings, bus, module, None, None, gen_settings)
    return os.path.join(str(out_dir), "example_axi", "hdl")


_LOCALBUS_FILES = (
    "example_axi_localbus_pkg.vhd",
    "example_axi_regfile_pkg.vhd",
    "example_axi_regfile.vhd",
    "example_axi_axi_endpoint.vhd",
    "example_axi.vhd",
)


def test_localbus_flag_emits_local_bus_files(tmp_path):
    hdl = _generate_only_localbus(tmp_path, gen_localbus=True)
    for name in _LOCALBUS_FILES:
        assert os.path.isfile(os.path.join(hdl, name))
    tb = os.path.join(str(tmp_path), "example_axi", "tb", "example_axi_tb.vhd")
    assert os.path.isfile(tb)


def test_localbus_flag_off_emits_nothing(tmp_path):
    hdl = _generate_only_localbus(tmp_path, gen_localbus=False)
    for name in _LOCALBUS_FILES:
        assert not os.path.isfile(os.path.join(hdl, name))


def test_empty_module_is_mapped_returns_false():
    """is_mapped must be valid VHDL when the module has no registers."""
    module = Module({"name": "empty", "register": []}, _axi_bus(), settings=None)
    out = GeneratorFactory.generate_regfile_package_vhdl(module)
    assert "return false;" in out
    assert "return ;" not in out


_ON_OFF = [{"name": "DISABLED", "value": 0}, {"name": "ENABLED", "value": 1}]


def _fields_module(*fields, **defaults):
    """Module with one fields register `r`; `defaults` are its access defaults."""
    reg = dict({"name": "r", "type": "fields", "fields": list(fields)}, **defaults)
    return Module({"name": "m", "register": [reg]}, _axi_bus(), settings=None)


def test_hwset_without_write_enable_takes_the_value_member():
    """from_hw.<reg>.<field> is a record once hwset/hwclr add strobes, so the
    every-cycle hardware write must read its value member."""
    module = _fields_module(
        {"name": "f", "type": "vector", "width": 4, "hwset": True}, sw="ro", hw="w"
    )
    out = GeneratorFactory.generate_regfile_vhdl(module)
    assert "regs.r.f <= from_hw.r.f.value;" in out
    assert "regs.r.f <= from_hw.r.f;" not in out


def test_bit_enum_encodes_as_one_element_vector():
    module = _fields_module(
        {"name": "lo", "type": "bit"},
        {"name": "f", "type": "bit", "enums": _ON_OFF},
        sw="rw",
        hw="r",
    )
    pkg = GeneratorFactory.generate_regfile_package_vhdl(module)
    regfile = GeneratorFactory.generate_regfile_vhdl(module)
    assert "function to_m_r_f(s : std_logic_vector(0 downto 0)) return t_m_r_f;" in pkg
    assert "variable slv : std_logic_vector(0 downto 0);" in pkg
    assert 'when "1" => return ENABLED;' in pkg
    assert "regs.r.f <= to_m_r_f(lb_m2s.wdata(1 downto 1));" in regfile
    assert "rdata(1 downto 1) <= to_slv(regs.r.f);" in regfile


def test_hw_written_enum_testbench_default_is_its_reset_literal():
    states = [{"name": n, "value": v} for n, v in (("A", 0), ("B", 1), ("C", 2))]
    module = _fields_module(
        {"name": "a", "type": "vector", "width": 2, "reset": "0x2", "enums": states},
        {"name": "b", "type": "bit", "we": True, "enums": _ON_OFF},
        sw="ro",
        hw="w",
    )
    tb = GeneratorFactory.generate_localbus_axi_testbench_vhdl(module)
    assert "r => (a => C, b => (value => DISABLED, we => '0')));" in tb


def test_constant_enum_read_is_type_qualified():
    """Enum literal names may repeat across fields, so a constant's literal is
    qualified to keep to_slv unambiguous."""
    module = _fields_module(
        {"name": "a", "type": "bit", "reset": "0x1", "enums": _ON_OFF},
        {"name": "b", "type": "bit", "enums": _ON_OFF},
        sw="ro",
        hw="r",
    )
    out = GeneratorFactory.generate_regfile_vhdl(module)
    assert "rdata(0 downto 0) <= to_slv(t_m_r_a'(ENABLED));" in out
    assert "rdata(1 downto 1) <= to_slv(t_m_r_b'(DISABLED));" in out
    assert "to_hw.r <= (a => t_m_r_a'(ENABLED), b => t_m_r_b'(DISABLED));" in out


def _strobe_read(module):
    reg = module.registers[0]
    tb = GeneratorFactory.generate_localbus_axi_testbench_vhdl(module)
    expected = reg.strobe_readback_value_vhdl
    assert f'bus_check(f_addr(C_M_R_OFFSET), {expected}, "read r");' in tb
    return expected


def test_strobe_read_applies_write_effects():
    """woclr: writing all ones clears the field, so the read returns 0."""
    module = _fields_module(
        {"name": "f", "type": "vector", "width": 4, "onwrite": "woclr", "swacc": True},
        sw="rw",
        hw="r",
    )
    assert _strobe_read(module) == '32x"00000000"'


def test_strobe_read_continues_from_the_onwrite_test():
    """The onwrite test runs first and leaves wot at 0x5; the strobe write of 0xF
    then toggles it to 0xA, not to the 0xF a write from reset would give."""
    module = _fields_module(
        {"name": "f", "type": "vector", "width": 4, "onwrite": "wot", "swacc": True},
        sw="rw",
        hw="r",
    )
    assert module.registers[0].is_onwrite_readback
    assert _strobe_read(module) == '32x"0000000A"'


def test_strobe_read_of_mixed_register():
    module = _fields_module(
        {"name": "acc", "type": "vector", "width": 4, "swacc": True},
        {"name": "fixed", "type": "vector", "width": 4, "sw": "ro", "reset": "0x9"},
        {"name": "arg", "type": "vector", "width": 4, "sw": "wo"},
        {"name": "go", "type": "bit", "singlepulse": True},
        {"name": "mode", "type": "bit", "enums": _ON_OFF},
        sw="rw",
        hw="r",
    )
    # acc=0xF, fixed=0x9, arg unreadable, go self-cleared, mode decodes 1 to ENABLED.
    assert _strobe_read(module) == '32x"0000209F"'


def test_strobe_read_decodes_an_undefined_enum_encoding_to_the_first_literal():
    states = [{"name": n, "value": v} for n, v in (("A", 0), ("B", 1), ("C", 2))]
    module = _fields_module(
        {"name": "f", "type": "vector", "width": 2, "swacc": True, "enums": states},
        sw="rw",
        hw="r",
    )
    assert _strobe_read(module) == '32x"00000000"'


def test_strobe_read_of_hw_written_field_returns_the_hw_input():
    """The status test drives 0x5 and leaves it applied; a software write cannot
    change a read-only field the hardware rewrites every cycle."""
    module = _fields_module(
        {"name": "f", "type": "vector", "width": 4, "swacc": True}, sw="ro", hw="rw"
    )
    assert module.registers[0].is_hw_driven_readback
    assert _strobe_read(module) == '32x"00000005"'


def test_singlepulse_returns_to_its_reset_value():
    module = _fields_module(
        {"name": "go", "type": "vector", "width": 4, "reset": "0xa"},
        sw="wo",
        hw="r",
        singlepulse=True,
    )
    regfile = GeneratorFactory.generate_regfile_vhdl(module)
    assert 'regs.r.go <= 4X"A";' in regfile
    assert "regs.r.go <= (others => '0');" not in regfile


def test_singlepulse_testbench_detects_the_pulse_against_the_reset_value():
    """The monitor counts cycles away from the reset value, and the strobe test
    writes the inverse of the reset so every bit of the pulse is visible."""
    module = _fields_module(
        {"name": "go", "type": "vector", "width": 4, "reset": "0xa"},
        {"name": "arm", "type": "bit", "reset": "0x1"},
        sw="wo",
        hw="r",
        singlepulse=True,
    )
    tb = GeneratorFactory.generate_localbus_axi_testbench_vhdl(module)
    assert 'signal r_go_sp_value : std_logic_vector(3 downto 0) := 4X"A";' in tb
    assert 'if to_hw.r.go /= 4x"A" then' in tb
    assert "if to_hw.r.arm /= '1' then" in tb
    # go=0x5 (inverse of 0xA) in bits 3:0, arm=0 (inverse of 1) in bit 4.
    assert 'bus_write(f_addr(C_M_R_OFFSET), 32x"00000005", "write r");' in tb
    assert 'check_value(r_go_sp_value, 4x"5", error,' in tb
    assert "check_value(r_arm_sp_value, '0', error," in tb


def test_readable_singlepulse_reads_back_its_reset_value():
    module = _fields_module(
        {"name": "acc", "type": "vector", "width": 4, "swacc": True},
        {
            "name": "go",
            "type": "vector",
            "width": 4,
            "reset": "0xa",
            "singlepulse": True,
        },
        sw="rw",
        hw="r",
    )
    reg = module.registers[0]
    assert reg.fields[1].written_result(0x5) == 0xA
    assert not reg.reads_back_zero
    # acc=0xF, go back at its reset 0xA after the pulse of 0x5.
    assert reg.strobe_write_value_vhdl == '32x"0000005F"'
    assert _strobe_read(module) == '32x"000000AF"'


def test_write_only_singlepulse_with_nonzero_reset_still_reads_back_zero():
    module = _fields_module(
        {"name": "go", "type": "vector", "width": 4, "reset": "0xa"},
        sw="wo",
        hw="r",
        singlepulse=True,
    )
    assert module.registers[0].reads_back_zero


def _p_write(module):
    regfile = GeneratorFactory.generate_regfile_vhdl(module)
    return regfile[regfile.index("p_write : process") : regfile.index("end process")]


def test_hardware_updates_override_onread_effects_in_the_same_cycle():
    """In p_write the last assignment wins, so each register's onread effects
    must come before its hwclr/hwset/we chain: a hardware set in the cycle of a
    read clear is then kept, not lost."""
    module = _fields_module(
        {"name": "f", "type": "bit", "hwset": True, "hwclr": True, "onread": "rclr"},
        {
            "name": "g",
            "type": "vector",
            "width": 4,
            "hw": "rw",
            "we": True,
            "onread": "rset",
        },
        sw="rw",
        hw="r",
    )
    p_write = _p_write(module)
    onread = p_write.index(
        "if rd_service and reg_addr_match(reg_offset, C_M_R_OFFSET) then"
    )
    assert onread < p_write.index("if from_hw.r.f.clr = '1' then")
    assert onread < p_write.index("if from_hw.r.g.we = '1' then")
    assert p_write.count("rd_service and reg_addr_match(reg_offset, C_M_R_OFFSET)") == 1


def test_sticky_flag_testbench_checks_hwset_against_the_read_clear():
    """With hwset held through a read, the value sampled with the swacc strobe
    is what the colliding cycle left: set, with hardware taking precedence."""
    module = _fields_module(
        {
            "name": "pending",
            "type": "bit",
            "hwset": True,
            "onread": "rclr",
            "swacc": True,
        },
        sw="ro",
        hw="r",
    )
    assert module.registers[0].is_hwset_read_clear_register
    tb = GeneratorFactory.generate_localbus_axi_testbench_vhdl(module)
    assert "r_pending_at_swacc <= to_hw.r.pending.value;" in tb
    sequence = tb[tb.index("hwset beats a read clear") :]
    assert sequence.index("from_hw.r.pending.set <= '1';") < sequence.index(
        'bus_check(f_addr(C_M_R_OFFSET), 32x"00000001", "r read while hwset is held");'
    )
    assert "check_value(r_pending_at_swacc, '1', error," in sequence
    assert 'bus_check(f_addr(C_M_R_OFFSET), 32x"0", "r cleared by a read' in sequence


@pytest.mark.parametrize(
    "change",
    [{"swacc": False}, {"onread": "rset"}, {"hw": "rw", "we": True}],
    ids=["no-swacc", "rset", "hw-write"],
)
def test_sticky_flag_check_needs_hwset_rclr_swacc_and_no_hw_write(change):
    field = dict(
        {"name": "f", "type": "bit", "hwset": True, "onread": "rclr", "swacc": True},
        **change,
    )
    module = _fields_module(field, sw="ro", hw="r")
    assert not module.registers[0].is_hwset_read_clear_register


def test_enum_without_a_zero_literal_reports_the_reset_hardware_uses():
    """Without a reset or a literal of value 0, hardware resets to the first
    literal. Headers, docs and the register reset must say the same."""
    from bust.generators.header_generator import HeaderGenerator

    states = [{"name": "LOW", "value": 1}, {"name": "HIGH", "value": 2}]
    module = _fields_module(
        {"name": "lo", "type": "vector", "width": 4},
        {"name": "mode", "type": "vector", "width": 2, "enums": states},
        sw="rw",
        hw="r",
    )
    reg = module.registers[0]
    assert reg.fields[1].reset == "0x1"
    assert reg.reset == "0x10"
    assert "reset" not in reg.fields[1].return_dic()

    pkg = GeneratorFactory.generate_regfile_package_vhdl(module)
    assert "r => (lo => (others => '0'), mode => LOW));" in pkg
    header = HeaderGenerator(module)
    assert "#define M_R_RESET 0x10" in header.generate_c_header()
    assert "#define M_R_MODE_RESET 0x1" in header.generate_c_header()
    assert "const uint32_t R_MODE_RESET = 0x1;" in header.generate_cpp_header()
    assert "R_MODE_RESET = 0x1" in header.generate_python_header()

    pytest.importorskip("pylatexenc")
    from bust.generators.documentation_generator import DocumentationGenerator

    tex = DocumentationGenerator(module).generate_tex_documentation()
    assert "\\regfield{mode}{2}{4}{{0x1}}" in tex
    assert "& \\texttt{0x10} \\\\" in tex
