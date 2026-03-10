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
# =============================================================================

REPO_ROOT   := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
SIM_DIR     := $(REPO_ROOT)/sim
IMAGE_NAME  := bust-sim
IMAGE_TAG   := latest
FULL_IMAGE  := $(IMAGE_NAME):$(IMAGE_TAG)

# Docker run flags shared by all simulation targets
DOCKER_RUN := docker run --rm \
    -v "$(REPO_ROOT):/work" \
    -e WORK_ROOT=/work \
    "$(FULL_IMAGE)"

.PHONY: help build rebuild sim-ipbus clean

# Default target
help:
	@echo ""
	@echo "  bust VHDL simulation targets"
	@echo ""
	@echo "  make build       Build the nvc+UVVM simulation Docker image"
	@echo "  make rebuild     Force-rebuild the image (no cache)"
	@echo "  make sim-ipbus   Run the example_ipbus testbench"
	@echo "  make clean       Remove the local Docker image"
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

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
_require-image:
	@if ! docker image inspect "$(FULL_IMAGE)" >/dev/null 2>&1; then \
	    echo "Image $(FULL_IMAGE) not found. Run 'make build' first."; \
	    exit 1; \
	fi

clean:
	docker image rm -f "$(FULL_IMAGE)" 2>/dev/null || true
	@echo "  Removed image: $(FULL_IMAGE)"
