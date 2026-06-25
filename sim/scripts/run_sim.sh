#!/usr/bin/env bash
# =============================================================================
# run_sim.sh  –  Compile and run a bust VHDL testbench with nvc
#
# Usage (inside Docker container, project mounted at /work):
#   /work/sim/scripts/run_sim.sh <testbench_target> [--wave[=FILE]]
#
# Supported targets:
#   example_ipbus   Run example/example_ipbus/tb/example_ipbus_ipb_pif_tb.vhd
#   example_axi     Run example/example_axi/tb/example_axi_axi_pif_tb.vhd
#   prototype       Run hdl/prototype/tb/prototype_regfile_tb.vhd (UVVM BFM)
#   prototype_generated  As 'prototype', but compiling the generator's emitted
#                   package (example/example_prototype) instead of the hand-written one
#   prototype_axi   Run hdl/prototype/tb/prototype_axi_endpoint_tb.vhd (AXI-Lite VIP)
#   prototype_axi_generated  As 'prototype_axi', but compiling the generator's
#                   emitted package, regfile, and AXI endpoint
#   prototype_tb_generated  The fully generated AXI stack incl. the generated UVVM
#                   testbench, self-checking the plain read-write registers
#   prototype_ipbus Run hdl/prototype/tb/prototype_ipb_endpoint_tb.vhd (vip_ipbus)
#   prototype_ipbus_generated  As 'prototype_ipbus', but compiling the generator's
#                   emitted package, regfile, and IPBus endpoint
#   prototype_ipbus_tb_generated  The fully generated IPBus stack incl. the
#                   generated UVVM testbench, self-checking every access mode
#   prototype_sbi   Run hdl/prototype/tb/prototype_sbi_endpoint_tb.vhd (SBI VIP)
#   prototype_avalon Run hdl/prototype/tb/prototype_avalon_endpoint_tb.vhd (Avalon-MM VIP)
#   prototype_wishbone Run hdl/prototype/tb/prototype_wishbone_endpoint_tb.vhd (hand BFM)
#   prototype_apb   Run hdl/prototype/tb/prototype_apb_endpoint_tb.vhd (hand BFM)
#
# Optional flags:
#   --wave          Generate a waveform file (FST) for GTKWave debugging.
#                   Output: ${WORK_ROOT}/sim/waves/<target>.fst
#   --wave=FILE     As above, but write to a specific path.
#
# Exit code:
#   0  – simulation completed; UVVM reported SUCCESS
#   1  – compilation error, elaboration error, or UVVM reported FAIL
#
# Environment:
#   NVC_LIBPATH   must point to directory with pre-compiled shared libraries.
#                 Defaults to /opt/nvc-libs (set in Docker image).
# =============================================================================
set -euo pipefail

TARGET="${1:-example_ipbus}"
WORK_ROOT="${WORK_ROOT:-/work}"
NVC_LIBPATH="${NVC_LIBPATH:-/opt/nvc-libs}"
export NVC_LIBPATH

# ---------------------------------------------------------------------------
# Parse optional flags (everything after the positional TARGET argument)
# ---------------------------------------------------------------------------
WAVE_FILE=""
for arg in "${@:2}"; do
    case "${arg}" in
        --wave=*)  WAVE_FILE="${arg#--wave=}" ;;
        --wave)    WAVE_FILE="${WORK_ROOT}/sim/waves/${TARGET}.fst" ;;
        *)         echo "WARNING: unknown argument '${arg}' – ignored" >&2 ;;
    esac
done

# Scratch directory for this run's work library – cleaned up on exit
SIM_WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${SIM_WORK_DIR}"' EXIT

WORK_LIB="${TARGET}"
WORK_PATH="${SIM_WORK_DIR}/${WORK_LIB}"
# Do NOT mkdir WORK_PATH: nvc creates it when it initialises the work library.

# NVC_OPTS targets the project work library.
# SIM_WORK_DIR is added to the library search path so that any extra lib
# compiled by pre_compile() (e.g. 'bust' for axi_pkg) is visible during
# both analysis and elaboration.
NVC_OPTS="--std=08 --work=${WORK_LIB}:${WORK_PATH} -L ${SIM_WORK_DIR}"

