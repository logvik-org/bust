# SPDX-License-Identifier: Apache-2.0
"""Draw the address figure of docs/addressing.md.

The figure is inline SVG in the page, so it takes its colours from the theme
through the classes styled in docs/_static/custom.css. This script replaces the
<svg class="addr-fig"> element in the page. Run it from the repository root:

    python scripts/make_address_figure.py
"""

import re
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / "docs" / "addressing.md"

X0 = 8  # left margin
W_BASE, W_MID, W_REG = 212, 152, 76  # base address, above the registers, select
BAR_H = 30

# One row per setting: name, G_CHECK_BASE_ADDRESS, G_MODULE_ADDR_WIDTH, fields.
ROWS = [
    ("A", "true", 4, [("base", W_BASE + W_MID, "compared with G_BASE_ADDRESS")]),
    (
        "B",
        "false",
        12,
        [("ignore", W_BASE, "not checked"), ("zero", W_MID, "must be 0")],
    ),
    ("C", "false", 4, [("ignore", W_BASE + W_MID, "not checked")]),
]


def figure() -> str:
    out = []

    def rect(x, y, w, kind):
        out.append(
            f'<rect class="f-{kind}" x="{x}" y="{y}" width="{w}" height="{BAR_H}" rx="3"/>'
        )

    def text(x, y, s, cls="t", anchor="middle"):
        out.append(
            f'<text class="{cls}" x="{x:g}" y="{y}" text-anchor="{anchor}">{s}</text>'
        )

    def bracket(x1, x2, y, label, anchor="middle"):
        for a, b, c, d in (
            (x1 + 1, y, x2 - 1, y),
            (x1 + 1, y - 5, x1 + 1, y),
            (x2 - 1, y - 5, x2 - 1, y),
        ):
            out.append(f'<line class="brace" x1="{a}" y1="{b}" x2="{c}" y2="{d}"/>')
        tx = {"middle": (x1 + x2) / 2, "end": x2 - 1, "start": x1 + 1}[anchor]
        text(tx, y + 14, label, "code", anchor)

    xb, xm, xr = X0, X0 + W_BASE, X0 + W_BASE + W_MID
    xe = xr + W_REG

    # Bit numbers for the timer with G_MODULE_ADDR_WIDTH => 12.
    for x, s, anchor in (
        (xb + 2, "31", "start"),
        (xm - 3, "12", "end"),
        (xm + 3, "11", "start"),
        (xr - 3, "4", "end"),
        (xr + 3, "3", "start"),
        (xe - 2, "0", "end"),
    ):
        text(x, 14, s, "bits", anchor)

    # The parts of an address.
    y = 22
    rect(xb, y, W_BASE, "base")
    rect(xm, y, W_MID, "zero")
    rect(xr, y, W_REG, "reg")
    text(xb + W_BASE / 2, y + 20, "base address")
    text(xm + W_MID / 2, y + 20, "above the registers")
    text(xr + W_REG / 2, y + 20, "register", "t-reg")
    yb = y + BAR_H + 8
    bracket(xr, xe, yb, "C_MODULE_ADDR_WIDTH bits", "end")
    bracket(xm, xe, yb + 28, "range: G_MODULE_ADDR_WIDTH bits")
    bracket(xb, xm, yb + 28, "the rest of addr_width")

    # The settings.
    y = yb + 76
    for name, check, width, fields in ROWS:
        text(xb, y, name, "row", "start")
        settings = (
            f"G_CHECK_BASE_ADDRESS =&gt; {check}, G_MODULE_ADDR_WIDTH =&gt; {width}"
        )
        text(xb + 16, y, settings, "code", "start")
        y += 7
        x = xb
        for kind, w, label in fields:
            rect(x, y, w, kind)
            text(x + w / 2, y + 20, label)
            x += w
        rect(x, y, W_REG, "reg")
        text(x + W_REG / 2, y + 20, "register", "t-reg")
        y += BAR_H + 26

    label = (
        "How the register file splits an address into base address, the part "
        "of the address range above the registers and register select, for "
        "three settings of the generics"
    )
    return (
        f'<svg class="addr-fig" viewBox="0 0 {X0 * 2 + W_BASE + W_MID + W_REG} {y - 14}" '
        f'role="img" aria-label="{label}">' + "".join(out) + "</svg>"
    )


def main() -> None:
    page = PAGE.read_text(encoding="utf-8")
    new, count = re.subn(
        r'<svg class="addr-fig".*?</svg>', lambda _: figure(), page, flags=re.S
    )
    if count != 1:
        raise SystemExit(f"Expected one address figure in {PAGE}, found {count}")
    PAGE.write_text(new, encoding="utf-8")
    print(f"Updated the address figure in {PAGE}")


if __name__ == "__main__":
    main()
