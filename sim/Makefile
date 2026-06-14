# =============================================================================
# bust simulation Makefile
#
# Provides convenient targets for building the simulation image and running
# VHDL testbenches locally using Docker.
#
# Prerequisites:
#   - Docker  (https://docs.docker.com/get-docker/)
#   - No local VHDL toolchain is required; everything runs inside Docker.
#
# Quick start:
#   make build          # Build the simulation Docker image
#   make sim-ipbus      # Run the example_ipbus testbench
#   make sim-axi        # Run the example_axi testbench
#   make wave-ipbus     # Run example_ipbus, capture FST, open in GTKWave
#   make wave-axi       # Run example_axi, capture FST, open in GTKWave
# =============================================================================

REPO_ROOT      := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
SIM_DIR        := $(REPO_ROOT)/sim
IMAGE_NAME     := bust-sim
IMAGE_TAG      := latest
FULL_IMAGE     := $(IMAGE_NAME):$(IMAGE_TAG)
GTKWAVE_IMAGE  := hdlc/gtkwave
WAVES_DIR      := $(REPO_ROOT)/sim/waves

# Surfer (https://surfer-project.org) is an open-source waveform viewer being
# evaluated as an alternative to GTKWave. Unlike GTKWave there is no canonical
# Docker image, so the wave-surfer-* targets invoke a locally-installed binary.
# Override on the command line if surfer is not on PATH: make SURFER=/path/to/surfer ...
SURFER         := surfer

# Docker run flags shared by all simulation targets
DOCKER_RUN := docker run --rm \
    -v "$(REPO_ROOT):/work" \
    -e WORK_ROOT=/work \
    "$(FULL_IMAGE)"

# Docker run flags for GTKWave – X11 forwarding, waves dir mounted read-only.
# Requires the display to be accessible from Docker.
# On most Linux desktops run: xhost +local:docker
GTKWAVE_RUN := docker run --rm \
    -e DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v "$(WAVES_DIR):/waves:ro" \
    $(GTKWAVE_IMAGE)

.PHONY: help build rebuild sim-ipbus sim-axi wave-ipbus wave-axi gtkwave \
        wave-surfer-ipbus wave-surfer-axi surfer clean

# Default target
help:
	@echo ""
	@echo "  bust VHDL simulation targets"
	@echo ""
	@echo "  make build          Build the nvc+UVVM simulation Docker image"
	@echo "  make rebuild        Force-rebuild the image (no cache)"
	@echo "  make sim-ipbus      Run the example_ipbus testbench"
	@echo "  make sim-axi        Run the example_axi testbench"
	@echo "  make wave-ipbus     Run example_ipbus + capture FST + open GTKWave"
	@echo "  make wave-axi       Run example_axi  + capture FST + open GTKWave"
	@echo "  make gtkwave FILE=<path>  Open any FST/VCD file in GTKWave"
	@echo ""
	@echo "  Surfer (experimental, https://surfer-project.org):"
	@echo "  make wave-surfer-ipbus  Run example_ipbus + capture FST + open Surfer"
	@echo "  make wave-surfer-axi    Run example_axi  + capture FST + open Surfer"
	@echo "  make surfer FILE=<path>   Open any FST/VCD file in Surfer"
	@echo ""
	@echo "  make clean          Remove the local Docker image"
	@echo ""
	@echo "  GTKWave note: before using wave-* or gtkwave targets, grant X11 access"
	@echo "  to your local user once: 'xhost +si:localuser:\$$USER'"
	@echo "  (avoid 'xhost +local:docker' on multi-user machines - see sim/README.md)."
	@echo ""
	@echo "  Surfer note: surfer-* targets run a locally-installed 'surfer' binary."
	@echo "  Install from https://surfer-project.org or override with SURFER=<path>."
	@echo ""