echo "============================================================"
echo "  bust VHDL simulation"
echo "  Target      : ${TARGET}"
echo "  NVC_LIBPATH : ${NVC_LIBPATH}"
echo "  Work dir    : ${SIM_WORK_DIR}"
if [[ -n "${WAVE_FILE}" ]]; then
    echo "  Waveform    : ${WAVE_FILE}"
fi
echo "============================================================"
echo ""

# ---------------------------------------------------------------------------
# Per-target compile lists and top-level entity
# Add new targets here as the project grows.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Target-specific pre-compile hook (optional).
# Used to compile shared libs that are NOT in NVC_LIBPATH (e.g. axi_pkg into
# the 'bust' library).  Called before the main COMPILE_ORDER loop.
# Override per-target below.
# ---------------------------------------------------------------------------
pre_compile() { :; }  # default: no-op

case "${TARGET}" in
    example_ipbus)
        # The generated local-bus IPBus stack (package, regfile, endpoint, top)
        # and generated UVVM testbench over the stock vip_ipbus VIP.
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/example/example_ipbus/hdl/example_ipbus_regfile_pkg.vhd"
            "${WORK_ROOT}/example/example_ipbus/hdl/example_ipbus_regfile.vhd"
            "${WORK_ROOT}/example/example_ipbus/hdl/example_ipbus_ipb_endpoint.vhd"
            "${WORK_ROOT}/example/example_ipbus/hdl/example_ipbus.vhd"
            "${WORK_ROOT}/example/example_ipbus/tb/example_ipbus_tb.vhd"
        )
        TOP_ENTITY="example_ipbus_tb"
        ;;
    example_axi)
        # The generated local-bus AXI stack (package, regfile, endpoint, top) and
        # generated UVVM testbench over the stock Bitvis AXI-Lite VIP.
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/example/example_axi/hdl/example_axi_regfile_pkg.vhd"
            "${WORK_ROOT}/example/example_axi/hdl/example_axi_regfile.vhd"
            "${WORK_ROOT}/example/example_axi/hdl/example_axi_axi_endpoint.vhd"
            "${WORK_ROOT}/example/example_axi/hdl/example_axi.vhd"
            "${WORK_ROOT}/example/example_axi/tb/example_axi_tb.vhd"
        )
        TOP_ENTITY="example_axi_tb"
        ;;
    prototype)
        # Local-bus register-file prototype with a UVVM testbench.
        # localbus_bfm_pkg uses uvvm_util's shared_msg_id_panel as a default
        # parameter value, which is not strictly static per VHDL-2008, so it is
        # analysed with --relaxed (as vip_ipbus is at image-build time).
        # uvvm_util itself resolves from nvc's system library path.
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
            echo "  [nvc -a --relaxed] localbus_bfm_pkg.vhd"
            nvc ${NVC_OPTS} -a --relaxed "${WORK_ROOT}/hdl/prototype/localbus_bfm_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/hdl/prototype/prototype_regfile_pkg.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_regfile.vhd"
            "${WORK_ROOT}/hdl/prototype/tb/prototype_regfile_tb.vhd"
        )
        TOP_ENTITY="prototype_regfile_tb"
        ;;
    prototype_generated)
        # The generator's emitted package AND entity (example/example_prototype)
        # compiled against the same verified UVVM testbench as 'prototype'. A PASS
        # proves the generated output compiles and behaves under the self-checking
        # testbench, not just that it matches the prototype textually.
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
            echo "  [nvc -a --relaxed] localbus_bfm_pkg.vhd"
            nvc ${NVC_OPTS} -a --relaxed "${WORK_ROOT}/hdl/prototype/localbus_bfm_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_regfile_pkg.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_regfile.vhd"
            "${WORK_ROOT}/hdl/prototype/tb/prototype_regfile_tb.vhd"
        )
        TOP_ENTITY="prototype_regfile_tb"
        ;;
    prototype_axi)
        # AXI4-Lite wrapper over the local-bus regfile, checked with the stock
        # Bitvis AXI-Lite VIP (resolved from nvc's system library path).
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/hdl/prototype/prototype_regfile_pkg.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_regfile.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_axi_endpoint.vhd"
            "${WORK_ROOT}/hdl/prototype/tb/prototype_axi_endpoint_tb.vhd"
        )
        TOP_ENTITY="prototype_axi_endpoint_tb"
        ;;
    prototype_axi_generated)
        # The generator's emitted package, regfile, and AXI endpoint compiled
        # against the verified AXI-Lite endpoint testbench. Proves the generated
        # AXI stack behaves, not just that it matches the prototype textually.
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_regfile_pkg.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_regfile.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_axi_endpoint.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype.vhd"
            "${WORK_ROOT}/hdl/prototype/tb/prototype_axi_endpoint_tb.vhd"
        )
        TOP_ENTITY="prototype_axi_endpoint_tb"
        ;;
    prototype_tb_generated)
        # The generator's emitted package, regfile, endpoint, top wrapper, AND
        # UVVM testbench - the whole AXI stack generated by bust, self-checking
        # the plain read-write registers over the stock AXI-Lite VIP.
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_regfile_pkg.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_regfile.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_axi_endpoint.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_tb.vhd"
        )
        TOP_ENTITY="prototype_tb"
        ;;
    prototype_ipbus)
        # IPBus wrapper over the local-bus regfile, checked with the stock
        # vip_ipbus VIP (resolved from nvc's system library path).
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/hdl/prototype/prototype_regfile_pkg.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_regfile.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_ipb_endpoint.vhd"
            "${WORK_ROOT}/hdl/prototype/tb/prototype_ipb_endpoint_tb.vhd"
        )
        TOP_ENTITY="prototype_ipb_endpoint_tb"
        ;;
    prototype_ipbus_generated)
        # The generator's emitted package, regfile, and IPBus endpoint compiled
        # against the verified IPBus endpoint testbench.
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_regfile_pkg.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_regfile.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_ipb_endpoint.vhd"
            "${WORK_ROOT}/hdl/prototype/tb/prototype_ipb_endpoint_tb.vhd"
        )
        TOP_ENTITY="prototype_ipb_endpoint_tb"
        ;;
    prototype_ipbus_tb_generated)
        # The generator's emitted package, regfile, IPBus endpoint, top wrapper,
        # AND UVVM testbench - the whole IPBus stack generated by bust, self-
        # checking every access mode over the stock vip_ipbus VIP.
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_regfile_pkg.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_regfile.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_ipb_endpoint.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_ipbus.vhd"
            "${WORK_ROOT}/example/example_prototype/hdl/prototype_ipbus_tb.vhd"
        )
        TOP_ENTITY="prototype_tb"
        ;;
    prototype_sbi)
        # SBI wrapper over the local-bus regfile, checked with the stock Bitvis
        # SBI VIP (resolved from nvc's system library path).
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/hdl/prototype/prototype_regfile_pkg.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_regfile.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_sbi_endpoint.vhd"
            "${WORK_ROOT}/hdl/prototype/tb/prototype_sbi_endpoint_tb.vhd"
        )
        TOP_ENTITY="prototype_sbi_endpoint_tb"
        ;;
    prototype_avalon)
        # Avalon-MM wrapper over the local-bus regfile, checked with the stock
        # Bitvis Avalon-MM VIP (resolved from nvc's system library path).
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/hdl/prototype/prototype_regfile_pkg.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_regfile.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_avalon_endpoint.vhd"
            "${WORK_ROOT}/hdl/prototype/tb/prototype_avalon_endpoint_tb.vhd"
        )
        TOP_ENTITY="prototype_avalon_endpoint_tb"
        ;;
    prototype_wishbone)
        # Wishbone wrapper over the local-bus regfile. UVVM has no Wishbone VIP,
        # so the testbench carries a hand-written classic-cycle master BFM and
        # needs only uvvm_util (resolved from nvc's system library path).
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/hdl/prototype/prototype_regfile_pkg.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_regfile.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_wishbone_endpoint.vhd"
            "${WORK_ROOT}/hdl/prototype/tb/prototype_wishbone_endpoint_tb.vhd"
        )
        TOP_ENTITY="prototype_wishbone_endpoint_tb"
        ;;
    prototype_apb)
        # APB wrapper over the local-bus regfile. UVVM has no APB VIP, so the
        # testbench carries a hand-written APB master BFM and needs only
        # uvvm_util (resolved from nvc's system library path).
        pre_compile() {
            echo "  [nvc -a] localbus_pkg.vhd"
            nvc ${NVC_OPTS} -a "${WORK_ROOT}/hdl/prototype/localbus_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/hdl/prototype/prototype_regfile_pkg.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_regfile.vhd"
            "${WORK_ROOT}/hdl/prototype/prototype_apb_endpoint.vhd"
            "${WORK_ROOT}/hdl/prototype/tb/prototype_apb_endpoint_tb.vhd"
        )
        TOP_ENTITY="prototype_apb_endpoint_tb"
        ;;
    *)
        echo "ERROR: Unknown target '${TARGET}'." >&2
        echo "Supported targets: example_ipbus, example_axi, prototype, prototype_generated, prototype_axi, prototype_axi_generated, prototype_tb_generated, prototype_ipbus, prototype_ipbus_generated, prototype_ipbus_tb_generated, prototype_sbi, prototype_avalon, prototype_wishbone, prototype_apb" >&2
        exit 1
        ;;
