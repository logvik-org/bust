#!/usr/bin/env bash
# =============================================================================
# run_sim.sh  –  Compile and run a bust VHDL testbench with nvc
#
# Usage (inside Docker container, project mounted at /work):
#   /work/sim/scripts/run_sim.sh <testbench_target>
#
# Supported targets:
#   example_ipbus   Run example/example_ipbus/tb/example_ipbus_ipb_pif_tb.vhd
#   example_axi     Run example/example_axi/tb/example_axi_axi_pif_tb.vhd
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
        COMPILE_ORDER=(
            "${WORK_ROOT}/example/example_ipbus/hdl/example_ipbus_pif_pkg.vhd"
            "${WORK_ROOT}/example/example_ipbus/hdl/example_ipbus_ipb_pif.vhd"
            "${WORK_ROOT}/example/example_ipbus/tb/example_ipbus_ipb_pif_tb.vhd"
        )
        TOP_ENTITY="example_ipbus_ipb_pif_tb"
        ;;
    example_axi)
        # axi_pkg.vhd is referenced as 'library bust' in the testbench.
        # We compile it into a separate 'bust' library inside the scratch dir.
        pre_compile() {
            echo "  [nvc -a] axi_pkg.vhd -> library bust"
            local bust_path="${SIM_WORK_DIR}/bust"
            nvc --std=08 --work="bust:${bust_path}" \
                -a "${WORK_ROOT}/example/example_axi/hdl/axi_pkg.vhd"
        }
        COMPILE_ORDER=(
            "${WORK_ROOT}/example/example_axi/hdl/example_axi_pif_pkg.vhd"
            "${WORK_ROOT}/example/example_axi/hdl/example_axi_axi_pif.vhd"
            "${WORK_ROOT}/example/example_axi/tb/example_axi_axi_pif_tb.vhd"
        )
        TOP_ENTITY="example_axi_axi_pif_tb"
        ;;
    *)
        echo "ERROR: Unknown target '${TARGET}'." >&2
        echo "Supported targets: example_ipbus, example_axi" >&2
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
# 2. Elaborate
# ---------------------------------------------------------------------------
echo ""
echo "--- Elaborating ${TOP_ENTITY} ---"
nvc ${NVC_OPTS} -e "${TOP_ENTITY}"

# ---------------------------------------------------------------------------
# 3. Run simulation and capture output
# ---------------------------------------------------------------------------
echo ""
echo "--- Running simulation ---"
echo ""

SIM_LOG="${SIM_WORK_DIR}/sim.log"

# nvc exits with non-zero if std.env.failure is called (UVVM error path).
# Capture the log so we can always print it and inspect it.
set +e
nvc ${NVC_OPTS} -r "${TOP_ENTITY}" 2>&1 | tee "${SIM_LOG}"
SIM_EXIT=${PIPESTATUS[0]}
set -e

echo ""
echo "============================================================"

# ---------------------------------------------------------------------------
# 4. Result evaluation
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