# ---------------------------------------------------------------------------
# build – Build the simulation Docker image.
# The image pre-compiles UVVM, IPBus firmware and vip_ipbus so that
# individual simulation runs stay fast.
# ---------------------------------------------------------------------------
build:
	docker build \
	    --tag "$(FULL_IMAGE)" \
	    "$(SIM_DIR)"
	@echo ""
	@echo "  Image built: $(FULL_IMAGE)"

rebuild:
	docker build --no-cache \
	    --tag "$(FULL_IMAGE)" \
	    "$(SIM_DIR)"

# ---------------------------------------------------------------------------
# Simulation targets
# ---------------------------------------------------------------------------
sim-ipbus: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh example_ipbus

sim-axi: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh example_axi

# ---------------------------------------------------------------------------
# Waveform targets
#
# wave-*  : run the simulation with FST capture, then open GTKWave.
# gtkwave : open an existing FST/VCD file in GTKWave directly.
#
# GTKWave runs in the hdlc/gtkwave Docker image and connects to the host
# X11 server.  Run 'xhost +local:docker' once if you see a display error.
# ---------------------------------------------------------------------------
wave-ipbus: _require-image
	@mkdir -p "$(WAVES_DIR)"
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh example_ipbus --wave=/work/sim/waves/example_ipbus.fst
	$(GTKWAVE_RUN) gtkwave /waves/example_ipbus.fst

wave-axi: _require-image
	@mkdir -p "$(WAVES_DIR)"
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh example_axi --wave=/work/sim/waves/example_axi.fst
	$(GTKWAVE_RUN) gtkwave /waves/example_axi.fst

# Open any FST or VCD file with GTKWave.
# Usage: make gtkwave FILE=sim/waves/example_axi.fst
gtkwave:
	@[ -n "$(FILE)" ] || { echo "Usage: make gtkwave FILE=<path/to/waveform.fst>"; exit 1; }
	docker run --rm \
	    -e DISPLAY \
	    -v /tmp/.X11-unix:/tmp/.X11-unix \
	    -v "$(abspath $(dir $(FILE))):/waves:ro" \
	    $(GTKWAVE_IMAGE) \
	    gtkwave "/waves/$(notdir $(FILE))"

# ---------------------------------------------------------------------------
# Surfer waveform targets (experimental alternative to GTKWave)
#
# Surfer is a native GUI binary, so unlike the GTKWave targets these run it
# directly on the host rather than inside Docker. The simulation itself still
# runs in Docker and writes the same FST files.
# ---------------------------------------------------------------------------
wave-surfer-ipbus: _require-image _require-surfer
	@mkdir -p "$(WAVES_DIR)"
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh example_ipbus --wave=/work/sim/waves/example_ipbus.fst
	$(SURFER) "$(WAVES_DIR)/example_ipbus.fst"

wave-surfer-axi: _require-image _require-surfer
	@mkdir -p "$(WAVES_DIR)"
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh example_axi --wave=/work/sim/waves/example_axi.fst
	$(SURFER) "$(WAVES_DIR)/example_axi.fst"

# Open any FST or VCD file with Surfer.
# Usage: make surfer FILE=sim/waves/example_axi.fst
surfer: _require-surfer
	@[ -n "$(FILE)" ] || { echo "Usage: make surfer FILE=<path/to/waveform.fst>"; exit 1; }
	$(SURFER) "$(FILE)"

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
_require-surfer:
	@command -v "$(SURFER)" >/dev/null 2>&1 || { \
	    echo "Surfer binary '$(SURFER)' not found on PATH."; \
	    echo "Install from https://surfer-project.org or override with SURFER=<path>."; \
	    exit 1; \
	}

_require-image:
	@if ! docker image inspect "$(FULL_IMAGE)" >/dev/null 2>&1; then \
	    echo "Image $(FULL_IMAGE) not found. Run 'make build' first."; \
	    exit 1; \
	fi

clean:
	docker image rm -f "$(FULL_IMAGE)" 2>/dev/null || true
	@echo "  Removed image: $(FULL_IMAGE)"
