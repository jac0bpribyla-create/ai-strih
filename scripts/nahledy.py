"""Náhledový list klipů: jeden snímek z každého klipu (s LUTem a otočením), popsaný názvem a časem.

Použití: python3 nahledy.py <projekt> <výstup.jpg> [--tile 200 --cols 8] C0001 C0002@3.5 …
@čas = sekunda, ze které se vezme snímek (jinak střed klipu). Bez klipů = všechny klipy ve zdrojích.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nastaveni import PISMO_NAHLED, ff  # noqa: E402
from projekt import Projekt  # noqa: E402

FONT = ff(PISMO_NAHLED)


def duration(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(p)], capture_output=True, text=True, check=True).stdout.strip())


if __name__ == "__main__":
    args = sys.argv[1:]
    proj, out, args = Projekt(Path(args[0])), Path(args[1]), args[2:]
    tw, cols = 200, 8
    while args and args[0].startswith("--"):
        if args[0] == "--tile":
            tw = int(args[1])
        elif args[0] == "--cols":
            cols = int(args[1])
        args = args[2:]
    if not args:
        exts = {e.lower() for e in proj.cfg["pripony"]}
        args = sorted({p.stem for z in proj.zdroje for p in z.iterdir() if p.suffix.lower() in exts})
    with tempfile.TemporaryDirectory() as tmp:
        for i, arg in enumerate(args):
            clip, _, t = arg.partition("@")
            p = proj.clip_path(clip)
            info = proj.info(clip)
            # Pevný rámeček podle prvního klipu: klip s jiným rozměrem/otočením by jinak rozbil mřížku
            # (ffmpeg tile při změně velikosti začne znovu a zůstane jen konec).
            if i == 0:
                th = round(tw * info["h"] / info["w"] / 2) * 2
            ts = float(t) if t else duration(p) / 2
            vf = ",".join(proj.source_filters(clip) + [
                f"scale={tw}:{th}:force_original_aspect_ratio=decrease", f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2",
                "format=yuvj420p",
                f"drawtext=fontfile='{FONT}':text='{clip} {ts:.0f}s':x=5:y=5:fontsize={max(12, tw // 12)}:"
                "fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=3"])
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ts:.2f}", "-i", str(p), "-frames:v", "1",
                            "-vf", vf, str(Path(tmp) / f"{i:03d}.jpg")], check=True)
        rows = (len(args) + cols - 1) // cols
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(Path(tmp) / "%03d.jpg"),
                        "-vf", f"tile={cols}x{rows}:padding=4:color=white", "-frames:v", "1", "-q:v", "3", str(out)],
                       check=True)
    print(out)
