#!/usr/bin/env python3
"""Generate 4 technical-drawing SVG sheets explaining the Bosch IXO 7 screwdriver."""
import html
import math
import os
import sys

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

FONT = "Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', 'WenQuanYi Zen Hei', sans-serif"
INK = "#1d2a3a"
MUTED = "#5b6675"
PAPER = "#fbfaf6"
INTERIOR = "#f3f5f1"
STEEL = "#c3c9d1"
STEEL_D = "#8e98a3"
GREEN = "#2f8f5b"
BLUE = "#3b6fb6"
RED = "#d8432f"
AMBER = "#e8a33d"
AMBER_D = "#9a6510"
PLANET = "#a9cbe8"
PLANET_D = "#2c5d8a"
COPPER = "#c98b4b"
DARK = "#2b3037"
W, H = 1400, 900


# ---------------------------------------------------------------- primitives
def esc(s):
    return html.escape(str(s), quote=False)


def f(v):
    if isinstance(v, float):
        s = f"{v:.2f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(v)


def T(x, y, s, size=13, weight=400, fill=INK, anchor="start", extra=""):
    return (f'<text x="{f(x)}" y="{f(y)}" font-size="{f(size)}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" {extra}>{esc(s)}</text>')


def R(x, y, w, h, fill="none", stroke=INK, sw=1, rx=0, extra=""):
    return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{f(sw)}" {extra}/>')


def RH(x, y, w, h, base, pat="hmm", stroke=INK, sw=0.3, rx=0):
    """Rect with section hatching."""
    return (R(x, y, w, h, base, "none", 0, rx) + R(x, y, w, h, f"url(#{pat})", "none", 0, rx)
            + R(x, y, w, h, "none", stroke, sw, rx))


def L(x1, y1, x2, y2, stroke=INK, sw=1, extra=""):
    return (f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" '
            f'stroke="{stroke}" stroke-width="{f(sw)}" {extra}/>')


