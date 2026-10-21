# Command line

bust reads one JSON register map and writes the VHDL, the testbench, the
headers and the documentation for it. This page lists the options, where the
files go, and what bust does when they already exist.

## Usage

`bust --help` starts with the usage lines:

```text
Usage:
  bust FILE [-o DIR] [[[-F | -f] [-d | -p] [-i] [--replace-top] [-u] [-b] [-t] [-m]] | [-a [-F | -f]] | [--migrate [-F | -f]] | [-c | -e]]
  bust --version
  bust -h | --help
```

`FILE` is the JSON register map, described in
[Register map format](register-map-format.md). The usage line also says which
options go together:

- `-o` combines with everything else, but only a run that generates files
  uses it.
- `-f` (or `-F`), one of `-d` and `-p`, and `-i` combine with each other. They
  control a normal run that generates files. So do `-u`, `-b`, `-t` and `-m`,
  which bust ignores.
- `-a` saves the JSON file instead of generating files. It takes `-f` (or `-F`)
  to save without asking.
- `-c` and `-e` open the editor, so they stand alone.

Any other combination, such as `-d -p` or `-c -f`, makes bust print the usage
and exit with status 1.

## Options

| Option         | Effect                                                                                                                                                                  |
|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-o DIR`       | Write the output under `DIR` instead of next to the JSON file. See [Output directory](#output-directory).                                                                 |
| `-f`           | Overwrite existing files without asking, except `<module>.vhd`, which is yours. See [Existing files](#existing-files).                                               |
| `-F`           | The same as `-f`.                                                                                                                                                       |
| `-d`           | Do not write the documentation, neither the `.tex` file nor the PDF.                                                                                                    |
| `-p`           | Write the `.tex` file, but do not run `pdflatex` to make the PDF.                                                                                                       |
| `-i`           | Do not write the headers: the `.h`, `.hpp` and `.py` files, and for IPBus the `.xml` address table.                                                                     |
| `--replace-top` | Replace `<module>.vhd` with a fresh starter and keep the old file as `<module>.vhd.bak`. Asks first unless you add `-f`. See [Your top level](#your-top-level). |
| `-u`, `-b`, `-t`, `-m` | Ignored, with a warning. These bust 0.14 options are accepted so that old command lines and Makefiles keep working. Remove them when you can.                    |
| `-a`           | Give every register a new address and save the JSON file. Generates nothing. With `-f`, saves without asking. See [Renumber addresses](#renumber-addresses).          |
| `--migrate`    | Migrate a bust 0.14 JSON file and its `<module>.vhd`. Generates nothing. With `-f`, without asking. See [Upgrading](upgrading.md#migrate-with---migrate). |
| `-c`           | Create `FILE` with the interactive editor. See [Interactive editor](#interactive-editor).                                                                               |
| `-e`           | Open `FILE` in the interactive editor.                                                                                                                                  |
| `--version`    | Print `bust` and the version, such as `bust v1.0.0a2`, then exit.                                                                                                       |
| `-h`, `--help` | Print the usage and a short description of each option, then exit.                                                                                                      |

Every run that generates files writes the VHDL files and the testbench. No
option turns them off. [Headers and documentation](headers-and-docs.md)
describes the headers, the address table and the documentation.

## Output directory

bust writes into `-o DIR`, or else into the directory that holds the JSON
file. There it adds a directory named after the module (the `name` in the
`module` section).

Inside that directory, bust writes four directories. This is the output of
`bust example_ipbus.json -o out` for the IPBus example from the repository,
with `pdflatex` installed:

```text
out/
└── example_ipbus/
    ├── doc/
    │   ├── example_ipbus.aux
    │   ├── example_ipbus.log
    │   ├── example_ipbus.pdf
    │   └── example_ipbus.tex
    ├── hdl/
    │   ├── example_ipbus.vhd
    │   ├── example_ipbus_ipb_endpoint.vhd
    │   ├── example_ipbus_localbus_pkg.vhd
    │   ├── example_ipbus_regfile.vhd
    │   └── example_ipbus_regfile_pkg.vhd
    ├── header/
    │   ├── example_ipbus.h
    │   ├── example_ipbus.hpp
    │   ├── example_ipbus.py
    │   └── example_ipbus.xml
    └── tb/
        └── example_ipbus_tb.vhd
