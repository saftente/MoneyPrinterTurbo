#!/usr/bin/env bash
# Render the return-trip short with MoneyPrinterTurbo from the curated scene clips.
# Same proven setup as projects/dejavu-short: local clips in order, hard cuts, Gemini voiceover
# with align.py word timings, word-by-word pop subtitles, music under the voice, -14 LUFS master.
# New here: key words marked *like this* in script.txt are coloured (SUB_HIGHLIGHT).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
P="$ROOT/projects/return-trip-short"
CLIPS_DIR="${CLIPS_DIR:-$P/work/clips}"
TASK_ID="${TASK_ID:-a7e1c2d3-0000-4000-8000-000000000002}"
VOICE_FILE="${VOICE_FILE:-$P/work/voice/Algenib_padded.wav}"
cd "$ROOT"

# MoneyPrinterTurbo only accepts custom music from storage/bgm or resource/songs.
mkdir -p storage/bgm && cp "$P/assets/bgm_travel.mp3" storage/bgm/returntrip_bgm_travel.mp3

CLIPS=$(ls "$CLIPS_DIR"/scene_*.mp4 | sort | paste -sd, -)

export DEJAVU_SRT="$P/work/voice/subtitle_words.srt"
export SUB_HIGHLIGHT="#FFD23F"

# bgm-volume 0.29: this track is mastered 2.4 dB quieter than the Déjà-vu one (0.22 there), so the
# music sits at the same ~13 dB under the voice. Clips up to 8 s: longer scenes would be trimmed.
PYTHONPATH="$P/tools${PYTHONPATH:+:$PYTHONPATH}" python3 "$P/tools/run_cli.py" \
  --video-script "$(tr -d '*' < "$P/script.txt")" \
  --video-language de-DE \
  --video-source local --video-materials "$CLIPS" \
  --video-aspect 9:16 --video-fit-mode cover \
  --video-concat-mode sequential --video-transition-mode none \
  --video-clip-duration 8 \
  --custom-audio-file "$VOICE_FILE" \
  --bgm-type custom --bgm-file storage/bgm/returntrip_bgm_travel.mp3 --bgm-volume 0.29 \
  --subtitle-enabled --subtitle-display-mode word_by_word --subtitle-animation pop_spring \
  --font-name BeVietnamPro-Bold.ttf --font-size 118 \
  --text-fore-color "#FFFFFF" --stroke-color "#000000" --stroke-width 6 \
  --subtitle-position custom --custom-position 62 \
  --task-id "$TASK_ID" \
  --stop-at video

# Master to the -14 LUFS short-form platforms play at; two-pass loudnorm, video copied untouched.
OUT="$ROOT/storage/tasks/$TASK_ID"
STATS=$(ffmpeg -hide_banner -nostats -i "$OUT/final-1.mp4" \
  -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
val() { echo "$STATS" | python3 -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -v error -i "$OUT/final-1.mp4" -c:v copy -c:a aac -b:a 192k -ar 48000 -af \
  "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(val input_i):measured_TP=$(val input_tp):measured_LRA=$(val input_lra):measured_thresh=$(val input_thresh):offset=$(val target_offset):linear=true" \
  -movflags +faststart "$P/work/rueckweg_short.mp4"
echo "final: $P/work/rueckweg_short.mp4"
