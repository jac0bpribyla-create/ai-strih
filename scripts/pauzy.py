"""Kde v klipu se mluví – podle hlasitosti zvuku (přesnější než časy z Whisperu) – a slova s časy.

Použití: scripts/py pauzy.py <projekt> C0001 C0002 …
Vypíše úseky řeči (od–do), pauzy nad 0,3 s uvnitř take a slova z přepisu (? = nejisté slovo).
Nástřih = začátek úseku − 0,12 s, výstřih = konec + 0,15 s.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from projekt import Projekt  # noqa: E402

SR, HOP = 16000, 0.01


def envelope(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR),
                          "-af", "highpass=f=90", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    n = int(SR * HOP)
    fr = x[: len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)


def speech_regions(db, min_gap=0.18, min_len=0.12):
    floor = np.percentile(db, 10)
    thr = max(floor + 12, db.max() - 38)
    regions, start = [], None
    for i, v in enumerate(db > thr):
        if v and start is None:
            start = i
        if not v and start is not None:
            regions.append([start * HOP, i * HOP])
            start = None
    if start is not None:
        regions.append([start * HOP, len(db) * HOP])
    merged = []
    for r in regions:
        if merged and r[0] - merged[-1][1] < min_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return [r for r in merged if r[1] - r[0] >= min_len], floor, thr


def hesitations(db, regions, min_len=0.14):
    """Zaváhání uvnitř řeči: přísnější práh (85. percentil − 22 dB). Hrubá detekce výš je počítá jako řeč,
    protože tichý dozvuk, nádech nebo „eee“ jsou nad prahem šumu. Tyhle mezery se vystřihují (mezeru 0,82 s
    uprostřed věty hrubá detekce vůbec nenašla)."""
    sm = np.convolve(db, np.ones(3) / 3, mode="same")
    out, utter = [], []
    for a, b in regions:  # promluva = úseky řeči spojené přes mezery do 0,8 s (zaváhání bývá na hranici úseků)
        if utter and a - utter[-1][1] < 0.8:
            utter[-1][1] = b
        else:
            utter.append([a, b])
    for a, b in utter:
        i0, i1 = int(a / HOP), int(b / HOP)
        if i1 - i0 < 20:
            continue
        quiet = sm < np.percentile(sm[i0:i1], 85) - 22   # hladina řeči v tomhle úseku, ne v celém klipu
        st = None
        for i in range(i0, i1 + 1):
            q = i < len(quiet) and quiet[i]
            if q and st is None:
                st = i
            if (not q or i == i1) and st is not None:
                if (i - st) * HOP >= min_len and st > i0 + 5 and i < i1 - 5:
                    out.append((st * HOP, i * HOP))
                st = None
    return out


if __name__ == "__main__":
    proj = Projekt(Path(sys.argv[1]))
    for clip in sys.argv[2:]:
        regions, floor, thr = speech_regions(envelope(proj.clip_path(clip)))
        print(f"## {clip}  (šum {floor:.0f} dB, práh {thr:.0f} dB)")
        print("  řeč:  " + "  ".join(f"{a:.2f}–{b:.2f}" for a, b in regions))
        gaps = [(a[1], b[0]) for a, b in zip(regions, regions[1:]) if b[0] - a[1] > 0.3]
        if gaps:
            print("  pauzy >0,3 s: " + "  ".join(f"{a:.2f}–{b:.2f}" for a, b in gaps))
        hes = hesitations(envelope(proj.clip_path(clip)), regions)
        if hes:
            print("  zaváhání (vystřihnout, nad 0,25 s vždy): "
                  + "  ".join(f"{a:.2f}–{b:.2f} ({b - a:.2f})" for a, b in hes))
        words = proj.words(clip)
        if words:
            print("  slova: " + " ".join(f"{w['w']}[{w['s']:.2f}]" + ("?" if w.get("p", 1) < 0.5 else "")
                                         for w in words))
