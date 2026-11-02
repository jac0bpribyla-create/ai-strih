"""Technická kontrola hotového videa (před odevzdáním, u každého renderu).

Použití: $PY kontrola.py video.mp4 [--prechody 2.64,8.92,…] [--pauza 0.25]
  $PY = scripts/py (python s numpy)

Vypíše:
  hlasitost   integrovaná LUFS a špička (cíl −14 LUFS, špička pod −1,5 dBTP)
  střihy      časy z detekce scén (ffmpeg select='gt(scene,0.18)')
  problik     dva střihy ≤ 1 snímek od sebe mimo přechody = 1snímkový problik (chyba renderu nebo B-rollu)
  jas         průměrný jas Y každého záběru: nad ~165 přesvětlené (bílé pozadí), pod ~60 tmavé
  pauzy       ticho delší než --pauza (výchozí 0,25 s) – mimo předěly scén nesmí být
Kašel, nádech, technika v pozadí, oči na třetině a text přes obličej skript nepozná → kontrolovat ručně (viz kontroly.md).
"""
import argparse
import json
import re
import subprocess

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--prechody", default="")
ap.add_argument("--pauza", type=float, default=0.25)
o = ap.parse_args()
tr = [float(x) for x in o.prechody.split(",") if x]
near = lambda t: any(T - 0.2 <= t <= T + 0.3 for T in tr)

info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=r_frame_rate,width,height,codec_type",
                                  "-of", "json", o.video], capture_output=True, text=True).stdout)
dur = float(info["format"]["duration"])
v = next(s for s in info["streams"] if s["codec_type"] == "video")
fps = eval(v["r_frame_rate"])
print(f"{o.video}: {v['width']}×{v['height']}, {fps:g} fps, {dur:.2f} s")

m = subprocess.run(["ffmpeg", "-hide_banner", "-i", o.video, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
lufs = re.findall(r"I:\s+(-?[0-9.]+) LUFS", m)
pk = re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", m)
print(f"hlasitost: {lufs[-1] if lufs else '?'} LUFS, špička {pk[-1] if pk else '?'} dBFS")

sc = subprocess.run(["ffmpeg", "-hide_banner", "-i", o.video, "-vf", "select='gt(scene,0.18)',showinfo", "-an", "-f", "null", "-"],
                    capture_output=True, text=True).stderr
cuts = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", sc)]
print("střihy:", " ".join(f"{c:g}" for c in cuts))
flash = [(a, b) for a, b in zip(cuts, cuts[1:]) if b - a <= 1.01 / fps and not (near(a) and near(b))]
print("problik (2 střihy ≤ 1 snímek):", flash or "žádný")

edges = [0.0] + cuts + [dur]
print("jas záběrů (Y 0–255):")
for a, b in zip(edges, edges[1:]):
    if b - a < 0.12:
        continue
    r = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{a + 0.04:.2f}", "-t", f"{b - a - 0.08:.2f}", "-i", o.video, "-vf",
                        "fps=5,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    y = [float(x) for x in re.findall(r"YAVG=([0-9.]+)", r)]
    if y:
        flag = "  ← přesvětlené" if np.mean(y) > 165 else ("  ← tmavé" if np.mean(y) < 60 else "")
        print(f"  {a:6.2f}–{b:6.2f}  {np.mean(y):5.1f}{flag}")

x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", o.video, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                 capture_output=True).stdout, np.float32)
db = 20 * np.log10(np.array([np.sqrt(np.mean(x[i:i + 400] ** 2) + 1e-12) for i in range(0, len(x) - 400, 160)]))
thr = np.percentile(db, 85) - 30
gaps, s = [], None
for i, q in enumerate(db < thr):
    if q and s is None:
        s = i
    if not q and s is not None:
        if (i - s) * 0.01 >= o.pauza and s > 0:
            gaps.append((round(s * 0.01, 2), round((i - s) * 0.01, 2)))
        s = None
print(f"pauzy ≥ {o.pauza} s (začátek, délka):", gaps or "žádné")