esac

# ---------------------------------------------------------------------------
# 1. Pre-compile (target-specific shared libs)
# ---------------------------------------------------------------------------
echo "--- Pre-compile (target-specific libs) ---"
pre_compile

# ---------------------------------------------------------------------------
# 2. Analyse (compile) project sources
# ---------------------------------------------------------------------------
echo "--- Analysing sources ---"
for vhd in "${COMPILE_ORDER[@]}"; do
    echo "  [nvc -a] $(basename "${vhd}")"
    nvc ${NVC_OPTS} -a "${vhd}"
done

# ---------------------------------------------------------------------------
# 3. Elaborate
# ---------------------------------------------------------------------------
echo ""
echo "--- Elaborating ${TOP_ENTITY} ---"
nvc ${NVC_OPTS} -e "${TOP_ENTITY}"

# ---------------------------------------------------------------------------
# 4. Run simulation and capture output
# ---------------------------------------------------------------------------
echo ""
echo "--- Running simulation ---"
echo ""

SIM_LOG="${SIM_WORK_DIR}/sim.log"

# Build optional wave argument.
# nvc --wave=FILE.fst writes an FST file (compact binary, readable by GTKWave).
WAVE_OPT=""
if [[ -n "${WAVE_FILE}" ]]; then
    mkdir -p "$(dirname "${WAVE_FILE}")"
    WAVE_OPT="--wave=${WAVE_FILE}"
