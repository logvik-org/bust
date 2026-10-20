# SPDX-License-Identifier: Apache-2.0
"""Draw the bust logo, wordmark, favicon and social preview into docs/images.

The letters are built like the logvik mark: a 40-unit stroke, a 60-unit outer
corner radius with a concentric 20-unit inner one, and square ends, all on a
20-unit grid. The teal square in the counter of the b is one register bit. The
tagline and the favicon are pixel art on the same grid.

Run it from the repository root. The PNG files need CairoSVG:

    pip install cairosvg
    python scripts/make_logo.py
"""

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"

# The logvik paper, ink and teal, with lighter ink and teal for dark backgrounds.
THEMES = {
    "light": {"ink": "#1c2118", "teal": "#2c6e6a", "muted": "#4a4d43"},
    "dark": {"ink": "#ece8df", "teal": "#5fa8a0", "muted": "#c9c3b6"},
}
PAPER = "#f2eee3"
TAGLINE = "SINGLE SOURCE OF TRUTH"

S = 40  # stroke
R = 60  # outer corner radius
r = R - S  # inner corner radius
X = 200  # x-height
A = 280  # ascender
GAP = 40  # space between letters
BIT = (60, -120, 60, 60)  # x, y, width and height of the bit in the b
TRACK = 2  # tagline letter spacing, in pixels

# The b at one pixel per 20-unit cell, for the favicon: ink (#) and bit (o).
FAVICON = [
    "##........",
    "##........",
    "##........",
    "##........",
    "#######...",
    "#########.",
    "##.....##.",
    "##......##",
    "##.ooo..##",
    "##.ooo..##",
    "##.ooo..##",
    "##......##",
    "##########",
    ".#########",
]

# 5x7 pixel capitals for the tagline, plus narrow punctuation.
PIXEL_FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00001", "00001", "00001", "00001", "10001", "01110"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    ",": ["00", "00", "00", "00", "11", "01", "10"],
    ".": ["00", "00", "00", "00", "00", "11", "11"],
    "-": ["000", "000", "000", "111", "000", "000", "000"],
    " ": ["00000"] * 7,
}


def num(v: float) -> str:
    return ("%.3f" % v).rstrip("0").rstrip(".")


class Path2D:
    """A minimal SVG path builder. y grows downwards, the baseline is y=0."""

    def __init__(self) -> None:
        self.parts: list[str] = []

    def move(self, x: float, y: float) -> "Path2D":
        self.parts.append(f"M{num(x)} {num(y)}")
        return self

    def line(self, x: float, y: float) -> "Path2D":
        self.parts.append(f"L{num(x)} {num(y)}")
        return self

    def arc(self, radius: float, x: float, y: float, sweep: int = 1) -> "Path2D":
        self.parts.append(f"A{num(radius)} {num(radius)} 0 0 {sweep} {num(x)} {num(y)}")
        return self

    def close(self) -> "Path2D":
        self.parts.append("Z")
        return self

    def __str__(self) -> str:
        return "".join(self.parts)


def letter_b(w: float = 200, bowl: float = 100) -> tuple[str, float]:
    """A stem and a bowl whose top right is a quarter circle."""
    inner = bowl - S
    p = Path2D()
    p.move(0, -A).line(S, -A).line(S, -X).line(w - bowl, -X).arc(bowl, w, -X + bowl)
    p.line(w, 0).line(R, 0).arc(R, 0, -R).close()
    p.move(S, -X + S).line(S, -S - r).arc(r, S + r, -S, 0).line(w - S, -S)
    p.line(w - S, -X + S + inner).arc(inner, w - S - inner, -X + S, 0).close()
    return str(p), w


def letter_u(w: float = 200) -> tuple[str, float]:
    p = Path2D()
    p.move(0, -X).line(S, -X).line(S, -S - r).arc(r, S + r, -S, 0).line(w - S, -S)
    p.line(w - S, -X).line(w, -X).line(w, 0).line(R, 0).arc(R, 0, -R).close()
    return str(p), w


def letter_s(w: float = 180) -> tuple[str, float]:
    """Three bars joined by a rounded spine."""
    top, bottom = -X / 2 - S / 2, -X / 2 + S / 2
    p = Path2D()
    p.move(R, -X).line(w, -X).line(w, -X + S).line(S + r, -X + S)
    p.arc(r, S, -X + S + r, 0).line(S, top).line(w - R, top).arc(R, w, top + R)
    p.line(w, -R).arc(R, w - R, 0).line(0, 0).line(0, -S).line(w - S - r, -S)
    p.arc(r, w - S, -S - r, 0).line(w - S, bottom).line(R, bottom)
    p.arc(R, 0, bottom - R).line(0, -X + R).arc(R, R, -X).close()
    return str(p), w


def letter_t(w: float = 160, top: float = -260) -> tuple[str, float]:
    """The logvik L with a crossbar."""
    x0, x1 = S, 2 * S
    p = Path2D()
    p.move(x0, top).line(x1, top).line(x1, -X).line(w, -X).line(w, -X + S)
    p.line(x1, -X + S).line(x1, -S - r).arc(r, x1 + r, -S, 0).line(w, -S)
    p.line(w, 0).line(x0 + R, 0).arc(R, x0, -R).line(x0, -X + S).line(0, -X + S)
    p.line(0, -X).line(x0, -X).close()
    return str(p), w


