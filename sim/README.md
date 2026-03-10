# bust VHDL Simulation Infrastructure

This directory contains everything needed to compile and run the bust example
testbenches with the **nvc** VHDL simulator, both locally (via Docker) and in
GitHub Actions CI.

---

## Architecture

```
sim/
├── Dockerfile             # Image recipe: nvc + UVVM + IPBus + vip_ipbus
├── .dockerignore
├── Makefile               # Local convenience targets
├── README.md              # This file
└── scripts/
    ├── compile_libs.sh    # Run at image build time: pre-compile shared libs
    └── run_sim.sh         # Run at simulation time: compile DUT+TB, elaborate, run
```

### Why Docker?

All VHDL tooling (nvc, UVVM, IPBus firmware, vip_ipbus) lives inside a single
Docker image.  Local machines need no VHDL toolchain installed, version
differences between developers are eliminated, and CI uses the exact same
environment.

### The nvc simulator

[nvc](https://github.com/nickg/nvc) is a fast, open-source VHDL-2008 simulator.
The image is based on the official nvc Docker image (`ghcr.io/nickg/nvc:latest`).

The current image was built with **nvc v1.19.3**.

### Library layers

Libraries are split into two layers:

| Layer | Where compiled | How | Contents |
|-------|---------------|-----|----------|
| **nvc system libs** | `/root/.nvc/lib/` | `nvc --install uvvm` at image build | UVVM util, UVVM VVC framework, bitvis_vip_scoreboard, bitvis_vip_axilite, and all other UVVM VIPs |
| **Project-specific libs** | `/opt/nvc-libs/` (`NVC_LIBPATH`) | `compile_libs.sh` at image build | `ipbus` (from ipbus-firmware v1.16) and `vip_ipbus` (BFM only) |
| **Per-run libs** | `$TMPDIR/bust/` | `run_sim.sh` pre-compile hook | `bust` lib, e.g. `axi_pkg.vhd` for AXI targets |

### compile_libs.sh

Runs once during `docker build`.  Compiles:

1. **`ipbus`** — `ipbus_package.vhd` from [ipbus-firmware v1.16](https://github.com/ipbus/ipbus-firmware)
2. **`vip_ipbus`** — `ipbus_bfm_pkg.vhd` from [vip_ipbus](https://github.com/olagrottvik/vip_ipbus)
   (BFM only; VVC files are not compiled because the testbench uses the BFM API)

`vip_ipbus` requires the `--relaxed` analysis flag because UVVM uses
`shared_msg_id_panel` as a default parameter value, which is not statically
valid per strict VHDL-2008.  The flag must be placed **after** `-a`, not before:

```bash
# Correct
nvc --std=08 --work=vip_ipbus:... -a --relaxed ipbus_bfm_pkg.vhd

# Wrong – nvc will reject it as an unrecognised global option
nvc --relaxed --std=08 --work=... -a ipbus_bfm_pkg.vhd
```

### run_sim.sh

Runs for each simulation target.  Steps:

1. **Pre-compile** (optional per-target hook) — compiles any auxiliary library
   needed by the DUT or TB (e.g. `axi_pkg.vhd` into library `bust`).
2. **Analyse** — compiles each source file in `COMPILE_ORDER` into the work library.
3. **Elaborate** — links the design.
4. **Run** — executes the simulation, capturing output to a log file.
5. **Result evaluation** — checks the nvc exit code and greps the log for UVVM
   FAIL markers.  Returns 0 (PASS) or 1 (FAIL/ERROR).

The work library and any per-run auxiliary libs are written to a `mktemp -d`
scratch directory and deleted on exit.

The `NVC_LIBPATH` environment variable extends nvc's library search path.  It
is set to `/opt/nvc-libs` in the Docker image and inherited by every run.
`SIM_WORK_DIR` is also added to the search path (`-L $SIM_WORK_DIR`) so that
per-run auxiliary libs (e.g. `bust`) are visible during analysis.

---

## Local usage

### Prerequisites

- Docker ([install guide](https://docs.docker.com/get-docker/))
- No local VHDL toolchain required

### 1. Build the image (once)

```bash
make build
```

This runs `docker build` with the `sim/` directory as context.  It takes
~30 s on first build; subsequent builds use Docker layer cache.

To force a clean rebuild (e.g. after changing `compile_libs.sh`):

```bash
make rebuild
```

### 2. Run a testbench

```bash
make sim-ipbus    # example/example_ipbus testbench
make sim-axi      # example/example_axi testbench
```

Both targets mount the repository root at `/work` inside the container and
call `run_sim.sh` with the appropriate target name.

You can also invoke the script directly if you prefer:

```bash
docker run --rm \
  -v "$(pwd):/work" \
  -e WORK_ROOT=/work \
  bust-sim:latest \
  /work/sim/scripts/run_sim.sh example_axi
```

Exit code: `0` = PASS, `1` = FAIL or compile error.

### 3. Clean up

```bash
make clean    # removes the local bust-sim:latest image
```

---

## CI/CD (GitHub Actions)

The workflow is defined in [`.github/workflows/vhdl_sim.yml`](../.github/workflows/vhdl_sim.yml).

### Trigger conditions

| Event | Condition |
|-------|-----------|
| Push | branches `master` or `dev`; paths `sim/**` or `example/**/*.vhd` |
| Pull request | any branch; same paths |
| Manual | `workflow_dispatch` |

### Docker layer caching

To avoid re-compiling UVVM and IPBus on every CI run, the image is cached in
GitHub Container Registry (GHCR):

```
ghcr.io/grottviq/bust-sim-cache:buildcache
```

`docker/build-push-action` with `cache-from`/`cache-to` handles this
automatically.  The `GITHUB_TOKEN` secret grants the workflow write access to
the GHCR namespace.

### Steps

1. Checkout
2. Set up Docker Buildx
3. Log in to GHCR
4. Build (or restore from cache) the simulation image as `bust-sim:ci`
5. Run `example_ipbus` testbench
6. Run `example_axi` testbench

---

## Adding a new testbench target

1. **Add a case to `run_sim.sh`** — define `pre_compile()` (if needed),
   `COMPILE_ORDER`, and `TOP_ENTITY`:

   ```bash
   example_newbus)
       pre_compile() {
           # compile any extra library here (optional)
           :
       }
       COMPILE_ORDER=(
           "${WORK_ROOT}/example/example_newbus/hdl/example_newbus_pif_pkg.vhd"
           "${WORK_ROOT}/example/example_newbus/hdl/example_newbus_nb_pif.vhd"
           "${WORK_ROOT}/example/example_newbus/tb/example_newbus_nb_pif_tb.vhd"
       )
       TOP_ENTITY="example_newbus_nb_pif_tb"
       ;;
   ```

   Update the error message in the `*)` catch-all to include the new name.

2. **Add a `sim-newbus` target to `sim/Makefile`**:

   ```makefile
   sim-newbus: _require-image
       $(DOCKER_RUN) /work/sim/scripts/run_sim.sh example_newbus
   ```

   Add it to the `.PHONY` list and `help` text.

3. **Add a CI step to `.github/workflows/vhdl_sim.yml`**:

   ```yaml
   - name: Run example_newbus simulation
     run: |
       docker run --rm \
         -v "${{ github.workspace }}:/work" \
         -e WORK_ROOT=/work \
         bust-sim:ci \
         /work/sim/scripts/run_sim.sh example_newbus
   ```

4. If the new target requires an additional shared library (like `ipbus`),
   add it to `compile_libs.sh` and rebuild the image.

---

## Known issues

### IPBus: "Checking that invalid register returns ERR" fails

The last test in `example_ipbus_ipb_pif_tb.vhd` reads an address that maps to
no register and expects the bus to return an error acknowledgement (`ack=0`,
`err=1`).  The vip_ipbus BFM's `ipbus_read` procedure internally waits for
`ack=1`, so it times out when the DUT correctly returns `err=1`.

This is a BFM/DUT alignment issue — the DUT behaviour is correct.  The test
is deferred; it will be resolved when vip_ipbus is updated to handle error
acknowledgements, or the testbench is adjusted to use a lower-level read.

All other IPBus tests (12 registers, read/write/reset checks) pass.

### nvc `--relaxed` position

See the note in the [compile_libs.sh](#compile_libssh) section above.  This
was a subtle gotcha during initial setup.

---

## Library dependency diagram

```
example_ipbus_tb
    ├── uvvm_util          (nvc system: nvc --install uvvm)
    ├── vip_ipbus          (/opt/nvc-libs: compile_libs.sh)
    │    └── ipbus         (/opt/nvc-libs: compile_libs.sh)
    └── work (example_ipbus_pif_pkg, example_ipbus_ipb_pif)

example_axi_tb
    ├── uvvm_util          (nvc system: nvc --install uvvm)
    ├── bitvis_vip_axilite (nvc system: nvc --install uvvm)
    ├── bust (axi_pkg)     ($TMPDIR/bust: run_sim.sh pre_compile)
    └── work (example_axi_pif_pkg, example_axi_axi_pif)
```
