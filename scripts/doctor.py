"""Kontrola instalace: co je hotové a co chybí (s odkazem na krok v INSTALL.md).

Použití: python3 doctor.py
Nic neinstaluje ani nemění. Konec 0 = vše povinné je hotové, 1 = něco chybí.
"""
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nastaveni import SKILL, cesta, nacti  # noqa: E402

HOME = Path.home()
chyby = 0


def radek(ok, co, detail="", krok="", povinne=True):
    global chyby
    znak = "✓" if ok else ("✗" if povinne else "!")
    if not ok and povinne:
        chyby += 1
    tip = f"  → INSTALL.md, krok {krok}" if not ok and krok else ""
    print(f" {znak} {co}{(' – ' + detail) if detail else ''}{tip}")


def out(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return (r.stdout + r.stderr).strip() if r.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


print("Počítač")
mac = platform.system() == "Darwin" and platform.machine() == "arm64"
radek(mac, "Mac s Apple Silicon", f"{platform.system()} {platform.machine()}", "0")
ram = int(out(["sysctl", "-n", "hw.memsize"]) or 0) / 2**30
radek(ram >= 16, "paměť aspoň 16 GB", f"{ram:.0f} GB", povinne=False)
volno = shutil.disk_usage(HOME).free / 2**30
radek(volno >= 12, "volné místo aspoň 12 GB", f"{volno:.0f} GB", povinne=False)

print("Nastavení")
cfg = nacti()
radek((SKILL / "nastaveni.json").exists(), "nastaveni.json", f"jazyk {cfg['jazyk'] or 'automaticky'}, projekty {cfg['projekty']}", "1")

print("Nástroje")
ff = out(["ffmpeg", "-hide_banner", "-filters"]) or ""
radek(bool(ff), "ffmpeg", (out(["ffmpeg", "-version"]) or "").split("\n")[0][:60], "2")
for f in ("drawtext", "ass", "lut3d", "loudnorm"):
    radek(bool(re.search(rf"\s{f}\s", ff)), f"ffmpeg filtr {f}", "" if f in ff else "obyčejný ffmpeg z Homebrew ho nemá, chce to ffmpeg-full", "2")
radek(bool(out(["ffprobe", "-version"])), "ffprobe", krok="2")
for nazev in ("yt-dlp", "uv", "git"):
    v = out([nazev, "--version"])
    radek(bool(v), nazev, (v or "").split("\n")[0][:40], "2")
node = out(["node", "--version"]) or ""
m = re.match(r"v(\d+)", node)
radek(bool(m and int(m.group(1)) >= 22), "Node.js 22+", node, "2")

print("Přepis řeči (Whisper)")
py = SKILL / "scripts" / "py"
w = out([str(py), "-c", "import mlx_whisper, numpy; print('ok')"])
radek(w == "ok", "mlx-whisper + numpy", "" if w == "ok" else "scripts/py nenašel Python s mlx_whisper", "3")

print("Grafika (HyperFrames)")
hf = out(["hyperframes", "--version"])
radek(bool(hf), "hyperframes CLI", hf or "", "4")
sk = HOME / ".claude" / "skills"
radek((sk / "hyperframes").exists(), "skilly HyperFrames", "", "4")

print("Zvuk")
zv = cesta("zvuky")
n = len(list((zv / "sounds").rglob("*.wav"))) if (zv / "sounds").exists() else 0
radek(n >= 300, "knihovna sfx-kit (CC0)", f"{n} zvuků v {zv}", "5")
ea = cesta("earshot") / ".venv" / "bin" / "python"
radek(out([str(ea), "-c", "import earshot; print('ok')"]) == "ok", "earshot", str(ea), "6")
try:
    mcp = json.loads((HOME / ".claude.json").read_text()).get("mcpServers", {})
except (FileNotFoundError, json.JSONDecodeError):
    mcp = {}
radek("earshot" in mcp, "earshot jako MCP server v Claude Code", "", "6")
radek((sk / "earshot").exists(), "skill earshot", "", "6")
rs = sk / "real-sfx" / "config.json"
radek(rs.exists() and bool(json.loads(rs.read_text()).get("libraries")), "skill real-sfx s knihovnou", "", "7")

print("Volitelné")
radek((sk / "watch").exists() or bool(list((HOME / ".claude" / "plugins").rglob("watch/SKILL.md"))),
      "skill watch (prohlédne video za tebe)", "", "8", povinne=False)

print()
if chyby:
    slovo = "věc" if chyby == 1 else "věci" if chyby < 5 else "věcí"
    print(f"Chybí {chyby} {slovo}. Projdi uvedené kroky v INSTALL.md a pusť doctor.py znovu.")
    sys.exit(1)
print("Všechno povinné je hotové. Po instalaci MCP serveru a skillů restartuj Claude Code.")
