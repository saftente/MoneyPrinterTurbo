"""Narrate script.txt with Google Gemini TTS, with a style direction against the robotic read.

  python3 projects/dream-short/tools/gemini_voice.py --list-models
  python3 projects/dream-short/tools/gemini_voice.py --voice Charon --sample   # hook only
  python3 projects/dream-short/tools/gemini_voice.py --voice Charon            # full script

The key comes from GEMINI_API_KEY, or is injected by the cloud proxy as a network secret
(header x-goog-api-key on generativelanguage.googleapis.com); the SDK then gets a dummy.
Output: work/voice/<voice>[_sample].wav, loudness-matched to the Déjà-vu voiceover so the music
balance in render.sh is the proven one. *Markers* in script.txt are for subtitles only.

Gemini's PCM sometimes ends (or starts) with ~0.2 s of full-scale garbage after the speech has
died away: white-noise-like, from one sample to the next, after a quiet gap. That burst was the
loud noise at the end of the first two videos. strip_bursts() removes it before anything else,
the end gets a short fade, and check_quiet_edges() refuses a voiceover whose edges are not quiet.
"""
import argparse
import os
import subprocess
import wave
from pathlib import Path

import numpy as np
import soundfile as sf

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "voice"
DEFAULT_MODEL = "gemini-3.8-flash-tts"
TARGET_LUFS = -19.7  # same voice level as the Déjà-vu short

# Gemini TTS speaks only the TRANSCRIPT section; the notes above it steer the delivery.
# (A plain instruction in the prompt gets read aloud, and the TTS models refuse system instructions.)
DIRECTION = """# AUDIO PROFILE: Erzähler eines deutschen Wissens-Kurzvideos für TikTok und YouTube Shorts
## THE SCENE: Spät in der Nacht. Er erzählt einer Freundin Anfang zwanzig leise und nah am Mikrofon
von einem unheimlichen Erlebnis, das fast jeder kennt, und davon, was die Forschung dazu sagt.
### DIRECTOR'S NOTES
Style: Ein echter Mensch, modern und natürlich. Am Anfang geheimnisvoll und gedämpft, beim
Erklären klar und neugierig, am Ende nüchtern und ehrlich. Kein Esoterik-Ton, kein
Nachrichtensprecher, keine Werbung. Betonung auf "Gänsehaut", "zufällig", "selektives Erinnern",
"probt die Zukunft", "jeder vierte", "kein Hinweis".
Pacing: Ruhig, aber nicht langsam; jedes Wort klar. Kurze Pause vor "Gänsehaut", vor "Aber",
vor "Echte Vorhersagen?" und vor der Schlussfrage.
Accent: Hochdeutsch.
#### TRANSCRIPT
"""


def client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY", "").strip() or "proxy-injected"
    return genai.Client(api_key=key, http_options=types.HttpOptions(api_version="v1beta"))


def _flatness(x: np.ndarray) -> float:
    x = x - x.mean()
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) + 1e-9
    return float(np.exp(np.mean(np.log(spec))) / np.mean(spec))


def strip_bursts(pcm: np.ndarray, sr: int) -> tuple[np.ndarray, list[str]]:
    """Cut a short noise burst that follows a quiet gap at the end (and, mirrored, at the start).

    Burst = at most 0.6 s long, spectrally flat (> 0.6; speech is ~0.3-0.4), preceded by at least
    0.15 s below -45 dBFS. A real last word is not flat, so it is never cut.
    """
    notes = []
    x = pcm.astype(np.float64) / 32768

    def one_side(x: np.ndarray, side: str) -> np.ndarray:
        f = int(0.01 * sr)
        n = len(x) // f
        db = 20 * np.log10(np.sqrt(np.mean(x[: n * f].reshape(n, f) ** 2, axis=1)) + 1e-12)
        quiet = db < -45
        # last quiet run of >= 0.15 s; everything after it is the candidate tail
        run_end = None
        k = n - 1
        while k >= 0:
            if quiet[k]:
                j = k
                while j >= 0 and quiet[j]:
                    j -= 1
                if k - j >= 15:
                    run_start, run_end = j + 1, k + 1
                    break
                k = j
            else:
                k -= 1
        if run_end is not None and 0 < n - run_end <= 60:
            seg = x[run_end * f:]
            flat = _flatness(seg)
            peak = 20 * np.log10(np.max(np.abs(seg)) + 1e-12)
            if flat > 0.6 and peak > -30:
                keep = (run_start + min(run_end - run_start, 20)) * f   # keep up to 0.2 s of natural decay
                notes.append(f"removed {len(x) - keep} samples ({(len(x) - keep) / sr * 1000:.0f} ms) of noise "
                             f"at the {side} (flatness {flat:.2f}, peak {peak:.1f} dBFS)")
                return x[:keep]
        return x

    x = one_side(x, "end")
    x = one_side(x[::-1], "start")[::-1]
    fade = min(len(x), int(0.04 * sr))          # 40 ms fade at both edges: no click either way
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    return x, notes


