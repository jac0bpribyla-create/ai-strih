"""Rozbor stylu z ukázkových videí (kanál nebo video, které chceš napodobit) → čísla pro styly/<název>.md.

Použití: scripts/py styl_rozbor.py --out <složka> video1.mp4 video2.mp4 …
Krátká videa (≤ 120 s) se rozeberou celá, dlouhá po úsecích: začátek 0–90 s (intro, hook), 60 s ze středu, posledních 60 s (CTA, outro).
Každý úsek jde přes rozbor_videa.py: střihy, délky záběrů, skoky ve stejném záběru (jump cut),
řeč, slova/s, pauzy, hlasitost, hudba, náhledový list list.jpg. Výsledek:
  <out>/styl.json   – všechna čísla
  <out>/styl.md     – tabulka po videích + mediány → podklad pro styl (ještě PROHLÉDNOUT list.jpg každého úseku:
                      titulky, popisky, písmo, barvy, přechody, B-roll, rámování, intro/outro – to čísla neřeknou)
"""
import argparse
import json
import statistics as stt
import subprocess
import sys
from pathlib import Path

ROZBOR = Path(__file__).resolve().parent / "rozbor_videa.py"
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--no-whisper", action="store_true")
ap.add_argument("videa", nargs="+")
o = ap.parse_args()
out = Path(o.out)
(out / "useky").mkdir(parents=True, exist_ok=True)


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout.strip())


rows = []
for v in map(Path, o.videa):
    d = dur(v)
    parts = [("cele", 0, d)] if d <= 120 else [("zacatek", 0, 90), ("stred", d / 2 - 30, 60), ("konec", max(0, d - 60), 60)]
    for name, a, length in parts:
        seg = out / "useky" / f"{v.stem}_{name}.mp4"
        if not seg.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.2f}", "-t", f"{length:.2f}", "-i", str(v), "-c:v", "libx264", "-preset",
                            "veryfast", "-crf", "20", "-c:a", "aac", str(seg)], check=True)
        cmd = [sys.executable, str(ROZBOR), "--out", str(out / "rozbory"), str(seg)] + (["--no-whisper"] if o.no_whisper else [])
        subprocess.run(cmd, capture_output=True, text=True)
        rj = out / "rozbory" / seg.stem / "rozbor.json"
        if rj.exists():
            r = json.loads(rj.read_text())
            r.update({"video": v.stem, "usek": name, "video_delka_s": round(d, 1)})
            rows.append(r)
            print(f"{v.stem} {name}: {r.get('zaberu')} záběrů, Ø {r.get('prumerny_zaber_s')} s, řeč {r.get('rec_pokryva_procent')} %")

(out / "styl.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
keys = [("pomer", "formát"), ("prumerny_zaber_s", "Ø záběr s"), ("median_zaber_s", "medián záběru s"), ("strihu_za_10s", "střihů / 10 s"),
        ("jump_cuty_s", "jump cutů"), ("slov_za_s", "slov/s"), ("rec_pokryva_procent", "řeč %"), ("nejdelsi_pauza_s", "nejdelší pauza s"),
        ("hlasitost_lufs", "LUFS"), ("hudba_odhad", "hudba"), ("prvni_slovo_s", "1. slovo s"), ("prvni_strih_s", "1. střih s")]
lines = ["| video | úsek | délka videa | " + " | ".join(k[1] for k in keys) + " |", "|" + "---|" * (3 + len(keys))]
for r in rows:
    vals = [str(len(r[k]) if isinstance(r.get(k), list) else r.get(k, "")) for k, _ in keys]
    lines.append(f"| {r['video']} | {r['usek']} | {r['video_delka_s']} | " + " | ".join(vals) + " |")
med = []
for k, label in keys:
    nums = [len(r[k]) if isinstance(r.get(k), list) else r.get(k) for r in rows]
    nums = [x for x in nums if isinstance(x, (int, float))]
    if nums:
        med.append(f"- {label}: medián {stt.median(nums):.2f} (rozsah {min(nums):g}–{max(nums):g})")
(out / "styl.md").write_text("# Rozbor stylu – čísla\n\n" + "\n".join(lines) + "\n\n## Mediány\n" + "\n".join(med)
                             + "\n\nNáhledové listy: rozbory/<úsek>/list.jpg (prohlédnout všechny).\n", encoding="utf-8")
print(out / "styl.md")
