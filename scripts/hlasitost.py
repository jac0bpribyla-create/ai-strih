"""Hlasitost hotového videa na cíl (výchozí −14 LUFS, špička −1,5 dBTP) – dvouprůchodový loudnorm, obraz se nepřekódovává.

Použití: python3 hlasitost.py vstup.mp4 vystup.mp4 [--lufs -14] [--tp -1.5]
Po renderu z HyperFrames vždy (z mono hlasu dělá dual-mono stereo, měří se o ~3 LU hlasitěji).
"""
import argparse
import json
import re
import subprocess

ap = argparse.ArgumentParser()
ap.add_argument("vstup")
ap.add_argument("vystup")
ap.add_argument("--lufs", type=float, default=-14.0)
ap.add_argument("--tp", type=float, default=-1.5)
o = ap.parse_args()

ln = f"loudnorm=I={o.lufs}:TP={o.tp}:LRA=11"
err = subprocess.run(["ffmpeg", "-hide_banner", "-i", o.vstup, "-vn", "-af", f"{ln}:print_format=json", "-f", "null", "-"],
                     capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
m = json.loads(re.findall(r"\{[^{}]*\}", err)[-1])
print(f"před: {m['input_i']} LUFS, špička {m['input_tp']} dBTP")
af = (f"{ln}:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
      f"measured_thresh={m['input_thresh']}:offset={m['target_offset']},aresample=48000")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", o.vstup, "-map", "0:v", "-map", "0:a", "-c:v", "copy", "-af", af,
                "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", o.vystup], check=True, stdin=subprocess.DEVNULL)
err = subprocess.run(["ffmpeg", "-hide_banner", "-i", o.vystup, "-af", "ebur128=peak=true", "-f", "null", "-"],
                     capture_output=True, text=True, stdin=subprocess.DEVNULL).stderr
i = re.findall(r"I:\s+(-?[0-9.]+) LUFS", err)
pk = re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", err)
print(f"po: {i[-1] if i else '?'} LUFS, špička {pk[-1] if pk else '?'} dBFS → {o.vystup}")
