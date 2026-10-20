"""The bust command line, run as a subprocess the way a user or CI runs it."""

import json
import os
import subprocess
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))

_REGISTER_MAP = {
    "bus": {"type": "axi", "addr_width": 32, "data_width": 32},
    "module": {
        "name": "timer",
        "description": "A timer.",
        "register": [
            {
                "name": "ctrl",
                "sw": "rw",
                "hw": "r",
                "type": "fields",
                "description": "Control.",
                "fields": [{"name": "enable", "type": "bit"}],
            }
        ],
    },
}


def _write_register_map(tmp_path, register_map=None):
    path = tmp_path / "timer.json"
    path.write_text(json.dumps(register_map or _REGISTER_MAP))
    return path


def _run_bust(tmp_path, *args):
    """Run bust with stdin closed, as in CI, and return (exit code, output)."""
    result = subprocess.run(
        [sys.executable, "-m", "bust", *args],
        cwd=str(tmp_path),
        env=dict(
            os.environ,
            PYTHONPATH=os.pathsep.join(
                filter(None, [_REPO_ROOT, os.environ.get("PYTHONPATH")])
            ),
        ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.returncode, result.stdout


def test_file_without_settings_generates(tmp_path):
    path = _write_register_map(tmp_path)

    code, output = _run_bust(tmp_path, str(path), "-o", "out", "-p")

    assert code == 0, output
    assert (tmp_path / "out" / "timer" / "hdl" / "timer.vhd").is_file()


def test_existing_output_without_terminal_asks_for_force(tmp_path):
    path = _write_register_map(tmp_path)
    _run_bust(tmp_path, str(path), "-o", "out", "-p")

    code, output = _run_bust(tmp_path, str(path), "-o", "out", "-p")

    assert code == 1
    assert "Run bust with -f to overwrite it." in output


def test_save_addresses_with_force(tmp_path):
    register_map = dict(
        _REGISTER_MAP,
        settings={"coverage": True},
        bus=dict(_REGISTER_MAP["bus"], comp_library="regs"),
    )
    path = _write_register_map(tmp_path, register_map)

    code, output = _run_bust(tmp_path, path.name, "-a", "-f")

    assert code == 0, output
    saved = json.loads(path.read_text())
    assert saved["module"]["register"][0]["address"] == "0x0"
    assert saved["settings"]["coverage"] is True
    assert saved["bus"] == {
        "type": "axi",
        "addr_width": 32,
        "data_width": 32,
        "comp_library": "regs",
    }


def test_save_addresses_without_terminal_asks_for_force(tmp_path):
    path = _write_register_map(tmp_path)
    original = path.read_text()

    code, output = _run_bust(tmp_path, path.name, "-a")

    assert code == 1
    assert "Run bust with -f to overwrite it." in output
    assert path.read_text() == original


def test_register_error_is_reported_once_with_its_cause(tmp_path):
    register_map = json.loads(json.dumps(_REGISTER_MAP))
    register_map["module"]["register"][0]["pulse_cycles"] = 4
    path = _write_register_map(tmp_path, register_map)

    code, output = _run_bust(tmp_path, str(path), "-o", "out", "-p")

    assert code == 1
    assert "Could not parse register ctrl:" in output
    assert "pulse_cycles=4 is not supported" in output
    assert "misspelt" not in output


def test_file_in_the_working_directory_writes_next_to_it(tmp_path):
    path = _write_register_map(tmp_path)

    code, output = _run_bust(tmp_path, path.name, "-p")

    assert code == 0, output
    assert (tmp_path / "timer" / "hdl" / "timer.vhd").is_file()


def test_unknown_key_is_reported(tmp_path):
    register_map = json.loads(json.dumps(_REGISTER_MAP))
    register_map["module"]["register"][0]["fields"][0]["onwrit"] = "woclr"
    path = _write_register_map(tmp_path, register_map)

    code, output = _run_bust(tmp_path, str(path), "-o", "out", "-p")

    assert code == 0, output
    assert "Unknown key 'onwrit' in field enable of register ctrl is ignored" in output


def test_editor_without_terminal_fails(tmp_path):
    path = _write_register_map(tmp_path)

    code, output = _run_bust(tmp_path, str(path), "-e")

    assert code == 1
    assert "needs an interactive terminal" in output


def test_bust_0_14_options_are_ignored_with_a_warning(tmp_path):
    path = _write_register_map(tmp_path)

    code, output = _run_bust(
        tmp_path, str(path), "-o", "out", "-d", "-u", "-b", "-t", "-m"
    )

    assert code == 0, output
    for option in ("-u", "-b", "-t", "-m"):
        assert f"Ignoring {option}, a bust 0.14 option" in output
    assert (tmp_path / "out/timer/tb/timer_tb.vhd").is_file()


def test_empty_version_leaves_no_version_label_in_the_latex(tmp_path):
    path = _write_register_map(tmp_path)

    code, output = _run_bust(tmp_path, str(path), "-o", "out", "-p")

    assert code == 0, output
    tex = (tmp_path / "out/timer/doc/timer.tex").read_text()
    assert "\\author{}" in tex
    assert "Version:" not in tex


def test_successful_run_writes_no_debug_log(tmp_path):
    path = _write_register_map(tmp_path)

    code, output = _run_bust(tmp_path, str(path), "-o", "out", "-p")

    assert code == 0, output
    assert not (tmp_path / "debug.log").exists()


def test_failed_run_writes_debug_log(tmp_path):
    register_map = json.loads(json.dumps(_REGISTER_MAP))
    register_map["bus"]["type"] = "pci"
    path = _write_register_map(tmp_path, register_map)

    code, output = _run_bust(tmp_path, str(path), "-o", "out")

    assert code == 1
    log = (tmp_path / "debug.log").read_text()
    assert "Bus type is not valid: pci" in log
    assert "Traceback" in log
