"""Original underscore for the earworm short: light, forward-moving, no vocals, subtle under the voice.

A minor-ish pad (Am9 - Fmaj7 - Cadd9 - G6, one chord per bar at 96 bpm), soft kick, a clock-like
tick on the off-beats (the video is about felt time), plucked arpeggios, and two risers that land
on the trick ("Der Trick dagegen") and on the closing question, each with a soft low impact.
No dips or sudden level changes: the groove fades in over 2 s and stays even.
Length and riser timing follow shotlist.json.

  python3 projects/earworm-short/tools/make_bgm.py work/bgm.wav
"""
import json
import sys
from pathlib import Path

import numpy as np
import scipy.signal as sg
import soundfile as sf

SHOTS = json.loads((Path(__file__).resolve().parents[1] / "shotlist.json").read_text(encoding="utf-8"))
TWIST = next(s["start"] for s in SHOTS if s["line"].startswith("Der Trick"))
QUESTION = next(s["start"] for s in SHOTS if s["line"].startswith("Welchen Song"))

sr = 44100
dur = round(SHOTS[-1]["end"] + 1.5, 2)
n = int(sr * dur)
rng = np.random.default_rng(11)
bpm = 108
beat = 60 / bpm
bar = 4 * beat


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def place(out, sig, t0, gain=1.0, pan=0.5):
    s = int(t0 * sr)
    if s >= n or s < 0:
        return
    sig = sig[: n - s]
    out[s : s + len(sig), 0] += sig * gain * (1 - pan)
    out[s : s + len(sig), 1] += sig * gain * pan


out = np.zeros((n, 2))

# Pad: detuned saws through a low-pass, one chord per bar, slow attack.
chords = [[57, 60, 64, 67, 71], [53, 57, 60, 64, 69], [48, 55, 60, 62, 64], [55, 59, 62, 64, 67]]
pad = np.zeros((n, 2))
for i in range(int(np.ceil(dur / bar)) + 1):
    L = int((bar + 1.5) * sr)
    tt = np.arange(L) / sr
    e = np.minimum(1, tt / 0.8) * np.exp(-np.maximum(0, tt - bar) * 3)
    for m in chords[i % 4]:
        for det, pan in ((-0.08, 0.3), (0.08, 0.7)):
            f = midi(m) * 2 ** (det / 12)
            w = sg.sawtooth(2 * np.pi * f * tt + rng.uniform(0, 6.28))
            place(pad, w * e, i * bar, 0.018, pan)
b, a = sg.butter(2, 1100 / (sr / 2))
out += sg.lfilter(b, a, pad, axis=0)

# Soft kick on every beat from 1.5 s, quieter under the explanation, fuller after the twist.
start_groove = 0.2
for k in np.arange(start_groove, dur - 1.0, beat):
    L = int(0.3 * sr)
    tt = np.arange(L) / sr
    f = 48 + 70 * np.exp(-tt * 30)
    w = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt * 14)
    g = 0.22 * min(1, 0.4 + (k - start_groove) / 2 * 0.6)
    place(out, w, k, g)

# Clock tick on the off-beats: short band-passed clicks, alternating left/right.
b, a = sg.butter(2, [3000 / (sr / 2), 9000 / (sr / 2)], btype="band")
for j, k in enumerate(np.arange(start_groove + beat / 2, dur - 1.0, beat)):
    L = int(0.03 * sr)
    click = sg.lfilter(b, a, rng.standard_normal(L)) * np.exp(-np.arange(L) / sr * 180)
    place(out, click, k, 0.05, 0.3 if j % 2 else 0.7)

# Plucked arpeggio (Karplus-Strong-ish decay), 8th notes, sparse: two bars on, one bar off.
for i in range(int(dur / bar)):
    if i % 3 == 2:
        continue
    notes = [chords[i % 4][j] + 12 for j in (0, 2, 4, 2, 1, 3, 4, 3)]
    for j, m in enumerate(notes):
        L = int(0.9 * sr)
        tt = np.arange(L) / sr
        f = midi(m)
        w = (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 5)
        place(out, w, i * bar + j * beat / 2, 0.022, 0.35 + 0.3 * (j % 2))

# Risers into the twist and the question, each landing on a soft low impact.
b, a = sg.butter(2, [600 / (sr / 2), 6000 / (sr / 2)], btype="band")
for end, length in ((TWIST, 2.4), (QUESTION, 1.8)):
    L = int(length * sr)
    tt = np.arange(L) / sr
    w = sg.lfilter(b, a, rng.standard_normal(L)) * (tt / tt[-1]) ** 2.5
    place(out, w, end - length, 0.06)
    Li = int(1.6 * sr)
    ti = np.arange(Li) / sr
    boom = np.sin(2 * np.pi * (40 + 30 * np.exp(-ti * 8)) * ti) * np.exp(-ti * 3)
    place(out, boom, end, 0.1)

# Light stereo room, fades, normalize.
rev = np.zeros_like(out)
for d, g in ((0.029, 0.4), (0.043, 0.35), (0.061, 0.3)):
    D = int(d * sr)
    y = np.copy(out)
    for _ in range(4):
        y[D:] += g * y[:-D] * 0.5
    rev += y
out = out * 0.75 + rev * 0.1
fe = np.ones(n)
fe[: int(0.3 * sr)] = np.linspace(0, 1, int(0.3 * sr))
fe[-int(2.5 * sr):] = np.linspace(1, 0, int(2.5 * sr))
out *= fe[:, None]
out /= np.max(np.abs(out))
out *= 0.7
sf.write(sys.argv[1], out.astype(np.float32), sr)
print(f"{sys.argv[1]}: {dur:.2f} s, risers end at {TWIST:.2f} s and {QUESTION:.2f} s")
