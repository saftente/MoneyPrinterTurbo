"""Narrate script.txt with Google Gemini TTS, with a style direction against the robotic read.

  python3 projects/return-trip-short/tools/gemini_voice.py --list-models
  python3 projects/return-trip-short/tools/gemini_voice.py --voice Charon --sample   # hook only
  python3 projects/return-trip-short/tools/gemini_voice.py --voice Charon            # full script

The key comes from GEMINI_API_KEY, or is injected by the cloud proxy as a network secret
(header x-goog-api-key on generativelanguage.googleapis.com); the SDK then gets a dummy.
Output: work/voice/<voice>[_sample].wav, loudness-matched to the Déjà-vu voiceover so the music
balance in render.sh is the proven one. *Markers* in script.txt are for subtitles only.
"""
import argparse
import os
import subprocess
import wave
from pathlib import Path

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "voice"
DEFAULT_MODEL = "gemini-3.8-flash-tts"
TARGET_LUFS = -19.7  # same voice level as the Déjà-vu short

# Gemini TTS speaks only the TRANSCRIPT section; the notes above it steer the delivery.
# (A plain instruction in the prompt gets read aloud, and the TTS models refuse system instructions.)
DIRECTION = """# AUDIO PROFILE: Erzähler eines deutschen Wissens-Kurzvideos für TikTok und YouTube Shorts
## THE SCENE: Er erzählt einem Freund Anfang zwanzig von einem Aha-Moment, den jeder von Autofahrten kennt.
Die Stimme ist nah am Mikrofon, locker und wach.
### DIRECTOR'S NOTES
Style: Ein echter Mensch, modern und natürlich, neugierig und ein bisschen verschmitzt. Kein
Nachrichtensprecher, keine Werbung, nicht übertrieben. Natürliche Betonung, die Hervorhebung liegt
auf den Schlüsselwörtern ("kürzer", "Return Trip Effect", "Erwartungen", "Rückblick").
Pacing: Lebendig, aber entspannt und nicht schnell; jedes Wort klar artikuliert, besonders
"erst in deiner Erinnerung". Kurze Pausen nach "endlos." und vor "Und zurück?", eine kleine
Spannungspause vor "Und jetzt kommt's" und vor "Erst im Rückblick".
Accent: Hochdeutsch. "Return Trip Effect" englisch aussprechen.
#### TRANSCRIPT
"""


def client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY", "").strip() or "proxy-injected"
    return genai.Client(api_key=key, http_options=types.HttpOptions(api_version="v1beta"))


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
    # Trim leading/trailing silence, then match the old voiceover's loudness.
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af",
        "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
        "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
        f"loudnorm=I={TARGET_LUFS}:TP=-2:LRA=11",
        "-ar", "44100", str(dst),
    ], check=True)
    raw.unlink()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="Charon")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--sample", action="store_true", help="only the hook and the twist")
    ap.add_argument("--list-models", action="store_true")
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
