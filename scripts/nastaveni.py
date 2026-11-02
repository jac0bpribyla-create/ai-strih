"""Nastavení skillu: <skill>/nastaveni.json (vytvoří ho instalace z nastaveni.example.json).

Klíče (všechny volitelné):
  projekty       kam se zakládají projekty střihu (výchozí ~/AI-strih/projekty)
  jazyk          jazyk řeči pro Whisper ("cs", "en", "sk"…; prázdné = rozpozná sám)
  whisper_model  model pro mlx-whisper (výchozí mlx-community/whisper-large-v3-turbo)
  python         Python s mlx_whisper a numpy (prázdné = najde ho scripts/py sám)
  zvuky          knihovna zvukových efektů (sfx-kit, CC0)
  earshot        složka s repem earshot (jeho .venv)
"""
import json
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
DEFAULT = {
    "projekty": "~/AI-strih/projekty",
    "jazyk": "",
    "whisper_model": "mlx-community/whisper-large-v3-turbo",
    "python": "",
    "zvuky": "~/AI-strih/zvuky/sfx-kit",
    "earshot": "~/AI-strih/nastroje/earshot",
}


def nacti() -> dict:
    p = SKILL / "nastaveni.json"
    cfg = json.loads(p.read_text()) if p.exists() else {}
    return {**DEFAULT, **{k: v for k, v in cfg.items() if v not in (None,)}}


def cesta(klic: str) -> Path:
    return Path(nacti()[klic]).expanduser()


if __name__ == "__main__":
    import sys
    cfg = nacti()
    print(cfg[sys.argv[1]] if len(sys.argv) > 1 else json.dumps(cfg, ensure_ascii=False, indent=2))