def check_quiet_edges(path: Path, edge: float = 0.15, limit_db: float = -30) -> None:
    """The end must be quiet (fade-out). The start begins right on the first word after trimming,
    so it is checked for noise (spectral flatness) rather than for level."""
    y, sr = sf.read(str(path))
    y = y if y.ndim == 1 else y.mean(1)
    pk = 20 * np.log10(np.max(np.abs(y[-int(edge * sr):])) + 1e-12)
    if pk > limit_db:
        raise SystemExit(f"{path}: end is not quiet (peak {pk:.1f} dBFS in the last {edge * 1000:.0f} ms)")
    head = y[: int(edge * sr)]
    if 20 * np.log10(np.max(np.abs(head)) + 1e-12) > -20 and _flatness(head) > 0.6:
        raise SystemExit(f"{path}: the first {edge * 1000:.0f} ms look like noise, not speech")


def synthesize(text: str, voice: str, model: str, dst: Path) -> None:
    with client() as c:
        r = c.models.generate_content(
            model=model,
            contents=DIRECTION + text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                ),
            ),
        )
    part = next(p for p in r.candidates[0].content.parts if p.inline_data)
    raw = dst.with_suffix(".raw.wav")
    with wave.open(str(raw), "wb") as w:  # Gemini returns 24 kHz 16-bit mono PCM
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(part.inline_data.data)
    process(raw, dst)


def process(raw: Path, dst: Path, keep_raw: bool = False) -> None:
    """raw Gemini PCM (as WAV) -> burst-free, trimmed, loudness-matched voiceover at dst."""
    with wave.open(str(raw)) as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), np.int16)
    clean, notes = strip_bursts(pcm, 24000)
    for note in notes:
        print(f"  {note}")
    cleaned = dst.with_suffix(".clean.wav")
    sf.write(str(cleaned), clean.astype(np.float32), 24000, subtype="PCM_24")
    # Trim leading/trailing silence, then match the old voiceover's loudness.
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(cleaned), "-af",
        "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
        # keep 0.25 s of the natural decay after the last word instead of ending mid-sound
        "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.25,areverse,"
        f"loudnorm=I={TARGET_LUFS}:TP=-2:LRA=11,"
        "areverse,afade=t=in:d=0.12,areverse",   # final 120 ms fade-out, whatever loudnorm did
        "-ar", "44100", str(dst),
    ], check=True)
    cleaned.unlink()
    if not (keep_raw or os.environ.get("KEEP_RAW")):
        raw.unlink()
    check_quiet_edges(dst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="Charon")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--sample", action="store_true", help="only the hook and the twist")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--from-raw", type=Path, help="reprocess a kept raw WAV (KEEP_RAW=1) without an API call")
    a = ap.parse_args()
    if a.list_models:
        with client() as c:
            for m in c.models.list():
                if "tts" in m.name:
                    print(m.name)
        return
    text = (ROOT / "script.txt").read_text(encoding="utf-8").strip().replace("*", "")
    if a.sample:
        text = " ".join(text.split()[:30])  # hook and everyday scene
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"{a.voice}{'_sample' if a.sample else ''}.wav"
    if a.from_raw:
        process(a.from_raw, dst, keep_raw=True)
    else:
        synthesize(text, a.voice, a.model, dst)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(dst)], capture_output=True, text=True).stdout.strip()
    # ~2.4 words/s is natural German narration; far longer means Gemini read the notes aloud.
    if float(dur) > len(text.split()) / 2.4 * 1.5:
        raise SystemExit(f"{dst}: {float(dur):.1f} s is too long for {len(text.split())} words, "
                         "the direction was probably spoken; check the prompt format")
    print(f"{dst} ({float(dur):.2f} s)")


if __name__ == "__main__":
    main()