def C(cx, cy, r, fill="none", stroke=INK, sw=1, extra=""):
    return (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{f(sw)}" {extra}/>')


def P(d, fill="none", stroke=INK, sw=1, extra=""):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{f(sw)}" {extra}/>'


def poly(pts):
    return "M " + " L ".join(f"{f(x)},{f(y)}" for x, y in pts) + " Z"


def arc(cx, cy, r, a0, a1, color=INK, sw=2, marker="arw"):
    """Arc from angle a0 to a1 (degrees, screen coords: increasing = clockwise)."""
    x0 = cx + r * math.cos(math.radians(a0))
    y0 = cy + r * math.sin(math.radians(a0))
    x1 = cx + r * math.cos(math.radians(a1))
    y1 = cy + r * math.sin(math.radians(a1))
    large = 1 if abs(a1 - a0) > 180 else 0
    sweep = 1 if a1 > a0 else 0
    return P(f"M {f(x0)},{f(y0)} A {f(r)} {f(r)} 0 {large} {sweep} {f(x1)},{f(y1)}",
             "none", color, sw, f'marker-end="url(#{marker})" stroke-linecap="round"')


def text_w(s, size):
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o >= 0x2E80:
            w += 0.95
        elif ch == " ":
            w += 0.3
        elif ch in "MW@%":
            w += 0.85
        elif ch.isupper() or ch.isdigit():
            w += 0.62
        else:
            w += 0.52
    return w * size


def wrap(s, max_px, size):
    words = s.split(" ")
    lines, cur = [], ""
    for wd in words:
        cand = wd if not cur else cur + " " + wd
        if text_w(cand, size) <= max_px:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def para(x, y, s, max_px, size=13, lh=None, fill=INK, weight=400, lead=None, lead_fill=INK):
    """Wrapped paragraph; optional bold lead prefix. Returns (svg, next_y)."""
    lh = lh or size * 1.55
    full = (lead + "  " + s) if lead else s
    out = []
    for i, line in enumerate(wrap(full, max_px, size)):
        yy = y + i * lh
        if i == 0 and lead and line.startswith(lead):
            rest = line[len(lead):]
            out.append(f'<text x="{f(x)}" y="{f(yy)}" font-size="{f(size)}" fill="{fill}" font-weight="{weight}">'
                       f'<tspan font-weight="700" fill="{lead_fill}">{esc(lead)}</tspan>{esc(rest)}</text>')
        else:
            out.append(T(x, yy, line, size, weight, fill))
    return "".join(out), y + len(out) * lh


def leader(bx, by, ax, ay, r=0, sw=0.9, color=INK, dot=True):
    """Leader line from (bx,by) [optionally offset by radius r] to anchor (ax,ay)."""
    dx, dy = ax - bx, ay - by
    d = math.hypot(dx, dy) or 1
    sx, sy = bx + dx / d * r, by + dy / d * r
    s = L(sx, sy, ax, ay, "white", sw + 2.6, 'stroke-linecap="round" stroke-opacity="0.85"')
    s += L(sx, sy, ax, ay, color, sw)
    if dot:
        s += C(ax, ay, 2.3, color, "none", 0)
    return s


def balloon(n, bx, by, ax, ay, r=13):
    return (leader(bx, by, ax, ay, r) + C(bx, by, r, "white", INK, 1.4)
            + T(bx, by + 4.6, n, 13, 700, INK, "middle"))


def dim_h(x1, x2, y, label, ext_from=None, size=13):
    s = L(x1, y, x2, y, INK, 0.8, 'marker-start="url(#dim)" marker-end="url(#dim)"')
    s += T((x1 + x2) / 2, y - 7, label, size, 600, INK, "middle")
    return s


def dim_v(x, y1, y2, label, size=13):
    s = L(x, y1, x, y2, INK, 0.8, 'marker-start="url(#dim)" marker-end="url(#dim)"')
    cy = (y1 + y2) / 2
    s += T(x - 8, cy, label, size, 600, INK, "middle", f'transform="rotate(-90 {f(x - 8)} {f(cy)})"')
    return s


CL_DASH = 'stroke-dasharray="14 3 2 3"'

DEFS = f"""<defs>
<pattern id="hmm" width="1.6" height="1.6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="1.6" stroke="{INK}" stroke-width="0.17" stroke-opacity="0.55"/></pattern>
<pattern id="hmm2" width="1.6" height="1.6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><line x1="0" y1="0" x2="0" y2="1.6" stroke="{INK}" stroke-width="0.17" stroke-opacity="0.55"/></pattern>
<pattern id="hmmW" width="1.6" height="1.6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="1.6" stroke="#ffffff" stroke-width="0.17" stroke-opacity="0.45"/></pattern>
<pattern id="wind" width="0.9" height="0.9" patternUnits="userSpaceOnUse" patternTransform="rotate(-62)"><line x1="0" y1="0" x2="0" y2="0.9" stroke="#7a4a1c" stroke-width="0.24"/></pattern>
<pattern id="hpx" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="{INK}" stroke-width="0.8" stroke-opacity="0.5"/></pattern>
<pattern id="hpx2" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><line x1="0" y1="0" x2="0" y2="7" stroke="{INK}" stroke-width="0.8" stroke-opacity="0.5"/></pattern>
<pattern id="hpxW" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="#ffffff" stroke-width="0.8" stroke-opacity="0.35"/></pattern>
<pattern id="layR" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(32)"><line x1="0" y1="0" x2="0" y2="5" stroke="#4a5866" stroke-width="1.5"/></pattern>
<pattern id="layL" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-32)"><line x1="0" y1="0" x2="0" y2="5" stroke="#4a5866" stroke-width="1.5"/></pattern>
<marker id="dim" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,1.8 L10,5 L0,8.2 z" fill="{INK}"/></marker>
<marker id="arw" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" fill="{INK}"/></marker>
<marker id="arwB" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="12" markerHeight="12" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" fill="{BLUE}"/></marker>
<marker id="arwG" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="13" markerHeight="13" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" fill="{GREEN}"/></marker>
<marker id="arwA" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="12" markerHeight="12" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" fill="{AMBER_D}"/></marker>
<marker id="arwP" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="11" markerHeight="11" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" fill="{PLANET_D}"/></marker>
<marker id="arwR" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" fill="{RED}"/></marker>
</defs>"""


def footer(no):
    return (L(20, 852, W - 20, 852, INK, 0.8)
            + T(40, 874, "BOSCH IXO 7 무선 전동 드라이버 — 작동원리 도면집", 12.5, 600)
            + T(W - 40, 874, f"도번 IXO7-0{no}  ·  {no} / 4  ·  축척 NTS (개략)  ·  2026-10-07  ·  작성 Claude Code",
                12.5, 400, MUTED, "end"))


def sheet(no, title, sub, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            f'font-family="{FONT}">' + DEFS
            + R(0, 0, W, H, PAPER, "none", 0)
            + R(14, 14, W - 28, H - 28, "none", INK, 2) + R(20, 20, W - 40, H - 40, "none", INK, 0.6)
            + T(40, 58, title, 24, 700) + T(40, 82, sub, 13, 400, MUTED)
            + body + footer(no) + "</svg>")


# ====================================================================== SHEET 1
def sheet1():
    OX, OY, S = 110, 150, 4.0

    def X(x):
        return OX + S * x

    def Y(y):
        return OY + S * y

    g = []
    outer = ("M 26,3 C 26,1 28,0 31,0 L 118,0 C 132,0 140,8 141,22 L 147,104 C 148,114 142,120 132,120 "
             "L 114,120 C 106,120 102,116 101,110 L 92,50 C 91,45 88,40 83,40 L 31,40 C 28,40 26,39 26,37 Z")
    inner = ("M 28.2,4.6 C 28.2,3 29.5,2.2 31.5,2.2 L 118,2.2 C 130.6,2.2 138,9.6 138.8,22.4 "
             "L 144.8,104.2 C 145.6,112.4 140.6,117.8 132,117.8 L 114.4,117.8 C 107.8,117.8 104.6,114.6 103.2,109.6 "
             "L 94.2,49.6 C 93.4,44.6 89.6,37.8 83,37.8 L 31.5,37.8 C 29.5,37.8 28.2,37 28.2,35.4 Z")
    g.append(P(outer, "#dfe8e1", "none", 0))
    g.append(P(outer, "url(#hmm)", "none", 0))
    g.append(P(inner, INTERIOR, INK, 0.22))
    g.append(P(outer, "none", INK, 0.55))
    g.append(R(25.8, 12.5, 2.8, 15, INTERIOR, "none", 0))           # front bore

    # nose collar (black plastic, sectioned)
    for y in (8, 27.5):
        g.append(RH(14, y, 14, 4.5, "#59616b", "hmmW", INK, 0.3))
    # front bearings
    for y in (12.5, 23):
        g.append(R(17, y, 8, 4.5, "white", INK, 0.25))
        g.append(L(17, y, 25, y + 4.5, INK, 0.18) + L(17, y + 4.5, 25, y, INK, 0.18))

    # bit (protruding, PH tip)
    bit = "M -8,17 L 0,17 L 0,23 L -8,23 L -17,21.8 L -23,20.5 L -24.2,20 L -23,19.5 L -17,18.2 Z"
    g.append(P(bit, "#e7e9ec", INK, 0.3))
    g.append(L(-8, 18.6, 0, 18.6, INK, 0.12) + L(-8, 21.4, 0, 21.4, INK, 0.12))
    g.append(L(-22.5, 20, -17.5, 20, INK, 0.15))

    # magnetic bit holder
    g.append(RH(0, 14, 15, 12, STEEL, "hmm", INK, 0.3))
    g.append(R(0, 16.8, 11, 6.4, INTERIOR, INK, 0.2))
    g.append(R(0, 17, 10.5, 6, "none", INK, 0.2, 0, 'stroke-dasharray="0.9 0.6"'))  # hidden bit shank
    g.append(R(11, 17.3, 1.25, 5.4, "#d06a5a", INK, 0.15) + R(12.25, 17.3, 1.25, 5.4, "#5d7fb8", INK, 0.15))
    g.append(RH(15, 16, 2.6, 8, STEEL, "hmm", INK, 0.25))

    # spindle + spindle lock
    g.append(RH(17.5, 17, 17.5, 6, STEEL, "hmm2", INK, 0.28))
    g.append(RH(35, 16, 5, 8, STEEL_D, "hmm2", INK, 0.28))            # cam
    for y in (7, 28):
        g.append(RH(35, y, 5, 5, "#aab2bb", "hmm", INK, 0.28))         # lock ring
    for cy in (14, 26):
        g.append(C(37.5, cy, 1.9, "#4a5260", INK, 0.2))                # rollers

    # gearbox: ring gear housing
    for y in (6, 31.4):
        g.append(RH(40, y, 31, 2.6, "#cfd3d8", "hmm", INK, 0.3))
    # carrier 2 + planets 2 + sun 2(on carrier 1)
    g.append(RH(40.5, 9.5, 1.8, 21, "#7fb894", "hmm", INK, 0.25))
    for y in (8.6, 23.9):
        g.append(R(44, y, 8.5, 7.5, PLANET, INK, 0.28, 0.6))
    g.append(R(44, 16.2, 11.2, 7.6, AMBER, INK, 0.28, 0.4))
    for y in (11.6, 26.9):
        g.append(R(42.3, y, 10.5, 1.5, STEEL_D, INK, 0.18))
    # carrier 1 + planets 1 + sun 1 (motor pinion)
    g.append(RH(55.2, 9.5, 1.8, 21, "#7fb894", "hmm", INK, 0.25))
    for y in (8.6, 23.9):
        g.append(R(58.5, y, 8.5, 7.5, PLANET, INK, 0.28, 0.6))
    g.append(R(58, 16.2, 11, 7.6, AMBER, INK, 0.28, 0.4))
    for y in (11.6, 26.9):
        g.append(R(57, y, 10.5, 1.5, STEEL_D, INK, 0.18))

    # DC motor
    g.append(RH(72, 6, 39, 28, "#b8c0c9", "hmm", INK, 0.4, 1.2))
    g.append(R(72.8, 6.8, 37.4, 26.4, "#eef0f2", "none", 0))
    g.append(R(76, 6.8, 28, 4, "#d06a5a", INK, 0.22) + R(76, 29.2, 28, 4, "#5d7fb8", INK, 0.22))
    g.append(T(90, 9.9, "N", 2.8, 700, "white", "middle") + T(90, 32.3, "S", 2.8, 700, "white", "middle"))
    g.append(R(69, 19.2, 44.5, 1.6, STEEL, INK, 0.18))                 # shaft
    g.append(R(78, 12.4, 24, 15.2, COPPER, INK, 0.25, 0.6))
    g.append(R(78, 12.4, 24, 15.2, "url(#wind)", "none", 0, 0.6))
    g.append(R(103, 16, 4.5, 8, "#a8692d", INK, 0.22))                # commutator
    for y in (18, 20, 22):
        g.append(L(103, y, 107.5, y, INK, 0.12))
    for y in (12.4, 24):
        g.append(R(103.6, y, 3.2, 3.6, "#3d4249", INK, 0.18))          # carbon brushes
    zz_top = "M 105.2,12.4 L 104.3,11.7 L 106.1,10.9 L 104.3,10.1 L 106.1,9.3 L 104.3,8.5 L 105.2,7.4"
    zz_bot = "M 105.2,27.6 L 104.3,28.3 L 106.1,29.1 L 104.3,29.9 L 106.1,30.7 L 104.3,31.5 L 105.2,32.6"
    g.append(P(zz_top, "none", INK, 0.2) + P(zz_bot, "none", INK, 0.2))
    g.append(R(108.2, 6.8, 2.4, 26.4, "#9aa3ad", INK, 0.2))
    for y in (13.4, 25):
        g.append(R(110.6, y, 3.6, 1.6, "#c9a227", INK, 0.18))          # terminals

    # trigger, plunger, direction switch
    g.append(P("M 92.6,52 L 86.6,52.6 Q 83,66.5 86.4,80.6 L 96.7,80.6 Z", RED, INK, 0.35))
    g.append(R(95.8, 60.8, 1.9, 3, STEEL_D, INK, 0.15))
    g.append(R(91.5, 43.2, 10.5, 4.4, "#e8572a", INK, 0.3, 1))
    g.append(P("M 94,45.4 L 99,45.4 M 97.6,44.4 L 99,45.4 L 97.6,46.4", "none", "white", 0.4))
    g.append(L(97, 47.6, 99.4, 52.2, INK, 0.2, 'stroke-dasharray="0.8 0.6"'))

    # switch module + PCB
    g.append('<g transform="translate(101.5,62) rotate(-8.5)">'
             + R(-4, -10, 8, 20, "#6c7a89", INK, 0.28, 0.8)
             + T(0, 1.1, "SW", 2.8, 700, "white", "middle") + "</g>")
    g.append('<g transform="translate(105,92) rotate(-7.5)">'
             + R(-1.5, -17, 3, 34, "#2f7d4f", INK, 0.25)
             + R(-3.6, -11, 2.1, 4, "#222", INK, 0.12) + R(-3.4, 1, 1.9, 5, "#333", INK, 0.12)
             + R(-2.9, 9, 1.4, 2.6, "#7a5c3a", INK, 0.1) + "</g>")

    # battery
    g.append('<g transform="translate(120.5,79) rotate(-6.65)">'
             + R(-9, -32, 18, 64, "#4f86c6", INK, 0.4, 3)
             + R(-9, -32, 18, 5, "#2f5f97", "none", 0, 2)
             + R(-3, -33.4, 6, 1.6, "#c9a227", INK, 0.15)
             + T(0, -24.6, "+", 4.2, 700, "white", "middle")
             + T(0, 1.2, "Li-ion 3.6 V · 2.0 Ah", 3.3, 600, "white", "middle", 'transform="rotate(-90)"')
             + "</g>")

    # USB-C port
    g.append(R(117.8, 115.4, 9.6, 4.6, "#454b53", INK, 0.25, 0.6))
    g.append(R(119.3, 117.6, 6.6, 2.6, INTERIOR, INK, 0.15, 1))

    # LED
    g.append(R(27.6, 33.2, 3.6, 3.4, "#ffd34d", INK, 0.25, 0.6))
    g.append(P("M 27.6,33.6 Q 25.8,34.9 27.6,36.2 Z", "#fff2b0", INK, 0.2))
    for x2, y2 in ((20.6, 39.4), (20.0, 35.8), (22.6, 41.8)):
        g.append(L(25.4, 35.6, x2, y2, "#d9a400", 0.3, 'stroke-dasharray="0.9 0.5"'))

    # wiring
    wire = 'fill="none" stroke-linecap="round" stroke-width="0.6"'
    g.append(f'<path d="M 114.2,14.2 C 121,14.2 123,30 113,40 C 106,46 101,47 99.6,52.4" stroke="#c0392b" {wire}/>')
    g.append(f'<path d="M 114.2,25.8 C 119,25.8 119,36 111,43 C 106,47 103.2,49 101.8,52.6" stroke="#111" {wire}/>')
    g.append(f'<path d="M 116.4,46.6 C 112,44.5 106.5,50 105.3,57.5" stroke="#c0392b" {wire}/>')
    g.append(f'<path d="M 124.6,111.6 C 121,116 111,114.5 107.2,108.8" stroke="#111" {wire}/>')
    g.append(f'<path d="M 107.4,109 C 108.5,113 113,115.5 118.4,116.6" stroke="#6b5b2e" {wire}/>')
    g.append(L(102.6, 71.8, 102.9, 75.3, "#6b5b2e", 0.9))
    g.append('<path d="M 98.8,53 C 96,45 90,36.3 82,36.3 L 31.2,35.4" fill="none" stroke="#8a7a3a" '
             'stroke-width="0.3" stroke-dasharray="1 0.6"/>')

    # centre line
    g.append(L(-26, 20, 116, 20, INK, 0.16, 'stroke-dasharray="3.5 0.8 0.6 0.8"'))

    body = [f'<g transform="translate({OX},{OY}) scale({S})">' + "".join(g) + "</g>"]

    # ---------- balloons
    top = [(1, 58, (-12, 20.6)), (2, 122, (6, 14.4)), (3, 186, (21, 13)), (4, 250, (37.5, 9.5)),
           (5, 314, (48, 10)), (6, 378, (62, 10)), (7, 442, (84, 8.8)), (8, 506, (105.2, 13.5)),
           (9, 600, (128, 2.2))]
    for n, bx, (ax, ay) in top:
        body.append(balloon(n, bx, 108, X(ax), Y(ay)))
    for n, by, (ax, ay) in [(10, 200, (112.4, 14.2)), (11, 420, (129.0, 78)), (12, 600, (122.6, 118.8))]:
        body.append(balloon(n, 790, by, X(ax), Y(ay)))
    for n, bx, by, (ax, ay) in [(13, 190, 410, (29.4, 36.6)), (14, 320, 350, (96.5, 45.4)),
                                (15, 320, 440, (85.2, 68)), (16, 320, 550, (104.6, 100))]:
        body.append(balloon(n, bx, by, X(ax), Y(ay)))

    # ---------- dimensions
    body.append(L(X(0), Y(26) + 6, X(0), 676, INK, 0.6) + L(X(147), Y(110), X(147), 676, INK, 0.6))
    body.append(dim_h(X(0), X(147), 666, "147  (비트 제외)"))
    body.append(L(X(120), Y(0), 750, Y(0), INK, 0.6) + L(X(134), Y(120), 750, Y(120), INK, 0.6))
    body.append(dim_v(740, Y(0), Y(120), "120"))
    body.append(T(110, 706, "단면 A–A · 측면 개략도   |   외형 147 × 46 × 120 mm · 0.32 kg · 3.6 V · 235 rpm · 5.5 Nm",
                  13, 500, MUTED))

    # ---------- parts list
    px0, py0 = 840, 104
    cols = [(px0, 46), (px0 + 46, 200), (px0 + 246, 274)]
    body.append(R(px0, py0, 520, 34, INK, INK, 1))
    for (cx, cw), name in zip(cols, ["No", "부품명", "기능"]):
        body.append(T(cx + 12, py0 + 22, name, 13, 700, "white"))
    parts = [
        ("비트 (PH2 등)", "나사 머리에 회전력 전달"),
        ("마그네틱 비트 홀더", "1/4″ 육각 소켓 + 자석 고정"),
        ("출력 스핀들 · 베어링", "감속된 회전을 홀더로 전달"),
        ("자동 스핀들 락", "모터 정지 시 축 잠금 → 손 조임"),
        ("유성기어 2단 (출력측)", "추가 감속 · 토크 증대"),
        ("유성기어 1단 (입력측)", "모터 피니언 = 1단 선기어"),
        ("DC 모터 (자석 · 전기자)", "전기 에너지 → 회전 운동"),
        ("정류자 · 카본 브러시", "코일 전류 방향 자동 전환"),
        ("하우징 (ABS + TPE)", "구조 지지 · 절연 · 그립"),
        ("모터 단자 · 배선", "(+)/(−) 전원 공급 경로"),
        ("리튬이온 셀 (내장)", "3.6 V · 2.0 Ah 에너지 저장"),
        ("USB-C 충전 포트", "5 V 입력 → 충전 회로"),
        ("LED 작업등", "작업 부위 조명"),
        ("정·역회전 스위치", "모터 극성 반전 (조임/풀기)"),
        ("가변속 트리거", "당기는 깊이 = 회전 속도"),
        ("제어 PCB · 트리거 스위치", "PWM 속도 제어 · 충전 · 보호"),
    ]
    rh = 31
    for i, (nm, fn) in enumerate(parts):
        y = py0 + 34 + i * rh
        body.append(R(px0, y, 520, rh, "#f1efe7" if i % 2 else "white", "none", 0))
        body.append(T(cols[0][0] + 23, y + 20.5, i + 1, 13, 700, INK, "middle"))
        body.append(T(cols[1][0] + 12, y + 20.5, nm, 13, 600))
        body.append(T(cols[2][0] + 12, y + 20.5, fn, 12.5, 400, "#33404f"))
    tbl_bottom = py0 + 34 + len(parts) * rh
    body.append(R(px0, py0, 520, tbl_bottom - py0, "none", INK, 1.2))
    for cx, _ in cols[1:]:
        body.append(L(cx, py0, cx, tbl_bottom, INK, 0.6))

    # ---------- notes
    body.append(T(40, 742, "주기", 14, 700))
    notes = [
        "1. 외형 치수·성능(3.6 V · 2.0 Ah · 무부하 235 rpm · 최대 5.5 Nm · 147 × 46 × 120 mm · 0.32 kg)은 Bosch 공개 사양 기준.",
        "2. 내부 부품의 배치·형상은 3.6 V급 전동 드라이버의 일반 구조를 바탕으로 그린 개략도이며, 실제 분해 도면이나 제조사 도면이 아님.",
        "3. 빗금 = 절단면 · 파선 = 숨은선/신호선 · 1점 쇄선 = 중심선 · 빨강 배선 = (+) · 검정 배선 = (−).",
    ]
    for i, n in enumerate(notes):
        body.append(T(40, 766 + i * 22, n, 13, 400, "#33404f"))

    return sheet(1, "도면 1 — BOSCH IXO 7 전체 구조 단면도",
                 "Sectional view · 측면 단면 개략 · 각 번호는 오른쪽 부품표 참조", "".join(body))


# ====================================================================== SHEET 2
def block(x, y, w, h, col, tint, num, title, l1, l2):
    s = R(x, y, w, h, tint, col, 1.6, 10)
    s += C(x + 22, y + 24, 12, col, "none", 0) + T(x + 22, y + 28.5, num, 12, 700, "white", "middle")
    s += T(x + 42, y + 29, title, 15.5, 700)
    s += T(x + 16, y + 64, l1, 13, 500, INK) + T(x + 16, y + 88, l2, 12.5, 400, MUTED)
    return s


def sheet2():
    b = []
    xs = [70, 330, 590, 850, 1110]
    bw, bh = 220, 110
    row1 = [("E1", "USB-C 입력", "5 V DC 입력", "충전기 · PC · 보조배터리"),
            ("E2", "충전 회로", "CC/CV 충전 · 과충전 보호", "완충 약 3시간"),
            ("E3", "리튬이온 셀", "3.6 V 공칭 (만충 4.2 V)", "2.0 Ah ≈ 7.2 Wh 저장"),
            ("E4", "트리거 · 제어 PCB", "PWM 듀티 0 → 100 %", "MOSFET 고속 스위칭"),
            ("E5", "정·역 전환", "모터 단자 +/− 맞바꿈", "→ 조임  ·  ← 풀기")]
    row2 = [("M1", "DC 모터", "전류 × 자기장 → 회전력", "고속 · 저토크"),
            ("M2", "유성기어 감속", "선기어 → 유성기어 → 캐리어", "속도 ↓ · 토크 ↑"),
            ("M3", "자동 스핀들 락", "구동 중: 그대로 통과", "정지 시: 잠김 → 손 조임"),
            ("M4", "비트 홀더 · 비트", "1/4″ 육각 · 자석 고정", "플렉시블 샤프트 연결 가능"),
            ("M5", "나사 체결", "무부하 최대 235 rpm", "최대 5.5 Nm (연질 3 Nm)")]
    y1, y2 = 128, 318
    for i, (n, t, a, c) in enumerate(row1):
        b.append(block(xs[i], y1, bw, bh, BLUE, "#eaf1fb", n, t, a, c))
        if i < 4:
            b.append(L(xs[i] + bw + 4, y1 + 55, xs[i + 1] - 6, y1 + 55, BLUE, 2, 'marker-end="url(#arwB)"'))
    for i, (n, t, a, c) in enumerate(row2):
        b.append(block(xs[i], y2, bw, bh, GREEN, "#e8f4ec", n, t, a, c))
        if i < 4:
            b.append(L(xs[i] + bw + 4, y2 + 55, xs[i + 1] - 6, y2 + 55, GREEN, 2, 'marker-end="url(#arwG)"'))
    # side tags
    for y, col, lab in ((y1, BLUE, "전기 계통"), (y2, GREEN, "기계 계통")):
        b.append(R(28, y, 30, bh, col, "none", 0, 6))
        b.append(T(43, y + bh / 2 + 5, lab, 13, 700, "white", "middle",
                   f'transform="rotate(-90 43 {f(y + bh / 2)})"'))
    # return connector
    b.append(P(f"M 1220,{y1 + bh} L 1220,276 L 180,276 L 180,{y2 - 6}", "none", BLUE, 1.8,
               'marker-end="url(#arwB)" stroke-linejoin="round"'))
    b.append(T(700, 268, "전류 공급 — 방향 스위치 위치에 따라 모터에 걸리는 극성이 정해진다", 12.5, 500, BLUE, "middle"))

    # speed / torque wedges
    b.append(P(poly([(260, 447), (1140, 458.5), (1140, 461.5), (260, 473)]), "#7d8ea3", "none", 0))
    b.append(P(poly([(260, 494.5), (1140, 483), (1140, 509), (260, 497.5)]), AMBER, "none", 0))
    b.append(T(250, 465, "모터  약 1만 rpm대*", 13, 600, INK, "end"))
    b.append(T(1150, 465, "출력  235 rpm", 13, 700, INK))
    b.append(T(250, 501, "모터  약 0.1 Nm대*", 13, 600, INK, "end"))
    b.append(T(1150, 501, "출력  최대 5.5 Nm", 13, 700, INK))
    b.append(T(700, 444, "회전수", 12, 700, "#5d6e83", "middle"))
    b.append(T(700, 524, "토크", 12, 700, AMBER_D, "middle"))
    b.append(T(1340, 534, "유성기어 감속비 ≈ 40~60 : 1 (추정*) — 회전수를 낮춘 만큼 토크가 커진다   * 추정치: 모터·기어 세부 사양은 비공개",
               11.5, 400, MUTED, "end"))

    # -------- panel A: PWM
    py = 548
    b.append(R(40, py, 440, 290, "white", INK, 1, 8))
    b.append(T(58, py + 28, "A. 가변속 원리 — PWM 제어", 15, 700))
    plots = [(0.25, "살짝 당김", "듀티 25 %", "0.9 V"), (0.6, "절반 당김", "듀티 60 %", "2.2 V"),
             (1.0, "끝까지", "듀티 100 %", "3.6 V")]
    for k, (d, l1, l2, avg) in enumerate(plots):
        top = py + 46 + k * 66
        yh, yb = top + 6, top + 42
        x0, per, n = 160, 48, 5
        b.append(T(58, top + 22, l1, 13, 600) + T(58, top + 40, l2, 12, 400, MUTED))
        b.append(L(x0, yb, x0 + per * n + 4, yb, "#9aa5b1", 0.8))
        b.append(L(x0, yh - 4, x0, yb, "#9aa5b1", 0.8))
        if d >= 1:
            pts = f"M {x0},{yb} L {x0},{yh} L {x0 + per * n},{yh}"
        else:
            pts = f"M {x0},{yb}"
            for i in range(n):
                xa = x0 + per * i
                pts += f" L {xa},{yh} L {f(xa + d * per)},{yh} L {f(xa + d * per)},{yb} L {xa + per},{yb}"
        b.append(P(pts, "none", BLUE, 1.8, 'stroke-linejoin="round"'))
        ya = yb - d * (yb - yh)
        b.append(L(x0, ya, x0 + per * n, ya, RED, 1.4, 'stroke-dasharray="5 3"'))
        b.append(T(410, top + 20, "평균", 11.5, 400, MUTED) + T(410, top + 38, avg, 14, 700, RED))
    s, _ = para(58, py + 248, "트리거를 당긴 깊이만큼 MOSFET가 켜져 있는 시간 비율(듀티)이 늘어나고, 모터에 걸리는 평균 전압과 회전 속도가 함께 올라간다.",
                404, 12.5, 18, "#33404f")
    b.append(s)

    # -------- panel B: polarity
    bx0 = 500
    b.append(R(bx0, py, 420, 290, "white", INK, 1, 8))
    b.append(T(bx0 + 18, py + 28, "B. 정·역 전환 — 극성 반전", 15, 700))
    for k, rev in enumerate((False, True)):
        bx = bx0 + 15 + k * 200
        yt, yb_, cy = 612, 706, 659
        mx = bx + 152
        # battery
        b.append(L(bx + 30, yt, bx + 30, cy - 8, INK, 1.6) + L(bx + 30, cy + 4, bx + 30, yb_, INK, 1.6))
        b.append(L(bx + 14, cy - 8, bx + 46, cy - 8, INK, 2.2) + L(bx + 21, cy + 4, bx + 39, cy + 4, INK, 4.5))
        b.append(T(bx + 52, cy - 10, "+", 14, 700, RED) + T(bx + 52, cy + 16, "−", 14, 700, INK))
        # switch box
        b.append(R(bx + 66, yt - 10, 68, yb_ - yt + 20, "none", MUTED, 1, 6, 'stroke-dasharray="4 3"'))
        if not rev:
            b.append(L(bx + 30, yt, mx, yt, INK, 1.6) + L(bx + 30, yb_, mx, yb_, INK, 1.6))
        else:
            b.append(P(f"M {bx + 30},{yt} L {bx + 82},{yt} L {bx + 118},{yb_} L {mx},{yb_}", "none", INK, 1.6))
            b.append(P(f"M {bx + 30},{yb_} L {bx + 82},{yb_} L {bx + 118},{yt} L {mx},{yt}", "none", INK, 1.6))
        b.append(L(mx, yt, mx, cy - 22, INK, 1.6) + L(mx, cy + 22, mx, yb_, INK, 1.6))
        b.append(C(mx, cy, 22, "#eef0f2", INK, 1.6) + T(mx, cy + 6, "M", 17, 700, INK, "middle"))
        # current arrows
        b.append(L(bx + 44, yt, bx + 64, yt, RED, 2, 'marker-end="url(#arwR)"'))
        if not rev:
            b.append(L(mx, yt + 6, mx, yt + 22, RED, 2, 'marker-end="url(#arwR)"'))
        else:
            b.append(L(mx, yb_ - 6, mx, yb_ - 22, RED, 2, 'marker-end="url(#arwR)"'))
        # rotation
        if not rev:
            b.append(arc(mx, cy, 33, 200, 330, AMBER_D, 2.2, "arwA"))
        else:
            b.append(arc(mx, cy, 33, 340, 210, AMBER_D, 2.2, "arwA"))
        b.append(T(bx + 100, yt - 16, "방향 스위치", 11, 500, MUTED, "middle"))
        b.append(T(bx + 95, 746, "역회전 → 풀기" if rev else "정회전 → 조임", 14, 700, INK, "middle"))
        b.append(T(bx + 95, 764, "반시계방향 (사용자 시점)" if rev else "시계방향 (사용자 시점)", 11.5, 400, MUTED, "middle"))
    s, _ = para(bx0 + 18, 788, "스위치는 배터리의 +/− 가 모터의 두 단자 중 어느 쪽으로 들어갈지를 맞바꾼다. 영구자석 DC 모터는 전류 방향이 바뀌면 회전 방향도 바뀐다.",
                386, 12.5, 18, "#33404f")
    b.append(s)

    # -------- panel C: speed-torque
    cx0 = 940
    b.append(R(cx0, py, 420, 290, "white", INK, 1, 8))
    b.append(T(cx0 + 18, py + 28, "C. 속도 · 토크 관계", 15, 700))
    b.append(T(cx0 + 18, py + 52, "출력 회전수 = 모터 회전수 ÷ 감속비", 12.5, 500))
    b.append(T(cx0 + 18, py + 71, "출력 토크 ≈ 모터 토크 × 감속비 × 효율", 12.5, 500))
    ox, oy, gx, gy = 1000, 778, 310, 112

    def gX(t):
        return ox + t * gx / 5.5

    def gY(n):
        return oy - n * gy / 235

    b.append(L(ox, oy, ox + gx + 16, oy, INK, 1, 'marker-end="url(#arw)"'))
    b.append(L(ox, oy, ox, oy - gy - 24, INK, 1, 'marker-end="url(#arw)"'))
    for t in range(6):
        b.append(L(gX(t), oy, gX(t), oy + 4, INK, 0.8) + T(gX(t), oy + 16, t, 10.5, 400, MUTED, "middle"))
    for n in (100, 200):
        b.append(L(ox - 4, gY(n), ox, gY(n), INK, 0.8) + T(ox - 7, gY(n) + 4, n, 10.5, 400, MUTED, "end"))
    b.append(L(gX(3), gY(0), gX(3), gY(235 * (1 - 3 / 5.5)), "#9aa5b1", 1, 'stroke-dasharray="3 3"'))
    pw = " L ".join(f"{f(gX(t))},{f(oy - (t * (1 - t / 5.5)) / (2.75 * 0.5) * 70)}"
                    for t in [i * 5.5 / 40 for i in range(41)])
    b.append(P("M " + pw, "none", AMBER, 2, 'stroke-dasharray="6 4"'))
    b.append(L(gX(0), gY(235), gX(5.5), gY(0), BLUE, 2.4))
    b.append(C(gX(0), gY(235), 3.5, BLUE, "none", 0) + C(gX(5.5), gY(0), 3.5, BLUE, "none", 0))
    b.append(T(gX(0) + 10, gY(235) + 2, "무부하 235 rpm", 11.5, 700, BLUE))
    b.append(T(gX(5.5) - 6, gY(0) - 34, "최대 5.5 Nm", 11.5, 700, BLUE, "end"))
    b.append(T(gX(3) + 5, gY(18), "연질 3 Nm", 10.5, 500, MUTED))
    b.append(T(gX(2.75), oy - 76, "출력(W)", 11, 700, AMBER_D, "middle"))
    b.append(T(ox + gx + 14, oy + 30, "토크 (Nm)", 11.5, 600, INK, "end"))
    b.append(T(ox + 8, oy - gy - 18, "회전수 (rpm)", 11.5, 600, INK))
    b.append(T(cx0 + 18, py + 279, "부하가 클수록 느려지고, 멈추기 직전이 최대 토크 (개념 그래프)", 11.5, 400, MUTED))

    return sheet(2, "도면 2 — 동력 전달 흐름도 · 제어 원리",
                 "Power flow · 전기 에너지가 나사를 돌리는 토크가 되기까지", "".join(b))


# ====================================================================== SHEET 3
def ext_gear(cx, cy, z, m, offset_deg):
    r = m * z / 2
    ra, rf = r + m, r - 1.25 * m
    p = 2 * math.pi / z
    pts = []
    for i in range(z):
        c = math.radians(offset_deg) + i * p
        for rad, a in ((rf, c - 0.34 * p), (r, c - 0.25 * p), (ra, c - 0.15 * p),
                       (ra, c + 0.15 * p), (r, c + 0.25 * p), (rf, c + 0.34 * p),
                       (rf, c + 0.42 * p), (rf, c + 0.5 * p), (rf, c + 0.58 * p)):
            pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return poly(pts)


def int_gear(cx, cy, z, m, offset_deg):
    r = m * z / 2
    rtip, rroot = r - m, r + 1.25 * m
    p = 2 * math.pi / z
    pts = []
    for i in range(z):
        c = math.radians(offset_deg) + i * p
        for rad, a in ((rroot, c - 0.34 * p), (r, c - 0.25 * p), (rtip, c - 0.15 * p),
                       (rtip, c + 0.15 * p), (r, c + 0.25 * p), (rroot, c + 0.34 * p),
                       (rroot, c + 0.5 * p)):
            pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return poly(pts)


def circle_path(cx, cy, r):
    return (f"M {f(cx + r)},{f(cy)} A {r} {r} 0 1 1 {f(cx - r)},{f(cy)} "
            f"A {r} {r} 0 1 1 {f(cx + r)},{f(cy)} Z")


def sheet3():
    b = []
    cx, cy, m = 390, 440, 9
    zs, zp, zr = 12, 12, 36
    a = (zs + zp) * m / 2
    # ring + housing
    ring = circle_path(cx, cy, 205) + " " + int_gear(cx, cy, zr, m, 0)
    b.append(P(ring, "#d5d9de", "none", 0, 'fill-rule="evenodd"'))
    b.append(P(ring, "url(#hpx)", INK, 1.3, 'fill-rule="evenodd"'))
    # carrier disc (behind)
    b.append(C(cx, cy, 128, "rgba(47,143,91,0.10)", GREEN, 1.6, 'stroke-dasharray="8 5"'))
    # sun
    b.append(P(ext_gear(cx, cy, zs, m, 0), AMBER, INK, 1.3))
    b.append(C(cx, cy, 14, "#8e98a3", INK, 1) + C(cx, cy, 14, "url(#hpx)", "none", 0))
    # planets
    pcs = []
    for ang in (270, 30, 150):
        px = cx + a * math.cos(math.radians(ang))
        py = cy + a * math.sin(math.radians(ang))
        pcs.append((px, py))
        b.append(P(ext_gear(px, py, zp, m, 15), PLANET, INK, 1.3))
        b.append(C(px, py, 11, GREEN, INK, 1) + C(px, py, 3.5, "white", "none", 0))
    # rotation arrows
    b.append(arc(cx, cy, 34, -40, 200, AMBER_D, 2.6, "arwA"))
    for px, py in pcs:
        b.append(arc(px, py, 33, 200, -40, PLANET_D, 2.2, "arwP"))
    b.append(arc(cx, cy, 226, 12, 66, GREEN, 3.2, "arwG"))
    # centre lines
    b.append(L(cx - 222, cy, cx + 222, cy, INK, 0.6, CL_DASH) + L(cx, cy - 222, cx, cy + 222, INK, 0.6, CL_DASH))
    b.append(C(cx, cy, a, "none", INK, 0.6, CL_DASH))

    # labels
    sx, sy = cx + 44 * math.cos(math.radians(210)), cy + 44 * math.sin(math.radians(210))
    b.append(leader(182, 284, sx, sy))
    b.append(T(40, 270, "선기어 (Sun) · Zs = 12", 14, 700) + T(40, 288, "입력 — 모터 피니언", 12.5, 400, AMBER_D))
    tpx, tpy = pcs[0]
    b.append(leader(560, 258, tpx + 40, tpy - 22))
    b.append(T(564, 254, "유성기어 (Planet)", 14, 700) + T(564, 272, "Zp = 12 × 3개 · 자전 + 공전", 12.5, 400, PLANET_D))
    rx_, ry_ = cx + 190 * math.cos(math.radians(140)), cy + 190 * math.sin(math.radians(140))
    b.append(leader(150, 638, rx_, ry_))
    b.append(T(40, 656, "링기어 (Ring) · Zr = 36", 14, 700) + T(40, 674, "하우징에 고정 — 돌지 않음", 12.5, 400, MUTED))
    b.append(T(560, 682, "캐리어 (Carrier) · 출력", 14, 700, GREEN))
    b.append(T(560, 700, "선기어 회전의 1/4 속도", 12.5, 400, GREEN))
    b.append(T(560, 610, "핀 = 유성기어 축", 11.5, 500, GREEN))
    b.append(leader(580, 598, pcs[1][0] + 4, pcs[1][1] + 6, color=GREEN))

    # steps
    b.append(T(40, 742, "동작 순서", 14, 700))
    steps = ["① 모터가 선기어를 시계방향으로 빠르게 돌린다.",
             "② 맞물린 유성기어 3개는 각자의 핀을 축으로 반시계방향 자전한다.",
             "③ 바깥 링기어가 고정돼 있으므로 유성기어는 링을 따라 시계방향으로 굴러가고(공전), 이 공전이 캐리어를 1/4 속도로 돌린다."]
    yy = 766
    for st in steps:
        s, yy = para(40, yy, st, 690, 13, 20, "#33404f")
        b.append(s)

    # ---------------- right panel
    X0 = 770
    b.append(R(X0, 100, 590, 210, "white", INK, 1, 8))
    b.append(T(X0 + 20, 128, "① 감속비 계산 — 링기어 고정 · 선기어 입력 · 캐리어 출력", 15, 700))
    b.append(T(X0 + 20, 172, "i = 1 + Zr ÷ Zs", 28, 700, INK))
    b.append(T(X0 + 20, 206, "= 1 + 36 ÷ 12 = 4    →    1단에 4 : 1 감속", 16, 500))
    b.append(T(X0 + 20, 240, "조립 조건", 13, 700, MUTED))
    b.append(T(X0 + 20, 262, "Zr = Zs + 2·Zp    →    36 = 12 + 2 × 12", 13.5, 400))
    b.append(T(X0 + 20, 284, "(Zs + Zr) ÷ 유성기어 수 = 정수    →    48 ÷ 3 = 16  (등간격 배치 가능)", 13.5, 400))

    b.append(R(X0, 325, 590, 250, "white", INK, 1, 8))
    b.append(T(X0 + 20, 353, "② 여러 단을 이으면 감속비가 곱해진다", 15, 700))
    cols = [X0 + 20, X0 + 120, X0 + 250, X0 + 420]
    b.append(R(X0 + 12, 368, 566, 28, "#ece9df", "none", 0, 4))
    for cxx, hd in zip(cols, ["단수", "감속비", "출력 회전수 *", "토크 배율 **"]):
        b.append(T(cxx, 387, hd, 13, 700))
    rows = [("1단", "4 : 1", "2,500 rpm", "× 3.6"), ("2단", "16 : 1", "625 rpm", "× 13.0"),
            ("3단", "64 : 1", "156 rpm", "× 46.7")]
    for i, row in enumerate(rows):
        y = 422 + i * 32
        for cxx, v in zip(cols, row):
            b.append(T(cxx, y, v, 14, 600 if cxx == cols[0] else 400))
        b.append(L(X0 + 12, y + 11, X0 + 578, y + 11, "#d9d6cc", 1))
    b.append(T(X0 + 20, 516, "* 모터 10,000 rpm 가정     ** 단당 효율 90 % 가정", 12, 400, MUTED))
    b.append(T(X0 + 20, 540, "IXO 7의 실제 잇수 · 단수는 공개되지 않음. 무부하 235 rpm으로 보면", 12.5, 500))
    b.append(T(X0 + 20, 559, "전체 감속비는 약 40~60 : 1 (2~3단 구성) 수준으로 추정된다.", 12.5, 500))

    b.append(R(X0, 590, 590, 250, "white", INK, 1, 8))
    b.append(T(X0 + 20, 618, "③ 2단 유성기어 구성 (측면 개략)", 15, 700))
    ay = 715
    b.append(L(790, ay, 1350, ay, INK, 0.6, CL_DASH))
    b.append(RH(1285, 690, 60, 50, "#d7dbe1", "hpx", INK, 1.2, 4) + T(1315, 720, "모터", 13, 700, INK, "middle"))
    b.append(R(1225, ay - 2, 60, 4, STEEL_D, INK, 0.6))
    for y in (655, 765):
        b.append(RH(1040, y, 200, 10, "#cfd3d8", "hpx", INK, 1))
    b.append(T(1140, 794, "링기어 — 하우징에 고정", 12, 500, MUTED, "middle"))
    # stage 1
    b.append(R(1190, 703, 40, 24, AMBER, INK, 1, 2))
    for y in (665, 727):
        b.append(R(1195, y, 30, 38, PLANET, INK, 1, 3))
    for y in (684, 746):
        b.append(L(1170, y, 1212, y, INK, 2))
    b.append(R(1164, 668, 7, 94, GREEN, INK, 1))
    # stage 2
    b.append(R(1110, 703, 54, 24, AMBER, INK, 1, 2))
    for y in (665, 727):
        b.append(R(1115, y, 30, 38, PLANET, INK, 1, 3))
    for y in (684, 746):
        b.append(L(1090, y, 1132, y, INK, 2))
    b.append(R(1084, 668, 7, 94, GREEN, INK, 1))
    b.append(RH(800, 709, 284, 12, STEEL, "hpx2", INK, 1))
    b.append(T(810, 700, "스핀들 → 비트 (출력)", 12.5, 600))
    b.append(T(1210, 648, "1단", 13, 700, INK, "middle") + T(1130, 648, "2단", 13, 700, INK, "middle"))
    b.append(T(1065, 822, "10,000 rpm (모터)  →  2,500 rpm (1단 후)  →  625 rpm (2단 후)   · 예시값",
               12, 500, "#33404f", "middle"))

    return sheet(3, "도면 3 — 유성기어 감속 원리",
                 "Planetary gear · 정면도(1단) · 선기어 입력 / 캐리어 출력 / 링기어 고정", "".join(b))


# ====================================================================== SHEET 4
def bez(p0, p1, p2, p3, t):
    u = 1 - t
    x = u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0]
    y = u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]
    return x, y


