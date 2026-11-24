"""Run MoneyPrinterTurbo's cli.py with a prepared word-level subtitle file.

MoneyPrinterTurbo only times subtitles itself (Edge word boundaries or Whisper). For a
custom voiceover we already have exact script-spelled word timings from tools/align.py, so
when DEJAVU_SRT is set the Whisper subtitle step is replaced by copying that file.
All arguments are passed through to cli.py.
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

sys.argv = ["cli.py", *sys.argv[1:]]
runpy.run_path(str(REPO / "cli.py"), run_name="__main__")
