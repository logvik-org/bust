# Contributing to bust

Thanks for your interest in improving bust. This guide covers how to set up a
development environment and what the project expects from a change.

## Development setup

bust targets Python 3.9 to 3.14 (3.9 is the mypy baseline).

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

CI runs `mypy bust` then `pytest` across Python 3.9 to 3.14, plus an
experimental 3.15 pre-release leg that may fail. It then builds the sdist and
wheel, checks them with `twine check`, installs the wheel into a fresh venv and
runs `scripts/smoke-test.sh` against it. The VHDL simulations (below) and the
pre-commit hooks run as separate workflows. PRs need a green pipeline to merge.

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
`sim/**`, `example/**/*.vhd`, or `hdl/**/*.vhd`, and for every release.

## Pull requests

- One feature or fix per PR. Keep changes well-scoped.
- Do not edit version strings by hand. Versioning is managed by bumpversion.
- Add user-facing changes to `CHANGELOG.md` under `## [Unreleased]`.
- Commit messages are one line, imperative mood, 72 characters max.

By contributing you agree that your contributions are licensed under the same
Apache License, Version 2.0 that covers the project. Please also review the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Releasing (maintainers)

1. On `master`, move the `Unreleased` entries in `CHANGELOG.md` under a new
   `## [<version>] - <date>` heading, update the compare links at the bottom,
   and commit.
2. Bump the version with bumpversion, for example `bump2version release`. It
   updates `pyproject.toml`, `bust/_version.py` and `.bumpversion.cfg` and
   commits, but does not tag. The configured formats drop a zero patch number,
   so `1.0.0-dev` becomes `1.0`, as `0.14` was. Push both commits.
3. Publish a **GitHub Release** on that commit with a new tag `v<version>`,
   where `<version>` is exactly `__VERSION__` from `bust/_version.py` (for
   example `v1.0`).

Afterwards, `bump2version patch` starts the next development version (for
example `1.0.1-dev`).

Publishing the release starts `.github/workflows/release.yml`, which runs these
jobs in order and stops at the first failure:

1. `python_tests.yml` (mypy, the test matrix, the wheel build and smoke test)
   and `vhdl_sim.yml` (every VHDL simulation), called as reusable workflows.
2. Build the sdist and wheel, after checking that the tag equals `v` +
   `__VERSION__`, and run `twine check`.
3. Upload them to **TestPyPI**.
4. Download the wheel from TestPyPI and check that it is the one step 2 built.
   Install it, taking its dependencies from PyPI (never from TestPyPI, where
   anyone can upload under their names), and run `scripts/smoke-test.sh`.
5. Upload the same files to **PyPI**.

If a job fails for a reason outside the code (for example TestPyPI was slow),
re-run the failed jobs from the Actions tab. TestPyPI skips files it already
has, so a re-run gets past step 3. If the code needs a fix and the release
failed before step 3, delete the release and its tag, fix the code, and publish
the release again. Once a version has reached TestPyPI, a fix needs a new
version: TestPyPI and PyPI never accept the same file name twice, and step 4
fails when TestPyPI holds an older build.

Publishing uses PyPI [Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
(OIDC), so no API tokens are stored. It needs this one-time setup:

- **PyPI**: in the settings of the `bust` project, under Publishing, add a
  GitHub trusted publisher with owner `logvik-org`, repository `bust`, workflow
  `release.yml` and environment `pypi`.
- **TestPyPI**: the same on [test.pypi.org](https://test.pypi.org) with
  environment `testpypi`. A `bust` project already exists there (0.7 to 0.8),
  so add the publisher from the account that owns it.
- **GitHub**: in the repository settings, under Environments, create the
  environments `testpypi` and `pypi`. Limit both to tags matching `v*` under
  "Deployment branches and tags", so that a workflow pushed to a branch cannot
  publish through them. To approve each PyPI upload by hand, add yourself as a
  required reviewer on `pypi`.