```

| Directory | Files                                                                                                     | Described in                                       |
|-----------|-----------------------------------------------------------------------------------------------------------|----------------------------------------------------|
| `hdl/`    | `<module>_localbus_pkg.vhd`, `<module>_regfile_pkg.vhd`, `<module>_regfile.vhd`, the endpoint, `<module>.vhd` | [Generated HDL](generated-hdl.md)                  |
| `tb/`     | `<module>_tb.vhd`                                                                                         | [Testbenches](testbenches.md)                      |
| `header/` | `<module>.h`, `<module>.hpp`, `<module>.py`, and `<module>.xml` for IPBus                                 | [Headers and documentation](headers-and-docs.md)   |
| `doc/`    | `<module>.tex`, `<module>.pdf`, and the `.aux` and `.log` files from `pdflatex`                           | [Headers and documentation](headers-and-docs.md)   |

The endpoint file is named after the bus:

| Bus type   | Endpoint file                     |
|------------|-----------------------------------|
| `axi`      | `<module>_axi_endpoint.vhd`       |
| `ipbus`    | `<module>_ipb_endpoint.vhd`       |
| `sbi`      | `<module>_sbi_endpoint.vhd`       |
| `avalon`   | `<module>_avalon_endpoint.vhd`    |
| `wishbone` | `<module>_wishbone_endpoint.vhd`  |
| `apb`      | `<module>_apb_endpoint.vhd`       |

bust creates all four directories whenever it generates files, so `-d` leaves
an empty `doc/` and `-i` an empty `header/`.

## Existing files

This section is about the files bust generates. `<module>.vhd` is yours, see
[Your top level](#your-top-level).

### Without `-f`

For each file that already exists, bust asks before it replaces it:

```text
Do you want to overwrite out/example_ipbus/hdl/example_ipbus_localbus_pkg.vhd? (y/N):
```

Answer `y` to replace the file. Any other answer keeps it, and bust prints
`Did not write` and the path, then goes on with the next file. The generated
files refer to each other, so keep them from the same run.

bust asks only when standard input is a terminal. In a script or a CI job, it
stops at the first existing file instead and exits with status 1:

```text
ERROR: Could not generate local-bus VHDL files
An error occurred during output generation...
FileExistsError: out/example_ipbus/hdl/example_ipbus_localbus_pkg.vhd already exists and there is no terminal to ask whether to overwrite it. Run bust with -f to overwrite it.
```

Use `-f` in scripts.

### With `-f`

bust replaces every file it generates without asking. It does not replace
`<module>.vhd`, which is yours, and says how to:

```text
out/example_axi/hdl/example_axi.vhd is yours, so -f did not replace it. To replace it with a fresh starter, run bust with --replace-top.
```

## Your top level

`<module>.vhd` is the top level of your module, and the file is yours. When it
does not exist, bust writes a starter and says so:

```text
Wrote out/example_axi/hdl/example_axi.vhd, a starting point that is yours to edit. bust will not change it again.
```

After that, bust leaves the file alone, with or without `-f`.
[Generated HDL](generated-hdl.md#your-top-level) describes the starter.

`--replace-top` replaces the file with a fresh starter and keeps your old file
next to it as `<module>.vhd.bak`. bust asks first, and with `-f` it replaces
the file without asking:

```bash
bust example_axi.json -o out --replace-top -f
```

```text
Replaced out/example_axi/hdl/example_axi.vhd with a fresh starter. The old file is out/example_axi/hdl/example_axi.vhd.bak.
```

## Renumber addresses

`-a` reads `FILE`, gives every register a new address, and writes the result
back to `FILE`. It generates no other output. It asks before it replaces
`FILE`, or, without a terminal, stops as described in
[Existing files](#existing-files). Add `-f` to save without asking:

```bash
bust timer.json -a -f
```

bust numbers the registers in the order they appear, starting at 0. They are
`data_width / 8` apart, and 1 apart on IPBus or with `"byte_addressable": false`
in the module. See
[Byte and word addresses](register-map-format.md#byte-and-word-addresses).
Addresses you wrote yourself are replaced.

bust then writes the whole file again, with 4-space indentation. Every register
gets an `address`, and the defaults bust used are written out, such as `type`,
`reset` and `description`. Keys that bust does not know are dropped, after the
warning described in [Register map format](register-map-format.md#keys-bust-does-not-know).
These registers:

```json
"register": [
  { "name": "ctrl", "sw": "rw", "hw": "r", "type": "vector", "width": 8, "address": "0x10" },
  { "name": "status", "sw": "ro", "hw": "w" },
  { "name": "irq", "sw": "rw", "hw": "r", "type": "fields", "address": "0x4",
    "fields": [ { "name": "done", "type": "bit", "onwrite": "woclr", "hwset": true } ] }
]
```

become:

```json
"register": [
    {
        "name": "ctrl",
        "sw": "rw",
        "hw": "r",
        "type": "vector",
        "address": "0x0",
        "width": 8,
        "reset": "0x0",
        "description": ""
    },
    {
        "name": "status",
        "sw": "ro",
        "hw": "w",
        "type": "default",
        "address": "0x4",
        "reset": "0x0",
        "description": ""
    },
    {
        "name": "irq",
        "sw": "rw",
        "hw": "r",
        "type": "fields",
        "address": "0x8",
        "fields": [
            {
                "name": "done",
                "type": "bit",
                "onwrite": "woclr",
                "hwset": true
            }
        ],
        "description": ""
    }
]
```

The `bus` and `module` sections get the same treatment, and a `settings`
section is dropped. Commit or copy the file first if you want to compare.

## Interactive editor

`-c` and `-e` open a menu-based editor in the terminal. It needs an interactive
terminal. Without one, bust stops with
`The editor (-c, -e) needs an interactive terminal.` and exits with status 1.

`bust FILE -c` starts a new register map. It asks for the bus type, the module
name and a description, then opens the menu. `bust FILE -e` loads `FILE` and
opens the same menu. The menu has these entries:

| Entry            | What it does                                                         |
|------------------|----------------------------------------------------------------------|
| Edit name        | Rename the module.                                                   |
| List registers   | Show the registers in a table, and the fields of one register.       |
| Add new register | Ask for the name, description, mode, fields, type, address and reset. |
| Remove register  | Delete a register.                                                   |
| Update addresses | Renumber the addresses, as `-a` does.                                |
| Save JSON        | Write the register map to `FILE`, asking before it replaces a file.  |
| Exit             | Leave the editor. Changes you did not save are lost.                 |

The line under the title shows the module name, the address and data width,
and whether there are unsaved changes. A new module from `-c` has 32-bit
addresses and data.

The editor writes registers with the `mode` key (`rw`, `ro` or `pulse`) and a
register type. It does not know the `sw` and `hw` keys or the other
[access modes](access-modes.md), so add those in a text editor.

## Messages and debug.log

bust prints its progress and its errors on standard error. A run that writes
every file prints:

```text
Parsing file: example_axi.json...
Project path: /path/to/out
Generating local-bus VHDL files...
Generating Module Include Files...
Generating Module Documentation...
Generating Documentation PDF...
```

When `pdflatex` is not on your `PATH`, the last line is followed by:

```text
Could not run pdflatex ([Errno 2] No such file or directory: 'pdflatex'). Use -p to skip the PDF.
```

When `pdflatex` runs but reports errors, bust prints
`pdflatex reported errors. See <doc dir>/<module>.log`. In both cases bust
still exits with status 0, since every other file was written.
[Headers and documentation](headers-and-docs.md) describes the PDF step.

An error in the register map is printed as a message that names the problem,
and bust exits with status 1. For example:

```text
When specifying address for register reg1, address 0x0 is already assigned to other register
```

```text
Bus type is not valid: pci
```

A run that stops with an error also adds to `debug.log` in the directory you
run bust from. Each run starts with a line that gives the time and the command
line, followed by the same messages with a timestamp, a line for each file
written, and the full Python traceback of the error. Look there when a message
is not enough, and attach it when you report a problem. A run that succeeds
adds nothing, and neither do `--version`, `--help` and a usage error. Delete
the file when you no longer need it.

## Exit codes

| Code | Meaning                                                                                                                                                                                                                      |
|------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0    | Success. Also when you answered no to an overwrite question, when the PDF could not be made, and for `--version` and `--help`.                                                                                               |
| 1    | Any error: invalid command-line arguments, a JSON file that is missing or not valid JSON, a register map that fails validation, a file that could not be written (including an existing file with no terminal to ask), or the editor without a terminal. |