fi

# nvc exits with non-zero if std.env.failure is called (UVVM error path).
# Capture the log so we can always print it and inspect it.
set +e
nvc ${NVC_OPTS} -r ${WAVE_OPT} "${TOP_ENTITY}" 2>&1 | tee "${SIM_LOG}"
SIM_EXIT=${PIPESTATUS[0]}
set -e

if [[ -n "${WAVE_FILE}" ]] && [[ -f "${WAVE_FILE}" ]]; then
    echo ""
    echo "  Waveform written: ${WAVE_FILE}"
fi

echo ""
echo "============================================================"

# ---------------------------------------------------------------------------
# 5. Result evaluation
#
# nvc returns 0 for std.env.stop (normal UVVM exit) and non-zero for
# std.env.failure (UVVM detected errors).  We additionally grep for UVVM's
# textual FAIL marker to be safe against edge-case exit-code quirks.
# ---------------------------------------------------------------------------
UVVM_FAIL=0
if grep -qiE "UVVM.*\*\*.*FAIL|\*\* FAIL \*\*|simulation result.*fail" "${SIM_LOG}" 2>/dev/null; then
    UVVM_FAIL=1
fi

if [ "${SIM_EXIT}" -ne 0 ] || [ "${UVVM_FAIL}" -ne 0 ]; then
    echo "  RESULT: FAIL (nvc exit=${SIM_EXIT}, uvvm_fail=${UVVM_FAIL})"
    echo "============================================================"
    exit 1
fi

echo "  RESULT: PASS"
echo "============================================================"
exit 0
