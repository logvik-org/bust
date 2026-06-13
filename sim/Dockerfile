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

# Pin to an immutable digest (tag 1.19.3) for reproducible, supply-chain-safe
# builds. Update deliberately by bumping both the tag and the digest.
FROM ghcr.io/nickg/nvc:1.19.3@sha256:863591811e713ebfac4828092eca8ea9d91851d89288f4ed4665954741c8ee1e

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
# Pinned to a specific commit so upstream changes cannot silently alter the
# VHDL executed during simulation. Bump VIP_IPBUS_REF to upgrade deliberately.
ARG VIP_IPBUS_REF=97fdf12ab7b895ee2b1d6926be120d6805ab9461
RUN git clone https://github.com/olagrottvik/vip_ipbus.git /opt/vip_ipbus \
    && git -C /opt/vip_ipbus checkout --detach "${VIP_IPBUS_REF}"

# ---------------------------------------------------------------------------
# Compile IPBus and vip_ipbus into /opt/nvc-libs/.
# NVC_LIBPATH is set so every subsequent nvc invocation can resolve them.
# ---------------------------------------------------------------------------
ENV NVC_LIBPATH=/opt/nvc-libs

COPY scripts/compile_libs.sh /opt/compile_libs.sh
RUN chmod +x /opt/compile_libs.sh && /opt/compile_libs.sh

# Default working directory – mount the bust project here at runtime
WORKDIR /work
