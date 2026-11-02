"""Začátky slov podle hlasitosti (Whisper dává začátky o 0,1–0,5 s vedle) + podezření na nádech/kašel.

Použití: $PY onsety.py <video nebo zvuk> <od> <do> [--prepis prepis.json]
  dipy  = lokální minima obálky (10 ms) uvnitř řeči → hranice slov/slabik, sem nasazovat B-roll a střihy
  šum   = úseky s vysokou spektrální plochostí (sykavky, nádech, kašel). Kašel/odkašlání = hlasitý šumový náraz
          ≥ 0,15 s s pomalým doznívaním PŘED první samohláskou věty; nádech = tichý šum (−45 až −55 dB) před větou.
  --prepis: JSON ze prepis_slova.py (segments → words w/s/e) pro porovnání se slovy z Whisperu.
"""
import argparse
import json
import subprocess

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("a", type=float)
ap.add_argument("b", type=float)
ap.add_argument("--prepis")
o = ap.parse_args()
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(o.a), "-t", str(o.b - o.a), "-i", o.src, "-ac", "1", "-ar", "16000",
                      "-f", "f32le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.float32)
hop, n = 160, 320
db, flat = [], []
for i in range(0, len(x) - n, hop):
    fr = x[i:i + n]
    db.append(20 * np.log10(np.sqrt(np.mean(fr ** 2)) + 1e-9))
    sp = np.abs(np.fft.rfft(fr * np.hanning(n))) + 1e-9
    flat.append(np.exp(np.mean(np.log(sp))) / np.mean(sp))
db, flat = np.array(db), np.array(flat)
sm = np.convolve(db, np.ones(5) / 5, mode="same")
peak = np.percentile(sm, 90)
dips = []
for i in range(3, len(sm) - 3):
    if sm[i] == sm[i - 3:i + 4].min() and sm[i] < peak - 14:
        t = o.a + i * 0.01
        if not dips or t - dips[-1][0] > 0.08:
            dips.append((round(t, 2), round(float(sm[i] - peak), 1)))
print("dipy (čas, dB pod špičkou):", dips)
noise, run = [], []
for i, (d, f) in enumerate(zip(db, flat)):
    if d > peak - 30 and f > 0.35:
        run.append(i)
    else:
        if len(run) >= 8:
            noise.append((round(o.a + run[0] * 0.01, 2), round(len(run) * 0.01, 2), round(float(db[run].max() - peak), 1)))
        run = []
print("šumové úseky ≥ 80 ms (začátek, délka, dB pod špičkou):", noise)
if o.prepis:
    d = json.load(open(o.prepis))
    print("whisper:", [(w["w"], w["s"]) for s in d["segments"] for w in s["words"] if o.a - 0.5 <= w["s"] <= o.b])
