#!/usr/bin/env bash
# Render the Déjà-vu short with MoneyPrinterTurbo from the curated scene clips.
# Run from anywhere; expects projects/dejavu-short/work/clips/scene_XX.mp4.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
P="$ROOT/projects/dejavu-short"
CLIPS_DIR="${CLIPS_DIR:-$P/work/clips}"
TASK_ID="${TASK_ID:-d3a0b0e1-0000-4000-8000-000000000001}"
cd "$ROOT"

# MoneyPrinterTurbo only accepts custom music from storage/bgm or resource/songs.
mkdir -p storage/bgm && cp "$P/assets/bgm_mystery.mp3" storage/bgm/dejavu_bgm_mystery.mp3

CLIPS=$(ls "$CLIPS_DIR"/scene_*.mp4 | sort | paste -sd, -)

# tools/ holds a sitecustomize that makes edge-tts trust the cloud proxy CA.
PYTHONPATH="$P/tools${PYTHONPATH:+:$PYTHONPATH}" python3 cli.py \
  --video-script "$(cat "$P/script.txt")" \
  --video-language de-DE \
  --video-source local --video-materials "$CLIPS" \
  --video-aspect 9:16 --video-fit-mode cover \
  --video-concat-mode sequential --video-transition-mode none \
  --video-clip-duration 4 \
  --voice-name de-DE-FlorianMultilingualNeural-Male --voice-rate 1.14 --voice-volume 1.0 \
  --bgm-type custom --bgm-file storage/bgm/dejavu_bgm_mystery.mp3 --bgm-volume 0.22 \
  --subtitle-enabled --subtitle-display-mode word_by_word --subtitle-animation pop_spring \
  --font-name BeVietnamPro-Bold.ttf --font-size 118 \
  --text-fore-color "#FFFFFF" --stroke-color "#000000" --stroke-width 6 \
  --subtitle-position custom --custom-position 62 \
  --task-id "$TASK_ID" \
  --stop-at video
