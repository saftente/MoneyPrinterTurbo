"""Turn the word-per-cue SRT from align.py into short word groups (2-3 words) for faster reading.

  python3 projects/mic-short/tools/group_subs.py

Reads work/voice/subtitle_words.srt and script.txt, writes work/voice/subtitle_groups.srt.
Rules: at most 3 words and 18 characters per group, each phrase split into as few and as evenly
long groups as possible (no dangling single words); a group ends after punctuation in the script;
highlighted (*marked*) words never share a group with plain words, so a group is either all yellow
or all white (MoneyPrinterTurbo draws one colour per cue). Each group stays on screen until the
next one starts (no flicker), unless the pause is longer than 0.4 s. The first group starts at
0.0 s so the very first frame already carries text.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_WORDS, MAX_CHARS, HOLD = 3, 18, 0.4


def parse(t: str) -> float:
    h, m, s, ms = map(int, re.findall(r"\d+", t))
    return h * 3600 + m * 60 + s + ms / 1000


def ts(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


cues = []
for block in (ROOT / "work/voice/subtitle_words.srt").read_text(encoding="utf-8").strip().split("\n\n"):
    lines = block.split("\n")
    a, b = lines[1].split(" --> ")
    cues.append((lines[2], parse(a), parse(b)))

# Script tokens in the same order, to know where punctuation ends a phrase.
tokens = [t for t in (ROOT / "script.txt").read_text(encoding="utf-8").split() if t.strip(".,:;!?\"'()–—")]
assert len(tokens) == len(cues), (len(tokens), len(cues))
ends_phrase = [bool(re.search(r"[.,:;!?]$", t)) for t in tokens]

def text_of(ws):
    return " ".join(w.strip("*") for w, _, _ in ws)


# A group should not end on a word that needs the next one (article, possessive, preposition).
GLUE = {"dein", "deine", "deinem", "deinen", "ein", "eine", "einem", "einen", "der", "die", "das", "den",
        "dem", "des", "mit", "in", "aus", "zu", "von", "welchen", "welche", "welcher", "mein", "sein"}


def best_split(ws):
    """Split ws into chunks of <= MAX_WORDS words and <= MAX_CHARS characters.

    Preference: fewest chunks ending on a GLUE word, then fewest chunks, then the most even lengths.
    Phrases are short (<= ~10 words), so all splits are tried.
    """
    from itertools import combinations
    n = len(ws)
    best = None
    for k in range(1, n + 1):
        for cuts in combinations(range(1, n), k - 1):
            edges = (0,) + cuts + (n,)
            chunks = [ws[edges[t]:edges[t + 1]] for t in range(k)]
            if any(len(c) > MAX_WORDS for c in chunks):
                continue
            lens = [len(text_of(c)) for c in chunks]
            over = sum(max(0, l - MAX_CHARS) for l in lens)
            glue = sum(1 for c in chunks[:-1] if c[-1][0].strip("*").lower() in GLUE)
            score = (over, glue, k, max(lens))
            if best is None or score < best[0]:
                best = (score, chunks)
    return best[1]


# Segments: runs of words inside one phrase that share the highlight state.
segments, cur = [], []
for i, (word, s_, e_) in enumerate(cues):
    if cur and word.startswith("*") != cur[-1][0].startswith("*"):
        segments.append(cur)
        cur = []
    cur.append((word, s_, e_))
    if ends_phrase[i]:
        segments.append(cur)
        cur = []
if cur:
    segments.append(cur)
groups = [g for seg in segments for g in best_split(seg)]

# Timing: a group shows from its first word until the next group starts (no flicker); after a pause
# longer than HOLD it ends 0.15 s after its last word. Every group stays at least MIN_SHOW on screen:
# a too-short group starts earlier, inside the pause before it, and if that is not enough the next
# group starts a little later. (Whisper sometimes squeezes a word to ~0.1 s after a pause.)
MIN_SHOW = 0.35
starts = [0.0 if k == 0 else g[0][1] for k, g in enumerate(groups)]
word_ends = [g[-1][2] for g in groups]
for k in range(1, len(groups)):
    nxt = starts[k + 1] if k + 1 < len(groups) else word_ends[k] + 0.6
    short = MIN_SHOW - (nxt - starts[k])
    if short > 0:
        room = starts[k] - (word_ends[k - 1] + 0.05)          # pause before this group
        move = max(0.0, min(short, room))
        starts[k] -= move
        short -= move
        if short > 0 and k + 1 < len(groups):
            starts[k + 1] += short
out = []
for k, g in enumerate(groups):
    if k + 1 < len(groups):
        nxt = starts[k + 1]
        end = nxt if nxt - word_ends[k] <= HOLD else word_ends[k] + 0.15
    else:
        end = word_ends[k] + 0.6
    end = max(end, starts[k] + MIN_SHOW) if k + 1 == len(groups) else end
    text = " ".join(w.strip("*") for w, _, _ in g)
    if g[0][0].startswith("*"):
        text = f"*{text}*"
    out.append(f"{k + 1}\n{ts(starts[k])} --> {ts(end)}\n{text}\n")
(ROOT / "work/voice/subtitle_groups.srt").write_text("\n".join(out), encoding="utf-8")
for line in out:
    print(line.split("\n")[1][3:], line.split("\n")[2])
