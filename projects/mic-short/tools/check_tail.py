"""Fail a render whose last seconds contain a noise burst or a hard end.

  python3 projects/mic-short/tools/check_tail.py work/traum_short.mp4 [seconds=3]

Checks the decoded audio of the final MP4 in 20 ms windows over the last N seconds:
- no window above -1 dBFS peak (decoded; above that AAC playback clips),
- no sudden jump: a window more than 18 dB louder (RMS) than the median of the 0.5 s before it,
  while it is louder than -30 dBFS (a burst out of quiet, which is what the old videos had),
- the very end is quiet: the last 0.25 s peak below -30 dBFS (the fade-out did its job).
Prints the window table on failure and exits 1.
"""
import subprocess
import sys

import numpy as np

path = sys.argv[1]
last = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
# Decode every channel as is: an "-ac 1" downmix sums identical channels at 0.707 each (+3 dB) and
# reports peaks that are not in the file. Per window we take the louder channel.
ch = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channels",
                         "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip())
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ar", "48000", "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
x = np.abs(np.frombuffer(raw, np.float32).reshape(-1, ch)).max(axis=1)
sr = 48000
dur = len(x) / sr
seg = x[-int(last * sr):]
w = int(0.02 * sr)
n = len(seg) // w
frames = seg[: n * w].reshape(n, w)
pk = 20 * np.log10(np.max(np.abs(frames), axis=1) + 1e-9)
rms = 20 * np.log10(np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-9)
problems = []
for i in range(n):
    t = dur - last + i * 0.02
    if pk[i] > -1:
        problems.append(f"{t:.2f}s peak {pk[i]:.1f} dBFS")
    if i >= 25:
        base = np.median(rms[i - 25:i])
        if rms[i] > -30 and rms[i] - base > 18:
            problems.append(f"{t:.2f}s jump {rms[i] - base:+.1f} dB over the previous 0.5 s (rms {rms[i]:.1f})")
end_peak = 20 * np.log10(np.max(np.abs(x[-int(0.25 * sr):])) + 1e-9)
if end_peak > -30:
    problems.append(f"last 0.25 s not quiet (peak {end_peak:.1f} dBFS)")
print(f"{path}: {dur:.2f} s; last {last:.0f} s: max peak {pk.max():.1f} dBFS, end peak {end_peak:.1f} dBFS")
if problems:
    print("TAIL CHECK FAILED:\n  " + "\n  ".join(problems))
    for i in range(0, n, 5):
        print(f"  {dur - last + i * 0.02:6.2f}s  peak {pk[i]:6.1f}  rms {rms[i]:6.1f}")
    sys.exit(1)
print("tail check passed: no burst, no jump, quiet end")
