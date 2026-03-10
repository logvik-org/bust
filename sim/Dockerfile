# =============================================================================
# bust simulation image
#
# Builds an nvc-based VHDL simulation environment with:
#   - UVVM verification framework
#   - IPBus firmware package
#   - vip_ipbus UVVM BFM
#
# Usage:
#   docker build -t bust-sim sim/
#   docker run --rm -v $(pwd):/work bust-sim sim/scripts/run_sim.sh example_ipbus
# =============================================================================

FROM ghcr.io/nickg/nvc:latest

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# UVVM – installed via nvc's built-in package manager.
# This compiles UVVM into nvc's system library path so it is always findable
# without any NVC_LIBPATH entry.
# ---------------------------------------------------------------------------
RUN nvc --install uvvm

# ---------------------------------------------------------------------------
# External VHDL library sources
# Pin these to specific tags for reproducibility. Update by rebuilding the image.
# ---------------------------------------------------------------------------

# IPBus firmware package  https://github.com/ipbus/ipbus-firmware
ARG IPBUS_TAG=v1.16
RUN git clone --depth 1 --branch "${IPBUS_TAG}" \
    https://github.com/ipbus/ipbus-firmware.git /opt/ipbus-firmware

# vip_ipbus – UVVM BFM for the IPBus protocol  https://github.com/olagrottvik/vip_ipbus
RUN git clone --depth 1 \
    https://github.com/olagrottvik/vip_ipbus.git /opt/vip_ipbus

# ---------------------------------------------------------------------------
# Compile IPBus and vip_ipbus into /opt/nvc-libs/.
# NVC_LIBPATH is set so every subsequent nvc invocation can resolve them.
# ---------------------------------------------------------------------------
ENV NVC_LIBPATH=/opt/nvc-libs

COPY scripts/compile_libs.sh /opt/compile_libs.sh
RUN chmod +x /opt/compile_libs.sh && /opt/compile_libs.sh

# Default working directory – mount the bust project here at runtime
WORKDIR /work
