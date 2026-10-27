#!/usr/bin/env bash
# Build docs/examples/prototype.pdf, the example PDF the documentation shows,
# from the committed prototype.tex. Read the Docs has no pdflatex, so the PDF is
# committed. Run this after the LaTeX golden changes.
# Usage: scripts/make-example-pdf.sh
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT

cp "$repo/example/example_prototype/doc/prototype.tex" "$build_dir/"
cd "$build_dir"
# Pin \today and the PDF dates to the time the HTML golden shows.
export SOURCE_DATE_EPOCH=0 FORCE_SOURCE_DATE=1
# The second run resolves the references the first one writes to the .aux file.
for _ in 1 2; do
    pdflatex --interaction=batchmode prototype.tex > /dev/null
done
mkdir -p "$repo/docs/examples"
cp prototype.pdf "$repo/docs/examples/prototype.pdf"
