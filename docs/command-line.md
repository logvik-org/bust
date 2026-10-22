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
| `--version`    | Print `bust` and the version, such as `bust v1.0.0a4`, then exit.                                                                                                       |
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

`-a` reads `FILE`, gives every register a new address, and writes the
addresses into `FILE`. It generates no other output. It asks before it replaces
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

Only the addresses change in the file. A register without an `address` gets
one, and an address that is already right keeps the form it has, such as `16`
or `"0x10"`. Comments, keys bust does not know and the layout of the file stay
as they are, in JSON and JSON5 files. These registers:

```json
"register": [
  { "name": "ctrl", "sw": "rw", "hw": "r", "type": "vector", "width": 8, "address": "0x10" },
  { "name": "status", "sw": "ro", "hw": "w" },
  { "name": "irq", "sw": "rw", "hw": "r", "address": "0x8" }
]
```

become:

```json
"register": [
  { "name": "ctrl", "sw": "rw", "hw": "r", "type": "vector", "width": 8, "address": "0x0" },
  { "name": "status", "sw": "ro", "hw": "w", "address": "0x4" },
  { "name": "irq", "sw": "rw", "hw": "r", "address": "0x8" }
]
```

When every address is right already, bust says
`The addresses in FILE are in order already.` and does not write `FILE`.

## Interactive editor

`-c` and `-e` open an editor that asks questions in the terminal. It needs an
interactive terminal. Without one, bust stops with
`The editor (-c, -e) needs an interactive terminal.` and exits with status 1.

Answer a menu or a list of choices with the number of an entry, or type the
entry itself. Enter takes the answer in brackets. Ctrl+C cancels the current
action and goes back to the menu.

### Create a register map

`bust FILE -c` asks for the bus type, the address width, the data width (not
for IPBus, which has 32-bit data), the module name, the version, a
description, and whether addresses count bytes (`byte_addressable`). The
module name defaults to the file name, and `byte_addressable` to what the bus
does. Then it offers to add
the first register and opens the menu. `FILE` must not exist. If it does, bust
stops with `FILE exists. Edit it with bust FILE -e.`

The editor writes every key the [register map format](register-map-format.md)
recommends, even where bust has a default:

- The module gets `name`, `version`, `description` and `byte_addressable`.
- Each register gets `name`, `address`, `type`, `sw`, `hw`, `width` for a
  `vector`, `reset` unless it has fields, and `description`. The editor offers
  the next free address.
- Each field gets `name`, `type`, `position`, `width` for a `vector`, `reset`
  and `description`. A field gets `sw` and `hw` only where they differ from
  its register, so it keeps [inheriting](access-modes.md#inheritance) the
  rest.

This applies to every register and field the editor adds, with `-c` or `-e`.

### Edit a register map

`bust FILE -e` reads `FILE`, in JSON or JSON5, and opens the menu:

| Entry | What it does |
|---|---|
| List registers | Show the registers with their address, type, width, `sw`, `hw` and reset. |
| Add a register | Ask for a new register, as described above. |
| Edit a register | Change any key of a register, its fields, and their enumerated values. |
| Remove a register | Delete a register, after asking. |
| Edit the module and bus | Change the module's `name`, `description`, `version` and `byte_addressable`, and the bus `type`, `addr_width` and `data_width`. |
| Give an address to each register without one | Write the address bust gives each register without an `address`. Unlike `-a`, it leaves the other addresses alone. |
| Save | Write `FILE` if the register map changed. |
| Quit | Leave the editor. With unsaved changes, it asks whether to save first. |

Editing a register or a field lists each of its keys with its value. A key the
file does not set shows the value bust uses and `(not set)`. Choose `not set`,
or answer `-`, to remove a key from the file. Changing the `type` of a register
asks for what the new type needs, such as the first field of a `fields`
register, and removes what it no longer uses, such as the `width` of a former
`vector`.

### Checks

The editor checks every change the way `bust FILE` checks the register map.
While you add a register or a field, it shows bust's message and asks again
for an answer bust rejects, such as an address that another register uses.
When you edit a key, it shows `Not changed:` and bust's message, and keeps the
old value:

```text
Not changed: Could not parse register count: Invalid field format: onwrite requires a software-writable field (sw rw or wo) (field count in reg count)
```

So the editor cannot save a register map that bust rejects. It shows each
warning, such as an unknown key, once.

### Saving

The editor writes `FILE` only when the register map changed. Opening a file
and quitting leaves it untouched, and changing a value and changing it back is
no change.

Saving changes only the text of the values that changed. Comments, the order
of the keys, number forms such as `0x1c`, keys bust does not know and the
layout of the file stay as they are. New values are written as plain JSON,
which a JSON5 file accepts too. If `FILE` changed on disk after the editor read
it, saving stops with `FILE changed after the editor read it, so it was not
saved`.

For a JSON5 file that bust cannot edit in place, such as one with escaped
characters in a key, the editor says so when it opens the file. Saving then
rewrites the file as plain JSON without comments, and asks first.

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
and bust exits with status 1. A value of the wrong form gives the file, the
line and the path to the value, and bust lists every such problem in one run:

```text
timer.json:3: bus.type: "pci" is not one of "axi", "ipbus", "sbi", "avalon", "wishbone", "apb"
timer.json:12: module.register[1].address: "1c" has hexadecimal digits but no 0x. Write "0x1c" for a hexadecimal number.
2 problems in timer.json
```

A rule that ties keys together stops bust at the first problem:

```text
When specifying address for register reg1, address 0x0 is already assigned to other register
```

[How bust checks the file](register-map-format.md#how-bust-checks-the-file)
describes the steps. A file that is missing or not JSON gives
`Cannot read timer.json: No such file or directory` or the line and column of
the error, as in `timer.json:3:5: Expecting ',' delimiter`.

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
