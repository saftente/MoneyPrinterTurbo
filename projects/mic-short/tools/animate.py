"""Own animated explainer scenes for the "does my phone listen?" short (pycairo, 1080x1920, 30 fps).

  python3 projects/mic-short/tools/animate.py                 # all scenes
  python3 projects/mic-short/tools/animate.py 4 10            # only these scene ids
  python3 projects/mic-short/tools/animate.py --still 10 0.5  # one PNG at 50 % of scene 10

Same rules as projects/traffic-short: frame-exact scene lengths from shotlist.json, beats timed to the
spoken words (work/voice/subtitle_words.srt), light look, key content above y=1250 (subtitles below).
The film is fictional ("STERNENFALL"); the app UI is generic (no platform logos).
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

def hexc(h, a=1.0):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (a,)

INK = hexc("#1F2937"); MUTED = hexc("#6B7280"); LINE = hexc("#CBD5E1"); CARD = hexc("#FFFFFF")
BLUE = hexc("#2F6FED"); GREEN = hexc("#22B573"); ORANGE = hexc("#F59E0B"); RED = hexc("#E5484D")
PURPLE = hexc("#7C3AED"); PINK = hexc("#EC4899"); YELLOW = hexc("#FFD23F"); TEAL = hexc("#14B8A6")
BG_BLUE = hexc("#EAF1FF"); BG_WARM = hexc("#FFF4E6"); BG_MINT = hexc("#E9F8F1"); BG_GREY = hexc("#F1F5F9"); BG_LILAC = hexc("#F3EEFF")
FILM = "STERNENFALL"

# ---------- helpers ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def ease(x):
    x = clamp(x); return x * x * (3 - 2 * x)

def ease_out(x):
    x = clamp(x); return 1 - (1 - x) ** 3

def prog(t, t0, t1):
    return ease((t - t0) / max(1e-6, t1 - t0))

def pop(t, t0, d=0.35):
    """0 -> overshoot -> 1, for things appearing."""
    x = clamp((t - t0) / d)
    return 0 if x <= 0 else 1 + 0.18 * math.sin(x * math.pi) * (1 - x) * 3 if x < 1 else 1.0

def mix(c1, c2, k):
    return tuple(a + (b - a) * k for a, b in zip(c1, c2))

def bg(ctx, c):
    ctx.set_source_rgba(*c); ctx.paint()

def rrect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0); ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()

def fill(ctx, c, a=1.0):
    ctx.set_source_rgba(*c[:3], c[3] * a); ctx.fill()

def text(ctx, s, x, y, size, color=INK, align="center", bold=True, alpha=1.0):
    ctx.new_path()
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)
    ext = ctx.text_extents(s)
    dx = {"center": -ext.x_advance / 2, "left": 0, "right": -ext.x_advance}[align]
    ctx.move_to(x + dx, y + size * 0.36); ctx.set_source_rgba(*color[:3], color[3] * alpha); ctx.show_text(s)
    ctx.new_path()
    return ext.x_advance

def text_w(ctx, s, size, bold=True):
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size); return ctx.text_extents(s).x_advance

def chip(ctx, s, x, y, size, bgc=CARD, fg=INK, alpha=1.0, scale=1.0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale)
    w = text_w(ctx, s, size) + size * 1.1; h = size * 1.7
    rrect(ctx, -w / 2 + 4, -h / 2 + 8, w, h, h / 2); fill(ctx, (0, 0, 0, 0.12), alpha)
    rrect(ctx, -w / 2, -h / 2, w, h, h / 2); fill(ctx, bgc, alpha)
    text(ctx, s, 0, 0, size, fg, alpha=alpha)
    ctx.restore()

def card(ctx, x, y, w, h, r=36, alpha=1.0, color=CARD):
    rrect(ctx, x + 6, y + 12, w, h, r); fill(ctx, (0, 0, 0, 0.10), alpha)
    rrect(ctx, x, y, w, h, r); fill(ctx, color, alpha)

def dot(ctx, x, y, r, c, a=1.0):
    ctx.new_path(); ctx.arc(x, y, max(0.1, r), 0, 2 * math.pi); fill(ctx, c, a)

def ring(ctx, x, y, r, c, width=5, a=1.0):
    ctx.new_path(); ctx.arc(x, y, max(0.1, r), 0, 2 * math.pi); ctx.set_line_width(width); ctx.set_source_rgba(*c[:3], c[3] * a); ctx.stroke()

def waves(ctx, x, y, t, c=BLUE, r0=20, r1=140, period=1.0, n=3, width=6):
    for k in range(n):
        ph = ((t / period) + k / n) % 1.0
        ring(ctx, x, y, r0 + (r1 - r0) * ph, c, width, 0.85 * (1 - ph))

def line(ctx, x0, y0, x1, y1, c=INK, width=6, dash=None, a=1.0):
    ctx.new_path(); ctx.move_to(x0, y0); ctx.line_to(x1, y1)
    if dash: ctx.set_dash(dash)
    ctx.set_line_width(width); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_source_rgba(*c[:3], c[3] * a); ctx.stroke()
    ctx.set_dash([])

def arrow(ctx, x0, y0, x1, y1, c=INK, width=8, head=26, k=1.0, a=1.0):
    if k <= 0.02:
        return
    x1, y1 = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
    ang = math.atan2(y1 - y0, x1 - x0)
    line(ctx, x0, y0, x1 - math.cos(ang) * head * 0.6, y1 - math.sin(ang) * head * 0.6, c, width, a=a)
    ctx.new_path(); ctx.move_to(x1, y1)
    ctx.line_to(x1 - head * math.cos(ang - 0.45), y1 - head * math.sin(ang - 0.45))
    ctx.line_to(x1 - head * math.cos(ang + 0.45), y1 - head * math.sin(ang + 0.45))
    ctx.close_path(); fill(ctx, c, a)

def check(ctx, x, y, s, c=GREEN, a=1.0):
    dot(ctx, x, y, s, c, a)
    ctx.new_path(); ctx.move_to(x - s * 0.45, y); ctx.line_to(x - s * 0.1, y + s * 0.35); ctx.line_to(x + s * 0.5, y - s * 0.35)
    ctx.set_line_width(s * 0.22); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_source_rgba(1, 1, 1, a); ctx.stroke()

def cross(ctx, x, y, s, c=RED, a=1.0, disc=True):
    if disc:
        dot(ctx, x, y, s, c, a)
    col = (1, 1, 1, a) if disc else (c[0], c[1], c[2], a)
    k = s * 0.42
    ctx.new_path(); ctx.move_to(x - k, y - k); ctx.line_to(x + k, y + k); ctx.move_to(x + k, y - k); ctx.line_to(x - k, y + k)
    ctx.set_line_width(s * 0.22 if disc else s * 0.18); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_source_rgba(*col); ctx.stroke()

# ---------- word timing ----------
def _srt():
    out = []
    for blk in (ROOT / "work/voice/subtitle_words.srt").read_text(encoding="utf-8").strip().split("\n\n"):
        l = blk.split("\n"); a, b = l[1].split(" --> ")
        f = lambda x: sum(int(p) * m for p, m in zip(re.findall(r"\d+", x)[:3], (3600, 60, 1))) + int(re.findall(r"\d+", x)[3]) / 1000
        out.append((re.sub(r"[^a-zäöüß0-9]", "", l[2].lower()), f(a)))
    return out

WORDS = _srt()

def wt(shot, word, frac):
    """Start of `word` within the scene, or frac * duration if not found."""
    key = re.sub(r"[^a-zäöüß0-9]", "", word.lower())
    for w, s in WORDS:
        if w.startswith(key) and shot["start"] - 0.05 <= s < shot["end"]:
            return s - shot["start"]
    return frac * (shot["end"] - shot["start"])

# ---------- shared objects ----------
def phone(ctx, cx, cy, w=520, h=1000, screen=CARD, alpha=1.0):
    """Phone frame; returns the screen rectangle (x, y, w, h)."""
    x, y = cx - w / 2, cy - h / 2
    rrect(ctx, x + 8, y + 16, w, h, 70); fill(ctx, (0, 0, 0, 0.14), alpha)
    rrect(ctx, x, y, w, h, 70); fill(ctx, INK, alpha)
    sx, sy, sw, sh = x + 22, y + 22, w - 44, h - 44
    rrect(ctx, sx, sy, sw, sh, 52); fill(ctx, screen, alpha)
    rrect(ctx, cx - 60, y + 36, 120, 30, 15); fill(ctx, INK, alpha)
    return sx, sy, sw, sh

THUMBS = [(PURPLE, ORANGE, FILM), (hexc("#F97316"), hexc("#FDBA74"), "Katzen"), (TEAL, hexc("#99F6E4"), "Rezepte"),
          (BLUE, hexc("#93C5FD"), "Fußball"), (PINK, hexc("#F9A8D4"), "Musik"), (hexc("#65A30D"), hexc("#BEF264"), "Reisen")]

def thumb(ctx, x, y, w, h, kind, label=None, alpha=1.0, glow=0.0, dim=0.0):
    c1, c2, name = THUMBS[kind]
    if glow > 0:
        rrect(ctx, x - 10, y - 10, w + 20, h + 20, 34); fill(ctx, YELLOW, glow)
    pat = cairo.LinearGradient(x, y, x + w, y + h)
    pat.add_color_stop_rgba(0, *c1[:3], alpha); pat.add_color_stop_rgba(1, *c2[:3], alpha)
    rrect(ctx, x, y, w, h, 26); ctx.set_source(pat); ctx.fill()
    if kind == 0:  # film: stars + title
        for i, (px, py, r) in enumerate(((0.2, 0.25, 7), (0.75, 0.2, 5), (0.6, 0.4, 4), (0.3, 0.55, 5), (0.85, 0.6, 6))):
            dot(ctx, x + w * px, y + h * py, r * w / 300, CARD, alpha * 0.9)
        text(ctx, name, x + w / 2, y + h * 0.72, w * 0.105, CARD, alpha=alpha)
    else:
        text(ctx, name, x + w / 2, y + h * 0.5, w * 0.12, CARD, alpha=alpha)
    # play icon
    px, py, s = x + w / 2, y + h * 0.42 if kind == 0 else y + h * 0.28, w * 0.07
    ctx.new_path(); ctx.move_to(px - s * 0.6, py - s); ctx.line_to(px + s, py); ctx.line_to(px - s * 0.6, py + s); ctx.close_path(); fill(ctx, CARD, alpha * 0.85)
    if label:
        text(ctx, label, x + 24, y + h - 34, w * 0.07, CARD, align="left", alpha=alpha)
    if dim > 0:
        rrect(ctx, x, y, w, h, 26); fill(ctx, (0.95, 0.96, 0.98, 1), dim * 0.75)

def app_header(ctx, sx, sy, sw, alpha=1.0):
    text(ctx, "Für dich", sx + sw / 2, sy + 90, 40, INK, alpha=alpha)
    line(ctx, sx + sw / 2 - 50, sy + 125, sx + sw / 2 + 50, sy + 125, INK, 6, a=alpha)

def mic_icon(ctx, x, y, s=1.0, c=INK, a=1.0):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    rrect(ctx, -34, -90, 68, 120, 34); fill(ctx, c, a)
    ctx.new_path(); ctx.arc(0, -10, 62, 0, math.pi); ctx.set_line_width(12); ctx.set_source_rgba(*c[:3], a); ctx.stroke()
    line(ctx, 0, 52, 0, 92, c, 12, a=a); line(ctx, -36, 94, 36, 94, c, 12, a=a)
    ctx.restore()

def person(ctx, x, y, s=1.0, c=INK, a=1.0):
    dot(ctx, x, y - 34 * s, 22 * s, c, a)
    ctx.new_path(); ctx.arc(x, y + 30 * s, 40 * s, math.pi, 2 * math.pi); ctx.close_path(); fill(ctx, c, a)

def server(ctx, x, y, s=1.0, c=INK, a=1.0):
    for i in range(3):
        rrect(ctx, x - 90 * s, y - 75 * s + i * 52 * s, 180 * s, 44 * s, 12 * s); fill(ctx, c, a)
        dot(ctx, x + 55 * s, y - 53 * s + i * 52 * s, 7 * s, GREEN, a)

def eye(ctx, x, y, s=1.0, c=INK, a=1.0, open_=1.0):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s * max(0.08, open_))
    ctx.new_path(); ctx.move_to(-120, 0); ctx.curve_to(-60, -80, 60, -80, 120, 0); ctx.curve_to(60, 80, -60, 80, -120, 0); ctx.close_path()
    fill(ctx, CARD, a); ctx.new_path(); ctx.move_to(-120, 0); ctx.curve_to(-60, -80, 60, -80, 120, 0); ctx.curve_to(60, 80, -60, 80, -120, 0); ctx.close_path()
    ctx.set_line_width(10); ctx.set_source_rgba(*c[:3], a); ctx.stroke()
    dot(ctx, 0, 0, 40, BLUE, a); dot(ctx, 0, 0, 18, INK, a)
    ctx.restore()

def stopwatch(ctx, x, y, r, frac, c=BLUE, a=1.0):
    dot(ctx, x, y, r, CARD, a); ring(ctx, x, y, r, INK, 10, a)
    rrect(ctx, x - 16, y - r - 30, 32, 22, 6); fill(ctx, INK, a)
    ctx.new_path(); ctx.move_to(x, y); ctx.arc(x, y, r - 14, -math.pi / 2, -math.pi / 2 + 2 * math.pi * frac); ctx.close_path(); fill(ctx, c, a * 0.85)

def ticket(ctx, x, y, s=1.0, a=1.0):
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s)
    rrect(ctx, -110, -60, 220, 120, 18); fill(ctx, ORANGE, a)
    line(ctx, 40, -50, 40, 50, CARD, 4, dash=[8, 8], a=a)
    text(ctx, "TICKET", -30, -8, 34, CARD, alpha=a); text(ctx, FILM, -30, 30, 16, CARD, alpha=a)
    ctx.restore()

# ---------- scenes ----------
def s_cinema(ctx, t, T, shot):
    bg(ctx, BG_WARM)
    # screen
    sc = 0.5 + 0.5 * math.sin(t * 3)
    rrect(ctx, 90, 200, 900, 470, 30); fill(ctx, INK)
    pat = cairo.LinearGradient(110, 220, 970, 650)
    pat.add_color_stop_rgb(0, *PURPLE[:3]); pat.add_color_stop_rgb(1, *ORANGE[:3])
    rrect(ctx, 110, 220, 860, 430, 20); ctx.set_source(pat); ctx.fill()
    for i, (px, py) in enumerate(((220, 300), (820, 280), (650, 380), (330, 470), (900, 520), (480, 290))):
        dot(ctx, px, py, 6 + 4 * abs(math.sin(t * 2.5 + i)), CARD, 0.9)
    text(ctx, FILM, 540, 470, 92, CARD)
    # light beam
    ctx.new_path(); ctx.move_to(540, 1260); ctx.line_to(140, 640); ctx.line_to(940, 640); ctx.close_path(); fill(ctx, (1, 1, 1, 1), 0.18 + 0.06 * sc)
    # seat rows with audience
    for r, (y, n, sw) in enumerate(((790, 7, 112), (930, 8, 118), (1080, 8, 124))):
        x0 = 540 - n * sw / 2
        for i in range(n):
            x = x0 + i * sw + sw / 2
            if (i + r) % 3 != 1:
                dot(ctx, x, y - 30, 30, hexc("#374151"))
                ctx.new_path(); ctx.arc(x, y + 20, 44, math.pi, 2 * math.pi); ctx.close_path(); fill(ctx, hexc("#374151"))
            rrect(ctx, x - sw * 0.42, y + 10, sw * 0.84, 90, 20); fill(ctx, RED)
            rrect(ctx, x - sw * 0.42, y + 10, sw * 0.84, 24, 12); fill(ctx, hexc("#F87171"))
    chip(ctx, "Kino", 540, 140, 48, INK, CARD)

def s_open_app(ctx, t, T, shot):
    bg(ctx, BG_BLUE)
    k = ease_out(t / max(0.4, T * 0.55))
    cy = 1700 - 1000 * k
    sx, sy, sw, sh = phone(ctx, 540, cy)
    app_header(ctx, sx, sy, sw)
    thumb(ctx, sx + 30, sy + 170, sw - 60, sh - 260, 1)
    # finger tap
    tap = prog(t, T * 0.55, T * 0.8)
    if tap > 0:
        ring(ctx, 540, cy, 60 + 60 * tap, BLUE, 8, 1 - tap)
        dot(ctx, 540, cy, 34, BLUE, 0.6 * (1 - tap))
    chip(ctx, "App öffnen", 540, 150, 46, BLUE, CARD, alpha=prog(t, 0.1, 0.4))

def s_feed_flood(ctx, t, T, shot):
    bg(ctx, BG_BLUE)
    sx, sy, sw, sh = phone(ctx, 540, 700)
    ctx.save(); rrect(ctx, sx, sy, sw, sh, 52); ctx.clip()
    app_header(ctx, sx, sy, sw)
    ch = 300
    scroll = t * 520
    n_film = 0
    for i in range(14):
        y = sy + 160 + i * (ch + 24) - scroll
        if y < sy - ch or y > sy + sh:
            continue
        kind = 0 if (i >= 1 and i % 4 != 2) else (i % 5) + 1
        thumb(ctx, sx + 26, y, sw - 52, ch, kind, label=f"Edit #{i}" if kind == 0 else None)
    ctx.restore()
    n = min(12, int(t / T * 14))
    chip(ctx, f"{FILM}-Edits: {n}", 540, 1310 - 1310 + 1260, 46, PURPLE, CARD, alpha=prog(t, 0.3, 0.6))

def s_listening(ctx, t, T, shot):
    bg(ctx, BG_LILAC)
    sx, sy, sw, sh = phone(ctx, 540, 720, 460, 880)
    mic_icon(ctx, 540, 640, 1.6, INK)
    waves(ctx, 540, 600, t, PURPLE, 140, 420, 1.1, 3, 8)
    k = pop(t, wt(shot, "heimlich", 0.5))
    if k > 0:
        dot(ctx, 540, 1000, 70 * k, RED)
        text(ctx, "?", 540, 1000, 110 * k, CARD)
    blink = (int(t * 2.5) % 2 == 0)
    dot(ctx, sx + 60, sy + 70, 14, RED, 1.0 if blink else 0.25)
    text(ctx, "REC", sx + 84, sy + 70, 30, RED, align="left", alpha=1.0 if blink else 0.25)

APPS = [(hexc("#EC4899"), "A"), (hexc("#2F6FED"), "B"), (hexc("#22B573"), "C"), (hexc("#F59E0B"), "D"), (hexc("#7C3AED"), "E"), (hexc("#14B8A6"), "F")]

def app_icon(ctx, x, y, s, i, a=1.0):
    c, lab = APPS[i % len(APPS)]
    rrect(ctx, x - s / 2, y - s / 2, s, s, s * 0.24); fill(ctx, c, a)
    text(ctx, lab, x, y, s * 0.42, CARD, alpha=a)

def s_mic_apps(ctx, t, T, shot):
    bg(ctx, BG_GREY)
    dot(ctx, 540, 650, 150, CARD); ring(ctx, 540, 650, 150, LINE, 6)
    mic_icon(ctx, 540, 650, 1.05, INK)
    for i in range(6):
        ang = -math.pi / 2 + i * math.pi / 3
        x, y = 540 + 380 * math.cos(ang), 650 + 380 * math.sin(ang)
        k = prog(t, 0.1 + i * 0.12, 0.4 + i * 0.12)
        line(ctx, x, y, 540 + 170 * math.cos(ang), 650 + 170 * math.sin(ang), BLUE, 6, dash=[14, 12], a=k)
        app_icon(ctx, x, y, 140 * (0.6 + 0.4 * k), i, a=max(0.3, k))
    chip(ctx, "Mikrofon", 540, 1160, 52, INK, CARD, alpha=prog(t, wt(shot, "mikrofon", 0.6) - 0.1, wt(shot, "mikrofon", 0.6) + 0.2))

def s_permission(ctx, t, T, shot):
    bg(ctx, BG_GREY)
    sx, sy, sw, sh = phone(ctx, 540, 700, 560, 1040, screen=hexc("#E5E7EB"))
    k = pop(t, 0.05)
    ctx.save(); ctx.translate(540, 700); ctx.scale(max(k, 0.01), max(k, 0.01)); ctx.translate(-540, -700)
    card(ctx, sx + 30, 470, sw - 60, 470, 40)
    mic_icon(ctx, 540, 590, 0.55, BLUE)
    text(ctx, "„App“ möchte auf dein", 540, 700, 36)
    text(ctx, "Mikrofon zugreifen", 540, 750, 36)
    line(ctx, sx + 30, 810, sx + sw - 30, 810, LINE, 3)
    line(ctx, 540, 810, 540, 940, LINE, 3)
    text(ctx, "Nicht erlauben", (sx + 30 + 540) / 2, 875, 30, BLUE, bold=False)
    text(ctx, "Erlauben", (540 + sx + sw - 30) / 2, 875, 30, BLUE)
    ctx.restore()
    e = wt(shot, "erlaubnis", 0.6)
    hl = prog(t, e - 0.1, e + 0.2)
    if hl > 0:
        rrect(ctx, 548, 822, sx + sw - 30 - 556, 108, 26); ctx.set_line_width(6); ctx.set_source_rgba(*YELLOW[:3], hl); ctx.stroke()
        chip(ctx, "nur mit Erlaubnis", 540, 1290 - 60, 46, YELLOW, INK, alpha=hl)

def status_bar(ctx, y, label, dot_c, k, t):
    card(ctx, 110, y, 860, 250, 44)
    text(ctx, label, 160, y + 50, 34, MUTED, align="left", bold=False)
    rrect(ctx, 150, y + 100, 780, 110, 30); fill(ctx, BG_GREY)
    text(ctx, "12:34", 190, y + 155, 44, INK, align="left")
    for i in range(3):
        rrect(ctx, 760 + i * 22, y + 175 - i * 14 - 14, 14, 14 + i * 14, 4); fill(ctx, INK)
    rrect(ctx, 840, y + 140, 60, 30, 8); fill(ctx, INK)
    if k > 0:
        dot(ctx, 640, y + 155, 22 * pop(k, 0, 1) if k < 1 else 22, dot_c)
        ring(ctx, 640, y + 155, 22 + 50 * ((t * 1.2) % 1), dot_c, 5, 1 - ((t * 1.2) % 1))

def s_indicator(ctx, t, T, shot):
    bg(ctx, BG_MINT)
    g = prog(t, wt(shot, "grünen", 0.45) - 0.05, wt(shot, "grünen", 0.45) + 0.2)
    o = prog(t, wt(shot, "orange", 0.7) - 0.05, wt(shot, "orange", 0.7) + 0.2)
    status_bar(ctx, 330, "Android", GREEN, g, t)
    status_bar(ctx, 680, "iPhone", ORANGE, o, t)
    chip(ctx, "Mikrofon aktiv", 540, 1080, 48, INK, CARD, alpha=max(g, o))

def s_study(ctx, t, T, shot):
    bg(ctx, BG_BLUE)
    card(ctx, 70, 200, 940, 960, 50)
    cols, rows = 10, 11
    k = prog(t, 0.1, T * 0.85)
    shown = int(cols * rows * k)
    for i in range(cols * rows):
        r, c = divmod(i, cols)
        x, y = 150 + c * 87, 300 + r * 70
        if i < shown:
            app_icon(ctx, x, y, 56, (i * 7) % 6)
        else:
            rrect(ctx, x - 28, y - 28, 56, 56, 14); fill(ctx, BG_GREY)
    n = int(17260 * k)
    chip(ctx, f"{n:,}".replace(",", ".") + " Apps", 540, 1100, 56, BLUE, CARD)
    chip(ctx, "Northeastern University · 2018", 540, 130, 38, CARD, INK, alpha=prog(t, 0.2, 0.5))

def s_no_audio(ctx, t, T, shot):
    bg(ctx, BG_MINT)
    phone(ctx, 260, 640, 300, 560)
    server(ctx, 820, 640, 1.1)
    text(ctx, "Server", 820, 780, 34, MUTED, bold=False)
    k = wt(shot, "keine", 0.3)
    # audio packets travel and get blocked midway
    for j in range(3):
        ph = ((t * 0.8 + j / 3) % 1.0)
        x = 420 + 230 * ease(ph)
        a = 1 - ph
        rrect(ctx, x - 50, 600, 100, 80, 18); fill(ctx, PURPLE, a)
        for b in range(5):
            hgt = 12 + 22 * abs(math.sin(b * 1.7 + t * 6))
            rrect(ctx, x - 36 + b * 16, 640 - hgt / 2, 9, hgt, 4); fill(ctx, CARD, a)
    line(ctx, 690, 520, 690, 760, RED, 10, a=prog(t, k - 0.1, k + 0.2))
    m = prog(t, k, k + 0.3)
    card(ctx, 190, 930, 700, 200, 44, alpha=m)
    text(ctx, "heimliche Audio-Uploads: 0", 540, 1030, 46, INK, alpha=m)
    if m > 0.5:
        check(ctx, 540, 870, 44 * pop(t, k + 0.15), GREEN)

def s_screenshots(ctx, t, T, shot):
    bg(ctx, hexc("#FFF1F2"))
    sx, sy, sw, sh = phone(ctx, 270, 640, 340, 640)
    thumb(ctx, sx + 16, sy + 110, sw - 32, 300, 3)
    server(ctx, 820, 600, 1.0, hexc("#9F1239"))
    text(ctx, "Dritte", 820, 740, 40, hexc("#9F1239"))
    for j in range(4):
        ph = ((t * 0.9 + j / 4) % 1.0)
        x0, y0 = 300, 600
        x = x0 + (760 - x0) * ease(ph); y = y0 - 120 * math.sin(ph * math.pi)
        a = 1 - ph * 0.6
        rrect(ctx, x - 45, y - 75, 90, 150, 14); fill(ctx, INK, a)
        rrect(ctx, x - 37, y - 66, 74, 132, 9); fill(ctx, BLUE, a)
    chip(ctx, "Bildschirmaufnahmen", 540, 1010, 52, RED, CARD, alpha=prog(t, wt(shot, "bildschirmaufnahmen", 0.5) - 0.1, wt(shot, "bildschirmaufnahmen", 0.5) + 0.2))
    chip(ctx, "ohne Hinweis", 540, 1120, 40, CARD, INK, alpha=prog(t, wt(shot, "unbemerkt", 0.3) - 0.1, wt(shot, "unbemerkt", 0.3) + 0.2))

def s_not_proof(ctx, t, T, shot):
    bg(ctx, BG_GREY)
    for i, (lab, x, c) in enumerate((("2018", 300, BLUE), ("heute", 780, INK))):
        k = prog(t, 0.05 + i * 0.35, 0.35 + i * 0.35)
        card(ctx, x - 180, 420, 360, 380, 40, alpha=k)
        rrect(ctx, x - 180, 420, 360, 90, 40); fill(ctx, c, k)
        rrect(ctx, x - 180, 470, 360, 40, 0); fill(ctx, c, k)
        text(ctx, lab, x, 466, 46, CARD, alpha=k)
        if i == 0:
            check(ctx, x, 650, 70 * k, GREEN, k)
        else:
            text(ctx, "?", x, 650, 150, MUTED, alpha=k)
    arrow(ctx, 500, 610, 580, 610, LINE, 8, 26, prog(t, 0.4, 0.7))
    chip(ctx, "kein Beweis für heute", 540, 1000, 48, CARD, INK, alpha=prog(t, 0.5, 0.9))

def s_evidence(ctx, t, T, shot):
    bg(ctx, BG_GREY)
    card(ctx, 80, 300, 920, 780, 50)
    rows = [("Technisch möglich", "ja", GREEN, 0.05), ("Nur mit Erlaubnis", "ja", GREEN, 0.2),
            ("Heimliches Abhören durch", "kein Beleg", RED, wt(shot, "beleg", 0.75) - 0.6)]
    for i, (lab, res, c, t0) in enumerate(rows):
        k = prog(t, t0, t0 + 0.35)
        y = 430 + i * 220
        text(ctx, lab, 140, y, 42, INK, align="left", alpha=k)
        if i == 2:
            text(ctx, "große Plattformen", 140, y + 56, 42, INK, align="left", alpha=k)
        chip(ctx, res, 820, y + (28 if i == 2 else 0), 42, c, CARD, alpha=k, scale=pop(t, t0 + 0.1))
        if i < 2:
            line(ctx, 140, y + 100, 940, y + 100, LINE, 3, a=k)

def s_no_link(ctx, t, T, shot):
    bg(ctx, BG_WARM)
    # mini cinema
    card(ctx, 90, 420, 360, 380, 40)
    pat = cairo.LinearGradient(120, 450, 420, 600)
    pat.add_color_stop_rgb(0, *PURPLE[:3]); pat.add_color_stop_rgb(1, *ORANGE[:3])
    rrect(ctx, 120, 450, 300, 170, 16); ctx.set_source(pat); ctx.fill()
    text(ctx, FILM, 270, 540, 34, CARD)
    for i in range(4):
        rrect(ctx, 130 + i * 74, 660, 60, 90, 14); fill(ctx, RED)
    text(ctx, "Kino", 270, 850, 40, MUTED, bold=False)
    sx, sy, sw, sh = phone(ctx, 790, 610, 290, 540)
    app_header(ctx, sx, sy, sw)
    k = prog(t, 0.1, 0.6)
    line(ctx, 460, 610, 460 + 170 * k, 610, LINE, 8, dash=[16, 14])
    c = prog(t, 0.5, 0.8)
    if c > 0:
        cross(ctx, 545, 610, 60 * pop(t, 0.5), RED)
    chip(ctx, "kein Signal aus dem Kino", 540, 1040, 46, CARD, INK, alpha=prog(t, 0.7, 1.0))

def s_trend(ctx, t, T, shot):
    bg(ctx, BG_LILAC)
    # people -> videos -> rising curve
    for i in range(12):
        r, c = divmod(i, 6)
        x, y = 150 + c * 156, 320 + r * 150
        person(ctx, x, y, 0.9, mix(INK, PURPLE, (i % 3) / 3), a=prog(t, 0.0 + i * 0.05, 0.3 + i * 0.05))
    tp = wt(shot, "posten", 0.6)
    for i in range(10):
        ph = prog(t, tp - 0.4 + i * 0.07, tp + 0.2 + i * 0.07)
        if ph <= 0:
            continue
        x0, y0 = 150 + (i % 6) * 156, 340 + (i // 6) * 150
        x, y = x0 + (540 - x0) * ph, y0 + (780 - y0) * ph * 0.6
        thumb(ctx, x - 50, y - 80, 100, 160, 0, alpha=1 - 0.3 * ph)
    # trend chart
    card(ctx, 110, 820, 860, 360, 40)
    k = prog(t, 0.3, T)
    ctx.new_path(); ctx.move_to(170, 1120)
    for i in range(int(60 * k) + 1):
        x = 170 + 740 * i / 60
        y = 1120 - 240 * (1 - math.exp(-((i / 60) * 4) ** 2 / 3)) - 8 * math.sin(i)
        ctx.line_to(x, y)
    ctx.set_line_width(10); ctx.set_source_rgba(*PURPLE); ctx.stroke()
    chip(ctx, "Trend", 860, 880, 44, PURPLE, CARD, alpha=prog(t, wt(shot, "trend", 0.2) - 0.1, wt(shot, "trend", 0.2) + 0.2))

def s_watchtime(ctx, t, T, shot):
    bg(ctx, BG_BLUE)
    sx, sy, sw, sh = phone(ctx, 400, 680, 440, 860)
    app_header(ctx, sx, sy, sw)
    thumb(ctx, sx + 22, sy + 160, sw - 44, sh - 240, 0, label="Edit")
    secs = 12 * prog(t, 0.2, T)
    stopwatch(ctx, 830, 520, 110, (secs % 12) / 12 if secs < 11.9 else 0.999)
    chip(ctx, f"{secs:4.1f} s".replace(".", ","), 830, 720, 50, BLUE, CARD)
    chip(ctx, "Wiedergabezeit", 830, 820, 36, CARD, INK)
    # progress bar on the video
    rrect(ctx, sx + 22, sy + sh - 70, sw - 44, 12, 6); fill(ctx, LINE)
    rrect(ctx, sx + 22, sy + sh - 70, (sw - 44) * clamp(secs / 12), 12, 6); fill(ctx, BLUE)

def s_loop(ctx, t, T, shot):
    bg(ctx, BG_LILAC)
    cx, cy, r = 540, 680, 330
    steps = [("länger schauen", BLUE, -90), ("Interesse ↑", PURPLE, 30), ("mehr Edits", ORANGE, 150)]
    ctx.new_path(); ctx.arc(cx, cy, r, 0, 2 * math.pi); ctx.set_line_width(10); ctx.set_source_rgba(*LINE); ctx.stroke()
    # moving dot around the loop
    ang = -math.pi / 2 + t * 2.2
    dot(ctx, cx + r * math.cos(ang), cy + r * math.sin(ang), 22, PURPLE)
    times = [wt(shot, "hängen", 0.3), wt(shot, "interesse", 0.6), wt(shot, "mehr", 0.85)]
    for (lab, c, deg), t0 in zip(steps, times):
        a = math.radians(deg)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        k = pop(t, t0 - 0.2)
        chip(ctx, lab, x, y, 42, c, CARD, scale=k, alpha=min(1, k))
    # interest meter in the middle
    lvl = 0.2 + 0.7 * prog(t, times[0], times[2] + 0.3)
    rrect(ctx, cx - 40, cy - 120, 80, 240, 40); fill(ctx, CARD)
    rrect(ctx, cx - 40, cy + 120 - 240 * lvl, 80, 240 * lvl, 40); fill(ctx, PURPLE)
    text(ctx, FILM, cx, cy + 180, 30, PURPLE)

def s_signals(ctx, t, T, shot):
    bg(ctx, BG_BLUE)
    cx, cy = 540, 560
    dot(ctx, cx, cy, 120, CARD); ring(ctx, cx, cy, 120, BLUE, 8)
    person(ctx, cx, cy + 10, 1.4, BLUE)
    text(ctx, "Dein Profil", cx, cy + 165, 36, INK)
    sigs = [("Likes", PINK, 230, 330, wt(shot, "likes", 0.15)), ("Suchen", TEAL, 850, 330, wt(shot, "suchen", 0.3)),
            ("Wiedergabezeit", PURPLE, 260, 820, 0.0), ("Ähnliche Nutzer", ORANGE, 820, 820, wt(shot, "ähnlichem", 0.65))]
    for lab, c, x, y, t0 in sigs:
        k = prog(t, t0 - 0.15, t0 + 0.2)
        chip(ctx, lab, x, y, 38, c, CARD, alpha=k, scale=0.8 + 0.2 * k)
        if k > 0.5:
            for j in range(2):
                ph = ((t * 1.1 + j / 2) % 1.0)
                dot(ctx, x + (cx - x) * ph, y + (cy - y) * ph, 10, c, 1 - ph * 0.5)
    # prediction bar
    p = prog(t, T * 0.45, T * 0.95)
    card(ctx, 140, 980, 800, 200, 40)
    text(ctx, "Interessen-Prognose", 540, 1025, 34, MUTED, bold=False)
    rrect(ctx, 190, 1070, 700, 40, 20); fill(ctx, BG_GREY)
    rrect(ctx, 190, 1070, 700 * 0.87 * p, 40, 20); fill(ctx, PURPLE)
    text(ctx, f"{FILM}: {round(87 * p)} %", 540, 1145, 36, PURPLE)

def s_ads(ctx, t, T, shot):
    bg(ctx, BG_GREY)
    for i, (lab, x, c) in enumerate((("Empfehlungen", 290, BLUE), ("Werbung", 790, ORANGE))):
        hl = 1.0 if i == 1 else 0.55
        card(ctx, x - 230, 260, 460, 720, 40, alpha=1.0)
        rrect(ctx, x - 230, 260, 460, 110, 40); fill(ctx, c, hl)
        rrect(ctx, x - 230, 320, 460, 50, 0); fill(ctx, c, hl)
        text(ctx, lab, x, 315, 40, CARD)
        text(ctx, "dein Verhalten", x, 450, 34, INK, bold=False)
        text(ctx, "in der App", x, 495, 34, INK, bold=False)
        check(ctx, x, 590, 34, c)
    tp = wt(shot, "partnern", 0.45)
    k = prog(t, tp - 0.2, tp + 0.3)
    text(ctx, "+ Daten von Partnern", 790, 720, 32, INK, alpha=k)
    tt = wt(shot, "online", 0.75)
    kt = prog(t, tt - 0.4, tt + 0.2)
    ticket(ctx, 790 + (1 - kt) * 0, 860 - (1 - kt) * 300, 0.9, a=kt)
    chip(ctx, "je nach Einstellungen", 540, 1110, 40, CARD, INK, alpha=prog(t, wt(shot, "einstellungen", 0.3) - 0.1, wt(shot, "einstellungen", 0.3) + 0.3))

def s_freq_term(ctx, t, T, shot):
    bg(ctx, BG_LILAC)
    k = pop(t, 0.05, 0.45)
    ctx.save(); ctx.translate(540, 640); ctx.scale(max(k, 0.01), max(k, 0.01)); ctx.translate(-540, -640)
    card(ctx, 90, 330, 900, 620, 56)
    eye(ctx, 540, 520, 1.1, open_=0.4 + 0.6 * prog(t, 0.2, 0.6))
    for j in range(8):  # attention rays
        a = j * math.pi / 4 + t * 0.6
        r0, r1 = 170, 210 + 20 * math.sin(t * 4 + j)
        line(ctx, 540 + r0 * math.cos(a), 520 + r0 * math.sin(a) * 0.7, 540 + r1 * math.cos(a), 520 + r1 * math.sin(a) * 0.7, PURPLE, 8)
    text(ctx, "Frequenzillusion", 540, 760, 72, PURPLE)
    text(ctx, "auch: Baader-Meinhof-Phänomen", 540, 850, 34, MUTED, bold=False, alpha=prog(t, 0.6, 1.0))
    ctx.restore()

def s_frequency(ctx, t, T, shot):
    bg(ctx, BG_LILAC)
    kinds = [1, 0, 3, 4, 0, 2, 5, 1, 0, 3, 0, 4]
    f = prog(t, wt(shot, "beschäftigt", 0.3), wt(shot, "stärker", 0.85))
    for i, kd in enumerate(kinds):
        r, c = divmod(i, 3)
        x, y = 120 + c * 290, 220 + r * 228
        film = kd == 0
        thumb(ctx, x, y, 260, 220, kd, glow=f if film else 0, dim=0 if film else f)
    eye(ctx, 540, 1215, 0.7, open_=0.3 + 0.7 * prog(t, 0.1, 0.5))
    chip(ctx, "fällt dir mehr auf", 540, 160, 50, PURPLE, CARD, alpha=prog(t, 0.0, 0.4))

def verdict(ctx, t, T, right):
    bg(ctx, BG_GREY)
    lk = 1.0 if not right else 0.5
    card(ctx, 70, 330, 450, 640, 44, alpha=1.0)
    mic_icon(ctx, 295, 590, 1.0, mix(INK, MUTED, 0.6))
    cross(ctx, 295, 590, 120 * (pop(t, 0.1) if not right else 1), RED, a=lk)
    text(ctx, "Mikrofon", 295, 830, 42, INK, alpha=lk)
    text(ctx, "nicht nötig", 295, 885, 36, MUTED, bold=False, alpha=lk)
    rk = prog(t, 0.05, 0.4) if right else 0.35
    card(ctx, 560, 330, 450, 640, 44, alpha=1.0)
    eye(ctx, 785, 560, 0.9, a=max(0.35, rk), open_=0.3 + 0.7 * rk)
    for j in range(4):
        ph = ((t * 1.2 + j / 4) % 1.0)
        dot(ctx, 785 + 150 * math.cos(j * 1.6), 700 - 120 * ph, 9, PURPLE, (1 - ph) * rk)
    text(ctx, "Verhalten", 785, 830, 42, INK, alpha=max(0.35, rk))
    text(ctx, "reicht", 785, 885, 36, MUTED, bold=False, alpha=max(0.35, rk))
    if right:
        check(ctx, 785, 380, 50 * pop(t, 0.25), GREEN)

def s_verdict_mic(ctx, t, T, shot):
    verdict(ctx, t, T, False)

def s_verdict_watch(ctx, t, T, shot):
    verdict(ctx, t, T, True)

def s_question(ctx, t, T, shot):
    bg(ctx, BG_BLUE)
    sx, sy, sw, sh = phone(ctx, 540, 680, 520, 980)
    app_header(ctx, sx, sy, sw)
    bubbles = [("Ich hab nur dran gedacht …", 0.2), ("Bei mir war's ein Song!", 0.45), ("Werbung für Schuhe 👀", 0.7)]
    for i, (s, f) in enumerate(bubbles):
        k = pop(t, f * T)
        if k <= 0:
            continue
        y = sy + 260 + i * 170
        ctx.save(); ctx.translate(sx + 50, y); ctx.scale(k, k)
        w = min(sw - 100, text_w(ctx, s.replace(" 👀", ""), 32) + 60)
        rrect(ctx, 0, -45, w, 90, 30); fill(ctx, BG_GREY)
        text(ctx, s.replace(" 👀", ""), 30, 0, 32, INK, align="left", bold=False)
        ctx.restore()
        person(ctx, sx + 20, y - 0, 0.35, MUTED)
    dot(ctx, 540, sy + sh - 130, 60, PURPLE)
    text(ctx, "?", 540, sy + sh - 130, 80, CARD)

SCENES = {k[2:]: v for k, v in globals().items() if k.startswith("s_") and callable(v)}

def frames_of(shot):
    return round(shot["end"] * FPS) - round(shot["start"] * FPS)

def render_frame(shot, t, T):
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    SCENES[shot["visual"].split(":", 1)[1]](cairo.Context(surf), t, T, shot)
    return surf

def render(shot):
    n = frames_of(shot); T = n / FPS
    out = ROOT / "work" / "clips" / f"scene_{shot['id']:02d}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-frames:v", str(n), "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                           "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(bytes(render_frame(shot, i / FPS, T).get_data()))
    ff.stdin.close(); ff.wait()
    print(f"scene {shot['id']:>2}: {shot['visual']:<22} {n} frames ({T:.2f} s)")

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--still":
        shot = next(s for s in SHOTS if s["id"] == int(args[1]))
        T = frames_of(shot) / FPS
        dst = ROOT / "work" / f"still_{shot['id']:02d}.png"
        render_frame(shot, float(args[2]) * T, T).write_to_png(str(dst)); print(dst)
    else:
        for s in SHOTS:
            if s["visual"].startswith("anim:") and (not args or str(s["id"]) in args):
                render(s)
