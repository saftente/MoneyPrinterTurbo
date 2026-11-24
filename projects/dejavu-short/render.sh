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

# Voice: a prepared voiceover (VOICE_FILE, e.g. work/voice/Charon.wav from tools/gemini_voice.py)
# with its word timings from tools/align.py, or else the Edge voice timed by Edge itself.
VOICE_FILE="${VOICE_FILE:-}"
if [ -n "$VOICE_FILE" ]; then
  VOICE_ARGS=(--custom-audio-file "$VOICE_FILE")
  export DEJAVU_SRT="$P/work/voice/subtitle_words.srt"
else
  VOICE_ARGS=(--voice-name de-DE-FlorianMultilingualNeural-Male --voice-rate 1.14 --voice-volume 1.0)
fi

# tools/ holds a sitecustomize that makes edge-tts trust the cloud proxy CA; run_cli.py
# hands MoneyPrinterTurbo the prepared subtitles when DEJAVU_SRT is set.
PYTHONPATH="$P/tools${PYTHONPATH:+:$PYTHONPATH}" python3 "$P/tools/run_cli.py" \
  --video-script "$(cat "$P/script.txt")" \
  --video-language de-DE \
  --video-source local --video-materials "$CLIPS" \
  --video-aspect 9:16 --video-fit-mode cover \
  --video-concat-mode sequential --video-transition-mode none \
  --video-clip-duration 4 \
  "${VOICE_ARGS[@]}" \
  --bgm-type custom --bgm-file storage/bgm/dejavu_bgm_mystery.mp3 --bgm-volume 0.22 \
  --subtitle-enabled --subtitle-display-mode word_by_word --subtitle-animation pop_spring \
  --font-name BeVietnamPro-Bold.ttf --font-size 118 \
  --text-fore-color "#FFFFFF" --stroke-color "#000000" --stroke-width 6 \
  --subtitle-position custom --custom-position 62 \
  --task-id "$TASK_ID" \
  --stop-at video

# Master the mix to the -14 LUFS short-form platforms play at (TikTok, Shorts, Reels);
# two-pass loudnorm keeps the voice/music balance and copies the video untouched.
OUT="$ROOT/storage/tasks/$TASK_ID"
STATS=$(ffmpeg -hide_banner -nostats -i "$OUT/final-1.mp4" \
  -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
val() { echo "$STATS" | python3 -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -v error -i "$OUT/final-1.mp4" -c:v copy -c:a aac -b:a 192k -ar 48000 -af \
  "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(val input_i):measured_TP=$(val input_tp):measured_LRA=$(val input_lra):measured_thresh=$(val input_thresh):offset=$(val target_offset):linear=true" \
  -movflags +faststart "$P/work/dejavu_short.mp4"
echo "final: $P/work/dejavu_short.mp4"
