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

.PHONY: help build rebuild sim-ipbus sim-axi sim-prototype sim-prototype-generated sim-prototype-axi sim-prototype-axi-generated sim-prototype-tb-generated sim-prototype-ipbus sim-prototype-ipbus-generated sim-prototype-ipbus-tb-generated sim-prototype-sbi sim-prototype-sbi-generated sim-prototype-sbi-tb-generated sim-prototype-avalon sim-prototype-avalon-generated sim-prototype-avalon-tb-generated sim-prototype-wishbone sim-prototype-apb wave-ipbus wave-axi wave-prototype wave-prototype-generated wave-prototype-axi wave-prototype-ipbus wave-prototype-sbi wave-prototype-avalon wave-prototype-wishbone wave-prototype-apb gtkwave clean

# Default target
help:
	@echo ""
	@echo "  bust VHDL simulation targets"
	@echo ""
	@echo "  make build          Build the nvc+UVVM simulation Docker image"
	@echo "  make rebuild        Force-rebuild the image (no cache)"
	@echo "  make sim-ipbus      Run the example_ipbus testbench"
	@echo "  make sim-axi        Run the example_axi testbench"
	@echo "  make sim-prototype  Run the prototype local-bus regfile testbench"
	@echo "  make sim-prototype-generated  Run that testbench against the generated package"
	@echo "  make sim-prototype-axi  Run the AXI-Lite wrapper testbench"
	@echo "  make sim-prototype-axi-generated  Run that testbench against the generated AXI stack"
	@echo "  make sim-prototype-tb-generated  Run the fully generated AXI stack incl. generated testbench"
	@echo "  make sim-prototype-ipbus  Run the IPBus wrapper testbench"
	@echo "  make sim-prototype-ipbus-generated  Run that testbench against the generated IPBus stack"
	@echo "  make sim-prototype-ipbus-tb-generated  Run the fully generated IPBus stack incl. generated testbench"
	@echo "  make sim-prototype-sbi  Run the SBI wrapper testbench"
	@echo "  make sim-prototype-sbi-generated  Run that testbench against the generated SBI stack"
	@echo "  make sim-prototype-sbi-tb-generated  Run the fully generated SBI stack incl. generated testbench"
	@echo "  make sim-prototype-avalon  Run the Avalon-MM wrapper testbench"
	@echo "  make sim-prototype-avalon-generated  Run that testbench against the generated Avalon stack"
	@echo "  make sim-prototype-avalon-tb-generated  Run the fully generated Avalon stack incl. generated testbench"
	@echo "  make sim-prototype-wishbone  Run the Wishbone wrapper testbench"
	@echo "  make sim-prototype-apb  Run the APB wrapper testbench"
	@echo "  make wave-ipbus     Run example_ipbus + capture FST + open GTKWave"
	@echo "  make wave-axi       Run example_axi  + capture FST + open GTKWave"
	@echo "  make wave-prototype Run prototype    + capture FST + open GTKWave"
	@echo "  make gtkwave FILE=<path>  Open any FST/VCD file in GTKWave"
	@echo "  make clean          Remove the local Docker image"
	@echo ""
	@echo "  GTKWave note: before using wave-* or gtkwave targets, grant X11 access"
	@echo "  to your local user once: 'xhost +si:localuser:\$$USER'"
	@echo "  (avoid 'xhost +local:docker' on multi-user machines - see sim/README.md)."
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

sim-prototype: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype

sim-prototype-generated: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_generated

sim-prototype-axi: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_axi

sim-prototype-axi-generated: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_axi_generated

sim-prototype-tb-generated: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_tb_generated

sim-prototype-ipbus: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_ipbus

sim-prototype-ipbus-generated: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_ipbus_generated

sim-prototype-ipbus-tb-generated: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_ipbus_tb_generated

sim-prototype-sbi: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_sbi

sim-prototype-sbi-generated: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_sbi_generated

sim-prototype-sbi-tb-generated: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_sbi_tb_generated

sim-prototype-avalon: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_avalon

sim-prototype-avalon-generated: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_avalon_generated

sim-prototype-avalon-tb-generated: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_avalon_tb_generated

sim-prototype-wishbone: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_wishbone

sim-prototype-apb: _require-image
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_apb

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

wave-prototype: _require-image
	@mkdir -p "$(WAVES_DIR)"
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype --wave=/work/sim/waves/prototype.fst
	$(GTKWAVE_RUN) gtkwave /waves/prototype.fst

wave-prototype-axi: _require-image
	@mkdir -p "$(WAVES_DIR)"
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_axi --wave=/work/sim/waves/prototype_axi.fst
	$(GTKWAVE_RUN) gtkwave /waves/prototype_axi.fst

wave-prototype-ipbus: _require-image
	@mkdir -p "$(WAVES_DIR)"
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_ipbus --wave=/work/sim/waves/prototype_ipbus.fst
	$(GTKWAVE_RUN) gtkwave /waves/prototype_ipbus.fst

wave-prototype-sbi: _require-image
	@mkdir -p "$(WAVES_DIR)"
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_sbi --wave=/work/sim/waves/prototype_sbi.fst
	$(GTKWAVE_RUN) gtkwave /waves/prototype_sbi.fst

wave-prototype-avalon: _require-image
	@mkdir -p "$(WAVES_DIR)"
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_avalon --wave=/work/sim/waves/prototype_avalon.fst
	$(GTKWAVE_RUN) gtkwave /waves/prototype_avalon.fst

wave-prototype-wishbone: _require-image
	@mkdir -p "$(WAVES_DIR)"
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_wishbone --wave=/work/sim/waves/prototype_wishbone.fst
	$(GTKWAVE_RUN) gtkwave /waves/prototype_wishbone.fst

wave-prototype-apb: _require-image
	@mkdir -p "$(WAVES_DIR)"
	$(DOCKER_RUN) /work/sim/scripts/run_sim.sh prototype_apb --wave=/work/sim/waves/prototype_apb.fst
	$(GTKWAVE_RUN) gtkwave /waves/prototype_apb.fst

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