def bez_d(p0, p1, p2, p3, t):
    u = 1 - t
    dx = 3 * u * u * (p1[0] - p0[0]) + 6 * u * t * (p2[0] - p1[0]) + 3 * t * t * (p3[0] - p2[0])
    dy = 3 * u * u * (p1[1] - p0[1]) + 6 * u * t * (p2[1] - p1[1]) + 3 * t * t * (p3[1] - p2[1])
    return dx, dy


def bez_dd(p0, p1, p2, p3, t):
    u = 1 - t
    ddx = 6 * u * (p2[0] - 2 * p1[0] + p0[0]) + 6 * t * (p3[0] - 2 * p2[0] + p1[0])
    ddy = 6 * u * (p2[1] - 2 * p1[1] + p0[1]) + 6 * t * (p3[1] - 2 * p2[1] + p1[1])
    return ddx, ddy


def sheet4():
    b = []
    # ---------------- outline (in use)
    b.append(T(40, 118, "외형도 — 사용 상태", 15, 700))
    p0, p1, p2, p3 = (520, 210), (370, 210), (240, 270), (240, 410)
    samples = [bez(p0, p1, p2, p3, i / 600) for i in range(601)]
    cum = [0.0]
    for i in range(1, len(samples)):
        cum.append(cum[-1] + math.dist(samples[i], samples[i - 1]))
    total, step = cum[-1], 12.5
    k, beads = 0, []
    dist = 4.0
    while dist < total - 3:
        while cum[k] < dist:
            k += 1
        t = k / 600
        x, y = samples[k]
        dx, dy = bez_d(p0, p1, p2, p3, t)
        beads.append((x, y, math.degrees(math.atan2(dy, dx)), t))
        dist += step
    for i, (x, y, ang, _) in enumerate(beads):
        b.append(f'<g transform="translate({f(x)},{f(y)}) rotate({f(ang)})">'
                 + R(-7, -14, 14, 28, "#2b3037" if i % 2 else "#383e47", "#15181c", 0.8, 5)
                 + L(-2.5, -11.5, -2.5, 11.5, "#69727d", 1) + "</g>")
    # input end
    b.append(R(520, 193, 46, 34, DARK, "#15181c", 1, 5))
    b.append(R(566, 201, 70, 18, STEEL, INK, 1) + L(566, 206, 636, 206, INK, 0.5) + L(566, 214, 636, 214, INK, 0.5))
    b.append(P("M 636,201 L 641,204 L 641,216 L 636,219", STEEL, INK, 1))
    b.append(P("M 656,186 A 10 24 0 0 1 656,234", "none", AMBER_D, 2.4, 'marker-end="url(#arwA)"'))
    b.append(T(672, 204, "회전", 13, 700, AMBER_D) + T(672, 222, "입력", 13, 700, AMBER_D))
    # output end
    b.append(R(223, 410, 34, 44, DARK, "#15181c", 1, 5))
    b.append(R(229, 454, 22, 40, STEEL, INK, 1))
    b.append(P("M 232,494 L 248,494 L 246,520 L 242,532 L 238,532 L 234,520 Z", "#e7e9ec", INK, 1))
    b.append(P("M 212,478 A 30 9 0 0 0 270,482", "none", AMBER_D, 2.4, 'marker-end="url(#arwA)"'))
    b.append(T(206, 478, "회전 출력", 13, 700, AMBER_D, "end"))
    # bend radius callout
    tb = 0.5
    bx_, by_ = bez(p0, p1, p2, p3, tb)
    dx, dy = bez_d(p0, p1, p2, p3, tb)
    ddx, ddy = bez_dd(p0, p1, p2, p3, tb)
    sp = math.hypot(dx, dy)
    nx, ny = -dy / sp, dx / sp
    if (dx * ddy - dy * ddx) < 0:
        nx, ny = -nx, -ny
    ex, ey = bx_ + nx * 96, by_ + ny * 96
    b.append(L(ex, ey, bx_ + nx * 16, by_ + ny * 16, INK, 1, 'stroke-dasharray="5 3" marker-end="url(#arw)"'))
    b.append(C(ex, ey, 3, INK, "none", 0))
    b.append(T(ex - 24, ey + 24, "굽힘 반경 R", 13, 700) + T(ex - 24, ey + 42, "작을수록 마찰 손실 ↑", 12, 400, MUTED))
    # labels
    lb = beads[len(beads) // 3]
    b.append(leader(300, 156, lb[0], lb[1] - 12))
    b.append(T(120, 150, "세그먼트 외피 — 회전하지 않음", 13.5, 700) + T(120, 168, "손으로 잡고 방향을 잡는 부분", 12.5, 400, MUTED))
    b.append(leader(500, 248, 596, 219))
    b.append(T(430, 262, "입력: 1/4″ 육각 생크", 13.5, 700) + T(430, 280, "IXO 7 비트 홀더에 그대로 꽂는다", 12.5, 400, MUTED))
    b.append(leader(296, 448, 251, 470))
    b.append(T(300, 446, "출력: 마그네틱 비트 홀더", 13.5, 700) + T(300, 464, "비트를 자석으로 고정", 12.5, 400, MUTED))

    # ---------------- section detail
    b.append(T(745, 118, "단면 상세 — 직선 상태 · 확대 · 개략", 15, 700))
    ay = 270
    b.append(RH(745, 252, 70, 36, STEEL, "hpx", INK, 1))
    b.append(R(745, 259, 44, 22, INTERIOR, INK, 0.8))
    b.append(R(789, 261, 3.5, 18, "#d06a5a", "none", 0) + R(792.5, 261, 3.5, 18, "#5d7fb8", "none", 0))
    for x0 in (815, 1203):
        for y in (236, 288):
            b.append(RH(x0, y, 72, 16, "#4b525b", "hpxW", INK, 1))
    for x0 in (825, 1215):
        for y in (252, 281):
            b.append(R(x0, y, 40, 7, "white", INK, 0.8) + L(x0, y, x0 + 40, y + 7, INK, 0.6) + L(x0, y + 7, x0 + 40, y, INK, 0.6))
    b.append(RH(815, 259, 60, 22, STEEL, "hpx2", INK, 0.8))
    # core (with stepped cut-away)
    core = [(895, 980, 258, 282, "layR"), (980, 1040, 261, 279, "layL"), (1040, 1090, 264, 276, "layR"),
            (1090, 1125, 266.5, 273.5, "layL"), (1150, 1205, 258, 282, "layR")]
    for xa, xb, ya, yb, pat in core:
        b.append(R(xa, ya, xb - xa, yb - ya, STEEL, "none", 0) + R(xa, ya, xb - xa, yb - ya, f"url(#{pat})", "none", 0)
                 + R(xa, ya, xb - xa, yb - ya, "none", INK, 0.8))
    b.append(R(1125, 268.5, 15, 3, STEEL_D, INK, 0.6))
    # crimp sleeves
    for x0 in (875, 1189):
        b.append(R(x0, 256, 36, 28, STEEL_D, INK, 1))
        for dx_ in (8, 18, 28):
            b.append(L(x0 + dx_, 258, x0 + dx_, 282, "white", 1, 'stroke-opacity="0.7"'))
    # liner + segments
    for y in (252, 283):
        b.append(R(887, y, 316, 5, "#e6e1d3", INK, 0.6))
    for i in range(12):
        x0 = 887 + 26.3 * i
        for y in (236, 288):
            b.append(R(x0 + 0.6, y, 25, 16, "#2b3037" if i % 2 else "#383e47", "#15181c", 0.8, 4))
            b.append(R(x0 + 0.6, y, 25, 16, "url(#hpxW)", "none", 0, 4))
    # input shaft
    b.append(RH(1225, 259, 50, 22, STEEL, "hpx2", INK, 0.8))
    b.append(R(1275, 262, 70, 16, STEEL, INK, 1) + L(1275, 266.5, 1345, 266.5, INK, 0.5) + L(1275, 273.5, 1345, 273.5, INK, 0.5))
    # break symbol
    b.append(R(1140, 228, 11, 84, PAPER, "none", 0))
    b.append(P("M 1140,228 C 1146,248 1134,262 1140,270 C 1146,280 1134,295 1140,312", "none", INK, 1))
    b.append(P("M 1151,228 C 1157,248 1145,262 1151,270 C 1157,280 1145,295 1151,312", "none", INK, 1))
    b.append(L(735, ay, 1355, ay, INK, 0.6, CL_DASH))
    # rotation arrows
    b.append(P("M 1352,248 A 8 22 0 0 1 1352,292", "none", AMBER_D, 2.2, 'marker-end="url(#arwA)"'))
    b.append(P("M 738,246 A 8 24 0 0 0 738,294", "none", AMBER_D, 2.2, 'marker-end="url(#arwA)"'))
    # section B-B
    b.append(L(940, 222, 940, 318, INK, 0.8, CL_DASH))
    b.append(L(940, 222, 924, 222, INK, 1.6, 'marker-end="url(#arw)"') + L(940, 318, 924, 318, INK, 1.6, 'marker-end="url(#arw)"'))
    b.append(T(932, 215, "B", 13, 700, INK, "middle") + T(932, 336, "B", 13, 700, INK, "middle"))
    # layer labels
    for tx, ty, lab, ax_, ay_ in ((850, 196, "4층(외층) · 우권", 925, 261), (975, 174, "3층 · 좌권", 1010, 263),
                                  (1045, 196, "2층 · 우권", 1065, 266), (1098, 174, "1층 · 좌권 + 심선", 1112, 269)):
        b.append(leader(tx + 20, ty + 5, ax_, ay_))
        b.append(T(tx, ty, lab, 12.5, 700))
    # bottom labels
    for tx, ty, lab, ax_, ay_ in ((780, 352, "마그네틱 비트 홀더", 780, 288), (850, 376, "부싱", 845, 288),
                                  (920, 352, "압착 슬리브", 893, 284), (1040, 376, "라이너", 1010, 288),
                                  (1080, 352, "세그먼트 외피 (회전 안 함)", 1070, 304),
                                  (1300, 352, "입력 생크 1/4″ 육각", 1310, 278)):
        b.append(leader(tx, ty - 14, ax_, ay_))
        b.append(T(tx, ty, lab, 12.5, 600, INK, "middle"))

    # ---------------- cross-section B-B
    b.append(T(40, 568, "단면 B–B — 코어 확대", 15, 700))
    ccx, ccy = 230, 712
    b.append(C(ccx, ccy, 92, "#383e47", INK, 1.2) + C(ccx, ccy, 92, "url(#hpxW)", "none", 0))
    b.append(C(ccx, ccy, 64, "#e6e1d3", INK, 1))
    b.append(C(ccx, ccy, 58, PAPER, INK, 0.8))
    layers = [(48, 24, 7.5, "#8ea3b8"), (36, 18, 0, "#d3dce6"), (24, 12, 15, "#8ea3b8"), (12, 6, 0, "#d3dce6")]
    for rr, n, off, colr in layers:
        for i in range(n):
            a_ = math.radians(off + i * 360 / n)
            b.append(C(ccx + rr * math.cos(a_), ccy + rr * math.sin(a_), 6, colr, INK, 0.8))
    b.append(C(ccx, ccy, 6, STEEL_D, INK, 0.8))

    def wire(rr, ang):
        return ccx + rr * math.cos(math.radians(ang)), ccy + rr * math.sin(math.radians(ang))

    lab_x = 356
    items = [("세그먼트 외피 (고정)", wire(80, -38)), ("라이너", wire(61, -18)), ("4층 (외층) · 우권", wire(48, 7.5)),
             ("3층 · 좌권", wire(36, 20)), ("2층 · 우권", wire(24, 45)), ("1층 · 좌권", wire(12, 60)),
             ("심선 (맨드릴)", (ccx, ccy))]
    for i, (lab, (ax_, ay_)) in enumerate(items):
        ly = 610 + i * 33
        b.append(leader(lab_x - 4, ly - 4, ax_, ay_, sw=0.8))
        b.append(T(lab_x, ly, lab, 12.5, 600))
    b.append(T(40, 830, "진한 색 = 우권 · 연한 색 = 좌권 — 층마다 감는 방향이 반대", 12, 400, MUTED))

    # ---------------- principle text
    X0, Y0 = 560, 470
    b.append(R(X0, Y0, 800, 368, "white", INK, 1, 8))
    b.append(T(X0 + 24, Y0 + 34, "작동 원리", 17, 700))
    items = [
        ("1. 토크 전달 —", "강선을 층마다 반대 방향으로 감은 코어가 비틀림(토션)으로 회전을 전달한다. 굽혀도 와이어끼리 미끄러지며 휘어지므로 꺾인 상태로 돈다."),
        ("2. 외피는 고정 —", "세그먼트 외피와 라이너는 돌지 않고 코어만 안에서 회전한다. 그래서 외피를 손으로 잡고 비트 방향을 잡을 수 있다."),
        ("3. 양 끝 단말 —", "코어 양 끝을 입력 생크와 출력 홀더에 압착(크림핑)하고, 부싱이 회전축을 지지한다."),
        ("4. 방향성 —", "일반적인 플렉시블 샤프트는 외층이 감기는 방향(조임)에서 토크 용량이 크고, 외층이 풀리려는 반대 방향(풀기)에서는 약하다."),
    ]
    y = Y0 + 64
    for lead, txt in items:
        s, y = para(X0 + 24, y, txt, 752, 13.5, 21, "#33404f", 400, lead, INK)
        b.append(s)
        y += 6
    b.append(L(X0 + 24, y - 4, X0 + 776, y - 4, "#e2dfd5", 1))
    b.append(T(X0 + 24, y + 20, "사용 시 주의", 15, 700, RED))
    y += 44
    for txt in ["굽힘이 클수록 마찰 손실과 코어 비틀림(와인드업)이 커진다 → 트리거를 살짝 당겨 저속으로 쓴다.",
                "최소 굽힘 반경보다 작게 꺾지 않는다 — 코어 피로·파단의 원인이 된다.",
                "마지막 조임은 본체 직결 상태나 스핀들 락을 이용한 손 조임이 더 정확하다."]:
        s, y = para(X0 + 24, y, "· " + txt, 752, 13.5, 21, "#33404f")
        b.append(s)

    return sheet(4, "도면 4 — 플렉시블 샤프트 어댑터",
                 "Flexible shaft adapter · 꺾인 상태로 회전을 전달하는 원리", "".join(b))


for i, fn in enumerate((sheet1, sheet2, sheet3, sheet4), 1):
    names = {1: "01-section", 2: "02-power-flow", 3: "03-planetary-gear", 4: "04-flexible-shaft"}
    path = os.path.join(OUT, f"ixo7-{names[i]}.svg")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(fn())
    print(path)
