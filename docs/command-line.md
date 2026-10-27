# Command line

bust reads one JSON register map and writes the VHDL, the testbench, the
headers and the documentation for it. This page lists the options, where the
files go, and what bust does when they already exist.

## Usage

`bust --help` starts with the usage lines:

```text
Usage:
  bust FILE [-o DIR] [[[-f] [-d | -p] [-i] [--replace-top]] | [-a [-f]] | [--migrate [-f]] | [-c | -e]]
  bust --version
  bust -h | --help
```

`FILE` is the JSON register map, described in
[Register map format](register-map-format.md). The usage line also says which
options go together:

- `-o` combines with everything else, but only a run that generates files
  uses it.
- `-f`, one of `-d` and `-p`, and `-i` combine with each other. They
  control a normal run that generates files.
- `-a` saves the JSON file instead of generating files. It takes `-f`
  to save without asking.
- `--migrate` converts the files instead of generating them. It takes `-f`
  to convert without asking.
- `-c` and `-e` open the editor, so they stand alone.

Any other combination, such as `-d -p` or `-c -f`, makes bust print the usage
and exit with status 1.

## Options

| Option         | Effect                                                                                                                                                                  |
|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-o DIR`       | Write the output under `DIR` instead of next to the JSON file. See [Output directory](#output-directory).                                                                 |
| `-f`           | Overwrite existing files without asking, except `<module>.vhd`, which is yours. See [Existing files](#existing-files).                                               |
| `-d`           | Do not write the documentation: no `.tex` or `.html` file and no PDF.                                                                                                    |
| `-p`           | Write the `.tex` and `.html` files, but do not run `pdflatex` to make the PDF, even when it is installed.                                                                |
| `-i`           | Do not write the headers: the `.h`, `.hpp` and `.py` files, and for IPBus the `.xml` address table.                                                                     |
| `--replace-top` | Replace `<module>.vhd` with a fresh starter and keep the old file as `<module>.vhd.bak`. Asks first unless you add `-f`. See [Your top level](#your-top-level). |
| `-a`           | Give every register a new address and save the JSON file. Generates nothing. With `-f`, saves without asking. See [Renumber addresses](#renumber-addresses).          |
| `--migrate`    | Convert a bust 0.14 JSON file and its `<module>.vhd`. Generates nothing. With `-f`, without asking. See [Migrate a bust 0.14 file](#migrate-a-bust-014-file). |
| `-c`           | Create `FILE` with the interactive editor. See [Interactive editor](#interactive-editor).                                                                               |
| `-e`           | Open `FILE` in the interactive editor.                                                                                                                                  |
| `--version`    | Print `bust` and the version, such as `bust v1.0.0`, then exit.                                                                                                         |
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
    │   ├── example_ipbus.html
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
| `doc/`    | `<module>.tex`, `<module>.html`, and with `pdflatex` installed `<module>.pdf` and its `.aux` and `.log` files | [Headers and documentation](headers-and-docs.md)   |

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

## Migrate a bust 0.14 file

bust reads only the bust 1.0 register map format. A file written for bust
0.14 stops bust with an error for each 0.14 key or value, such as:

```text
timer.json:14: module.register[0].mode: a bust 0.14 key, which bust no longer reads. Run bust with --migrate to convert the file.
```

`bust FILE --migrate` converts such a file to the bust 1.0 format. It replaces
each `mode` with the access keys it stands for, removes the `settings` section
and the keys bust 1.0 has no use for, and changes the old type names and
values. It changes only those values in the file, so comments and the layout
stay. It also connects a bust 0.14 `<module>.vhd` to the bust 1.0 endpoint.
It lists the changes and asks first, unless you add `-f`, and keeps each old
file with the suffix `.0_14`. Give it the same `-o` as your other runs, then
generate the files:

```bash
bust timer.json -o out --migrate
bust timer.json -o out
```

bust lists any line of `<module>.vhd` it could not change. Change those by
hand. A register with a `pulse_cycles` other than 1 or a `stall_cycles` other
than 0 stops the migration, because bust 1.0 cannot generate that timing.

## Interactive editor

`-c` and `-e` open a full-screen editor in the terminal, built on
[Textual](https://textual.textualize.io/). It runs in any terminal Textual
supports, on Linux, macOS and Windows. It needs an interactive terminal.
Without one, bust stops with
`The editor (-c, -e) needs an interactive terminal.` and exits with status 1.

### The main screen

The main screen shows the register map in three panes:

- **Registers** lists every register with its name, address, type, width,
  `sw`, `hw`, reset and description.
- **Fields of ...** lists the fields of the register under the cursor, if it
  is a `fields` register.
- The right pane lists each key of the register or field in focus with its
  value, and under it what the key does. A key the file does not set shows
  the value bust uses, dimmed, with `(not set)`.

The panes are numbered 1, 2 and 3, and the one with focus has a highlighted
border. Tab and Shift+Tab move between them, the keys `1`, `2` and `3` jump to
one, and the mouse works too. The arrow keys move within a pane. Enter on a
register or a field moves to its keys, and Enter on a key opens a dialog to
change it. The line under the title repeats this, and `?` lists every key.
These keys work on the main screen, and the footer lists most of them:

| Key | What it does |
|---|---|
| `a` | Add a register. |
| `f` | Add a field to the register under the cursor, which must be a `fields` register. |
| `Delete` or `d` | Remove the register or field in focus, after asking. |
| `m` | Change the module's `name`, `description`, `version` and `byte_addressable`, and the bus `type`, `addr_width` and `data_width`. |
| `g` | Write the address bust gives each register without an `address`. Unlike `-a`, it leaves the other addresses alone. |
| `o` | Show the overview of the register map. |
| `t` | Switch between the light and the dark theme, which use the colours of this documentation. |
| `?` | List every key. |
| `s` or `Ctrl+S` | Save `FILE` if the register map changed. |
| `q` or `Ctrl+Q` | Quit. With unsaved changes, the editor asks whether to save first. |

In a dialog, Enter or OK takes the answers and Escape cancels. A key with a
fixed set of values, such as `sw` or `onread`, is a list to choose from. Choose
`not set`, or press **Remove from the file** for a key typed as text, to remove
the key from the file. Changing the `type` of a register asks for what the new
type needs, such as the first field of a `fields` register, and removes what it
no longer uses, such as the `width` of a former `vector`. The `enums` row of a
field lists its enumerated values, where `a` adds one, Enter changes one and
Delete removes one.

### The overview

`o` shows the whole register map the way the
[documentation](headers-and-docs.md) does. It has the module's name, version,
register map hash and bus, then the register list with the number, name,
software and hardware access, address, type, width and reset of each register.
Then each register follows with its address, its description and a bit
diagram. The diagram draws each field as a box over its bits, with the
numbers of its highest and lowest bit above and its reset value below. Bits no
field uses show as `unused`. A box is wider than its bits where its name would
not fit. Under the diagram, each field is listed with its description and its
access.

Enter on a register in the list moves to its diagram. Escape goes back to the
editor. The overview shows the register map as it is in the editor, including
changes that are not saved yet.

### Create a register map

`bust FILE -c` opens a dialog for the bus type, the address width, the data
width (not for IPBus, which has 32-bit data), the module name, the version, a
description, and whether addresses count bytes (`byte_addressable`). The module
name defaults to the file name, and `byte_addressable` to what the bus does.
Then it asks for the first register. `FILE` must not exist. If it does, bust
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
A `hash` or `version` register gets only `name`, `address`, `type` and
`description`, since bust sets its access and its value. Set the other keys, such as `onwrite`, in the right pane once the register or
field is added.

### Edit a register map

`bust FILE -e` reads `FILE`, in JSON or JSON5, and opens the main screen.

### Checks

The editor checks every change the way `bust FILE` checks the register map. A
dialog shows bust's message under the answers and stays open for an answer
bust rejects, such as an address that another register uses:

```text
Could not parse register count: Invalid field format: onwrite requires a software-writable field (sw rw or wo) (field count in reg count)
```

Fix the answer or press Escape to keep the old value. A change made without a
dialog, such as removing a field, shows `Not changed:` and bust's message
instead. So the editor cannot save a register map that bust rejects. It shows
each warning, such as an unknown key, once.

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

When `pdflatex` is not on your `PATH`, the last line is instead:

```text
pdflatex is not on PATH, so bust skipped the PDF. The documentation is in /path/to/out/example_axi/doc/example_axi.html.
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

## From Python

`bust.generate_files` returns every file the command line writes, without writing anything or running `pdflatex`. It takes the text of a register map or the parsed JSON, and gives the content of each file by its path under the output directory:

```python
import bust

with open("timer.json", encoding="utf-8") as fp:
    files = bust.generate_files(fp.read())

print(files["timer/hdl/timer_regfile.vhd"])
```

The paths are the ones `bust timer.json -o DIR -p` writes under `DIR`, with `/` on every platform. The result always holds a starter `timer/hdl/timer.vhd`. The command line writes that file only when it is missing, since it is yours to edit, so a program that keeps files should do the same. A register map with problems raises `bust.exceptions.FormatError`, with every problem in the message.
