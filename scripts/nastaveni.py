"""Nastavení skillu: <skill>/nastaveni.json (vytvoří ho instalace z nastaveni.example.json) a výchozí hodnoty podle systému.

Klíče (všechny volitelné):
  projekty          kam se zakládají projekty střihu (výchozí ~/AI-strih/projekty)
  jazyk             jazyk řeči pro Whisper ("cs", "en", "sk"…; prázdné = rozpozná sám)
  whisper_model     model Whisperu (prázdné = large-v3-turbo: na Macu s Apple Silicon přes mlx-whisper, jinde přes faster-whisper)
  whisper_zarizeni  jen faster-whisper: "cpu" (výchozí) nebo "cuda" (karta NVIDIA s nainstalovanou CUDA)
  python            Python s Whisperem a numpy (prázdné = najde ho scripts/py sám)
  zvuky             knihovna zvukových efektů (sfx-kit, CC0)
  earshot           složka s repem earshot (jeho .venv)
"""
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
DEFAULT = {
    "projekty": "~/AI-strih/projekty",
    "jazyk": "",
    "whisper_model": "",
    "whisper_zarizeni": "cpu",
    "python": "",
    "zvuky": "~/AI-strih/zvuky/sfx-kit",
    "earshot": "~/AI-strih/nastroje/earshot",
}

WINDOWS = sys.platform == "win32"
MAC = sys.platform == "darwin"
# Písmo titulků a grafiky, složka systémových písem (pro ffmpeg ass) a tučné písmo popisků v náhledech (drawtext).
PISMO = "Avenir Next" if MAC else "Segoe UI" if WINDOWS else "DejaVu Sans"
FONTY = "/System/Library/Fonts/Supplemental" if MAC else "C:/Windows/Fonts" if WINDOWS else "/usr/share/fonts"
PISMO_NAHLED = next((f for f in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
                                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if Path(f).exists()), "")


def nacti() -> dict:
    p = SKILL / "nastaveni.json"
    cfg = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return {**DEFAULT, **{k: v for k, v in cfg.items() if v not in (None,)}}


def cesta(klic: str) -> Path:
    return Path(nacti()[klic]).expanduser()


def ff(p) -> str:
    """Cesta do filtru ffmpeg v '…' (lut3d, ass, drawtext): lomítka dopředu a escapovaná dvojtečka (C\\:/Users/…)."""
    return str(p).replace("\\", "/").replace(":", "\\:")


def venv_python(slozka: Path) -> Path:
    """Python ve virtuálním prostředí: bin/python (Mac, Linux) nebo Scripts/python.exe (Windows)."""
    return slozka / ("Scripts/python.exe" if WINDOWS else "bin/python")


if __name__ == "__main__":
    cfg = nacti()
    print(cfg[sys.argv[1]] if len(sys.argv) > 1 else json.dumps(cfg, ensure_ascii=False, indent=2))
