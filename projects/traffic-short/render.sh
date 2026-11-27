#!/usr/bin/env bash
# Render the traffic short with MoneyPrinterTurbo from the curated scene clips.
# Same proven setup as projects/dejavu-short: local clips in order, hard cuts, Gemini voiceover
# with align.py word timings, word-by-word pop subtitles, music under the voice, -14 LUFS master.
# New here: key words marked *like this* in script.txt are coloured (SUB_HIGHLIGHT).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
P="$ROOT/projects/traffic-short"
CLIPS_DIR="${CLIPS_DIR:-$P/work/clips}"
TASK_ID="${TASK_ID:-e1c5a6b7-0000-4000-8000-000000000006}"
VOICE_FILE="${VOICE_FILE:-$P/work/voice/Algenib_padded.wav}"
cd "$ROOT"

# MoneyPrinterTurbo only accepts custom music from storage/bgm or resource/songs.
# Music: a gentle cut around 2 kHz leaves room for consonants, and the level is fixed and low
# (bgm-volume 0.13, ~17 dB under the voice). With the earlier ~10 dB, the plucked notes masked words
# such as "Ort"; sidechain ducking fixed that but made the bed pump, a steady lower level does not.
mkdir -p storage/bgm
ffmpeg -y -v error -i "$P/assets/bgm_groove.mp3" -af "equalizer=f=2000:t=q:w=1:g=-4" \
  -b:a 192k storage/bgm/traffic_bgm.mp3

# One frame-exact file instead of 14 clips: MoviePy reads clip lengths rounded to 0.01 s
# (37 frames = 1.2333 s -> 1.23 s), and MoneyPrinterTurbo re-cuts every clip to that length, which
# dropped about one frame per two clips (cuts up to 8 frames early by the end). Splitting one file
# into 8 s pieces (240 frames) has no rounding loss.
ls "$CLIPS_DIR"/scene_*.mp4 | sort | sed "s/^/file '/; s/$/'/" > "$P/work/concat.txt"
ffmpeg -y -v error -f concat -safe 0 -i "$P/work/concat.txt" -c:v libx264 -crf 16 -preset medium \
  -pix_fmt yuv420p -r 30 -an "$P/work/scenes_all.mp4"
WANT=$(for f in "$CLIPS_DIR"/scene_*.mp4; do ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=nb_read_frames -of csv=p=0 "$f"; done | paste -sd+ - | bc)
GOT=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$P/work/scenes_all.mp4")
[ "$WANT" = "$GOT" ] || { echo "concat lost frames: $GOT of $WANT"; exit 1; }
CLIPS="$P/work/scenes_all.mp4"

# Short word groups (tools/group_subs.py) instead of single words; one cue per group.
export DEJAVU_SRT="$P/work/voice/subtitle_groups.srt"
export SUB_HIGHLIGHT="#FFD23F"

# Clips up to 8 s: longer scenes would be trimmed.
PYTHONPATH="$P/tools${PYTHONPATH:+:$PYTHONPATH}" python3 "$P/tools/run_cli.py" \
  --video-script "$(tr -d '*' < "$P/script.txt")" \
  --video-language de-DE \
  --video-source local --video-materials "$CLIPS" \
  --video-aspect 9:16 --video-fit-mode cover \
  --video-concat-mode sequential --video-transition-mode none \
  --video-clip-duration 8 \
  --custom-audio-file "$VOICE_FILE" \
  --bgm-type custom --bgm-file storage/bgm/traffic_bgm.mp3 --bgm-volume 0.13 \
  --subtitle-enabled --subtitle-display-mode word_by_word --subtitle-animation pop_spring \
  --font-name BeVietnamPro-Bold.ttf --font-size 88 \
  --text-fore-color "#FFFFFF" --stroke-color "#000000" --stroke-width 6 \
  --subtitle-position custom --custom-position 74 \
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
  -movflags +faststart "$P/work/stau_short.mp4"

# Length guard for this version: 60 s.
python3 -c "import sys; d=float(sys.argv[1]); sys.exit(f'video is {d:.2f} s, over the 60 s limit') if d > 60 else print(f'length {d:.2f} s (limit 60 s)')" \
  "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$P/work/stau_short.mp4")"

# Refuse the result if the last 3 seconds hold a burst, a jump or a hard end.
python3 "$P/tools/check_tail.py" "$P/work/stau_short.mp4" 3
echo "final: $P/work/stau_short.mp4"
