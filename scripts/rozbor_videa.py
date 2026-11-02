"""Rozbor hotového videa: střihy, tempo, řeč, hudba a náhledový list.

Použití:
  scripts/py rozbor_videa.py --out <složka> video1.mp4 [video2.mp4 ...]
  volitelně --no-whisper (bez přepisu), --lang cs (výchozí z nastaveni.json, prázdné = rozpozná sám)

Pro každé video vznikne <out>/<název>/:
  rozbor.json  – čísla (délka, formát, střihy, délky záběrů, řeč, slova za sekundu, hlasitost, hudba pod řečí)
  list.jpg     – náhledový list: prvních 3 s hustě (0; 0,5; 1; 1,5; 2; 3 s) + střed každého záběru, s časem
Hodí se na referenční videa (styl, který chceš napodobit) i na kontrolu vlastního střihu.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nastaveni import nacti  # noqa: E402

FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
SR = 16000
HOP = 0.01


def probe(p: Path) -> dict:
    js = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(p)],
        capture_output=True, text=True, check=True).stdout)
    v = next(s for s in js["streams"] if s["codec_type"] == "video")
    num, den = (int(x) for x in v["r_frame_rate"].split("/"))
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []):
        rot = int(sd.get("rotation", 0) or 0)
    if abs(rot) == 90:
        w, h = h, w
    return {
        "sirka": w, "vyska": h, "fps": round(num / den, 2),
        "delka_s": round(float(js["format"]["duration"]), 2),
        "zvuk": any(s["codec_type"] == "audio" for s in js["streams"]),
        "pomer": "9:16" if h / w > 1.6 else "4:5" if h / w > 1.15 else "1:1" if h / w > 0.9 else "16:9",
    }


def detect_cuts(p: Path, fps: float, dur: float) -> list[float]:
    """Tvrdé střihy z rozdílu po sobě jdoucích snímků (adaptivní práh proti pohybu v záběru)."""
    W, H = 64, 112
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(p), "-an", "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
        capture_output=True, check=True).stdout
    n = len(raw) // (W * H)
    if n < 3:
        return []
    f = np.frombuffer(raw[: n * W * H], dtype=np.uint8).reshape(n, H, W).astype(np.float32)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))  # d[i] = rozdíl snímku i+1 proti i
    hist = np.stack([np.histogram(x, bins=16, range=(0, 256))[0] for x in f]).astype(np.float32) / (W * H)
    hd = np.abs(np.diff(hist, axis=0)).sum(axis=1)
    rate = n / dur if dur else fps
    cuts, jumps, last = [], [], -1e9
    k = max(3, int(rate * 0.5))
    for i in range(len(d)):
        lo, hi = max(0, i - k), min(len(d), i + k + 1)
        neigh = np.concatenate([d[lo:i], d[i + 1:hi]])
        base = np.median(neigh) if len(neigh) else 0
        t = (i + 1) / rate
        if t - last < 0.2:
            continue
        if d[i] > max(14, 3.2 * base) and hd[i] > 0.22:
            cuts.append(round(t, 2))
            last = t
        elif d[i] > max(4.5, 6 * (base + 0.3)):
            # Jump cut: stejný záběr, skok v čase (u mluvící hlavy malý, ale ostrý rozdíl).
            jumps.append(round(t, 2))
            last = t
    return cuts, jumps


def audio_env(p: Path) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    n = int(SR * HOP)
    fr = x[: len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)


def lufs(p: Path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(p), "-vn", "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    for line in reversed(out.splitlines()):
        if line.strip().startswith("I:"):
            return float(line.split()[1])
    return None


def transcribe(p: Path, lang: str):
    import mlx_whisper
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
        r = mlx_whisper.transcribe(str(wav), path_or_hf_repo=nacti()["whisper_model"], language=lang or None,
                                   word_timestamps=True, condition_on_previous_text=False,
                                   hallucination_silence_threshold=1.0, no_speech_threshold=0.5)
    words = []
    for s in r["segments"]:
        if s.get("no_speech_prob", 0) > 0.8:
            continue
        for w in s.get("words", []):
            words.append({"w": w["word"].strip(), "s": round(w["start"], 2), "e": round(w["end"], 2),
                          "p": round(w.get("probability", 0), 2)})
    words = [w for w in words if w["p"] > 0.15 and w["w"]]
    # Whisper si do hudby vymýšlí typické české „titulky“. Takové věty zahodit.
    text = " ".join(w["w"] for w in words).lower()
    if any(h in text for h in HALLUCINATIONS) and len(words) < 12:
        return []
    return words


HALLUCINATIONS = ("titulky vytvořil", "johnyx", "muzika", "hudba", "děkuji za pozornost", "titulky:", "www.")


def speech_regions(words, gap=0.35):
    reg = []
    for w in words:
        if reg and w["s"] - reg[-1][1] < gap:
            reg[-1][1] = max(reg[-1][1], w["e"])
        else:
            reg.append([w["s"], w["e"]])
    return reg


def contact_sheet(p: Path, times: list[float], labels: list[str], out: Path, aspect_h_over_w: float):
    tw = 200
    th = int(round(tw * aspect_h_over_w / 2) * 2)
    cols = 8 if aspect_h_over_w > 1.1 else 6
    with tempfile.TemporaryDirectory() as tmp:
        for i, (t, lab) in enumerate(zip(times, labels)):
            vf = (f"scale={tw}:{th},format=yuvj420p,"
                  f"drawtext=fontfile='{FONT}':text='{lab}':x=4:y=4:fontsize=17:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=3")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(p), "-frames:v", "1",
                            "-vf", vf, str(Path(tmp) / f"{i:03d}.jpg")], check=True)
        rows = (len(times) + cols - 1) // cols
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(Path(tmp) / "%03d.jpg"),
                        "-vf", f"tile={cols}x{rows}:padding=3:color=white", "-frames:v", "1", "-q:v", "4", str(out)],
                       check=True)


def analyze(p: Path, out_root: Path, use_whisper: bool, lang: str) -> dict:
    out = out_root / p.stem
    out.mkdir(parents=True, exist_ok=True)
    info = probe(p)
    dur = info["delka_s"]
    hard, jumps = detect_cuts(p, info["fps"], dur)
    cuts = sorted(hard + jumps)
    bounds = [0.0] + cuts + [dur]
    shots = [round(b - a, 2) for a, b in zip(bounds, bounds[1:])]
    r = {"soubor": p.name, **info,
         "strihy_s": hard,
         "jump_cuty_s": jumps,
         "zaberu": len(shots),
         "prumerny_zaber_s": round(dur / len(shots), 2),
         "median_zaber_s": round(float(np.median(shots)), 2),
         "nejdelsi_zaber_s": max(shots),
         "prvni_strih_s": cuts[0] if cuts else None,
         "strihu_v_prvnich_3s": sum(1 for c in cuts if c < 3),
         "strihu_za_10s": round(len(cuts) / dur * 10, 1) if dur else 0}

    if info["zvuk"]:
        env = audio_env(p)
        r["hlasitost_lufs"] = lufs(p)
        words = transcribe(p, lang) if use_whisper else []
        reg = speech_regions(words)
        mask = np.zeros(len(env), dtype=bool)
        for a, b in reg:
            mask[int(a / HOP): int(b / HOP) + 1] = True
        speech_db = float(np.median(env[mask])) if mask.any() else None
        gap_db = float(np.median(env[~mask])) if (~mask).any() else None
        talk = sum(b - a for a, b in reg)
        r.update({
            "slov": len(words),
            "prvni_slovo_s": words[0]["s"] if words else None,
            # Pauzy mezi slovy uvnitř řeči (nad 0,3 s) – ve vlastním střihu mají být vystříhané.
            "pauzy_nad_0_3s": [round(b["s"], 2) for a, b in zip(words, words[1:]) if b["s"] - a["e"] > 0.3],
            "nejdelsi_pauza_s": round(max([b["s"] - a["e"] for a, b in zip(words, words[1:])] or [0]), 2),
            "rec_pokryva_procent": round(100 * talk / dur) if dur else 0,
            "slov_za_s": round(len(words) / talk, 2) if talk > 1 else None,
            "hlasitost_reci_db": round(speech_db, 1) if speech_db is not None else None,
            "hlasitost_mimo_rec_db": round(gap_db, 1) if gap_db is not None else None,
            # Hudba pod řečí: v pauzách řeči zůstává zvuk blízko úrovni řeči.
            "hudba_odhad": (None if gap_db is None else
                            "jen hudba/zvuk" if not words else
                            "hudba pod řečí" if gap_db > -38 and (speech_db - gap_db) < 18 else
                            "bez hudby / tichá"),
            "hook_text_0_3s": " ".join(w["w"] for w in words if w["s"] < 3.0),
            "prepis": " ".join(w["w"] for w in words),
            "slova": words,
        })

    first = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]
    mids = [round((a + b) / 2, 2) for a, b in zip(bounds, bounds[1:])]
    if len(mids) > 34:
        idx = np.linspace(0, len(mids) - 1, 34).round().astype(int)
        mids = [mids[i] for i in sorted(set(idx))]
    times = [t for t in first if t < dur] + [m for m in mids if m >= 3.0 or len(mids) <= 3]
    labels = [f"{t:.1f}s" for t in times]
    for i in range(len([t for t in first if t < dur])):
        labels[i] = "H " + labels[i]
    contact_sheet(p, times, labels, out / "list.jpg", info["vyska"] / info["sirka"])
    (out / "rozbor.json").write_text(json.dumps(r, ensure_ascii=False, indent=1))
    return r


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-whisper", action="store_true")
    ap.add_argument("--lang", default=nacti()["jazyk"])
    a = ap.parse_args()
    for v in a.videos:
        r = analyze(Path(v), Path(a.out), not a.no_whisper, a.lang)
        print(f"{Path(v).stem}: {r['delka_s']}s {r['pomer']} záběrů {r['zaberu']} (Ø {r['prumerny_zaber_s']} s, "
              f"nejdelší {r['nejdelsi_zaber_s']} s), 1. střih {r['prvni_strih_s']}, 1. slovo {r.get('prvni_slovo_s')}, "
              f"slov/s {r.get('slov_za_s')}, řeč {r.get('rec_pokryva_procent')} %, nejdelší pauza "
              f"{r.get('nejdelsi_pauza_s')} s, {r.get('hlasitost_lufs')} LUFS, {r.get('hudba_odhad')} | "
              f"{r.get('hook_text_0_3s', '')[:70]}", flush=True)
