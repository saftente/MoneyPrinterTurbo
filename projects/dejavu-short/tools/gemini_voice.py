"""Narrate script.txt with Google Gemini TTS, with a style direction against the robotic read.

  python3 projects/dejavu-short/tools/gemini_voice.py --list-models
  python3 projects/dejavu-short/tools/gemini_voice.py --voice Charon --sample   # hook only
  python3 projects/dejavu-short/tools/gemini_voice.py --voice Charon            # full script

The key comes from GEMINI_API_KEY, or is injected by the cloud proxy as a network secret
(header x-goog-api-key on generativelanguage.googleapis.com); the SDK then gets a dummy.
Output: work/voice/<voice>[_sample].wav, loudness-matched to the old Edge voiceover so the
music balance in render.sh stays the same.
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
DEFAULT_MODEL = "gemini-3.8-flash-lite-tts"
TARGET_LUFS = -19.7  # assets/voiceover.mp3 (Edge) measured with ebur128

STYLE = (
    "Lies den folgenden deutschen Text als Erzähler eines spannenden Wissens-Kurzvideos vor. "
    "Klinge wie ein echter Mensch, der etwas Unheimliches und Faszinierendes erzählt: ruhig, "
    "nah am Mikrofon, leicht geheimnisvoll, mit natürlicher Betonung und kurzen Spannungspausen "
    "vor den Pointen. Nicht werblich, nicht übertrieben, kein Nachrichtensprecher. Zügiges, "
    "aber nicht gehetztes Tempo. Sprich ausschließlich den Text, ohne etwas hinzuzufügen:\n\n"
)


def client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY", "").strip() or "proxy-injected"
    return genai.Client(api_key=key, http_options=types.HttpOptions(api_version="v1beta"))


def synthesize(text: str, voice: str, model: str, dst: Path) -> None:
    with client() as c:
        r = c.models.generate_content(
            model=model,
            contents=STYLE + text,
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
    text = (ROOT / "script.txt").read_text(encoding="utf-8").strip()
    if a.sample:
        text = ("Dein Gehirn lügt dich manchmal an – und du spürst es. Ein Raum, in dem du nie warst. "
                "Und trotzdem: Genau das hast du schon mal erlebt. Jetzt wird es seltsam: "
                "Im Déjà-vu glauben viele zu wissen, was gleich passiert.")
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"{a.voice}{'_sample' if a.sample else ''}.wav"
    synthesize(text, a.voice, a.model, dst)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(dst)], capture_output=True, text=True).stdout.strip()
    print(f"{dst} ({float(dur):.2f} s)")


if __name__ == "__main__":
    main()
