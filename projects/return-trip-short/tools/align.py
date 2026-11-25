"""Time a voiceover word by word and move the scene cuts onto its sentences.

  python3 projects/return-trip-short/tools/align.py work/voice/Algenib_padded.wav

Whisper (models/whisper-medium) transcribes with word timestamps; the transcript is matched
to script.txt so the subtitles keep the script's exact spelling (Whisper writes "Deja-vu",
the script "Déjà-vu"). *Markers* from script.txt stay on the subtitle words (run_cli.py colours
them). Writes:
  work/voice/subtitle_words.srt   one cue per word, the format MoneyPrinterTurbo's Edge path makes
  shotlist.json                   start/end of every scene moved to its first word
"""
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
FPS = 30


def norm(w: str) -> str:
    w = unicodedata.normalize("NFKD", w.lower())
    return re.sub(r"[^a-z0-9ß]", "", "".join(c for c in w if not unicodedata.combining(c)))


def words(text: str) -> list[str]:
    # Same tokens as the Edge subtitles: punctuation dropped, inner hyphens kept, "–" skipped.
    out = []
    for tok in text.split():
        tok = tok.strip(".,:;!?\"'()–—")
        if tok:
            out.append(tok)
    return out


def ts(t: float) -> str:
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main(audio: str) -> None:
    script = (ROOT / "script.txt").read_text(encoding="utf-8").strip()
    target = words(script)
    model = WhisperModel(str(REPO / "models" / "whisper-medium"), device="cpu", compute_type="int8")
    segs, _ = model.transcribe(audio, language="de", word_timestamps=True, beam_size=5,
                               initial_prompt=script.replace("*", ""), condition_on_previous_text=False)
    heard = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words if norm(w.word)]

    # Match transcript to script; Whisper may split or merge words ("Déjà-vu" -> "Déjà", "-vu").
    a = [norm(w) for w in target]
    b = [norm(h[0]) for h in heard]
    times: list[tuple[float, float] | None] = [None] * len(target)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                times[i1 + k] = (heard[j1 + k][1], heard[j1 + k][2])
        elif op == "replace" and j2 > j1:
            # Spread the heard span evenly over the script words it stands for.
            t0, t1 = heard[j1][1], heard[j2 - 1][2]
            n = i2 - i1
            for k in range(n):
                times[i1 + k] = (t0 + (t1 - t0) * k / n, t0 + (t1 - t0) * (k + 1) / n)
    missing = [target[i] for i, t in enumerate(times) if t is None]
    # Interpolate anything Whisper dropped between its neighbours.
    for i, t in enumerate(times):
        if t is None:
            prev = next((times[j][1] for j in range(i - 1, -1, -1) if times[j]), 0.0)
            nxt = next((times[j][0] for j in range(i + 1, len(times)) if times[j]), prev + 0.3)
            times[i] = (prev, max(prev + 0.05, nxt))
    # Whisper sometimes stacks several words on one instant; spread such clumps up to the next word.
    i = 0
    while i < len(times):
        j = i
        while j + 1 < len(times) and times[j + 1][0] - times[i][0] < 0.04 * (j + 1 - i):
            j += 1
        if j > i:
            t0 = times[i][0]
            t1 = times[j + 1][0] if j + 1 < len(times) else max(times[j][1], t0 + 0.3 * (j - i + 1))
            n = j - i + 1
            for k in range(n):
                times[i + k] = (t0 + (t1 - t0) * k / n, t0 + (t1 - t0) * (k + 1) / n - 0.01)
        i = j + 1
    # Whisper's word starts run ~0.15 s late against TTS word boundaries; lead slightly.
    LEAD = 0.1
    times = [(max(0.0, s - LEAD), max(0.0, s - LEAD) + max(0.05, e - s)) for s, e in times]
    matched = sum(1 for op in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks() for _ in range(op.size))
    print(f"words: script {len(target)}, heard {len(heard)}, exact matches {matched}, interpolated {len(missing)} {missing}")

    out = ROOT / "work" / "voice"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "subtitle_words.srt", "w", encoding="utf-8") as f:
        for i, (w, (s, e)) in enumerate(zip(target, times), 1):
            f.write(f"{i}\n{ts(s)} --> {ts(e)}\n{w}\n\n")

    # Scene cuts: a scene starts with the first word of its line; cut a little before the word,
    # halfway into the pause, so the picture changes as the sentence begins.
    shots = json.loads((ROOT / "shotlist.json").read_text(encoding="utf-8"))
    pos = 0
    starts = []
    for shot in shots:
        first = words(shot["line"])[0]
        while norm(target[pos]) != norm(first):  # script words may carry *highlight* markers
            pos += 1
        s = times[pos][0]
        prev_end = times[pos - 1][1] if pos else 0.0
        starts.append(0.0 if pos == 0 else round(max(prev_end, s - 0.12, (prev_end + s) / 2), 2))
        pos += len(words(shot["line"]))
    # The last scene runs to the end of the audio (pad the voiceover so the question can hang).
    import subprocess
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                  audio], capture_output=True, text=True).stdout) + 0.2
    # (+0.2 s: MoneyPrinterTurbo loops clips to fill if the pictures end even a frame before the audio)
    for k, shot in enumerate(shots):
        shot["start"] = starts[k]
        shot["end"] = round(starts[k + 1] if k + 1 < len(shots) else total, 2)
    (ROOT / "shotlist.json").write_text(
        "[\n" + ",\n".join("  " + json.dumps(s, ensure_ascii=False) for s in shots) + "\n]\n", encoding="utf-8")
    for s in shots:
        print(f"scene {s['id']:>2}: {s['start']:6.2f}-{s['end']:6.2f}  {s['line'][:50]}")


if __name__ == "__main__":
    main(sys.argv[1])
