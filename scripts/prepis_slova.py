"""Přepis klipů s časem každého slova (Whisper z whisper_prepis.py, jazyk z projekt.json / nastaveni.json).

Použití: scripts/py prepis_slova.py <projekt> [C0001 C0002 … | --vse]
Klipy se hledají ve zdrojích z projekt.json; --vse = všechny klipy ve zdrojích.
První spuštění stáhne model Whisperu (~1,6 GB, jednou).
Ukládá <projekt>/prepisy-slova/<klip>.json a vypíše text. Hotové přepisy přeskočí.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from projekt import Projekt  # noqa: E402
from whisper_prepis import prepis  # noqa: E402

if __name__ == "__main__":
    proj = Projekt(Path(sys.argv[1]))
    names = sys.argv[2:]
    if names == ["--vse"]:
        exts = {e.lower() for e in proj.cfg["pripony"]}
        names = sorted({p.stem for z in proj.zdroje for p in z.iterdir() if p.suffix.lower() in exts})
    proj.prepisy.mkdir(parents=True, exist_ok=True)
    for clip in names:
        dst = proj.prepisy / f"{Path(clip).stem}.json"
        if dst.exists():
            continue
        if not proj.info(clip)["channels"]:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "a.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(proj.clip_path(clip)), "-vn", "-ac", "1",
                            "-ar", "16000", str(wav)], check=True)
            r = prepis(wav, proj.cfg.get("jazyk"))
        segs = [{"start": round(s["start"], 3), "end": round(s["end"], 3), "text": s["text"].strip(),
                 "words": [{"w": w["word"].strip(), "s": round(w["start"], 3), "e": round(w["end"], 3),
                            "p": round(w.get("probability", 0), 3)} for w in s.get("words", [])]}
                for s in r["segments"]]
        dst.write_text(json.dumps({"clip": clip, "segments": segs}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(clip, "|", " / ".join(s["text"] for s in segs), flush=True)
