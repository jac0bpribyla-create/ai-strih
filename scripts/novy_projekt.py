"""Založí projekt střihu: <projekty>/<název>/ se složkami, projekt.json a pravidly (<projekty> z nastaveni.json).

Použití: python3 novy_projekt.py "<název>" <složka se záběry> [další složka …] [--styl <styl>]
Existující soubory nepřepisuje.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nastaveni import PISMO, SKILL, cesta, nacti  # noqa: E402

if __name__ == "__main__":
    args = sys.argv[1:]
    styl = ""
    if "--styl" in args:
        i = args.index("--styl")
        styl = args[i + 1]
        del args[i:i + 2]
    nazev, zdroje = args[0], args[1:]
    root = cesta("projekty") / nazev
    for d in ("edl", "export", "nahledy", "prepisy-slova", "tmp", "assets", "hyperframes", "zvuk"):
        (root / d).mkdir(parents=True, exist_ok=True)
    cfg = root / "projekt.json"
    if not cfg.exists():
        cfg.write_text(json.dumps({
            "nazev": nazev,
            "styl": styl,
            "zdroje": [str(Path(z).expanduser().resolve()) for z in zdroje],
            "jazyk": nacti()["jazyk"],
            "lut": {"kdy": "nikdy"},
            "otocit": {},
            "fps": 30,
            "font": PISMO,
            "barvy": {"box": "#141414", "text": "#FFFFFF", "zvyrazneni": "#FFD400"},
        }, ensure_ascii=False, indent=2) + "\n")
    rules = root / "PRAVIDLA-STRIHU.md"
    if not rules.exists():
        rules.write_text((SKILL / "references" / "sablona-pravidla.md").read_text().replace("{nazev}", nazev))
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(f"# {nazev} — AI střih\n\nZáběry: {', '.join(zdroje)}\nStyl: {styl or '(zatím žádný)'}\n\n## Verze\n\n"
                          "## Složky\n"
                          "- `edl/` střihové listy, `export/` hrubé střihy a hotová videa + .srt, `nahledy/` náhledové listy,\n"
                          "  `prepisy-slova/` přepisy Whisperu, `hyperframes/` grafika, `zvuk/` efekty a mix, `assets/` logo, hudba, obrázky\n")
    print(root)
