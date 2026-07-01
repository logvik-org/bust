# Contributing to bust

Thanks for your interest in improving bust. This guide covers how to set up a
development environment and what the project expects from a change.

## Development setup

bust targets Python 3.9, 3.10, and 3.11 (3.9 is the mypy baseline).

```bash
git clone https://github.com/logvik-org/bust.git
cd bust
pip install -r requirements.txt   # pinned deps + dev tools (pytest, mypy, sphinx) matching CI
pip install -e .                   # editable install so the `bust` CLI runs from your checkout
pip install pre-commit             # formatting/lint hooks (black, flake8) run via pre-commit
```

## Before you open a PR

Run the same checks CI runs, from the repository root:

```bash
mypy bust                          # type-check; must be clean
pytest                             # full test suite
pre-commit run --all-files         # black, flake8, trailing-ws, eof, tabs, crlf
```

CI runs `mypy bust` then `pytest` across Python 3.9/3.10/3.11. Both must be green.

## Golden-file tests

The test suite is not unit-style. It regenerates output from the example JSON
configs and asserts byte-for-byte equality against the committed reference files
under `example/example_axi/`, `example/example_ipbus/`, and the full-coverage
`example/example_prototype`.

Any change to a generator or template that alters output will fail the suite
until you regenerate and commit the corresponding `example/.../` reference files
for every affected example. Treat the example output trees as fixtures that must
be updated alongside generator or template changes.

## VHDL simulation

Generated HDL and its UVVM testbench change together. The `sim/` infrastructure
runs the generated example testbenches (and the hand-written prototype
testbenches) with the open-source nvc simulator inside Docker; no local VHDL
toolchain is needed. See `sim/README.md`. Simulation runs in CI on changes under
`sim/**`, `example/**/*.vhd`, or `hdl/**/*.vhd`.

## Pull requests

- One feature or fix per PR. Keep changes well-scoped.
- Do not edit version strings by hand; versioning is managed by bumpversion.
- Commit messages are one line, imperative mood, 72 characters max.

By contributing you agree that your contributions are licensed under the same
Apache License, Version 2.0 that covers the project. Please also review the
[Code of Conduct](CODE_OF_CONDUCT.md).
