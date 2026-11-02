"""Kompozice HyperFrames (texty, počítadla, karty produktů, pilulka s webem, přechody se zvuky) ze zadání v JSON.

Použití: python3 hf_kompozice.py zadani.json  → <vystup>/public/index.html + zvuky, gsap, obrázky (+ fonty, když jsou zadané)
Render:  cd <vystup> && PRODUCER_BROWSER_GPU_MODE=hardware hyperframes render public -o output.mp4 --fps 25
         pak hlasitost na −14 LUFS (HyperFrames dělá z mono dual-mono stereo, měří se o ~3 LU hlasitěji).

Zadání (časy v s od začátku videa, cesty relativně k souboru zadání):
{
  "id": "video-01", "video": "../export/01_zaklad.mp4", "vystup": "../hyperframes/01_v1", "frames": 779, "fps": 25, "w": 1080, "h": 1920,
  "styl": {"font": "Avenir Next", "fonty": {"700": "fonts/MujFont-Bold.woff2"}, "ink": "#141414", "paper": "#ffffff",
           "radius": 14, "verzalky": true, "prostrkani": 0.07},   # "fonty" volitelné: bez nich se použije písmo z počítače
  "texty": [{"id": "h1", "radky": ["Začal jsem", "s nulou"], "od": 0.08, "do": 3.0, "y": 1100, "velikost": "md",
             "odstup": 0.16, "pocitadlo": null}],          # "radky": ["{n} surovin"], "pocitadlo": 7 → číslo naběhne 0 → 7
  "pilulka": {"text": "mujweb.cz", "od": 29.8, "y": 1060},
  "karty": {"od": 22.5, "do": 25.36, "polozky": [{"img": "foto.jpg", "nazev": "Produkt"}]},   # 1–4 karty, mřížka 2×2
  "prechody": [[2.64, "zoom"], [8.92, "whip", -1]],
  "posun": 0.0                                                # přičte se ke všem časům (verze s jinou délkou hooku)
}
Zvuky jsou ze sfx-kit (CC0) a nasazují se podle bodu synchronizace (vrchol whooshe přesně na střih).
Pravidla polohy (viz references/kontroly.md): text aspoň ~100 px pod nejnižší polohou brady, nikdy přes obličej ani přes věc,
o které se mluví; bezpečná zóna 9:16 y 220–1250 px. Pozici ověřit snímky po 0,5 s (`hyperframes snapshot --at …`).
"""
import glob
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nastaveni import PISMO  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "assets"
# zvuk: (soubor, bod synchronizace v s = kde je vrchol, délka v s) – časy ze sfx-kit catalogue.md
SFX = {"pop": ("pop.wav", 0.011, 0.08), "zoom": ("whoosh-zoom.wav", 0.489, 0.57), "whip": ("whoosh-whip.wav", 0.092, 0.26)}
GSAP_CDN = "https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"


def gsap_lokalne():
    """gsap.min.js z instalace HyperFrames (npm -g), jinak None → načte se z CDN."""
    npm = shutil.which("npm")  # na Windows npm.cmd
    if not npm:
        return None
    root = subprocess.run([npm, "root", "-g"], capture_output=True, text=True).stdout.strip()
    hits = sorted(glob.glob(f"{root}/hyperframes/dist/vendor/npm/gsap@*/dist/gsap.min.js"))
    return Path(hits[-1]) if hits else None


spec_path = Path(sys.argv[1]).resolve()
z = json.loads(spec_path.read_text(encoding="utf-8"))
base = spec_path.parent
S = z.get("posun", 0.0)
W, H, FPS = z.get("w", 1080), z.get("h", 1920), z.get("fps", 25)
dur = z["frames"] / FPS
st = {"font": PISMO, "ink": "#141414", "paper": "#ffffff", "radius": 14, "verzalky": True, "prostrkani": 0.07, **z.get("styl", {})}
out = (base / z["vystup"]).resolve()
pub = out / "public"
(pub / "assets").mkdir(parents=True, exist_ok=True)
shutil.copytree(ASSETS / "sfx", pub / "sfx", dirs_exist_ok=True)
faces = []
for weight, f in st.get("fonty", {}).items():
    src = (base / f).resolve()
    (pub / "fonts").mkdir(exist_ok=True)
    shutil.copy(src, pub / "fonts" / src.name)
    faces.append(f'@font-face {{ font-family: "{st["font"]}"; src: url("fonts/{src.name}"); font-weight: {weight}; font-display: block; }}')
g = gsap_lokalne()
if g:
    (pub / "vendor").mkdir(exist_ok=True)
    shutil.copy(g, pub / "vendor/gsap.min.js")
GSAP_SRC = "vendor/gsap.min.js" if g else GSAP_CDN
shutil.copy((base / z["video"]).resolve(), pub / "input-video.mp4")
(pub / "hyperframes.json").write_text(json.dumps({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                                                  "paths": {"assets": "assets"}, "media": {"autoProxy": True}}, indent=2))