def wordmark(theme: str) -> tuple[str, float]:
    """The letters and the bit, with the baseline at y=0. Returns SVG and width."""
    colours = THEMES[theme]
    paths, x = [], 0.0
    for draw in (letter_b, letter_u, letter_s, letter_t):
        d, w = draw()
        paths.append(f'<path transform="translate({num(x)} 0)" d="{d}"/>')
        x += w + GAP
    bx, by, bw, bh = BIT
    body = (
        f'<g fill="{colours["ink"]}" fill-rule="evenodd">{"".join(paths)}</g>'
        f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{colours["teal"]}"/>'
    )
    return body, x - GAP


def tagline(text: str, width: float, colour: str) -> tuple[str, float]:
    """The tagline in pixel capitals, with the pixel size chosen to span `width`.

    Returns SVG and height.
    """
    glyphs = [PIXEL_FONT[c] for c in text]
    px = width / (sum(len(g[0]) for g in glyphs) + TRACK * (len(glyphs) - 1))
    runs, x = [], 0.0
    for glyph in glyphs:
        for row, bits in enumerate(glyph):
            col = 0
            while col < len(bits):
                if bits[col] == "1":
                    length = len(bits[col:]) - len(bits[col:].lstrip("1"))
                    runs.append(
                        f"M{num(x + col * px)} {num(row * px)}"
                        f"h{num(length * px)}v{num(px)}h{num(-length * px)}Z"
                    )
                    col += length
                else:
                    col += 1
        x += (len(glyph[0]) + TRACK) * px
    return f'<path fill="{colour}" d="{"".join(runs)}"/>', 7 * px


def svg(view_box: str, body: str, label: str, extra: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" '
        f'role="img" aria-label="{label}"{extra}>{body}</svg>\n'
    )


def logo_body(theme: str, text: str = TAGLINE) -> tuple[str, tuple[float, ...]]:
    """The wordmark over the tagline. Returns SVG and the x, y, width and height
    of the box around it."""
    body, width = wordmark(theme)
    line, height = tagline(text, width, THEMES[theme]["muted"])
    body += f'<g transform="translate(0 80)">{line}</g>'
    m = 40
    return body, (-m, -A - m, width + 2 * m, A + 80 + height + 2 * m)


def logo(theme: str, text: str = TAGLINE) -> str:
    body, box = logo_body(theme, text)
    return svg(" ".join(num(v) for v in box), body, f"bust: {text.lower()}")


def social_preview() -> str:
    """The light logo on a paper card of the size GitHub asks for, 1280 by 640."""
    w, h, logo_width = 1280, 640, 760
    body, (x, y, bw, bh) = logo_body("light")
    scale = logo_width / bw
    tx, ty = (w - bw * scale) / 2 - x * scale, (h - bh * scale) / 2 - y * scale
    place = f"translate({num(tx)} {num(ty)}) scale({num(scale)})"
    card = f'<rect width="{w}" height="{h}" fill="{PAPER}"/>'
    card += f'<g transform="{place}">{body}</g>'
    return svg(f"0 0 {w} {h}", card, f"bust: {TAGLINE.lower()}")


def wordmark_svg(theme: str) -> str:
    body, width = wordmark(theme)
    return svg(f"0 {-A} {num(width)} {A}", body, "bust")


def favicon() -> str:
    """The pixel b on a paper tile, 16 units square."""
    colours = THEMES["light"]
    ox, oy = (16 - len(FAVICON[0])) // 2, (16 - len(FAVICON)) // 2
    body = f'<rect width="16" height="16" rx="3" fill="{PAPER}"/>'
    for y, row in enumerate(FAVICON):
        for x, cell in enumerate(row):
            if cell != ".":
                fill = colours["teal"] if cell == "o" else colours["ink"]
                body += f'<rect x="{x + ox}" y="{y + oy}" width="1" height="1" fill="{fill}"/>'
    return svg("0 0 16 16", body, "bust", ' shape-rendering="crispEdges"')


def main() -> None:
    import cairosvg  # type: ignore[import-not-found]

    OUT.mkdir(parents=True, exist_ok=True)
    files = {"favicon.svg": favicon()}
    for theme in THEMES:
        files[f"logo-{theme}.svg"] = logo(theme)
        files[f"wordmark-{theme}.svg"] = wordmark_svg(theme)
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")
    for theme in THEMES:
        cairosvg.svg2png(
            bytestring=files[f"logo-{theme}.svg"].encode(),
            write_to=str(OUT / f"logo-{theme}.png"),
            output_width=1200,
        )
    cairosvg.svg2png(
        bytestring=files["favicon.svg"].encode(),
        write_to=str(OUT / "favicon.png"),
        output_width=64,
    )
    cairosvg.svg2png(
        bytestring=social_preview().encode(),
        write_to=str(OUT / "social-preview.png"),
        output_width=1280,
    )
    print(f"Wrote {len(files) + 4} files to {OUT}")


if __name__ == "__main__":
    main()
