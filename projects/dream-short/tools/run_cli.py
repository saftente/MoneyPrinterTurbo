"""Run MoneyPrinterTurbo's cli.py with prepared word-level subtitles and highlighted key words.

- DEJAVU_SRT: a word-per-cue SRT from tools/align.py replaces MoneyPrinterTurbo's own Whisper step.
- SUB_HIGHLIGHT: #RRGGBB colour for words written as *word* in that SRT (the markers come from
  script.txt). MoneyPrinterTurbo has one subtitle colour only, so the text-clip factory is wrapped:
  marked words lose their asterisks and get the highlight colour; everything else is unchanged.
All arguments are passed through to cli.py; MoneyPrinterTurbo's own code is not modified.
"""
import os
import runpy
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
os.chdir(REPO)

srt = os.environ.get("DEJAVU_SRT")
if srt:
    from app.config import config
    from app.services import subtitle

    config.app["subtitle_provider"] = "whisper"

    def create(audio_file, subtitle_file="", word_level=False, log_details=True):
        dst = subtitle_file or f"{audio_file}.srt"
        shutil.copyfile(srt, dst)
        return dst

    subtitle.create = create

highlight = os.environ.get("SUB_HIGHLIGHT")
if highlight:
    from app.services.utils import subtitle_shaping

    _text_clip = subtitle_shaping.text_clip

    def text_clip(native, **kwargs):
        text = kwargs.get("text") or ""
        if "*" in text:
            kwargs["text"] = text.replace("*", "")
            if kwargs.get("color") is not None:  # the measuring call passes no colour
                kwargs["color"] = highlight
        return _text_clip(native, **kwargs)

    subtitle_shaping.text_clip = text_clip

sys.argv = ["cli.py", *sys.argv[1:]]
runpy.run_path(str(REPO / "cli.py"), run_name="__main__")
