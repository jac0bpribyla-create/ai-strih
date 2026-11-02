"""Společné nastavení projektu střihu. Čte projekt.json z kořene projektu (hledá se nahoru od zadané cesty).

projekt.json (všechno kromě "zdroje" je volitelné):
{
  "nazev": "moje-video",
  "zdroje": ["/Volumes/karta/CLIP/natoceni", "/Volumes/karta/CLIP/b-roll"],
  "jazyk": "cs",
  "pripony": [".MP4", ".mp4", ".MOV", ".mov"],
  "prepisy": "prepisy-slova",
  "lut": {"soubor": "assets/slog3-to-709.cube", "kdy": "sony-slog3"},
  "otocit": {"C0007": "cclock"},
  "font": "Avenir Next",
  "fonty": "/System/Library/Fonts/Supplemental",
  "barvy": {"box": "#141414", "text": "#FFFFFF", "zvyrazneni": "#E63B2E"}
}
lut.kdy: "vzdy" | "nikdy" | "sony-slog3" (podle Sony XML vedle klipu) | seznam názvů klipů.
otocit: klipy bez příznaku otočení – "cclock" | "clock" | "180".
jazyk: jazyk řeči pro Whisper (výchozí z nastaveni.json).
"""
import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nastaveni import nacti  # noqa: E402

DEFAULT = {
    "pripony": [".MP4", ".mp4", ".MOV", ".mov", ".m4v", ".MTS"],
    "prepisy": "prepisy-slova",
    "lut": {"kdy": "nikdy"},
    "otocit": {},
    "font": "Avenir Next",
    "fonty": "/System/Library/Fonts/Supplemental",
    "barvy": {"box": "#141414", "text": "#FFFFFF", "zvyrazneni": "#FFD400"},
}


def find_root(start: Path) -> Path:
    p = start.resolve()
    for d in [p] + list(p.parents):
        if (d / "projekt.json").exists():
            return d
    raise FileNotFoundError(f"Nenašel jsem projekt.json nad {start}. Založ projekt: novy_projekt.py")


class Projekt:
    def __init__(self, start: Path):
        self.root = find_root(start)
        cfg = json.loads((self.root / "projekt.json").read_text())
        self.cfg = {**DEFAULT, "jazyk": nacti()["jazyk"], **cfg, "barvy": {**DEFAULT["barvy"], **cfg.get("barvy", {})}}
        self.zdroje = [Path(z).expanduser() for z in self.cfg.get("zdroje", [])]
        self.prepisy = self.path(self.cfg["prepisy"])

    def path(self, p: str) -> Path:
        q = Path(p).expanduser()
        return q if q.is_absolute() else self.root / q

    @lru_cache(maxsize=None)
    def clip_path(self, clip: str) -> Path:
        """Klip podle názvu (C0001) ve zdrojových složkách, nebo cesta k souboru."""
        direct = self.path(clip)
        if direct.suffix and direct.exists():
            return direct
        for z in self.zdroje:
            for ext in self.cfg["pripony"]:
                p = z / f"{clip}{ext}"
                if p.exists():
                    return p
        raise FileNotFoundError(f"Klip {clip} není v {', '.join(map(str, self.zdroje))}")

    def is_slog3(self, clip: str) -> bool:
        p = self.clip_path(clip)
        xml = p.with_name(f"{p.stem}M01.XML")
        return xml.exists() and "s-log3" in xml.read_text(errors="ignore").lower()

    def color_filter(self, clip: str) -> str:
        lut = self.cfg["lut"]
        kdy = lut.get("kdy", "nikdy")
        use = (kdy == "vzdy" or (kdy == "sony-slog3" and self.is_slog3(clip))
               or (isinstance(kdy, list) and clip in kdy))
        return f"lut3d=file='{self.path(lut['soubor'])}':interp=tetrahedral" if use and lut.get("soubor") else ""

    def rotate_filter(self, clip: str) -> str:
        r = self.cfg["otocit"].get(clip, "")
        return {"cclock": "transpose=cclock", "clock": "transpose=clock",
                "180": "transpose=clock,transpose=clock"}.get(r, "")

    def source_filters(self, clip: str) -> list:
        """LUT na zdrojové pixely, pak ruční otočení (automatické otočení dělá ffmpeg sám)."""
        return [f for f in (self.color_filter(clip), self.rotate_filter(clip)) if f]

    @lru_cache(maxsize=None)
    def info(self, clip: str) -> dict:
        """Rozměry po otočení, počet zvukových kanálů."""
        js = json.loads(subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(self.clip_path(clip))],
            capture_output=True, text=True, check=True).stdout)
        v = next(s for s in js["streams"] if s["codec_type"] == "video")
        a = next((s for s in js["streams"] if s["codec_type"] == "audio"), None)
        w, h = int(v["width"]), int(v["height"])
        rot = 0
        for sd in v.get("side_data_list", []):
            rot = int(sd.get("rotation", 0) or 0)
        if abs(rot) == 90:
            w, h = h, w
        if self.cfg["otocit"].get(clip) in ("cclock", "clock"):
            w, h = h, w
        return {"w": w, "h": h, "channels": int(a["channels"]) if a else 0}

    def words(self, clip: str) -> list:
        """Slova s časy z Whisper přepisu (prepis_slova.py), pokud existuje."""
        js = self.prepisy / f"{Path(clip).stem}.json"
        if not js.exists():
            return []
        return [w for s in json.loads(js.read_text())["segments"] for w in s.get("words", [])]


def ass_color(hex_rgb: str, alpha: int = 0) -> str:
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()
