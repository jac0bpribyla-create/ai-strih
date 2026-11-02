"""Kontrola instalace: co je hotové a co chybí (s odkazem na krok v INSTALL.md). Mac i Windows.

Použití: python3 doctor.py   (Windows: python doctor.py)
Nic neinstaluje ani nemění. Konec 0 = vše povinné je hotové, 1 = něco chybí.
"""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nastaveni import MAC, SKILL, WINDOWS, cesta, nacti, venv_python  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")  # Windows: ✓ a čeština i v okně, které má jinou znakovou sadu
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
    exe = shutil.which(str(cmd[0])) or str(cmd[0])  # na Windows najde i hyperframes.cmd
    try:
        r = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        return (r.stdout + r.stderr).strip() if r.returncode == 0 else None
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None


def pamet_gb():
    if WINDOWS:
        import ctypes

        class Stav(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        s = Stav(dwLength=ctypes.sizeof(Stav))
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
        return s.ullTotalPhys / 2**30
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
    except (ValueError, OSError, AttributeError):
        return 0


def python_s_whisperem():
    """Stejné pořadí jako scripts/py: nastaveni.json → ~/AI-strih/nastroje/python → nástroj uv mlx-whisper."""
    kandidati = [Path(nacti()["python"]).expanduser()] if nacti()["python"] else []
    kandidati.append(venv_python(HOME / "AI-strih" / "nastroje" / "python"))
    uv = out(["uv", "tool", "dir"])
    if uv:
        kandidati.append(Path(uv) / "mlx-whisper" / "bin" / "python")
    return next((k for k in kandidati if k.exists()), None)


print("Počítač")
system = f"{platform.system()} {platform.release()} {platform.machine()}"
apple = MAC and platform.machine() == "arm64"
radek(MAC or WINDOWS, "Mac nebo Windows", system, "0", povinne=False)
if not apple:
    radek(False, "přepis řeči poběží na procesoru (faster-whisper)", "pomalejší než na Macu s Apple Silicon", povinne=False)
ram = pamet_gb()
radek(ram >= 16, "paměť aspoň 16 GB", f"{ram:.0f} GB", povinne=False)
volno = shutil.disk_usage(HOME).free / 2**30
radek(volno >= 12, "volné místo aspoň 12 GB", f"{volno:.0f} GB", povinne=False)

print("Nastavení")
cfg = nacti()
radek((SKILL / "nastaveni.json").exists(), "nastaveni.json", f"jazyk {cfg['jazyk'] or 'automaticky'}, projekty {cfg['projekty']}", "1")

print("Nástroje")
ff = out(["ffmpeg", "-hide_banner", "-filters"]) or ""
radek(bool(ff), "ffmpeg", (out(["ffmpeg", "-version"]) or "").split("\n")[0][:60], "2")
plna = "Windows: plná verze Gyan.FFmpeg" if WINDOWS else "obyčejný ffmpeg z Homebrew ho nemá, chce to ffmpeg-full"
for f in ("drawtext", "ass", "lut3d", "loudnorm"):
    radek(bool(re.search(rf"\s{f}\s", ff)), f"ffmpeg filtr {f}", "" if f in ff else plna, "2")
radek(bool(out(["ffprobe", "-version"])), "ffprobe", krok="2")
for nazev in ("yt-dlp", "uv", "git"):
    v = out([nazev, "--version"])
    radek(bool(v), nazev, (v or "").split("\n")[0][:40], "2")
node = out(["node", "--version"]) or ""
m = re.match(r"v(\d+)", node)
radek(bool(m and int(m.group(1)) >= 22), "Node.js 22+", node, "2")

print("Přepis řeči (Whisper)")
py = python_s_whisperem()
test = "import numpy\ntry:\n import mlx_whisper as w\nexcept ImportError:\n import faster_whisper as w\nprint(w.__name__)"
w = out([str(py), "-c", test]) if py else None
radek(bool(w), "Whisper + numpy", (w or "").replace("_", "-") if w else "scripts/py nenašel Python s Whisperem", "3")

print("Grafika (HyperFrames)")
hf = out(["hyperframes", "--version"])
radek(bool(hf), "hyperframes CLI", hf or "", "4")
sk = HOME / ".claude" / "skills"
radek((sk / "hyperframes").exists(), "skilly HyperFrames", "", "4")

print("Zvuk")
zv = cesta("zvuky")
n = len(list((zv / "sounds").rglob("*.wav"))) if (zv / "sounds").exists() else 0
radek(n >= 300, "knihovna sfx-kit (CC0)", f"{n} zvuků v {zv}", "5")
ea = venv_python(cesta("earshot") / ".venv")
radek(out([str(ea), "-c", "import earshot; print('ok')"]) == "ok", "earshot", str(ea), "6")
try:
    mcp = json.loads((HOME / ".claude.json").read_text(encoding="utf-8")).get("mcpServers", {})
except (FileNotFoundError, json.JSONDecodeError):
    mcp = {}
radek("earshot" in mcp, "earshot jako MCP server v Claude Code", "", "6")
radek((sk / "earshot").exists(), "skill earshot", "", "6")
rs = sk / "real-sfx" / "config.json"
radek(rs.exists() and bool(json.loads(rs.read_text(encoding="utf-8")).get("libraries")), "skill real-sfx s knihovnou", "", "7")

print("Volitelné")
radek((sk / "watch").exists() or bool(list((HOME / ".claude" / "plugins").rglob("watch/SKILL.md"))),
      "skill watch (prohlédne video za tebe)", "", "8", povinne=False)

print()
if chyby:
    slovo = "věc" if chyby == 1 else "věci" if chyby < 5 else "věcí"
    print(f"Chybí {chyby} {slovo}. Projdi uvedené kroky v INSTALL.md a pusť doctor.py znovu.")
    sys.exit(1)
print("Všechno povinné je hotové. Po instalaci MCP serveru a skillů restartuj Claude Code.")
