"""Replace single flawed sentences of a voiceover with a fresh Gemini read, instead of a whole new take.

  python3 projects/mic-short/tools/patch_voice.py work/voice/Algenib.wav 1 7 9
      -> re-reads sentences 1, 7 and 9 (1-based, as split from script.txt) in ONE request,
         splices them into the take at the speech pauses, writes work/voice/Algenib.wav (backup: *.prev.wav)
  python3 projects/mic-short/tools/patch_voice.py --list        # numbered sentences

Long reads (~190 words) almost always contain one small slip or an improvised extra line somewhere;
a full retake costs a request each time (free tier: 10 per day and model) and brings new slips.
Cut points lie in the pauses around a sentence (between the neighbouring words), with 15 ms crossfades;
the patch is processed exactly like a take (burst removal, same loudness target), so levels match.
Run align.py and verify_take.py --scenes afterwards as usual.
"""
import difflib
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_voice as gv  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
norm = lambda x: re.sub(r"[^a-zäöüß0-9]", "", x.lower())


def sentences():
    text = (ROOT / "script.txt").read_text(encoding="utf-8").replace("*", "").strip()
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]


def words_with_times(model, path):
    segs, _ = model.transcribe(str(path), language="de", word_timestamps=True, beam_size=5)
    return [(norm(w.word), w.start, w.end) for s in segs for w in s.words if norm(w.word)]


def locate(heard, sent_words, start_hint=0):
    """Index range [i, j) in `heard` that matches sent_words best, searching from start_hint."""
    best = (0.0, None)
    n = len(sent_words)
    for i in range(start_hint, len(heard)):
        for j in (i + n - 1, i + n, i + n + 1):
            if j > len(heard) or j <= i:
                continue
            r = difflib.SequenceMatcher(a=sent_words, b=[h[0] for h in heard[i:j]], autojunk=False).ratio()
            if r > best[0]:
                best = (r, (i, j))
        if best[0] > 0.95:
            break
    return best


def main():
    if sys.argv[1] == "--list":
        for k, s in enumerate(sentences(), 1):
            print(f"{k:>2}: {s}")
        return
    base_path = Path(sys.argv[1]).resolve()
    ids = [int(x) for x in sys.argv[2:] if x.isdigit()]
    sents = sentences()
    patch_text = "\n\n".join(sents[i - 1] for i in ids)
    raw = base_path.with_name("patch.raw.wav")
    patch = base_path.with_name("patch.wav")
    reuse = "--reuse" in sys.argv   # splice again from the last patch.wav, no new request
    print("re-reading:", " | ".join(sents[i - 1] for i in ids))
    # one request with only these sentences (same voice and direction as the take)
    gv_text = patch_text
    from google.genai import types
    if reuse:
        main_splice(base_path, patch, ids, sents)
        return
    with gv.client() as c:
        r = c.models.generate_content(
            model=gv.DEFAULT_MODEL, contents=gv.DIRECTION + gv_text,
            config=types.GenerateContentConfig(response_modalities=["AUDIO"], speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Algenib")))))
    part = next(p for p in r.candidates[0].content.parts if p.inline_data)
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(part.inline_data.data)
    gv.process(raw, patch, keep_raw=True)
    main_splice(base_path, patch, ids, sents)


def main_splice(base_path, patch, ids, sents):
    model = WhisperModel(str(ROOT.parents[1] / "models/whisper-medium"), device="cpu", compute_type="int8")
    hb, hp = words_with_times(model, base_path), words_with_times(model, patch)
    y, sr = sf.read(str(base_path)); p, _ = sf.read(str(patch))
    pieces, cursor, hint_b, hint_p = [], 0, 0, 0
    fade = int(0.015 * sr)
    for i in ids:
        sw = [norm(w) for w in sents[i - 1].split() if norm(w)]
        rb, span_b = locate(hb, sw, hint_b)
        rp, span_p = locate(hp, sw, hint_p)
        if not span_b or not span_p or rp < 0.95:
            sys.exit(f"sentence {i}: could not locate cleanly (base {rb:.2f}, patch {rp:.2f}); nothing written")
        bi, bj = span_b; pi, pj = span_p
        # base cut points: middle of the pauses before/after the sentence
        b0 = (hb[bi - 1][2] + hb[bi][1]) / 2 if bi > 0 else 0.0
        b1 = (hb[bj - 1][2] + hb[bj][1]) / 2 if bj < len(hb) else len(y) / sr
        # patch segment: the sentence with a little air
        # generous lead-in (soft onsets like the 'N' of 'Neuere' start before Whisper's word start),
        # but never reach back into the previous sentence of the patch
        prev_end = hp[pi - 1][2] + 0.03 if pi > 0 else 0.0
        p0 = max(prev_end, hp[pi][1] - 0.18); p1 = min(len(p) / sr, hp[pj - 1][2] + 0.15)
        seg = p[int(p0 * sr):int(p1 * sr)].copy()
        seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
        # keep the base's pause lengths: fill the rest of the gap with silence
        gap = int((b1 - b0) * sr) - len(seg)
        pre = max(0, gap // 2) if bi > 0 else 0
        a = y[cursor:int(b0 * sr)].copy()
        if len(a) > fade:
            a[-fade:] *= np.linspace(1, 0, fade)
        pieces += [a, np.zeros(pre), seg, np.zeros(max(0, gap - pre))]
        cursor = int(b1 * sr)
        tail = y[cursor:cursor + fade]
        if len(tail):
            y[cursor:cursor + len(tail)] *= np.linspace(0, 1, len(tail))
        print(f"sentence {i}: base {b0:.2f}-{b1:.2f} s replaced by patch {p0:.2f}-{p1:.2f} s (match {rp:.2f})")
        hint_b, hint_p = bj, pj
    pieces.append(y[cursor:])
    out = np.concatenate(pieces)
    shutil.copy(base_path, base_path.with_suffix(".prev.wav"))
    sf.write(str(base_path), out, sr)
    gv.check_quiet_edges(base_path)
    print(f"{base_path}: {len(out) / sr:.2f} s")


if __name__ == "__main__":
    main()
