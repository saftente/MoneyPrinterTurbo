"""Accept a voice take only if Whisper hears the script word for word.

  python3 projects/mic-short/tools/verify_take.py <audio-or-video>            whole file
  python3 projects/mic-short/tools/verify_take.py <audio-or-video> --scenes   also scene by scene

--scenes cuts the file at the shotlist times (after align.py) and checks each scene's line on its own.
Over the whole file Whisper can "hear" a swallowed word from context ("dir" heard right overall,
"ihr" in isolation); scene by scene there is no such help. (exit 1 on any difference)
"""
import difflib, re, sys
from pathlib import Path
from faster_whisper import WhisperModel
ROOT = Path(__file__).resolve().parents[1]
m = WhisperModel(str(ROOT.parents[1] / "models/whisper-medium"), device="cpu", compute_type="int8")
norm = lambda x: re.sub(r"[^a-zäöüß0-9]", "", x.lower())
NUM = {"17000": "17000", "siebzehntausend": "17000", "zweitausendachtzehn": "2018",
       # spelling variants Whisper may write for the same spoken word (both in the Duden)
       "orangenfarbenen": "orangefarbenen"}
script = [NUM.get(norm(w), norm(w)) for w in (ROOT / "script.txt").read_text(encoding="utf-8").replace("*", "").split()]
def compare(path, words, edges_ok=False):
    """Differences between words and what Whisper hears. edges_ok: ignore words heard before the
    first or after the last expected word (they leak in from the neighbouring scene)."""
    segs, _ = m.transcribe(path, language="de", word_timestamps=True, beam_size=5)
    heard = [NUM.get(norm(w.word), norm(w.word)) for s in segs for w in s.words if norm(w.word)]
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=words, b=heard, autojunk=False).get_opcodes():
        if op == "equal" or "".join(words[i1:i2]) == "".join(heard[j1:j2]):
            continue
        if edges_ok and op == "insert" and (i1 == 0 or i1 == len(words)):
            continue
        out.append((words[i1:i2], heard[j1:j2]))
    return out

bad = compare(sys.argv[1], script)
print("whole file differences:", bad)
if "--scenes" in sys.argv:
    import json, subprocess, tempfile
    shots = json.loads((ROOT / "shotlist.json").read_text(encoding="utf-8"))
    for k, sh in enumerate(shots):
        # Very short scenes (< 1.5 s) are checked together with their neighbours: half a second of audio
        # alone is too little for Whisper ("öffnest TikTok" became "öffne das"). Still no whole-file context.
        group = shots[max(0, k - 1):k + 2] if sh["end"] - sh["start"] < 1.5 else [sh]
        words = [NUM.get(norm(w), norm(w)) for g in group for w in g["line"].split() if norm(w)]
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            # 0.15 s margin each side so cut-off word edges are not counted as errors
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(max(0, group[0]["start"] - 0.15)), "-to", str(group[-1]["end"] + 0.15),
                            "-i", sys.argv[1], "-ac", "1", "-ar", "16000", tmp.name], check=True)
            d = compare(tmp.name, words, edges_ok=True)
        if d:
            print(f"  scene {sh['id']:>2}: {d}")
            bad += d
sys.exit(1 if bad else 0)
