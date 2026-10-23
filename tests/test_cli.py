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


def test_save_addresses_with_force_changes_only_addresses(tmp_path):
    register_map = json.loads(json.dumps(_REGISTER_MAP))
    register_map["bus"]["owner"] = "regs"
    register_map["module"]["register"].append(
        {"name": "status", "sw": "ro", "hw": "w", "address": "0x10"}
    )
    path = tmp_path / "timer.json"
    path.write_text(json.dumps(register_map, indent=4))

    code, output = _run_bust(tmp_path, path.name, "-a", "-f")

    assert code == 0, output
    register_map["module"]["register"][0]["address"] = "0x0"
    register_map["module"]["register"][1]["address"] = "0x4"
    assert json.loads(path.read_text()) == register_map


def test_save_addresses_in_order_does_not_write(tmp_path):
    register_map = json.loads(json.dumps(_REGISTER_MAP))
    register_map["module"]["register"][0]["address"] = 0
    path = _write_register_map(tmp_path, register_map)
    os.utime(path, (0, 0))

    code, output = _run_bust(tmp_path, path.name, "-a")

    assert code == 0, output
    assert "are in order already" in output
    assert os.stat(path).st_mtime == 0


def test_save_addresses_without_terminal_asks_for_force(tmp_path):
    path = _write_register_map(tmp_path)
    original = path.read_text()

    code, output = _run_bust(tmp_path, path.name, "-a")

    assert code == 1
    assert "Run bust with -f to overwrite it." in output
    assert path.read_text() == original


def test_register_error_is_reported_once_with_its_cause(tmp_path):
    register_map = json.loads(json.dumps(_REGISTER_MAP))
    register_map["module"]["register"][0]["fields"][0].update(type="vector", width=40)
    path = _write_register_map(tmp_path, register_map)

    code, output = _run_bust(tmp_path, str(path), "-o", "out", "-p")

    assert code == 1
    assert "Could not parse register ctrl:" in output
    assert output.count("Register width exceeded module data width") == 1
    assert "misspelt" not in output


def test_bust_0_14_key_points_to_migrate(tmp_path):
    register_map = json.loads(json.dumps(_REGISTER_MAP))
    register_map["module"]["register"][0]["pulse_cycles"] = 1
    path = _write_register_map(tmp_path, register_map)

    code, output = _run_bust(tmp_path, str(path), "-o", "out", "-p")

    assert code == 1
    assert (
        "module.register[0].pulse_cycles: a bust 0.14 key, which bust no longer "
        "reads. Run bust with --migrate to convert the file."
    ) in output
    assert not (tmp_path / "out").exists()


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
    assert (
        "module.register[0].fields[0].onwrit: bust does not know this key and "
        "ignores it. Did you mean 'onwrite'?"
    ) in output


def test_editor_without_terminal_fails(tmp_path):
    path = _write_register_map(tmp_path)

    code, output = _run_bust(tmp_path, str(path), "-e")

    assert code == 1
    assert "needs an interactive terminal" in output


def test_bust_0_14_options_are_gone(tmp_path):
    path = _write_register_map(tmp_path)

    for option in ("-u", "-b", "-t", "-m", "-F"):
        code, output = _run_bust(tmp_path, str(path), "-o", "out", "-d", option)

        assert code == 1, output
        assert "Usage:" in output
    assert not (tmp_path / "out").exists()


def test_empty_version_leaves_no_version_label_in_the_latex(tmp_path):
    path = _write_register_map(tmp_path)

    code, output = _run_bust(tmp_path, str(path), "-o", "out", "-p")

    assert code == 0, output
    tex = (tmp_path / "out/timer/doc/timer.tex").read_text()
    assert "\\author{Register map hash: \\texttt{0x" in tex
    assert "Version:" not in tex


def test_successful_run_writes_no_debug_log(tmp_path):
    path = _write_register_map(tmp_path)

    code, output = _run_bust(tmp_path, str(path), "-o", "out", "-p")

    assert code == 0, output
    assert not (tmp_path / "debug.log").exists()


def test_failed_run_writes_debug_log(tmp_path):
    register_map = json.loads(json.dumps(_REGISTER_MAP))
    register_map["bus"]["data_width"] = 12
    path = _write_register_map(tmp_path, register_map)

    code, output = _run_bust(tmp_path, str(path), "-o", "out")

    assert code == 1
    log = (tmp_path / "debug.log").read_text()
    assert "data_width must be a whole number of bytes" in log
    assert "Traceback" in log
    assert f"bust {path} -o out" in log.splitlines()[0]


def test_failed_runs_append_to_debug_log(tmp_path):
    register_map = json.loads(json.dumps(_REGISTER_MAP))
    register_map["bus"]["type"] = "pci"
    path = _write_register_map(tmp_path, register_map)

    for out in ("first", "second"):
        code, output = _run_bust(tmp_path, str(path), "-o", out)
        assert code == 1, output

    runs = [
        line
        for line in (tmp_path / "debug.log").read_text().splitlines()
        if line.startswith("=== ")
    ]
    assert len(runs) == 2
    assert runs[0].endswith("-o first") and runs[1].endswith("-o second")


def test_every_schema_problem_is_reported_with_its_line(tmp_path):
    register_map = json.loads(json.dumps(_REGISTER_MAP))
    register = register_map["module"]["register"][0]
    register["sw"] = "rx"
    register["fields"][0]["type"] = "bits"
    path = tmp_path / "timer.json"
    path.write_text(json.dumps(register_map, indent=2))

    code, output = _run_bust(tmp_path, "timer.json", "-o", "out")

    assert code == 1
    assert (
        'timer.json:13: module.register[0].sw: "rx" is not one of "rw", "ro", '
        '"wo", "na". Did you mean "rw"?'
    ) in output
    assert (
        'timer.json:20: module.register[0].fields[0].type: "bits" is not one of '
        '"vector", "bit". Did you mean "bit"?'
    ) in output
    assert "2 problems in timer.json" in output
    assert not (tmp_path / "out").exists()


def test_missing_file(tmp_path):
    code, output = _run_bust(tmp_path, "nothing.json")

    assert code == 1
    assert "Cannot read nothing.json: No such file or directory" in output
    assert "unknown error" not in output


def test_json_syntax_error_gives_the_place(tmp_path):
    (tmp_path / "timer.json").write_text(
        '{\n  "bus": {"type": "axi"\n  "module": {}\n}'
    )

    code, output = _run_bust(tmp_path, "timer.json")

    assert code == 1
    assert "timer.json:3:3: Expecting ',' delimiter" in output
    assert "unknown error" not in output
