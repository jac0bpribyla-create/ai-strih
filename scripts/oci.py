"""Výška očí v záběru → výřez s očima na horní třetině (pravidlo třetin).

Použití: uv run --with "opencv-python-headless==4.10.0.84" --with "numpy<2.3" python oci.py [--zdroje složka …] KLIP@od-do[@zoom] …
KLIP = cesta k souboru, nebo název klipu (C0001) hledaný ve složkách --zdroje (výchozí: zdroje z projekt.json v aktuální složce).
(OpenCV 4.11+ nemá CascadeClassifier v cv2 → verze 4.10 napevno.)
Na plochém S-Log záznamu a s brýlemi detekce občas selže (hlásí málo snímků / nesmyslné x) → změřit ručně z náhledu. Vypíše výšku očí (0–1 od horního okraje zdrojového záběru na výšku), vodorovný střed
obličeje a doporučené cy/cx pro daný zoom, aby oči byly ve výšce 1/3 výsledného obrazu: cy = oči + 1/(6·zoom).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

import json as _json

args = sys.argv[1:]
SRC = []
if args and args[0] == "--zdroje":
    args = args[1:]
    while args and "@" not in args[0]:
        SRC.append(Path(args.pop(0)))
elif Path("projekt.json").exists():
    SRC = [Path(z) for z in _json.loads(Path("projekt.json").read_text()).get("zdroje", [])]
face_c = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
eye_c = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")


def find(clip):
    if Path(clip).exists():
        return Path(clip)
    for p in SRC:
        for ext in (".MP4", ".mp4", ".MOV", ".mov"):
            if (p / f"{clip}{ext}").exists():
                return p / f"{clip}{ext}"
    raise FileNotFoundError(clip)


def frame(clip, t, out):
    src = find(clip)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1", "-vf", "scale=-2:1920", str(out)], check=True)
    return cv2.imread(str(out), cv2.IMREAD_GRAYSCALE)


def eyes(img):
    H, W = img.shape
    g = cv2.equalizeHist(img)
    faces = face_c.detectMultiScale(g, 1.1, 6, minSize=(W // 12, W // 12))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    roi = g[y:y + h // 2 + h // 8, x:x + w]
    ee = eye_c.detectMultiScale(roi, 1.1, 5, minSize=(w // 10, w // 10))
    ey = y + (np.mean([e[1] + e[3] / 2 for e in ee]) if len(ee) >= 1 else 0.42 * h)
    return ey / H, (x + w / 2) / W, h / H


tmp = Path(tempfile.mkdtemp())
for arg in args:
    parts = arg.split("@")
    clip, (a, b) = parts[0], map(float, parts[1].split("-"))
    z = float(parts[2]) if len(parts) > 2 else 1.0
    res = [r for t in np.linspace(a, b, 5) if (r := eyes(frame(clip, t, tmp / "f.png")))]
    if not res:
        print(f"{clip} {a}-{b}: obličej nenalezen")
        continue
    ey = float(np.median([r[0] for r in res])); ex = float(np.median([r[1] for r in res])); fh = float(np.median([r[2] for r in res]))
    lo, hi = 0.5 / z, 1 - 0.5 / z
    cy = min(max(ey + 1 / (6 * z), lo), hi)
    eye_out = (ey - cy) * z + 0.5
    cx = min(max(ex, lo), hi)
    print(f"{clip} {a:.1f}-{b:.1f} zoom {z}: oči {ey:.3f}, střed obličeje x {ex:.3f}, obličej {fh:.3f} výšky "
          f"→ cy {cy:.3f}, cx {cx:.3f} (oči ve výsledku {eye_out:.3f}, cíl 0.333) [{len(res)}/5 snímků]")
