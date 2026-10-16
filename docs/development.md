# Development

This page is for working on bust itself. Report bugs and ideas as
[GitHub issues](https://github.com/logvik-org/bust/issues).

## Set up

```bash
git clone https://github.com/logvik-org/bust.git
cd bust
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
pre-commit install
```

bust runs on Python 3.9 to 3.14. mypy checks against 3.9.

## Checks

| Command | What it does |
|---|---|
| `pytest` | Run the test suite |
| `mypy bust` | Type-check the package |
| `pre-commit run --all-files` | Run black and the whitespace, tab and line-ending checks |
| `sphinx-build -W --keep-going -b html docs docs/_build/html` | Build this site, failing on any warning |

CI runs mypy and the tests on Python 3.9 to 3.14 (plus the next Python while it
is in pre-release), builds the docs, builds the package and smoke-tests the
wheel, runs the pre-commit hooks and simulates the generated VHDL. A pull
request needs all of it green.

## Golden files

Most tests regenerate the outputs of the examples in `example/` and compare
them byte for byte with the committed files in `example/<name>/`. A change to
a template or generator that changes the output fails these tests until the
committed files are updated. To rewrite them from the current generator:

```bash
BUST_UPDATE_GOLDENS=1 pytest tests/test_suite.py
git diff example/
```

Review the diff before you commit it. It is the clearest record of what your
change does to the generated code.

## Simulation

`sim/` simulates the generated example testbenches, and the hand-written
reference testbenches in `hdl/prototype/`, with the open-source nvc simulator
in Docker. You need Docker, but no local VHDL tools:

```bash
cd sim
make build      # build the nvc + UVVM image once
make sim-axi    # simulate the AXI4-Lite example
make help       # list every target
```

`sim/README.md` describes the image and how to add a target. CI runs the
simulations when files under `sim/`, `hdl/` or the generated example VHDL
change, and for every release.

## Documentation

This site is built with Sphinx from the Markdown pages in `docs/` and published
on Read the Docs, which rebuilds it for every push to `master` and every
release tag. The configuration is in `.readthedocs.yaml` and `docs/conf.py`.

The logo, the sidebar wordmark and the favicon in `docs/images/` are drawn by
`scripts/make_logo.py`. To change them, edit the script and run it from the
repository root. The PNG files need `pip install cairosvg`.

## Changelog

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Add user-facing changes under `## [Unreleased]`.

## Releasing

The version is set in one place, `__VERSION__` in `bust/_version.py`.
Versions follow [PEP 440](https://peps.python.org/pep-0440/): `1.2.0a1`,
`1.2.0b1` and `1.2.0rc1` are pre-releases, and `1.2.0` is a final release.

1. On the branch you release from (`master` for a final release), move the
   `Unreleased` entries in `CHANGELOG.md` under a new `## [<version>] - <date>`
   heading, update the compare links at the bottom, set `__VERSION__`, and
   push.
2. Publish a GitHub Release on that commit with the tag `v<version>`, for
   example `v1.2.0`. The tag must be `v` followed by exactly `__VERSION__`. For
   a pre-release, tick "Set as a pre-release". pip installs pre-releases only
   when asked (`pip install --pre bust`).

Publishing the release starts `.github/workflows/release.yml`. It stops at the
first failing step:

1. The test and simulation workflows.
2. Build the sdist and wheel, after checking the tag against `__VERSION__`.
3. Upload them to TestPyPI.
4. Download the wheel from TestPyPI, check that it is the one step 2 built,
   install it and run `scripts/smoke-test.sh`.
5. Upload the same files to PyPI.

If a step fails for a reason outside the code, re-run the failed jobs. TestPyPI
skips files it already has. If the code needs a fix and the release stopped
before the TestPyPI upload, delete the release and its tag, fix the code and
publish again. Once a version is on TestPyPI, a fix needs a new version,
because neither index accepts the same file twice.

Uploads use PyPI Trusted Publishing through the `testpypi` and `pypi` GitHub
environments, so no tokens are stored in the repository.
