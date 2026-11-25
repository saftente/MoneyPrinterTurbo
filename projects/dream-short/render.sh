#!/usr/bin/env bash
# Render the dream short with MoneyPrinterTurbo from the curated scene clips.
# Same proven setup as projects/dejavu-short: local clips in order, hard cuts, Gemini voiceover
# with align.py word timings, word-by-word pop subtitles, music under the voice, -14 LUFS master.
# New here: key words marked *like this* in script.txt are coloured (SUB_HIGHLIGHT).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
P="$ROOT/projects/dream-short"
CLIPS_DIR="${CLIPS_DIR:-$P/work/clips}"
TASK_ID="${TASK_ID:-b8f2d3e4-0000-4000-8000-000000000003}"
VOICE_FILE="${VOICE_FILE:-$P/work/voice/Algenib_padded.wav}"
cd "$ROOT"

# MoneyPrinterTurbo only accepts custom music from storage/bgm or resource/songs.
mkdir -p storage/bgm && cp "$P/assets/bgm_mystery.mp3" storage/bgm/dream_bgm_mystery.mp3

CLIPS=$(ls "$CLIPS_DIR"/scene_*.mp4 | sort | paste -sd, -)

export DEJAVU_SRT="$P/work/voice/subtitle_words.srt"
export SUB_HIGHLIGHT="#FFD23F"

# Same music generator and level as the Déjà-vu short (bgm-volume 0.22, ~13 dB under the voice).
# Clips up to 8 s: longer scenes would be trimmed.
PYTHONPATH="$P/tools${PYTHONPATH:+:$PYTHONPATH}" python3 "$P/tools/run_cli.py" \
  --video-script "$(tr -d '*' < "$P/script.txt")" \
  --video-language de-DE \
  --video-source local --video-materials "$CLIPS" \
  --video-aspect 9:16 --video-fit-mode cover \
  --video-concat-mode sequential --video-transition-mode none \
  --video-clip-duration 8 \
  --custom-audio-file "$VOICE_FILE" \
  --bgm-type custom --bgm-file storage/bgm/dream_bgm_mystery.mp3 --bgm-volume 0.22 \
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
# The voiceover is already burst-free and faded (gemini_voice.py); the whole mix additionally
# fades out over the last 1.5 s so the video never ends on a hard edge. alimiter at -2 dBFS keeps
# the AAC-decoded peaks below -1 dBFS (loudnorm alone targets -1.5 dBTP; AAC adds a little overshoot).
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/final-1.mp4")
FADE_ST=$(python3 -c "print(max(0, $DUR - 1.5))")
ffmpeg -y -v error -i "$OUT/final-1.mp4" -c:v copy -c:a aac -b:a 192k -ar 48000 -af \
  "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=$(val input_i):measured_TP=$(val input_tp):measured_LRA=$(val input_lra):measured_thresh=$(val input_thresh):offset=$(val target_offset):linear=true,alimiter=limit=0.79:attack=5:release=50:level=0,afade=t=out:st=$FADE_ST:d=1.5" \
  -movflags +faststart "$P/work/traum_short.mp4"

# Refuse the result if the last 3 seconds hold a burst, a jump or a hard end.
python3 "$P/tools/check_tail.py" "$P/work/traum_short.mp4" 3
echo "final: $P/work/traum_short.mp4"
