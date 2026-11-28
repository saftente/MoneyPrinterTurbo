"""Curate one Pixabay clip per scene of shotlist.json and cut it to the scene length.

Steps (run from the repository root):
  python3 projects/mic-short/tools/curate.py search   # candidates + contact sheets
  python3 projects/mic-short/tools/curate.py fetch    # download picks from picks.json
  python3 projects/mic-short/tools/curate.py cut      # 1080x1920 graded scene clips

The Pixabay key is read from the PIXABAY_API_KEY environment variable.
Work files go to projects/mic-short/work/ (ignored by git).
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
SHOTS = json.loads((ROOT / "shotlist.json").read_text(encoding="utf-8"))
PICKS = ROOT / "picks.json"
CANDS = WORK / "candidates.json"
TAIL_PAD = 0.0
FPS = 30


def _key() -> str:
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        sys.exit("PIXABAY_API_KEY is not set")
    return key


def _search(query: str) -> list[dict]:
    params = {"key": _key(), "q": query, "video_type": "film", "per_page": 100, "safesearch": "true"}
    r = requests.get(f"https://pixabay.com/api/videos/?{urlencode(params)}", timeout=30)
    if r.status_code != 200:
        print(f"  ! {query!r}: HTTP {r.status_code} {r.text[:120]}")
        return []
    return r.json().get("hits", [])


def _stem(w: str) -> str:
    return w.lower().strip().rstrip("s")


def _relevant(query: str, tags: str) -> bool:
    # Pixabay ORs the words of a query; keep only hits whose tags contain every word.
    tokens = {_stem(t) for t in tags.replace(",", " ").split()}
    return all(_stem(w) in tokens for w in query.split())


def _rendition(hit: dict) -> dict:
    vids = hit.get("videos", {})
    # Prefer a rendition that is at least 1080 px on its short side, else the biggest.
    for name in ("large", "medium", "small"):
        v = vids.get(name) or {}
        if v.get("url") and min(v.get("width", 0), v.get("height", 0)) >= 1080:
            return v | {"name": name}
    best = max((vids.get(n) or {} for n in ("large", "medium", "small")), key=lambda v: v.get("width", 0) * v.get("height", 0))
    return best | {"name": "best"}


def _sharpness(c: dict) -> float:
    """Source pixels per output pixel after the 9:16 cover crop (>=1 means no upscaling)."""
    w, h = c["width"] or 1, c["height"] or 1
    return min(w / 1080, h / 1920) if w / h <= 1080 / 1920 else h / 1920


USED_BEFORE = set()  # Pixabay ids used in earlier projects: never reuse footage
for _c in ROOT.parent.glob("*/credits.json"):
    if _c.parent != ROOT:
        USED_BEFORE |= {e["pixabay_id"] for e in json.loads(_c.read_text(encoding="utf-8"))}


def _stock(shot: dict) -> bool:
    return not shot.get("visual", "").startswith("anim:")


def search(only: list[str] | None = None) -> None:
    """Search all scenes, or only the given scene ids (merged into candidates.json)."""
    WORK.mkdir(exist_ok=True)
    out: dict[str, list[dict]] = json.loads(CANDS.read_text(encoding="utf-8")) if only and CANDS.exists() else {}
    for shot in SHOTS:
        if (only and str(shot["id"]) not in only) or not _stock(shot):
            continue
        need = shot["end"] - shot["start"] + TAIL_PAD + 0.5
        seen, cands = set(), []
        for qi, q in enumerate(shot["queries"]):
            for rank, h in enumerate(_search(q)):
                if h["id"] in seen or h["id"] in USED_BEFORE or h.get("duration", 0) < need or not _relevant(q, h.get("tags", "")):
                    continue
                seen.add(h["id"])
                v = _rendition(h)
                c = {
                    "pixabay_id": h["id"], "query": q, "page": h.get("pageURL"), "user": h.get("user"),
                    "duration": h.get("duration"), "tags": h.get("tags"), "url": v.get("url"),
                    "width": v.get("width"), "height": v.get("height"),
                    "thumb": v.get("thumbnail") or (h.get("videos", {}).get("medium") or {}).get("thumbnail"),
                    "portrait": v.get("height", 0) > v.get("width", 0), "likes": h.get("likes", 0),
                }
                if _sharpness(c) < 0.55:  # 720p and smaller look mushy at 1080x1920
                    continue
                c["sharp"] = round(_sharpness(c), 2)
                # Earlier queries are the better fit; within one, Pixabay's popularity rank.
                c["score"] = min(c["sharp"], 1.0) * 2 - qi * 0.25 - rank * 0.02
                cands.append(c)
        cands.sort(key=lambda c: -c["score"])
        out[str(shot["id"])] = cands[:16]
        print(f"scene {shot['id']:>2}: {len(cands)} relevant candidates")
        _sheet(shot, out[str(shot["id"])])
    CANDS.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


def _sheet(shot: dict, cands: list[dict]) -> None:
    tw, th, cols = 320, 180, 4
    rows = max(1, (len(cands) + cols - 1) // cols)
    sheet = Image.new("RGB", (tw * cols, th * rows + 30), "black")
    d = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    d.text((6, 6), f"scene {shot['id']}: {shot['line']}", fill="white", font=font)
    for i, c in enumerate(cands):
        try:
            img = Image.open(requests.get(c["thumb"], stream=True, timeout=30).raw).convert("RGB")
            img.thumbnail((tw, th))
            x, y = (i % cols) * tw, 30 + (i // cols) * th
            sheet.paste(img, (x, y))
            d.rectangle((x, y, x + 200, y + 14), fill="black")
            d.text((x + 3, y + 2), f"#{i} {c['width']}x{c['height']} {c['duration']}s {c['query']}", fill="yellow", font=font)
        except Exception as e:  # thumbnail failures should not stop the run
            print(f"  thumb {i} failed: {e}")
    sheet.save(WORK / f"sheet_{shot['id']:02d}.jpg", quality=85)


def fetch() -> None:
    cands = json.loads(CANDS.read_text(encoding="utf-8"))
    picks = json.loads(PICKS.read_text(encoding="utf-8"))
    raw = WORK / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    credits = []
    for shot in SHOTS:
        if not _stock(shot):
            continue
        sid = str(shot["id"])
        p = picks[sid]
        if p.get("still"):  # a Pixabay photo instead of a clip, credited from its own record
            credits.append({"scene": shot["id"], "pixabay_id": p["still"]["pixabay_id"], "user": p["still"]["user"],
                            "page": p["still"]["page"], "type": "photo"})
            print(f"scene {sid:>2}: {p['still']['page']} (photo)")
            continue
        # "from": use a candidate found for another scene (same footage fits two lines)
        c = cands[str(p.get("from", sid))][p["index"]]
        dst = raw / f"scene_{shot['id']:02d}.mp4"
        if not dst.exists():
            with requests.get(c["url"], stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(dst, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
        credits.append({"scene": shot["id"], "pixabay_id": c["pixabay_id"], "user": c["user"], "page": c["page"]})
        print(f"scene {sid:>2}: {c['page']}")
    (ROOT / "credits.json").write_text(json.dumps(credits, indent=1, ensure_ascii=False), encoding="utf-8")


def cut(only: list[str] | None = None) -> None:
    """Cut all scenes, or only the given scene ids."""
    picks = json.loads(PICKS.read_text(encoding="utf-8"))
    out = WORK / "clips"
    out.mkdir(parents=True, exist_ok=True)
    for shot in SHOTS:
        sid = str(shot["id"])
        if (only and sid not in only) or not _stock(shot):
            continue
        p = picks[sid]
        # Frame-accurate lengths so the scene cuts never drift against the voiceover.
        dur = (round(shot["end"] * FPS) - round(shot["start"] * FPS)) / FPS
        speed = p.get("speed", 1.0)
        # Crop to 9:16 around a horizontal focus point (0..1), then a cool, slightly
        # desaturated grade with a soft vignette for one consistent mysterious look.
        fx = p.get("focus_x", 0.5)
        # Optional slow push-in for static shots: zoom 0.1 ends 10 % tighter. zoompan runs
        # on a 2x upscale so the sub-pixel steps stay smooth instead of jittering.
        zoom = p.get("zoom", 0)
        frames = round(dur * FPS)
        push = (
            f"scale=2160:3840:flags=bicubic,zoompan=z='1+{zoom}*on/{frames}':"
            f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps={FPS},"
            if zoom else ""
        )
        pre = f"crop={p['pre_crop']}," if p.get("pre_crop") else ""  # e.g. "iw:ih*0.78:0:0" (keep the top)
        vf = (
            f"{pre}setpts=PTS/{speed},"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920:(in_w-1080)*{fx}:(in_h-1920)/2,fps={FPS},{push}"
            # bright, clean look for this project (no vignette or desaturation)
            "eq=saturation=1.05:contrast=1.03:brightness=0.03,format=yuv420p"
        )
        if p.get("still"):  # photo: loop it as a 30 fps input, the push-in gives it motion
            src = ["-loop", "1", "-framerate", str(FPS), "-i", str(ROOT / p["still"]["file"])]
        else:
            src = ["-ss", str(p.get("offset", 0.5)), "-i", str(WORK / "raw" / f"scene_{shot['id']:02d}.mp4")]
        cmd = [
            "ffmpeg", "-y", "-v", "error", *src, "-t", f"{dur:.3f}",
            "-vf", vf, "-an", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
            str(out / f"scene_{shot['id']:02d}.mp4"),
        ]
        subprocess.run(cmd, check=True)
        print(f"scene {sid:>2}: {dur:.2f}s")


if __name__ == "__main__":
    if sys.argv[1] == "search":
        search(sys.argv[2:] or None)
    elif sys.argv[1] == "cut":
        cut(sys.argv[2:] or None)
    else:
        fetch()