html, js, sfx = [], [], []
for t in z.get("texty", []):
    a, b = t["od"] + S, t["do"] + S
    rows = []
    for i, line in enumerate(t["radky"]):
        lid = f"{t['id']}-{i}"
        label = line.replace("{n}", f'<span class="num" id="{lid}-n">0</span>') if t.get("pocitadlo") is not None else line
        y = t["y"] + i * (102 if t.get("velikost", "md") == "md" else 150)
        rows.append(f'        <div class="line" style="top: {y}px"><span class="box {t.get("velikost", "md")}" id="{lid}">{label}</span></div>')
        ta = a + i * t.get("odstup", 0.16)
        js.append(f'          pop("#{lid}", {ta:.2f});')
        sfx.append((ta, 0.25 if i == 0 else 0.2))
        if t.get("pocitadlo") is not None and "{n}" in line:
            js.append(f'''          (function () {{ const o = {{ v: 0 }};
            tl.to(o, {{ v: {t["pocitadlo"]}, duration: 0.5, ease: "power1.out", onUpdate: function () {{
              const el = document.getElementById("{lid}-n"); if (el) el.textContent = String(Math.round(o.v)); }} }}, {ta + 0.04:.2f}); }})();''')
    sels = ", ".join("#%s-%d" % (t["id"], i) for i in range(len(t["radky"])))
    js.append(f'          out("{sels}", {b:.2f});')
    html.append(f'      <div class="card-host clip" id="{t["id"]}" data-start="{a:.2f}" data-duration="{b - a + 0.16:.2f}" data-track-index="2">\n'
                + "\n".join(rows) + "\n      </div>")

k = z.get("karty")
if k:
    a, b = k["od"] + S, k["do"] + S
    pos = [(66, 300), (554, 300), (66, 752), (554, 752)]
    rot, end = [-14, 12, -10, 13], [-1.5, 1.2, 1, -1.2]
    cards = []
    for i, it in enumerate(k["polozky"][:4]):
        src = (base / it["img"]).resolve()
        shutil.copy(src, pub / "assets" / src.name)
        x, y = pos[i]
        cards.append(f'        <div class="pcard" id="pc{i}" style="left: {x}px; top: {y}px"><img src="assets/{src.name}" alt=""><div class="title">{it["nazev"]}</div></div>')
        js.append(f'          tl.fromTo("#pc{i}", {{ y: 1720, rotation: {rot[i]}, scale: 0.85 }}, {{ y: 0, rotation: {end[i]}, scale: 1, duration: 0.6, ease: "back.out(1.5)" }}, {a + 0.06 + i * 0.13:.2f});')
        js.append(f'          tl.to("#pc{i}", {{ y: 1720, rotation: {-rot[i] * 0.6}, duration: 0.3, ease: "power2.in" }}, {b - 0.34 + (len(k["polozky"]) - 1 - i) * 0.03:.2f});')
        sfx.append((a + 0.4 + i * 0.13, 0.12))
    js.append(f'          tl.fromTo("#cards-dim", {{ opacity: 0 }}, {{ opacity: 0.5, duration: 0.3, ease: "power2.out" }}, {a:.2f});')
    js.append(f'          tl.to("#cards-dim", {{ opacity: 0, duration: 0.26, ease: "power2.in" }}, {b - 0.28:.2f});')
    html.append(f'      <div class="card-host clip" id="cards" data-start="{a:.2f}" data-duration="{b - a:.2f}" data-track-index="5">\n'
                f'        <div class="dim" id="cards-dim"></div>\n' + "\n".join(cards) + "\n      </div>")
    whoosh = [(a - 0.04, "whoosh-zoom.wav", 0.57, 0.22)]
else:
    whoosh = []

p = z.get("pilulka")
if p:
    a = p["od"] + S
    html.append(f'      <div class="card-host clip" id="cta" data-start="{a:.2f}" data-duration="{dur - a:.2f}" data-track-index="3">\n'
                f'        <div class="line" style="top: {p.get("y", 1060)}px"><span class="pill" id="pill">{p["text"]}</span></div>\n      </div>')
    js.append(f'          pop("#pill", {a:.2f});')
    sfx.append((a, 0.25))

pf, psync, pd = SFX["pop"]
audio = [f'      <audio id="sfx-{i}" src="sfx/{pf}" data-start="{max(0, s - psync):.2f}" data-duration="{pd}" data-track-index="{4 + i % 2}" data-volume="{v}"></audio>'
         for i, (s, v) in enumerate(sfx)]
for i, (s, f, d, v) in enumerate(whoosh):
    audio.append(f'      <audio id="sfx-w{i}" src="sfx/{f}" data-start="{s:.2f}" data-duration="{d}" data-track-index="6" data-volume="{v}"></audio>')
for i, tr in enumerate(z.get("prechody", [])):
    T, kind = tr[0] + S, tr[1]
    f, sync, d = SFX["zoom" if kind == "zoom" else "whip"]
    audio.append(f'      <audio id="sfx-tr{i}" src="sfx/{f}" data-start="{max(0, T - sync):.2f}" data-duration="{d}" data-track-index="7" data-volume="0.3"></audio>')
    if kind == "zoom":
        js.append(f"          zoomTr({T:.2f});")
    else:
        js.append(f"          whipTr({T:.2f}, {tr[2] if len(tr) > 2 else 1});")

