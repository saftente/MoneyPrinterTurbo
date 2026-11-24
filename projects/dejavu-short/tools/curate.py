"""Curate one Pixabay clip per scene of shotlist.json and cut it to the scene length.

Steps (run from the repository root):
  python3 projects/dejavu-short/tools/curate.py search   # candidates + contact sheets
  python3 projects/dejavu-short/tools/curate.py fetch    # download picks from picks.json
  python3 projects/dejavu-short/tools/curate.py cut      # 1080x1920 graded scene clips

The Pixabay key is read from the PIXABAY_API_KEY environment variable.
Work files go to projects/dejavu-short/work/ (ignored by git).
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
    params = {"key": _key(), "q": query, "video_type": "film", "per_page": 30, "safesearch": "true"}
    r = requests.get(f"https://pixabay.com/api/videos/?{urlencode(params)}", timeout=30)
    if r.status_code != 200:
        print(f"  ! {query!r}: HTTP {r.status_code} {r.text[:120]}")
        return []
    return r.json().get("hits", [])


def _rendition(hit: dict) -> dict:
    vids = hit.get("videos", {})
    # Prefer a rendition that is at least 1080 px on its short side, else the biggest.
    for name in ("large", "medium", "small"):
        v = vids.get(name) or {}
        if v.get("url") and min(v.get("width", 0), v.get("height", 0)) >= 1080:
            return v | {"name": name}
    best = max((vids.get(n) or {} for n in ("large", "medium", "small")), key=lambda v: v.get("width", 0) * v.get("height", 0))
    return best | {"name": "best"}


def search() -> None:
    WORK.mkdir(exist_ok=True)
    out: dict[str, list[dict]] = {}
    for shot in SHOTS:
        need = shot["end"] - shot["start"] + TAIL_PAD + 0.5
        seen, cands = set(), []
        for q in shot["queries"]:
            for h in _search(q):
                if h["id"] in seen or h.get("duration", 0) < need:
                    continue
                seen.add(h["id"])
                v = _rendition(h)
                cands.append({
                    "pixabay_id": h["id"], "query": q, "page": h.get("pageURL"), "user": h.get("user"),
                    "duration": h.get("duration"), "tags": h.get("tags"), "url": v.get("url"),
                    "width": v.get("width"), "height": v.get("height"),
                    "thumb": v.get("thumbnail") or (h.get("videos", {}).get("medium") or {}).get("thumbnail"),
                    "portrait": v.get("height", 0) > v.get("width", 0), "likes": h.get("likes", 0),
                })
        cands.sort(key=lambda c: (not c["portrait"], -c["likes"]))
        out[str(shot["id"])] = cands[:12]
        print(f"scene {shot['id']:>2}: {len(cands)} candidates")
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
            d.rectangle((x, y, x + 150, y + 14), fill="black")
            d.text((x + 3, y + 2), f"#{i} {'P' if c['portrait'] else 'L'} {c['duration']}s", fill="yellow", font=font)
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
        sid = str(shot["id"])
        c = cands[sid][picks[sid]["index"]]
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


def cut() -> None:
    picks = json.loads(PICKS.read_text(encoding="utf-8"))
    out = WORK / "clips"
    out.mkdir(parents=True, exist_ok=True)
    for shot in SHOTS:
        sid = str(shot["id"])
        p = picks[sid]
        # Frame-accurate lengths so the scene cuts never drift against the voiceover.
        dur = (round(shot["end"] * FPS) - round(shot["start"] * FPS)) / FPS
        speed = p.get("speed", 1.0)
        # Crop to 9:16 around a horizontal focus point (0..1), then a cool, slightly
        # desaturated grade with a soft vignette for one consistent mysterious look.
        fx = p.get("focus_x", 0.5)
        vf = (
            f"setpts=PTS/{speed},"
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920:(in_w-1080)*{fx}:(in_h-1920)/2,"
            "eq=saturation=0.82:contrast=1.06:brightness=-0.02,"
            "colorbalance=bs=0.05:ms=0.02:hs=-0.02,"
            "vignette=PI/5,fps=30,format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y", "-v", "error", "-ss", str(p.get("offset", 0.5)),
            "-i", str(WORK / "raw" / f"scene_{shot['id']:02d}.mp4"), "-t", f"{dur:.3f}",
            "-vf", vf, "-an", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
            str(out / f"scene_{shot['id']:02d}.mp4"),
        ]
        subprocess.run(cmd, check=True)
        print(f"scene {sid:>2}: {dur:.2f}s")


if __name__ == "__main__":
    {"search": search, "fetch": fetch, "cut": cut}[sys.argv[1]]()
