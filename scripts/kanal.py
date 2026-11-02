"""Videa z YouTube kanálu (styl, který chceš napodobit): výpis a stažení vybraných ukázek (yt-dlp).

Výpis (nic nestahuje, jen metadata):
  python3 kanal.py seznam https://www.youtube.com/@kanal [--shorts] [--pocet 60]
  → tabulka id | délka | zhlédnutí | datum | název, seřazená podle zhlédnutí, + uloží seznam.json do aktuální složky
Stažení (POZOR: stahuje soubory – předtím uživateli říct kolik videí, odkud a přibližně kolik MB, a počkat na souhlas):
  python3 kanal.py stahni <cílová složka> ID1 ID2 … [--max 720]   (místo ID jde i celý odkaz na video nebo short)
  → <složka>/<id>.mp4 (výška max 720 px stačí na rozbor stylu; titulky .vtt, pokud existují)
"""
import json
import re
import subprocess
import sys
from pathlib import Path


def video_id(x):
    """ID videa z odkazu (watch?v=, youtu.be/, shorts/) nebo samotné ID."""
    m = re.search(r"(?:v=|youtu\.be/|shorts/|live/)([\w-]{11})", x)
    return m.group(1) if m else x


def seznam(url, shorts=False, pocet=60):
    url = url.rstrip("/")
    if not url.endswith(("/videos", "/shorts", "/streams")) and "playlist" not in url and "watch" not in url:
        url += "/shorts" if shorts else "/videos"
    js = json.loads(subprocess.run(["yt-dlp", "--flat-playlist", "-J", "--playlist-end", str(pocet), url],
                                   capture_output=True, text=True, check=True).stdout)
    rows = [{"id": e.get("id"), "nazev": e.get("title"), "delka": e.get("duration"), "zhlednuti": e.get("view_count"),
             "datum": e.get("upload_date") or e.get("release_timestamp")} for e in js.get("entries", [])]
    rows.sort(key=lambda r: -(r["zhlednuti"] or 0))
    Path("seznam.json").write_text(json.dumps({"kanal": js.get("channel") or js.get("title"), "url": url, "videa": rows},
                                              ensure_ascii=False, indent=1))
    print(f"{js.get('channel') or js.get('title')}: {len(rows)} videí ({url})")
    for r in rows:
        d = r["delka"] or 0
        print(f"{r['id']:12} {int(d) // 60:3d}:{int(d) % 60:02d} {r['zhlednuti'] or 0:>10,} {r['datum'] or '':10} {(r['nazev'] or '')[:70]}")


def stahni(dst, ids, maxh=720):
    Path(dst).mkdir(parents=True, exist_ok=True)
    for i in map(video_id, ids):
        out = Path(dst) / f"{i}.mp4"
        if out.exists() and out.stat().st_size > 0:
            continue
        r = subprocess.run(["yt-dlp", "-q", "--no-warnings", "-f", f"bv*[height<={maxh}][ext=mp4]+ba[ext=m4a]/b[height<={maxh}]/b",
                            "--merge-output-format", "mp4", "--write-subs", "--write-auto-subs", "--sub-langs", "cs,en", "--sub-format", "vtt",
                            "-o", str(Path(dst) / f"{i}.%(ext)s"), f"https://www.youtube.com/watch?v={i}"], capture_output=True, text=True)
        print(("ok    " if out.exists() else "CHYBA ") + i + (f" {out.stat().st_size / 1e6:.0f} MB" if out.exists() else f" {r.stderr[-200:]}"))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("seznam", "stahni"):
        print(__doc__)
        sys.exit(1)
    if a[0] == "seznam":
        n = int(a[a.index("--pocet") + 1]) if "--pocet" in a else 60
        seznam(a[1], shorts="--shorts" in a, pocet=n)
    else:
        maxh = int(a[a.index("--max") + 1]) if "--max" in a else 720
        ids = [x for x in a[2:] if not x.startswith("--") and x != str(maxh)]
        stahni(a[1], ids, maxh)
