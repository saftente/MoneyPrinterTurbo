"""Own animated explainer scenes for the traffic short (pycairo, 1080x1920, 30 fps).

  python3 projects/traffic-short/tools/animate.py            # all "anim:" scenes of shotlist.json
  python3 projects/traffic-short/tools/animate.py 4 10       # only these scene ids
  python3 projects/traffic-short/tools/animate.py --still 10 0.5   # one PNG at 50 % of scene 10

Each scene is rendered to work/clips/scene_XX.mp4 with exactly the frame count the shotlist asks for
(the same frame-exact rule as curate.py cut). Beats inside a scene are timed to the spoken words
(work/voice/subtitle_words.srt), e.g. the road turns orange on "orange" and red on "rot".
Visual language: light map, white roads, green/orange/red traffic overlay, blue route, top-down cars,
phones with signal rings. Key content stays above y=1250; the subtitles sit below it.
"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import cairo

ROOT = Path(__file__).resolve().parents[1]
W, H, FPS = 1080, 1920, 30
SHOTS = json.loads((ROOT / "shotlist.json").read_text(encoding="utf-8"))

# ---------- palette ----------
def hexc(h, a=1.0):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (a,)

BG = hexc("#F3F0E8"); BLOCK = hexc("#E7E2D6"); PARK = hexc("#CFE8C6"); WATER = hexc("#BCDDF3")
ROAD = hexc("#FFFFFF"); ROAD_EDGE = hexc("#D3CEC2"); INK = hexc("#1F2937"); MUTED = hexc("#6B7280")
GREEN = hexc("#22B573"); ORANGE = hexc("#F59E0B"); RED = hexc("#E5484D"); DARKRED = hexc("#B42318")
BLUE = hexc("#2F6FED"); CARD = hexc("#FFFFFF"); YELLOW = hexc("#FFD23F")
CAR_COLORS = [hexc(c) for c in ("#4F7DF3", "#F97362", "#34B3A0", "#8B5CF6", "#F2B33D", "#5B6B82", "#EC6FA9")]

# ---------- easing / helpers ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)

def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3

def prog(t, t0, t1):
    return ease((t - t0) / max(1e-6, t1 - t0))

def mix(c1, c2, k):
    return tuple(a + (b - a) * k for a, b in zip(c1, c2))

def rrect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()

def font(ctx, size, bold=True):
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)

def text(ctx, s, x, y, size, color=INK, align="center", bold=True, alpha=1.0):
    font(ctx, size, bold)
    ext = ctx.text_extents(s)
    dx = {"center": -ext.x_advance / 2, "left": 0, "right": -ext.x_advance}[align]
    ctx.move_to(x + dx, y + size * 0.36)
    ctx.set_source_rgba(*color[:3], color[3] * alpha)
    ctx.show_text(s)
    return ext.x_advance

def chip(ctx, s, x, y, size, bg=CARD, fg=INK, alpha=1.0, pad=0.55, shadow=True):
    font(ctx, size)
    w = ctx.text_extents(s).x_advance + size * pad * 2
    h = size * 1.7
    if shadow:
        rrect(ctx, x - w / 2 + 4, y - h / 2 + 8, w, h, h / 2)
        ctx.set_source_rgba(0, 0, 0, 0.12 * alpha); ctx.fill()
    rrect(ctx, x - w / 2, y - h / 2, w, h, h / 2)
    ctx.set_source_rgba(*bg[:3], bg[3] * alpha); ctx.fill()
    text(ctx, s, x, y, size, fg, alpha=alpha)
    return w

def card(ctx, x, y, w, h, r=36, alpha=1.0):
    rrect(ctx, x + 6, y + 12, w, h, r); ctx.set_source_rgba(0, 0, 0, 0.10 * alpha); ctx.fill()
    rrect(ctx, x, y, w, h, r); ctx.set_source_rgba(1, 1, 1, alpha); ctx.fill()

# ---------- word timing ----------
def load_words():
    out = []
    srt = (ROOT / "work/voice/subtitle_words.srt").read_text(encoding="utf-8").strip().split("\n\n")
    for blk in srt:
        l = blk.split("\n")
        a, b = l[1].split(" --> ")
        f = lambda x: sum(int(p) * m for p, m in zip(re.findall(r"\d+", x)[:3], (3600, 60, 1))) + int(re.findall(r"\d+", x)[3]) / 1000
        out.append((l[2].strip("*").lower(), f(a), f(b)))
    return out

WORDS = load_words()

def word_t(shot, word, nth=0):
    """Start time of `word` inside the scene (seconds from scene start)."""
    hits = [s for w, s, e in WORDS if w.strip(".,:;?!") == word.lower() and shot["start"] - 0.05 <= s < shot["end"]]
    return hits[nth] - shot["start"] if len(hits) > nth else None

# ---------- geometry: polylines ----------
def catmull(pts, n=24):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(pts[-1])
    return out

class Path_:
    def __init__(self, pts):
        self.p = pts
        self.cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.cum.append(self.cum[-1] + math.dist(a, b))
        self.L = self.cum[-1]

    def at(self, s):
        s = clamp(s, 0, self.L)
        for i in range(1, len(self.cum)):
            if self.cum[i] >= s:
                a, b = self.p[i - 1], self.p[i]
                k = (s - self.cum[i - 1]) / max(1e-9, self.cum[i] - self.cum[i - 1])
                return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k), math.atan2(b[1] - a[1], b[0] - a[0])
        return self.p[-1], 0.0

    def sub(self, s0, s1):
        s0, s1 = clamp(s0, 0, self.L), clamp(s1, 0, self.L)
        pts = [self.at(s0)[0]] + [p for p, c in zip(self.p, self.cum) if s0 < c < s1] + [self.at(s1)[0]]
        return pts

def stroke_poly(ctx, pts, width, color, cap=cairo.LINE_CAP_ROUND):
    if len(pts) < 2:
        return
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.set_line_width(width); ctx.set_line_cap(cap); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_source_rgba(*color); ctx.stroke()

# ---------- the city ----------
MAIN = Path_(catmull([(-200, 1700), (120, 1450), (380, 1180), (560, 930), (700, 700), (860, 470), (1060, 240), (1300, -50)]))
ALT = Path_(catmull([(120, 1450), (60, 1150), (90, 860), (260, 620), (520, 430), (760, 330), (1060, 240)]))
# Weckert street: a straight, quiet city street
QUIET = Path_([(540, 1500), (540, -100)])

def draw_city(ctx, main_overlay=None, main_width=64, extra=None):
    ctx.set_source_rgba(*BG); ctx.paint()
    # blocks
    for gx in range(-400, 1600, 240):
        for gy in range(-400, 2300, 240):
            rrect(ctx, gx + 16, gy + 16, 208, 208, 18)
            ctx.set_source_rgba(*BLOCK); ctx.fill()
    # park + water
    rrect(ctx, 616, 1216, 448, 448, 30); ctx.set_source_rgba(*PARK); ctx.fill()
    rrect(ctx, -224, 256, 208, 448, 30); ctx.set_source_rgba(*PARK); ctx.fill()
    river = catmull([(-100, 40), (200, 120), (420, 60), (700, -40)])
    stroke_poly(ctx, river, 90, WATER)
    # side streets (grid)
    for gx in range(-400, 1600, 240):
        stroke_poly(ctx, [(gx, -400), (gx, 2400)], 30, ROAD_EDGE, cairo.LINE_CAP_BUTT)
        stroke_poly(ctx, [(gx, -400), (gx, 2400)], 22, ROAD, cairo.LINE_CAP_BUTT)
    for gy in range(-400, 2400, 240):
        stroke_poly(ctx, [(-400, gy), (1600, gy)], 30, ROAD_EDGE, cairo.LINE_CAP_BUTT)
        stroke_poly(ctx, [(-400, gy), (1600, gy)], 22, ROAD, cairo.LINE_CAP_BUTT)
    if extra:
        extra(ctx)
    # main road
    stroke_poly(ctx, MAIN.p, main_width + 12, ROAD_EDGE)
    stroke_poly(ctx, MAIN.p, main_width, ROAD)
    if main_overlay:
        for s0, s1, col in main_overlay:
            stroke_poly(ctx, MAIN.sub(s0, s1), main_width * 0.42, col)

def camera(ctx, cx, cy, z):
    ctx.translate(W / 2, H * 0.36)
    ctx.scale(z, z)
    ctx.translate(-cx, -cy)

# ---------- icons ----------
def car(ctx, x, y, ang, color, scale=1.0):
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang); ctx.scale(scale, scale)
    rrect(ctx, -30 + 3, -15 + 5, 60, 30, 9); ctx.set_source_rgba(0, 0, 0, 0.15); ctx.fill()
    rrect(ctx, -30, -15, 60, 30, 9); ctx.set_source_rgba(*color); ctx.fill()
    rrect(ctx, 4, -11, 13, 22, 4); ctx.set_source_rgba(1, 1, 1, 0.75); ctx.fill()
    rrect(ctx, -22, -11, 10, 22, 4); ctx.set_source_rgba(1, 1, 1, 0.55); ctx.fill()
    ctx.restore()

def phone(ctx, x, y, s=1.0, screen=BLUE, alpha=1.0):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    rrect(ctx, -32 + 4, -58 + 8, 64, 116, 14); ctx.set_source_rgba(0, 0, 0, 0.15 * alpha); ctx.fill()
    rrect(ctx, -32, -58, 64, 116, 14); ctx.set_source_rgba(*INK[:3], alpha); ctx.fill()
    rrect(ctx, -27, -50, 54, 98, 9); ctx.set_source_rgba(*screen[:3], alpha); ctx.fill()
    ctx.restore()

def rings(ctx, x, y, t, color=BLUE, r0=10, r1=70, period=1.0, n=2, width=5):
    for k in range(n):
        ph = ((t / period) + k / n) % 1.0
        ctx.new_sub_path()
        ctx.arc(x, y, r0 + (r1 - r0) * ph, 0, 2 * math.pi)
        ctx.set_line_width(width); ctx.set_source_rgba(*color[:3], 0.85 * (1 - ph)); ctx.stroke()

def dot(ctx, x, y, r, color, ring=None):
    ctx.new_path()
    if ring:
        ctx.arc(x, y, r + ring[0], 0, 2 * math.pi); ctx.set_source_rgba(*ring[1]); ctx.fill()
    ctx.arc(x, y, r, 0, 2 * math.pi); ctx.set_source_rgba(*color); ctx.fill()

def pin(ctx, x, y, color=RED, s=1.0, alpha=1.0):
    ctx.save(); ctx.new_path(); ctx.translate(x, y); ctx.scale(s, s)
    ctx.move_to(0, 0); ctx.curve_to(-30, -38, -34, -60, -34, -74)
    ctx.arc(0, -74, 34, math.pi, 2 * math.pi)
    ctx.curve_to(34, -60, 30, -38, 0, 0); ctx.close_path()
    ctx.set_source_rgba(*color[:3], alpha); ctx.fill()
    ctx.arc(0, -74, 13, 0, 2 * math.pi); ctx.set_source_rgba(1, 1, 1, alpha); ctx.fill()
    ctx.restore()

def arrow(ctx, x0, y0, x1, y1, color=INK, width=8, head=26, k=1.0):
    if k <= 0.02:
        return
    x1, y1 = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
    ang = math.atan2(y1 - y0, x1 - x0)
    ctx.move_to(x0, y0); ctx.line_to(x1 - math.cos(ang) * head * 0.6, y1 - math.sin(ang) * head * 0.6)
    ctx.set_line_width(width); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_source_rgba(*color); ctx.stroke()
    ctx.move_to(x1, y1)
    ctx.line_to(x1 - head * math.cos(ang - 0.45), y1 - head * math.sin(ang - 0.45))
    ctx.line_to(x1 - head * math.cos(ang + 0.45), y1 - head * math.sin(ang + 0.45))
    ctx.close_path(); ctx.fill()

def server(ctx, x, y, s=1.0, alpha=1.0):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    for i in range(3):
        rrect(ctx, -90, -75 + i * 52, 180, 44, 12); ctx.set_source_rgba(*INK[:3], alpha); ctx.fill()
        ctx.arc(55, -53 + i * 52, 7, 0, 2 * math.pi); ctx.set_source_rgba(*GREEN[:3], alpha); ctx.fill()
    ctx.restore()

def speed_color(v, normal=100):
    r = v / normal
    if r > 0.75:
        return GREEN
    if r > 0.45:
        return mix(ORANGE, GREEN, (r - 0.45) / 0.3) if r > 0.6 else ORANGE
    return mix(RED, ORANGE, clamp((r - 0.25) / 0.2))

# ---------- scenes ----------
def scene_hook(ctx, t, T, shot):
    z = 1.75 + 0.1 * t
    ctx.save(); camera(ctx, 600, 860, z)
    jam = (MAIN.L * 0.46, MAIN.L * 0.62)
    pulse = 0.5 + 0.5 * math.sin(t * 7)
    draw_city(ctx, [(0, jam[0] - 120, GREEN), (jam[0] - 120, jam[0], ORANGE), (jam[0], jam[1], mix(RED, DARKRED, pulse * 0.5)), (jam[1], MAIN.L, GREEN)], main_width=104)
    for i in range(7):
        s = jam[0] + 30 + i * 62 + 5 * math.sin(t * 2 + i)
        (x, y), a = MAIN.at(s)
        side = 36 if i % 2 else -36
        car(ctx, x - side * math.sin(a), y + side * math.cos(a), a, CAR_COLORS[i % 7], 0.8)
    (x, y), a = MAIN.at(sum(jam) / 2)
    ctx.restore()
    # warning chip near the jam, phone with rings below
    sx, sy = W / 2 + (x - 600) * z, H * 0.36 + (y - 860) * z
    chip(ctx, "STAU", sx + 230, sy - 60, 76, RED, CARD)
    rings(ctx, 540, 1080, t, BLUE, 40, 190, 0.9, 3, 7)
    phone(ctx, 540, 1080, 1.25)
    pin(ctx, 540, 1080 + 20, RED, 0.55)

def scene_toggle(ctx, t, T, shot):
    ctx.set_source_rgba(*hexc("#EAF1FF")); ctx.paint()
    on = word_t(shot, "standorterfassung") or 1.0
    k = prog(t, on - 0.1, on + 0.25)
    # phone mockup with settings row
    card(ctx, 250, 230, 580, 980, 70)
    rrect(ctx, 280, 270, 520, 900, 46); ctx.set_source_rgba(*hexc("#F7F8FA")); ctx.fill()
    text(ctx, "Einstellungen", 540, 350, 44)
    rrect(ctx, 310, 430, 460, 130, 28); ctx.set_source_rgba(1, 1, 1, 1); ctx.fill()
    pin(ctx, 365, 535, mix(MUTED, BLUE, k), 0.55)
    text(ctx, "Standort", 425, 495, 44, align="left")
    # toggle
    tx, ty = 690, 495
    rrect(ctx, tx - 50, ty - 30, 100, 60, 30); ctx.set_source_rgba(*mix(hexc("#C9CED6"), GREEN, k)); ctx.fill()
    dot(ctx, tx - 22 + 44 * k, ty, 24, CARD)
    for i, lab in enumerate(("WLAN", "Bluetooth", "Mobile Daten")):
        rrect(ctx, 310, 600 + i * 120, 460, 96, 24); ctx.set_source_rgba(1, 1, 1, 1); ctx.fill()
        text(ctx, lab, 350, 648 + i * 120, 34, MUTED, align="left", bold=False)
    if k > 0.5:
        rings(ctx, 370, 450, t - on, BLUE, 20, 120, 0.8, 2, 6)
        chip(ctx, "Standort: AN", 540, 1140, 46, GREEN, CARD, alpha=prog(t, on + 0.2, on + 0.5))

def cars_on_main(ctx, t, n, s_start, gap, speed, offset=14):
    out = []
    for i in range(n):
        s = s_start + i * gap + speed * t
        (x, y), a = MAIN.at(s)
        side = offset if i % 2 == 0 else -offset
        px, py = x - side * math.sin(a), y + side * math.cos(a)
        car(ctx, px, py, a, CAR_COLORS[i % 7])
        out.append((px, py, a))
    return out

def scene_pings(ctx, t, T, shot):
    ctx.save(); camera(ctx, 520, 1000, 1.25)
    draw_city(ctx)
    cars = cars_on_main(ctx, t, 6, MAIN.L * 0.25, 120, 70)
    ctx.restore()
    z = 1.25
    to_screen = lambda x, y: (W / 2 + (x - 520) * z, H * 0.36 + (y - 1000) * z)
    server(ctx, 810, 170, 0.9)
    text(ctx, "Google", 810, 290, 40)
    an = word_t(shot, "anonyme") or 1.0
    for i, (x, y, a) in enumerate(cars):
        sx, sy = to_screen(x, y)
        rings(ctx, sx, sy, t + i * 0.17, BLUE, 8, 60, 1.0, 1, 5)
        dot(ctx, sx, sy, 10, BLUE, (5, CARD))
        # data packets flying to the server, repeatedly
        for j in range(3):
            ph = ((t * 0.9 + i * 0.23 + j / 3) % 1.0)
            px, py = sx + (810 - sx) * ease(ph), sy + (170 - sy) * ease(ph)
            rrect(ctx, px - 22, py - 15, 44, 30, 8); ctx.set_source_rgba(*BLUE[:3], 0.9 * (1 - ph * 0.5)); ctx.fill()
    if t > an:
        chip(ctx, "anonym", 300, 300, 50, YELLOW, INK, alpha=prog(t, an, an + 0.3))

def scene_speed1(ctx, t, T, shot):
    ctx.save(); camera(ctx, 560, 930, 2.0)
    draw_city(ctx)
    s0 = MAIN.L * 0.40
    t_b = (word_t(shot, "zeit") or T * 0.5)
    s = s0 + 300 * prog(t, 0.25, t_b)
    (xa, ya), a = MAIN.at(s0)
    (x, y), a2 = MAIN.at(s)
    car(ctx, x, y, a2, CAR_COLORS[0], 1.2)
    ctx.restore()
    z = 2.0
    scr = lambda px, py: (W / 2 + (px - 560) * z, H * 0.36 + (py - 930) * z)
    A = scr(xa, ya); B = scr(*MAIN.at(s0 + 300)[0])
    pin(ctx, A[0], A[1] - 30, BLUE, 1.0)
    chip(ctx, "12:00:00", A[0] - 40, A[1] - 230, 42)
    if t > t_b - 0.05:
        k = prog(t, t_b - 0.05, t_b + 0.25)
        pin(ctx, B[0], B[1] - 30, BLUE, 1.0 * k)
        chip(ctx, "12:00:05", B[0] + 30, B[1] - 230, 42, alpha=k)
        # distance bracket
        mx, my = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
        arrow(ctx, mx, my, A[0], A[1], INK, 6, 22, k)
        arrow(ctx, mx, my, B[0], B[1], INK, 6, 22, k)
        chip(ctx, "150 m", mx + 140, my + 40, 46, YELLOW, INK, alpha=k)

def scene_speed2(ctx, t, T, shot):
    ctx.set_source_rgba(*hexc("#EAF1FF")); ctx.paint()
    card(ctx, 110, 260, 860, 860, 60)
    text(ctx, "150 m in 5 s", 540, 380, 64)
    k = prog(t, 0.1, 0.9)
    # speedometer
    cx, cy, r = 540, 820, 270
    ctx.arc(cx, cy, r, math.pi, 2 * math.pi); ctx.set_line_width(36); ctx.set_source_rgba(*hexc("#E5E7EB")); ctx.stroke()
    ang = math.pi + math.pi * (108 / 160) * k
    ctx.arc(cx, cy, r, math.pi, ang); ctx.set_source_rgba(*GREEN); ctx.stroke()
    ctx.move_to(cx, cy); ctx.line_to(cx + (r - 60) * math.cos(ang), cy + (r - 60) * math.sin(ang))
    ctx.set_line_width(14); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_source_rgba(*INK); ctx.stroke()
    dot(ctx, cx, cy, 22, INK)
    text(ctx, f"= {round(108 * k)} km/h", 540, 980, 84)

def scene_aggregate(ctx, t, T, shot):
    ctx.save(); camera(ctx, 560, 930, 1.6)
    draw_city(ctx)
    speeds = [96, 104, 99, 92, 108, 101]
    cars = cars_on_main(ctx, t, 6, MAIN.L * 0.36, 70, 60)
    ctx.restore()
    z = 1.6
    scr = lambda px, py: (W / 2 + (px - 560) * z, H * 0.36 + (py - 930) * z)
    merge = prog(t, T * 0.55, T * 0.85)
    for (x, y, a), v in zip(cars, speeds):
        sx, sy = scr(x, y)
        rings(ctx, sx, sy, t, BLUE, 6, 40, 1.0, 1, 4)
        bx, by = sx + 120, sy - 70
        tx, ty = 540 + (bx - 540) * (1 - merge), 300 + (by - 300) * (1 - merge)
        if merge < 0.98:
            chip(ctx, f"{v}", tx, ty, 40, CARD, INK, alpha=1 - merge)
    if merge > 0:
        chip(ctx, "Ø 100 km/h", 540, 300, 64, GREEN, CARD, alpha=merge)

def scene_anon(ctx, t, T, shot):
    ctx.set_source_rgba(*hexc("#F1F5F9")); ctx.paint()
    k = prog(t, 0.15, 0.8)
    # grid of phones that turn into identical grey dots
    for i in range(4):
        for j in range(4):
            x, y = 240 + i * 200, 330 + j * 200
            if k < 0.5:
                phone(ctx, x, y, 0.9 * (1 - k * 2) + 0.01, BLUE)
            else:
                dot(ctx, x, y, 34 * (k - 0.5) * 2, hexc("#94A3B8"))
    card(ctx, 190, 1060, 700, 150, 40, alpha=prog(t, 0.5, 0.9))
    text(ctx, "keine einzelnen Geräte", 540, 1135, 46, alpha=prog(t, 0.5, 0.9))

def scene_slowdown(ctx, t, T, shot):
    ctx.save(); camera(ctx, 560, 930, 1.7)
    k = prog(t, 0.2, T - 0.2)
    v = round(100 - 75 * k)
    col = speed_color(v)
    seg = (MAIN.L * 0.40, MAIN.L * 0.58)
    draw_city(ctx, [seg + (col,)])
    for i in range(8):
        gap = 85 - 50 * k
        s = seg[0] + i * gap + (60 - 50 * k) * t
        (x, y), a = MAIN.at(s)
        car(ctx, x - 14 * math.sin(a) * (1 if i % 2 else -1), y + 14 * math.cos(a) * (1 if i % 2 else -1), a, CAR_COLORS[i % 7])
    ctx.restore()
    card(ctx, 140, 1010, 800, 200, 44)
    text(ctx, "sonst: 100 km/h", 540, 1060, 40, MUTED, bold=False)
    text(ctx, f"jetzt: {v} km/h", 540, 1140, 62, col)

def scene_color(ctx, t, T, shot):
    t_or = word_t(shot, "orange") or T * 0.3
    t_rot = word_t(shot, "rot") or T * 0.7
    c = GREEN
    c = mix(c, ORANGE, prog(t, t_or - 0.1, t_or + 0.2))
    c = mix(c, RED, prog(t, t_rot - 0.1, t_rot + 0.2))
    ctx.save(); camera(ctx, 600, 880, 1.15 + 0.05 * t)
    draw_city(ctx, [(0, MAIN.L * 0.42, GREEN), (MAIN.L * 0.42, MAIN.L * 0.66, c), (MAIN.L * 0.66, MAIN.L, GREEN)])
    ctx.restore()
    # legend
    card(ctx, 140, 1030, 800, 170, 44)
    for i, (col, lab) in enumerate(((GREEN, "frei"), (ORANGE, "zäh"), (RED, "Stau"))):
        x = 270 + i * 270
        active = [1.0, prog(t, t_or - 0.1, t_or + 0.2), prog(t, t_rot - 0.1, t_rot + 0.2)][i]
        rrect(ctx, x - 70, 1075, 140, 26, 13); ctx.set_source_rgba(*col); ctx.fill()
        text(ctx, lab, x, 1150, 40, INK if active > 0.5 else MUTED)

def network(ctx, t, x0, y0, w, h, layers=(3, 5, 5, 2), alpha=1.0, speed=1.0):
    pos = []
    for li, n in enumerate(layers):
        x = x0 + w * li / (len(layers) - 1)
        pos.append([(x, y0 + h * (j + 1) / (n + 1)) for j in range(n)])
    for li in range(len(layers) - 1):
        for a in pos[li]:
            for b in pos[li + 1]:
                ctx.move_to(*a); ctx.line_to(*b)
                ctx.set_line_width(3); ctx.set_source_rgba(*hexc("#94A3B8")[:3], 0.5 * alpha); ctx.stroke()
    # a pulse travelling through the layers
    ph = (t * speed) % 1.0
    for li, col in enumerate(pos):
        lit = clamp(1 - abs(ph * (len(layers) - 1) - li))
        for (x, y) in col:
            dot(ctx, x, y, 22, mix(hexc("#CBD5E1"), BLUE, lit), (6, (1, 1, 1, alpha)))
    return pos

def scene_ml(ctx, t, T, shot):
    ctx.set_source_rgba(*hexc("#EEF2FF")); ctx.paint()
    card(ctx, 90, 250, 900, 820, 56)
    network(ctx, t, 220, 300, 640, 640, speed=0.9)
    chip(ctx, "maschinelles Lernen", 540, 1010, 52, BLUE, CARD, alpha=prog(t, 0.2, 0.6))

def history_chart(ctx, x0, y0, w, h, k=1.0, cursor=None, alpha=1.0):
    # typical weekday traffic: peaks around 8 and 17 o'clock (illustrative, not measured data)
    def f(hh):
        return 0.15 + 0.75 * math.exp(-((hh - 8) / 1.3) ** 2) + 0.85 * math.exp(-((hh - 17) / 1.6) ** 2) + 0.2 * math.exp(-((hh - 13) / 2.5) ** 2)
    ctx.move_to(x0, y0 + h)
    n = 80
    for i in range(int(n * k) + 1):
        hh = 24 * i / n
        ctx.line_to(x0 + w * i / n, y0 + h - h * f(hh) / 1.1)
    ctx.set_line_width(8); ctx.set_source_rgba(*ORANGE[:3], alpha); ctx.stroke()
    for hh, lab in ((0, "0"), (6, "6"), (12, "12"), (18, "18"), (24, "24 Uhr")):
        text(ctx, lab, x0 + w * hh / 24, y0 + h + 40, 30, MUTED, bold=False, alpha=alpha)
    if cursor is not None:
        x = x0 + w * cursor / 24
        ctx.move_to(x, y0); ctx.line_to(x, y0 + h); ctx.set_line_width(4); ctx.set_source_rgba(*BLUE[:3], alpha); ctx.stroke()
        dot(ctx, x, y0 + h - h * f(cursor) / 1.1, 14, BLUE)
    return f

def scene_history(ctx, t, T, shot):
    ctx.set_source_rgba(*hexc("#EEF2FF")); ctx.paint()
    t_hist = word_t(shot, "historischen") or T * 0.5
    # left input: live map tile; right input: history chart; both into the network
    card(ctx, 70, 230, 440, 380, 40)
    ctx.save(); rrect(ctx, 90, 250, 400, 340, 28); ctx.clip()
    ctx.translate(90, 250); ctx.scale(0.42, 0.42); ctx.translate(-150, -500)
    draw_city(ctx, [(0, MAIN.L * 0.45, GREEN), (MAIN.L * 0.45, MAIN.L * 0.6, RED), (MAIN.L * 0.6, MAIN.L, GREEN)])
    ctx.restore()
    chip(ctx, "jetzt", 290, 650, 42, RED, CARD)
    k = prog(t, t_hist - 0.1, t_hist + 0.4)
    card(ctx, 570, 230, 440, 380, 40, alpha=k)
    if k > 0:
        history_chart(ctx, 610, 280, 360, 230, k, alpha=k)
        chip(ctx, "historisch", 790, 650, 42, ORANGE, CARD, alpha=k)
    arrow(ctx, 290, 720, 470, 840, INK, 8, 28, prog(t, 0.2, 0.6))
    arrow(ctx, 790, 720, 610, 840, INK, 8, 28, k)
    network(ctx, t, 330, 830, 420, 340, layers=(3, 4, 2), speed=1.1)

def scene_clock(ctx, t, T, shot):
    ctx.set_source_rgba(*hexc("#FFF7ED")); ctx.paint()
    card(ctx, 70, 250, 940, 820, 56)
    text(ctx, "Diese Straße, werktags", 540, 340, 46)
    cur = 6 + 11.5 * prog(t, 0.2, T - 0.3)
    history_chart(ctx, 140, 420, 800, 460, 1.0, cursor=cur)
    hh, mm = int(cur), int((cur % 1) * 60)
    chip(ctx, f"{hh:02d}:{mm:02d} Uhr", 540, 1000, 52, BLUE, CARD)

def scene_forecast(ctx, t, T, shot):
    marks = [(word_t(shot, "zehn") or T * 0.3, "+10 min", ORANGE), (word_t(shot, "zwanzig") or T * 0.5, "+20 min", RED),
             (word_t(shot, "fünfzig") or T * 0.7, "+50 min", GREEN)]
    c, label = GREEN, "jetzt"
    for tm, lab, col in marks:
        k = prog(t, tm - 0.1, tm + 0.2)
        c = mix(c, col, k)
        if k > 0.5:
            label = lab
    ctx.save(); camera(ctx, 600, 880, 1.2)
    draw_city(ctx, [(0, MAIN.L * 0.42, GREEN), (MAIN.L * 0.42, MAIN.L * 0.66, c), (MAIN.L * 0.66, MAIN.L, GREEN)])
    ctx.restore()
    # timeline
    card(ctx, 90, 1000, 900, 210, 44)
    xs = [210, 430, 650, 870]
    ctx.move_to(xs[0], 1070); ctx.line_to(xs[-1], 1070); ctx.set_line_width(6); ctx.set_source_rgba(*hexc("#CBD5E1")); ctx.stroke()
    for i, (x, lab) in enumerate(zip(xs, ["jetzt", "+10", "+20", "+50"])):
        active = 1.0 if i == 0 else prog(t, marks[i - 1][0] - 0.1, marks[i - 1][0] + 0.2)
        dot(ctx, x, 1070, 16, mix(hexc("#CBD5E1"), BLUE, active))
        text(ctx, lab, x, 1140, 40, INK if active > 0.5 else MUTED)
    chip(ctx, f"Prognose: {label}", 540, 230, 50, BLUE, CARD)

def scene_reroute(ctx, t, T, shot):
    t_alt = word_t(shot, "schnellere") or T * 0.4
    k = prog(t, t_alt - 0.2, t_alt + 0.4)
    ctx.save(); camera(ctx, 560, 860, 0.95)
    def extra(c):
        stroke_poly(c, ALT.p, 64, ROAD_EDGE); stroke_poly(c, ALT.p, 52, ROAD)
    draw_city(ctx, [(0, MAIN.L * 0.42, GREEN), (MAIN.L * 0.42, MAIN.L * 0.66, RED), (MAIN.L * 0.66, MAIN.L, GREEN)], extra=extra)
    # old route (through the jam) fades to grey, new route draws in
    s_start, s_end = MAIN.L * 0.13, MAIN.L * 0.80
    stroke_poly(ctx, MAIN.sub(s_start, s_end), 16, mix(BLUE, hexc("#9CA3AF", 0.7), k))
    stroke_poly(ctx, ALT.sub(0, ALT.L * k), 22, BLUE)
    p0 = MAIN.at(s_start)[0]; p1 = MAIN.at(s_end)[0]
    ctx.restore()
    z = 0.95
    scr = lambda px, py: (W / 2 + (px - 560) * z, H * 0.36 + (py - 860) * z)
    a, b = scr(*p0), scr(*p1)
    dot(ctx, a[0], a[1], 20, BLUE, (8, CARD))
    pin(ctx, b[0], b[1], RED, 0.9)
    chip(ctx, "32 min", 760, 760, 46, mix(RED, hexc("#9CA3AF"), k), CARD)
    if k > 0:
        chip(ctx, "24 min", 300, 480, 52, BLUE, CARD, alpha=k)

def draw_quiet_street(ctx, red=0.0, cart_y=None, t=0.0):
    ctx.set_source_rgba(*BG); ctx.paint()
    for gy in range(-200, 2200, 260):
        for side in (-1, 1):
            rrect(ctx, 540 + side * 120 + (0 if side > 0 else -360), gy + 20, 360, 220, 20)
            ctx.set_source_rgba(*BLOCK); ctx.fill()
    for gy in range(-200, 2200, 260):
        stroke_poly(ctx, [(-50, gy), (1130, gy)], 30, ROAD_EDGE, cairo.LINE_CAP_BUTT)
        stroke_poly(ctx, [(-50, gy), (1130, gy)], 22, ROAD, cairo.LINE_CAP_BUTT)
    stroke_poly(ctx, [(540, -50), (540, 1970)], 132, ROAD_EDGE, cairo.LINE_CAP_BUTT)
    stroke_poly(ctx, [(540, -50), (540, 1970)], 120, ROAD, cairo.LINE_CAP_BUTT)
    if red > 0 and cart_y is not None:
        top = cart_y - 40
        bottom = min(1970, cart_y + red)
        stroke_poly(ctx, [(540, top), (540, bottom)], 50, RED)
        stroke_poly(ctx, [(540, bottom), (540, 1970)], 50, GREEN)
        stroke_poly(ctx, [(540, -50), (540, top)], 50, GREEN)
    else:
        stroke_poly(ctx, [(540, -50), (540, 1970)], 50, GREEN)

def cart(ctx, x, y, t, n_phones=99, s=1.0):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    # walker (top view, simple): head + body
    wy = -150 + 6 * math.sin(t * 9)
    dot(ctx, 0, wy, 26, INK)
    ctx.move_to(0, wy + 26); ctx.line_to(0, -70); ctx.set_line_width(8); ctx.set_source_rgba(*INK); ctx.stroke()
    # cart body with phones
    rrect(ctx, -110 + 5, -70 + 8, 220, 230, 22); ctx.set_source_rgba(0, 0, 0, 0.15); ctx.fill()
    rrect(ctx, -110, -70, 220, 230, 22); ctx.set_source_rgba(*RED); ctx.fill()
    rrect(ctx, -96, -56, 192, 202, 14); ctx.set_source_rgba(*hexc("#7F1D1D")); ctx.fill()
    for i in range(min(n_phones, 99)):
        r, c = divmod(i, 9)
        px, py = -86 + c * 21, -48 + r * 17
        rrect(ctx, px, py, 16, 14, 3); ctx.set_source_rgba(*hexc("#E0E7FF")); ctx.fill()
        rrect(ctx, px + 2, py + 2, 12, 10, 2); ctx.set_source_rgba(*BLUE); ctx.fill()
    for wx in (-120, 120):
        for wyy in (-30, 120):
            rrect(ctx, wx - 10, wyy - 22, 20, 44, 8); ctx.set_source_rgba(*INK); ctx.fill()
    ctx.restore()

def scene_weckert_intro(ctx, t, T, shot):
    draw_quiet_street(ctx)
    ctx.set_source_rgba(1, 1, 1, 0.35); ctx.paint()
    k = prog(t, 0.1, 0.5)
    card(ctx, 120, 360, 840, 560, 56, alpha=k)
    text(ctx, "Berlin, 2020", 540, 500, 72, alpha=k)
    text(ctx, "Kunstprojekt von", 540, 620, 42, MUTED, bold=False, alpha=prog(t, 0.6, 1.0))
    text(ctx, "Simon Weckert", 540, 700, 64, BLUE, alpha=prog(t, 0.6, 1.0))
    tw = word_t(shot, "handys") or 0.5
    phone(ctx, 540, 830, 0.6, BLUE, alpha=k)
    rings(ctx, 540, 830, t, BLUE, 20, 90, 0.9, 2, 5)

def scene_cart(ctx, t, T, shot):
    y = 1500 - 520 * (t / T)
    draw_quiet_street(ctx)
    cart(ctx, 540, y, t, s=1.4)
    t99 = word_t(shot, "99") or 0.3
    n = round(99 * prog(t, t99 - 0.1, t99 + 0.8))
    chip(ctx, f"{n} Smartphones", 540, 260, 58, CARD, INK)
    t_nav = word_t(shot, "navigation") or T * 0.4
    if t > t_nav:
        chip(ctx, "Navigation läuft", 540, 380, 44, BLUE, CARD, alpha=prog(t, t_nav, t_nav + 0.3))
    for i in range(3):
        rings(ctx, 540, y - 10, t + i * 0.3, BLUE, 60, 220, 1.2, 1, 5)

def scene_fakejam(ctx, t, T, shot):
    y = 980 - 300 * (t / T)
    t_stau = word_t(shot, "stau") or T * 0.3
    red = 900 * prog(t, t_stau - 0.3, t_stau + 0.6)
    draw_quiet_street(ctx, red=max(1, red), cart_y=y, t=t)
    cart(ctx, 540, y, t, s=1.1)
    if t > t_stau - 0.2:
        chip(ctx, "STAU?", 800, y + 250, 58, RED, CARD, alpha=prog(t, t_stau - 0.2, t_stau + 0.2))
    t_leer = word_t(shot, "leeren") or T * 0.7
    if t > t_leer - 0.2:
        chip(ctx, "0 Autos", 280, y + 420, 50, CARD, INK, alpha=prog(t, t_leer - 0.2, t_leer + 0.2))

SCENES = {
    "hook": scene_hook, "toggle": scene_toggle, "pings": scene_pings, "speed1": scene_speed1, "speed2": scene_speed2,
    "aggregate": scene_aggregate, "anon": scene_anon, "slowdown": scene_slowdown, "color": scene_color, "ml": scene_ml,
    "history": scene_history, "clock": scene_clock, "forecast": scene_forecast, "reroute": scene_reroute,
    "weckert_intro": scene_weckert_intro, "cart": scene_cart, "fakejam": scene_fakejam,
}

def frames_of(shot):
    return round(shot["end"] * FPS) - round(shot["start"] * FPS)

def render_frame(shot, t, T):
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    SCENES[shot["visual"].split(":", 1)[1]](ctx, t, T, shot)
    return surf

def render(shot):
    n = frames_of(shot)
    T = n / FPS
    out = ROOT / "work" / "clips" / f"scene_{shot['id']:02d}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-frames:v", str(n), "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                           "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    for i in range(n):
        surf = render_frame(shot, i / FPS, T)
        ff.stdin.write(bytes(surf.get_data()))
    ff.stdin.close()
    ff.wait()
    print(f"scene {shot['id']:>2}: {shot['visual']:<20} {n} frames ({T:.2f} s)")

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--still":
        shot = next(s for s in SHOTS if s["id"] == int(args[1]))
        T = frames_of(shot) / FPS
        surf = render_frame(shot, float(args[2]) * T, T)
        dst = ROOT / "work" / f"still_{shot['id']:02d}.png"
        surf.write_to_png(str(dst)); print(dst)
    else:
        for s in SHOTS:
            if s["visual"].startswith("anim:") and (not args or str(s["id"]) in args):
                render(s)