upper = "uppercase" if st["verzalky"] else "none"
nl = "\n"
doc = f"""<!DOCTYPE html>
<html lang="cs">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width={W}, height={H}">
    <title>{z.get("titul", z["id"])}</title>
    <style>
      {nl.join(faces)}
      :root {{ --ink: {st["ink"]}; --paper: {st["paper"]}; --radius-box: {st["radius"]}px; }}
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background: #000; font-family: "{st["font"]}", "Avenir Next", "Segoe UI", "Helvetica Neue", Arial, sans-serif; }}
      #stage {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
      #video-wrap {{ position: absolute; inset: 0; overflow: hidden; }}
      #video-wrap video {{ width: 100%; height: 100%; object-fit: cover; }}
      .card-host {{ position: absolute; inset: 0; pointer-events: none; }}
      .line {{ position: absolute; left: 0; right: 0; height: 0; display: flex; justify-content: center; align-items: center; }}
      .box {{ display: block; background: var(--ink); color: var(--paper); font-weight: 700; text-transform: {upper}; letter-spacing: {st["prostrkani"]}em;
              line-height: 1; white-space: nowrap; border-radius: var(--radius-box); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.28); }}
      .box.md {{ font-size: 66px; padding: 20px 30px 15px; }}
      .box.lg {{ font-size: 112px; padding: 24px 36px 18px; }}
      .num {{ display: inline-block; min-width: 0.62em; text-align: center; }}
      .pill {{ display: block; background: var(--paper); color: var(--ink); font-weight: 700; font-size: 84px; letter-spacing: 0.01em; line-height: 1;
               padding: 26px 56px 20px; border-radius: 999px; white-space: nowrap; box-shadow: 0 14px 40px rgba(0, 0, 0, 0.3); }}
      .dim {{ position: absolute; inset: 0; background: #000; opacity: 0; }}
      .pcard {{ position: absolute; width: 460px; background: var(--paper); border-radius: 44px; overflow: hidden; box-shadow: 0 30px 70px rgba(0, 0, 0, 0.45); }}
      .pcard img {{ display: block; width: 460px; height: 330px; object-fit: cover; }}
      .pcard .title {{ color: var(--ink); font-weight: 700; font-size: 50px; line-height: 1; padding: 24px 30px 22px; white-space: nowrap; }}
    </style>
  </head>
  <body>
    <div id="stage" data-composition-id="{z["id"]}" data-start="0" data-duration="{dur:.2f}" data-fps="{FPS}" data-width="{W}" data-height="{H}">
      <div id="video-wrap">
        <video id="bg-video" src="input-video.mp4" playsinline data-has-audio="true" data-start="0" data-duration="{dur:.2f}" data-track-index="1"></video>
      </div>
{nl.join(html)}

{nl.join(audio)}

      <script src="{GSAP_SRC}"></script>
      <script>
        (function () {{
          const tl = window.gsap.timeline({{ paused: true }});
          // pop: z 30 % přes překmit na 100 % (~0,28 s); out: zmenšení a zmizení
          function pop(sel, t) {{ tl.fromTo(sel, {{ scale: 0.3, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.28, ease: "back.out(2.2)" }}, t); }}
          function out(sel, t, d) {{ tl.to(sel, {{ opacity: 0, scale: 0.92, duration: d || 0.14, ease: "power2.in" }}, t); }}
          // přechody na hlavních předělech: hýbe se jen video, 3 snímky ven před střihem, 5–6 dovnitř
          const W = "#video-wrap", OFF = {{ immediateRender: false }};
          function zoomTr(T) {{
            tl.fromTo(W, {{ scale: 1, x: 0, filter: "blur(0px)" }}, {{ ...OFF, scale: 1.25, filter: "blur(10px)", duration: 0.12, ease: "power2.in" }}, T - 0.12);
            tl.fromTo(W, {{ scale: 1.25, x: 0, filter: "blur(10px)" }}, {{ ...OFF, scale: 1, filter: "blur(0px)", duration: 0.24, ease: "power2.out" }}, T);
          }}
          function whipTr(T, dir) {{
            tl.fromTo(W, {{ scale: 1, x: 0, filter: "blur(0px)" }}, {{ ...OFF, scale: 1.35, x: -dir * 180, filter: "blur(16px)", duration: 0.12, ease: "power2.in" }}, T - 0.12);
            tl.fromTo(W, {{ scale: 1.35, x: dir * 180, filter: "blur(16px)" }}, {{ ...OFF, scale: 1, x: 0, filter: "blur(0px)", duration: 0.2, ease: "power3.out" }}, T);
          }}
{nl.join(js)}
          window.__timelines["{z["id"]}"] = tl;
        }})();
      </script>
    </div>
  </body>
</html>
"""
(pub / "index.html").write_text(doc, encoding="utf-8")
print(out, f"{dur:.2f} s, {len(z.get('texty', []))} textů, {len(z.get('prechody', []))} přechodů")
