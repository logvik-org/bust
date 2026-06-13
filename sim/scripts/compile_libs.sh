#!/usr/bin/env bash
# =============================================================================
# compile_libs.sh
#
# Compiles project-specific VHDL libraries into ${NVC_LIBPATH} using nvc.
# UVVM is NOT compiled here – it is installed via `nvc --install uvvm` during
# the Docker image build and lives in nvc's system library path.
#
# Libraries compiled:
#   ipbus     – IPBus protocol package (ipb_wbus / ipb_rbus records)
#   vip_ipbus – UVVM BFM for the IPBus protocol (BFM package only)
#
# Designed to run inside the bust-sim Docker image during build.
# =============================================================================
set -euo pipefail

IPBUS_FW_DIR="${IPBUS_FW_DIR:-/opt/ipbus-firmware}"
VIP_IPBUS_DIR="${VIP_IPBUS_DIR:-/opt/vip_ipbus}"
LIB_DIR="${NVC_LIBPATH:-/opt/nvc-libs}"
# Export so every nvc invocation below can resolve inter-library dependencies
# (e.g. vip_ipbus -> ipbus) even when this script is run outside the Docker build.
export NVC_LIBPATH="${LIB_DIR}"

mkdir -p "${LIB_DIR}"

echo "========================================================"
echo "  Compiling project VHDL libraries"
echo "  NVC_LIBPATH : ${LIB_DIR}"
echo "  IPBus FW    : ${IPBUS_FW_DIR}"
echo "  vip_ipbus   : ${VIP_IPBUS_DIR}"
echo "========================================================"
echo ""

# ---------------------------------------------------------------------------
# Helper: analyze VHDL files into a named library (strict VHDL-2008).
# The library directory is created by nvc; do not pre-create it or nvc
# will warn that it is "not an NVC library".
# ---------------------------------------------------------------------------
analyze() {
    local lib="$1"; shift
    local lib_path="${LIB_DIR}/${lib}"
    echo "  [nvc] ${lib} <- $(basename "$1")"
    nvc --std=08 --work="${lib}:${lib_path}" -a "$@"
}

# Like analyze(), but with --relaxed to permit UVVM's shared_msg_id_panel
# used as a default parameter value (not strictly static per VHDL-2008).
analyze_relaxed() {
    local lib="$1"; shift
    local lib_path="${LIB_DIR}/${lib}"
    echo "  [nvc --relaxed] ${lib} <- $(basename "$1")"
    nvc --std=08 --work="${lib}:${lib_path}" -a --relaxed "$@"
}

# ---------------------------------------------------------------------------
# 1. IPBus firmware package
#    A single VHDL file containing the ipb_wbus / ipb_rbus record types.
# ---------------------------------------------------------------------------
echo "--- 1. IPBus firmware package ---"
analyze ipbus \
    "${IPBUS_FW_DIR}/components/ipbus_core/firmware/hdl/ipbus_package.vhd"

# ---------------------------------------------------------------------------
# 2. vip_ipbus – UVVM BFM for IPBus (BFM package only)
#
#    The testbenches use the direct BFM style (ipbus_bfm_pkg) rather than
#    the full UVVM VVC infrastructure, so only ipbus_bfm_pkg.vhd is compiled.
#
#    --relaxed is required because UVVM uses shared_msg_id_panel as a default
#    parameter value, which is not strictly static per VHDL-2008.
#
#    Depends on: uvvm_util (nvc system path), ipbus (NVC_LIBPATH above)
# ---------------------------------------------------------------------------
echo ""
echo "--- 2. vip_ipbus (BFM only) ---"
analyze_relaxed vip_ipbus \
    "${VIP_IPBUS_DIR}/src/ipbus_bfm_pkg.vhd"

# ---------------------------------------------------------------------------
echo ""
echo "========================================================"
echo "  All libraries compiled successfully."
echo "  Contents of ${LIB_DIR}:"
ls -1 "${LIB_DIR}"
echo "========================================================"
