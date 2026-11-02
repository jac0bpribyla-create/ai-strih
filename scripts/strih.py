"""Sestaví video ze střihového listu (EDL) – hrubý střih i jednoduché texty a titulky.

Použití:  python3 strih.py <projekt>/edl/<nazev>.json [--rychle]
Výstup:   <projekt>/export/<name>[_<hook>].mp4 + .srt (titulky pro CapCut)
Projekt:  projekt.json v kořeni (viz projekt.py). Formát EDL: references/strihovy-list.md.

Zkráceně:
  format     "9:16" (1080×1920, výchozí) | "4:5" (1080×1350) | "1:1" (1080×1080) | "16:9" (1920×1080, YouTube)
  fps        výchozí z projekt.json, jinak 30
  grade      barevná úprava všech záběrů (ffmpeg filtr)
  segments   A-roll za sebou: clip, in, out, [speech_from, speech_to, text, zoom, cx, cy, uhel, speed, mute, grade, lut]
             nebo {"karta": {logo, pozadi, text, delka}} = koncová karta
  overlays   B-roll přes A-roll (zvuk A-rollu běží dál): clip, src, t_from, t_to, [speed, zoom, cx, cy, uhel, grade, lut]
             nebo {"obrazek": "assets/web.png", t_from, t_to, [zoom_od, zoom_do, vypln]}
  popups     texty: text, t_from, t_to, y, [x, style, size, pop, sfx, barva, barva_textu, animace]
  titulky    titulky v obraze: {styl: karaoke|slova|vety, y, velikost, verzalky, max_znaku, zvyraznit, animace}
  animace    {typ: pop|rise|fall|zleva|zprava|fade|focus|zadna|box|psaci, sila 0–4, delka_ms, odskok, blikani, zablesk, tres}
  hudba      {soubor, od, pod_reci_db (12), ducking (true)}
  hooks      {"A-otazka": [segmenty], ...} → každý hook = samostatné video se stejným tělem
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from projekt import Projekt, ass_color  # noqa: E402

FORMATS = {"9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080), "16:9": (1920, 1080)}
FADE = 0.02
TARGET_LUFS, TARGET_TP = -14.0, -1.5
POP_GAIN = 0.15  # ~ -16 dB, pod hlasem
ASSETS = Path(__file__).resolve().parent.parent / "assets" / "sfx"

# Pop: z 30 % přes 112 % na 100 % za 230 ms, zmizí prolnutím za 120 ms.
POP_ANIM = r"\fscx30\fscy30\t(0,130,\fscx112\fscy112)\t(130,230,\fscx100\fscy100)\fad(0,120)"
STILL_ANIM = r"\fad(150,120)"
WORD_ANIM = r"\fscx88\fscy88\t(0,90,\fscx100\fscy100)"
UNITS = r"(mm|cm|m|km|kg|g|l|ml|%|Kč|kč|€|ks|let|dní|dnů|min|h|x|×)"
CAPTION_DEFAULTS = {
    "karaoke": {"velikost": 64, "max_znaku": 22, "y": 1180},
    "slova": {"velikost": 92, "max_znaku": 13, "y": 1150},
    "vety": {"velikost": 54, "max_znaku": 30, "y": 1200},
}


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def seg_dur(seg) -> float:
    if "karta" in seg:
        return float(seg["karta"].get("delka", 1.5))
    return (seg["out"] - seg["in"]) / seg.get("speed", 1.0)


def esc_ass(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", r"\N")


def ass_time(t: float) -> str:
    cs = round(max(t, 0) * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def srt_time(t: float) -> str:
    ms = round(max(t, 0) * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


# ---------- animace textů ----------
# Popup / titulky s polem "animace": {typ, sila 0–4, delka_ms 80–1000, odskok, blikani, zablesk, tres}.
# Bez "animace" platí POP_ANIM / STILL_ANIM / WORD_ANIM beze změny (stejné ASS bajt po bajtu).
ANIM_IDS = ["pop", "rise", "fall", "zleva", "zprava", "fade", "focus", "zadna", "box", "psaci"]
ANIM_MODS = ["odskok", "blikani", "zablesk", "tres"]
ANIM_EXIT, ANIM_FLASH, ANIM_GLOW_BLUR = 120, 200, 12
ANIM_FMT = {
    "boxX": lambda v: rf"\fscx{f100(v)}",
    "scale": lambda v: rf"\fscx{f100(v)}\fscy{f100(v)}",
    "rot": lambda v: rf"\frz{f100(v)}",
    "blur": lambda v: rf"\blur{f100(v)}",
    "color": lambda v: rf"\1c{v}",
    "glow": lambda v: rf"\alpha&H{v:02X}&",
}
ANIM_LAYER_TRACKS = {
    "main": ["scale", "rot", "blur", "color"], "text": ["scale", "rot", "blur", "color"],
    "box": ["boxX", "scale", "rot", "blur"], "glow": ["scale", "rot", "glow"],
    "shadow": ["scale", "rot"], "kbox": ["scale", "rot"],
}
ANIM_LAYER_PREFIX = {"box": r"\1a&HFF&", "text": r"\bord0\shad0", "glow": rf"\bord0\shad0\1c&H00FFFFFF\blur{ANIM_GLOW_BLUR}"}


def _half(x) -> int:
    return math.floor(x + 0.5)


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def f100(v: int) -> str:
    """Setiny (celé číslo) → text: 11200 → 112, 2640 → 26.4, -960 → -9.6."""
    m = abs(v)
    s = str(m // 100)
    if m % 100:
        r = f"{m % 100:02d}"
        s += "." + (r[:-1] if r.endswith("0") else r)
    return ("-" if v < 0 and m else "") + s


def has_anim(a) -> bool:
    return isinstance(a, dict) and a.get("typ") in ANIM_IDS


def anim_normalize(a, legacy: dict | None = None) -> dict:
    legacy = legacy or {}
    mods = {m: (isinstance(a, dict) and a.get(m) is True) for m in ANIM_MODS}
    if has_anim(a):
        sila = min(4, max(0, a["sila"])) if _num(a.get("sila")) else 1
        delka = min(1000, max(80, _half(a["delka_ms"]))) if _num(a.get("delka_ms")) else 220
        return {"typ": a["typ"], "sila": _half(sila * 100) / 100, "delka_ms": delka, **mods}
    mods = {m: False for m in ANIM_MODS}
    if legacy.get("kind") == "caption":
        if legacy.get("styl") == "slova":
            return {"typ": "slovo", "sila": 1, "delka_ms": 90, **mods}
        return {"typ": "zadna", "sila": 1, "delka_ms": 220, **mods}
    if legacy.get("pop") is False:
        return {"typ": "fade", "sila": 1, "delka_ms": 150, **mods}
    return {"typ": "pop", "sila": 1, "delka_ms": 230, **mods}


def anim_plan(a: dict, ctx: dict) -> dict:
    D, S = a["delka_ms"], _half(a["sila"] * 100)
    n = max(0, int(ctx.get("n") or 0))
    typ = a["typ"]
    if typ == "box" and not ctx.get("hasBox"):
        typ = "fade"
    if typ == "psaci" and (ctx.get("noType") or n < 1):
        typ = "fade"
    tr, fade_in, move, layers, text_fade, box_fade = {}, 0, None, ["main"], None, None

    def pulse():
        return {"init": None, "steps": [[0, D * 6 // 10, 10000 + 12 * S], [D * 6 // 10, D, 10000]]}

    if typ == "pop":
        ta = D * 13 // 23
        tr["scale"] = {"init": max(0, 10000 - 70 * S),
                       "steps": [[0, ta, 10000 + 12 * S * (2 if a["odskok"] else 1)], [ta, D, 10000]]}
    elif typ == "slovo":
        tr["scale"] = {"init": 8800, "steps": [[0, D, 10000]]}
    elif typ in ("rise", "fall", "zleva", "zprava"):
        fade_in = D
        horiz = typ in ("zleva", "zprava")
        base = 160 if horiz else 80
        sign = 1 if typ in ("rise", "zprava") else -1
        T = base * S

        def pt(v):
            return [v, 0] if horiz else [0, v]
        if a["odskok"]:
            O = base * S * 12 // 100
            B = D * 7 // 100 * 10
            move = [[0, B, pt(sign * T), pt(-sign * O)], [B, D, pt(-sign * O), [0, 0]]]
        else:
            move = [[0, D, pt(sign * T), [0, 0]]]
    elif typ == "fade":
        fade_in = D
        if a["odskok"]:
            tr["scale"] = pulse()
    elif typ == "focus":
        fade_in = D
        layers = ["box", "text"]
        tr["blur"] = {"init": 18 * S, "steps": [[0, D, 0]]}
        if a["odskok"]:
            tr["scale"] = pulse()
    elif typ == "box":
        layers = ["box", "text"]
        box_fade = [0, 0]
        text_fade = [D * 45 // 100, D]
        tb, ta = D * 55 // 100, D * 40 // 100
        tr["boxX"] = {"init": 0, "steps": [[0, ta, 10000 + 12 * S], [ta, tb, 10000]] if a["odskok"] else [[0, tb, 10000]]}
    elif a["odskok"]:  # zadna, psaci
        tr["scale"] = pulse()
    if a["tres"]:
        steps = []
        for i in (1, 2, 3, 4):
            amp = 3 * S * (5 - i) // 4
            steps.append([(i - 1) * 60, i * 60, amp if i % 2 else -amp])
        steps.append([240, 300, 0])
        tr["rot"] = {"init": None, "steps": steps}
    if a["zablesk"]:
        tr["color"] = {"init": "&H00FFFFFF", "steps": [[0, ANIM_FLASH, ctx.get("textColor") or "&H00FFFFFF"]]}
        tr["glow"] = {"init": 0, "steps": [[0, ANIM_FLASH, 255]]}
        layers = layers + ["glow"]
    main_fade = [0, fade_in]
    bounds = set()
    if move and len(move) > 1:
        bounds.add(move[0][1])
    if a["blikani"]:
        bounds.update(i * 40 for i in range(1, 7))
    char_b = None
    if typ == "psaci":
        T = min(900, D * n // 10)
        char_b = [k * T // (n * 10) * 10 for k in range(1, n)]
        bounds.update(char_b)
    bounds.discard(0)
    return {"typ": typ, "n": n, "tr": tr, "move": move, "layers": layers,
            "exit": ctx["exit"] if ctx.get("exit") is not None else ANIM_EXIT,
            "main_fade": main_fade, "box_fade": box_fade or main_fade, "text_fade": text_fade or main_fade,
            "bounds": sorted(bounds), "char_b": char_b, "blink": a["blikani"]}


def anim_pieces(P: dict, dur: int) -> list:
    starts = [0] + [b for b in P["bounds"] if b < dur]
    out = []
    for i, frm in enumerate(starts):
        if P["blink"] and frm < 240 and frm // 40 % 2 == 1:
            continue
        chars = None
        if P["char_b"] is not None:
            c = 1 + sum(1 for b in P["char_b"] if b <= frm)
            chars = None if c >= P["n"] else c
        out.append({"from": frm, "to": starts[i + 1] if i + 1 < len(starts) else None, "chars": chars})
    return out


def _anim_track(name: str, t: dict, p0: int, length):
    fmt = ANIM_FMT[name]
    start, s = t["init"], ""
    for t1, t2, v in t["steps"]:
        a, b = t1 - p0, t2 - p0
        if b <= 0:
            start = v
        elif length is not None and a >= length:
            continue
        else:
            s += rf"\t({a},{b},{fmt(v)})"
    return ("" if start is None else fmt(start)) + s


def _anim_fade(fd, EX: int, dur: int, frm: int, to) -> str:
    fin0, fin1 = fd
    if fin1 == 0 and EX == 0:
        return ""
    if frm == 0 and to is None and fin0 == 0:
        return rf"\fad({fin1},{EX})"
    return rf"\fade(255,0,255,{fin0 - frm},{fin1 - frm},{dur - EX - frm},{dur - frm})"


def _anim_pos(move, p0: int, X: int, Y: int) -> str:
    if not move:
        return rf"\pos({f100(X)},{f100(Y)})"
    for t1, t2, f, g in move:
        if p0 < t2:
            return rf"\move({f100(X + f[0])},{f100(Y + f[1])},{f100(X + g[0])},{f100(Y + g[1])},{t1 - p0},{t2 - p0})"
    g = move[-1][3]
    return rf"\pos({f100(X + g[0])},{f100(Y + g[1])})"


def anim_tags(a: dict, ctx: dict) -> list:
    """Události libass pro jeden text: [{from, to, layer, pos, tags, chars, hide}] (viz assTags v text-anim.js)."""
    P = anim_plan(a, ctx)
    dur, EX = ctx["dur"], P["exit"]
    X, Y = _half(ctx["x"] * 100), _half(ctx["y"] * 100)
    shadow = _half(ctx["shadowOff"] * 100) if _num(ctx.get("shadowOff")) else None
    kinds = ctx.get("layers") or ((["shadow"] if shadow is not None else []) + P["layers"])
    out = []
    for kind in kinds:
        for pc in anim_pieces(P, dur):
            frm, to = pc["from"], pc["to"]
            if ctx.get("window"):
                w0, w1 = ctx["window"]
                frm = max(frm, w0)
                ends = [x for x in (to, w1) if x is not None]
                to = min(ends) if ends else None
                if to is not None and frm >= to:
                    continue
            if kind == "glow":
                if frm >= ANIM_FLASH:
                    continue
                to = (ANIM_FLASH if ANIM_FLASH < dur else None) if to is None else min(to, ANIM_FLASH)
            length = None if to is None else to - frm
            tags = ANIM_LAYER_PREFIX.get(kind, "")
            for name in ANIM_LAYER_TRACKS[kind]:
                if name in P["tr"]:
                    tags += _anim_track(name, P["tr"][name], frm, length)
            fd = P["box_fade"] if kind == "box" else P["main_fade"] if kind in ("main", "kbox") else P["text_fade"]
            tags += _anim_fade(fd, EX, dur, frm, to)
            off = shadow if kind == "shadow" else 0
            chars = None if kind == "box" else pc["chars"]
            hide = None if chars is None else (r"\1a&HFF&" if kind == "main" and ctx.get("hasBox") else r"\alpha&HFF&")
            out.append({"from": frm, "to": to, "layer": kind, "pos": _anim_pos(P["move"], frm, X + off, Y + off),
                        "tags": tags, "chars": chars, "hide": hide})
    return out


def anim_text(raw: str, chars, hide) -> str:
    """Text události: prvních `chars` znaků (bez \\n) viditelných, zbytek skrytý tagem `hide`."""
    if chars is None:
        return esc_ass(raw)
    i = c = 0
    while i < len(raw) and c < chars:
        if raw[i] != "\n":
            c += 1
        i += 1
    rest = raw[i:]
    return esc_ass(raw[:i]) + (f"{{{hide}}}" + esc_ass(rest) if rest else "")


def ass_cs(cs: int) -> str:
    """Čas ASS ze setin (navazující události animace)."""
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


class Render:
    def __init__(self, proj: Projekt, edl: dict, fast: bool):
        self.p, self.edl, self.fast = proj, edl, fast
        self.W, self.H = FORMATS[edl.get("format", "9:16")]
        self.FPS = edl.get("fps", proj.cfg.get("fps", 30))
        self.grade = edl.get("grade", proj.cfg.get("grade", ""))
        self.inputs, self.chains, self.k = [], [], 0
        b = proj.cfg["barvy"]
        self.c_box, self.c_text, self.c_hi = b["box"], b["text"], b["zvyrazneni"]
        self.font = proj.cfg["font"]

    # ---------- vstupy ----------
    def add_input(self, *args) -> int:
        self.inputs += list(args)
        self.k += 1
        return self.k - 1

    def crop_filter(self, seg) -> str:
        """Výřez na cílový poměr stran (cover) + volitelné přiblížení se středem cx, cy (0–1).
        `uhel` (stupně, + = po směru hodinových ručiček) srovná křivý záběr; přiblížení se samo zvětší,
        aby po otočení nebyly vidět černé rohy."""
        info = self.p.info(seg["clip"])
        sw, sh = info["w"], info["h"]
        a = self.W / self.H
        cw0, ch0 = (sh * a, sh) if sw / sh > a else (sw, sw / a)
        z = max(seg.get("zoom", 1.0), 1.0)
        th = math.radians(seg.get("uhel", 0.0))
        cx, cy = seg.get("cx", 0.5) * sw, seg.get("cy", 0.5) * sh
        if th:
            c, s = abs(math.cos(th)), abs(math.sin(th))

            def fits(z):  # obal otočeného výřezu se musí vejít do zdroje (pro jistotu oba směry otočení)
                bw, bh = cw0 / z * c + ch0 / z * s, cw0 / z * s + ch0 / z * c
                dx, dy = cx - sw / 2, cy - sh / 2
                return all(abs(dx * math.cos(t) + dy * math.sin(t)) <= (sw - bw) / 2
                           and abs(-dx * math.sin(t) + dy * math.cos(t)) <= (sh - bh) / 2 for t in (th, -th))
            while not fits(z) and z < 4:
                z += 0.01
        cw, ch = round(cw0 / z / 2) * 2, round(ch0 / z / 2) * 2
        if cw >= sw - 1 and ch >= sh - 1 and not th:
            return ""
        x = min(max(cx - cw / 2, 0), sw - cw)
        y = min(max(cy - ch / 2, 0), sh - ch)
        rot = f"rotate={th:.5f}:ow=iw:oh=ih:c=black," if th else ""
        return f"{rot}crop={cw}:{ch}:{x:.0f}:{y:.0f}"

    def source(self, seg) -> list:
        """LUT a otočení zdroje. `lut` u záběru přebije projekt.json: false = bez LUTu, true = LUT projektu,
        "cesta.cube" = jiný LUT (např. slabší LUT pro záběr natočený v barvách místo S-Logu)."""
        if "lut" not in seg:
            return self.p.source_filters(seg["clip"])
        l = seg["lut"]
        f = f"lut3d=file='{self.p.path(l if isinstance(l, str) else self.p.cfg['lut']['soubor'])}':interp=tetrahedral" if l else ""
        return [x for x in (f, self.p.rotate_filter(seg["clip"])) if x]

    def picture(self, seg, speed: float) -> str:
        return ",".join(self.source(seg) + [f for f in [
            f"setpts=(PTS-STARTPTS)/{speed}",
            f"fps={self.FPS}",
            self.crop_filter(seg),
            f"scale={self.W}:{self.H}:flags=lanczos",
            self.grade,
            seg.get("grade", ""),  # úprava jednoho záběru (např. přesvětlený B-roll), po společné
            "setsar=1",
            "format=yuv420p",
        ] if f])

    def audio_chain(self, seg, k: int, dur: float) -> str:
        ch = self.p.info(seg["clip"])["channels"]
        pan = "pan=mono|c0=c0" if ch == 1 else "pan=mono|c0=0.5*c0+0.5*c1"
        af = [pan, "aresample=48000", "highpass=f=80"]
        speed = seg.get("speed", 1.0)
        if seg.get("mute"):
            af.append("volume=0")
        elif speed != 1.0:
            af.append(f"atempo={speed}")
        af += [f"apad=whole_dur={dur:.3f}", f"atrim=0:{dur:.3f}",
               f"afade=t=in:st=0:d={FADE}", f"afade=t=out:st={dur - FADE:.3f}:d={FADE}"]
        return f"[{k}:a]{','.join(af)}"

    # ---------- časy ----------
    def frame_starts(self):
        """Začátky úseků: podle střihového listu (přesné délky) a skutečné (celé snímky)."""
        exact, real, e, r = [], [], 0.0, 0.0
        for seg in self.edl["segments"]:
            exact.append(e)
            real.append(r)
            e += seg_dur(seg)
            r += max(1, round(seg_dur(seg) * self.FPS)) / self.FPS
        return exact, real

    def retime(self, t: float) -> float:
        """Čas ze střihového listu → čas ve videu: posun o zaokrouhlení nasbírané do začátku úseku."""
        k = max((i for i, s in enumerate(self.exact) if s <= t + 1e-6), default=0)
        return t + self.real[k] - self.exact[k]

    def snap(self, t: float) -> float:
        """B-roll, který začíná nebo končí do 1,5 snímku od střihu A-rollu, srovnat přesně na střih.
        Jinak na hranici problikne 1 snímek A-rollu (třeba když se úsek za ním ořízne o pár setin)."""
        b = min(self.real[1:] + [self.real[-1] + max(1, round(seg_dur(self.edl["segments"][-1]) * self.FPS)) / self.FPS],
                key=lambda x: abs(x - t), default=t)
        return b if abs(b - t) <= 1.5 / self.FPS else t

    # ---------- obraz ----------
    def segments(self, card_events: list):
        labels, t0 = [], 0.0
        for i, seg in enumerate(self.edl["segments"]):
            # Každý úsek má přesně n snímků a zvuk přesně n/FPS. Bez toho trim=duration zaokrouhlí obraz
            # podle časových značek zdroje někdy nahoru, jindy dolů, a B-rolly a popisky se ke konci
            # rozjedou se střihy (na hranici úseku pak problikne 1 snímek předchozího záběru).
            n = max(1, round(seg_dur(seg) * self.FPS))
            dur = n / self.FPS
            if "karta" in seg:
                c = seg["karta"]
                bg = c.get("pozadi", "#000000").replace("#", "0x")
                kc = self.add_input("-f", "lavfi", "-t", f"{dur:.3f}", "-i",
                                    f"color=c={bg}:s={self.W}x{self.H}:r={self.FPS}")
                base = f"[{kc}:v]format=yuv420p"
                if c.get("logo"):
                    kl = self.add_input("-loop", "1", "-framerate", str(self.FPS), "-t", f"{dur:.3f}",
                                        "-i", str(self.p.path(c["logo"])))
                    lw = int(self.W * c.get("logo_sirka", 0.6)) // 2 * 2
                    self.chains.append(f"[{kl}:v]scale={lw}:-2,format=rgba[lg{i}]")
                    self.chains.append(f"{base}[cb{i}]")
                    self.chains.append(f"[cb{i}][lg{i}]overlay=(W-w)/2:H*{c.get('y_logo', 0.42)}-h/2,"
                                       f"setsar=1,format=yuv420p,trim=end_frame={n}[v{i}]")
                else:
                    self.chains.append(f"{base},setsar=1,trim=end_frame={n}[v{i}]")
                ka = self.add_input("-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=mono")
                self.chains.append(f"[{ka}:a]atrim=0:{dur:.3f}[a{i}]")
                if c.get("text"):
                    card_events.append((t0, t0 + dur, c))
            else:
                speed = seg.get("speed", 1.0)
                src_dur = seg["out"] - seg["in"]
                kv = self.add_input("-ss", f"{seg['in']:.3f}", "-t", f"{src_dur + 0.2 * speed:.3f}",
                                    "-i", str(self.p.clip_path(seg["clip"])))
                self.chains.append(f"[{kv}:v]{self.picture(seg, speed)},trim=end_frame={n}[v{i}]")
                if self.p.info(seg["clip"])["channels"]:
                    self.chains.append(f"{self.audio_chain(seg, kv, dur)}[a{i}]")
                else:
                    ka = self.add_input("-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=mono")
                    self.chains.append(f"[{ka}:a]atrim=0:{dur:.3f}[a{i}]")
            labels.append(f"[v{i}][a{i}]")
            t0 += dur
        n = len(self.edl["segments"])
        self.chains.append(f"{''.join(labels)}concat=n={n}:v=1:a=1[base][acat]")
        self.chains.append("[acat]acompressor=threshold=-24dB:ratio=2.5:attack=8:release=160:makeup=4dB,"
                           "volume=8dB,alimiter=limit=0.5:attack=3:release=60:level=false[voice]")
        return t0

    def overlays(self, vlast: str) -> str:
        h = 0.5 / self.FPS  # půl snímku: hranice na mřížce snímků se zaokrouhlí vždy stejně (od včetně, do bez)
        for j, o in enumerate(self.edl.get("overlays", [])):
            dur = o["t_to"] - o["t_from"]
            t0, t1 = o["t_from"] - h, o["t_to"] - h
            if "obrazek" in o:
                n = max(round(dur * self.FPS), 1)
                zo, zd = o.get("zoom_od", 1.0), o.get("zoom_do", 1.06)
                kk = self.add_input("-loop", "1", "-framerate", str(self.FPS), "-t", f"{dur + 0.2:.3f}",
                                    "-i", str(self.p.path(o["obrazek"])))
                W2, H2 = self.W * 2, self.H * 2
                fit = (f"scale={W2}:{H2}:force_original_aspect_ratio=increase,crop={W2}:{H2}"
                       if o.get("vypln", "cover") == "cover" else
                       f"scale={W2}:{H2}:force_original_aspect_ratio=decrease,"
                       f"pad={W2}:{H2}:(ow-iw)/2:(oh-ih)/2:color={o.get('pozadi', '#000000').replace('#', '0x')}")
                self.chains.append(
                    f"[{kk}:v]{fit},zoompan=z='{zo}+({zd}-{zo})*on/{n}':x='iw/2-(iw/zoom/2)':"
                    f"y='ih/2-(ih/zoom/2)':d=1:s={self.W}x{self.H}:fps={self.FPS},"
                    f"trim=duration={dur + 2 / self.FPS:.3f},setsar=1,format=yuv420p,setpts=PTS-STARTPTS+{t0:.4f}/TB[o{j}]")
            else:
                speed = o.get("speed", 1.0)
                kk = self.add_input("-ss", f"{o['src']:.3f}", "-t", f"{(dur + 2 / self.FPS) * speed + 0.1:.3f}",
                                    "-i", str(self.p.clip_path(o["clip"])))
                # +2 snímky rezervy: začátek B-rollu nesedí na mřížku snímků, bez rezervy mu chybí poslední snímek
                # a overlay (eof_action=pass) na 1 snímek ukáže A-roll pod ním (problik). Konec hlídá enable.
                self.chains.append(f"[{kk}:v]{self.picture(o, speed)},trim=duration={dur + 2 / self.FPS:.3f},"
                                   f"setpts=PTS+{t0:.4f}/TB[o{j}]")
            self.chains.append(f"[{vlast}][o{j}]overlay=0:0:eof_action=pass:"
                               f"enable='between(t,{t0:.4f},{t1:.4f})'[vo{j}]")
            vlast = f"vo{j}"
        return vlast

    # ---------- titulky ----------
    def tokens(self, seg, t0: float) -> list:
        """Slova úseku s časy na výsledné ose. Opravený text z EDL dostane časy z Whisperu,
        když sedí počet slov; jinak se rozprostře přes úsek řeči podle délky slov."""
        speed = seg.get("speed", 1.0)
        a, b = seg["in"], seg["out"]
        # Slovo patří do úseku, když jeho střed leží uvnitř (Whisper dává začátky vět o 0,3–0,5 s dřív).
        ww = [w for w in self.p.words(seg["clip"]) if a <= (w["s"] + w["e"]) / 2 < b]
        toks = seg["text"].split() if seg.get("text") else [w["w"] for w in ww]
        if ww and len(ww) == len(toks):
            times = [(max(w["s"], a), min(w["e"], b)) for w in ww]
            if "speech_from" in seg:
                times[0] = (max(times[0][0], seg["speech_from"]), times[0][1])
        else:
            s0, s1 = seg.get("speech_from", a), seg.get("speech_to", b)
            weights = [len(t) + 1 for t in toks]
            tot, t, times = sum(weights) or 1, s0, []
            for wt in weights:
                d = (s1 - s0) * wt / tot
                times.append((t, t + d))
                t += d
        out = [[tok, t0 + (s - a) / speed, t0 + (e - a) / speed] for tok, (s, e) in zip(toks, times)]
        merged = []
        for tok in out:  # číslo drží s jednotkou (15 mm, 150 kg) nezlomitelnou mezerou
            if merged and re.fullmatch(r"[\d.,]+", merged[-1][0]) and re.fullmatch(UNITS + r"[.,!?]?", tok[0]):
                merged[-1] = [merged[-1][0] + " " + tok[0], merged[-1][1], tok[2]]
            else:
                merged.append(tok)
        return merged

    @staticmethod
    def chunk(tokens: list, max_chars: int, orphans: bool) -> list:
        chunks, cur = [], []
        for t in tokens:
            if cur and len(" ".join(x[0] for x in cur + [t])) > max_chars:
                chunks.append(cur)
                cur = []
            cur.append(t)
            if len(cur) >= 2 and re.search(r"[.?!,:;]$", t[0]):
                chunks.append(cur)
                cur = []
        if cur:
            chunks.append(cur)
        if orphans:
            return chunks
        out = []
        for c in chunks:  # osamocené slovo přilepit k předchozímu řádku
            if (out and len(c) == 1 and not re.search(r"[.?!]$", out[-1][-1][0])
                    and len(" ".join(x[0] for x in out[-1] + c)) <= max_chars + 6):
                out[-1] = out[-1] + c
            else:
                out.append(c)
        return out

    def caption_chunks(self, cfg: dict) -> list:
        """[(start, end, [tokens])] pro celé video."""
        styl = cfg.get("styl", "karaoke")
        if styl not in CAPTION_DEFAULTS:  # "zadne" = jen .srt, rozdělení jako u vět
            styl, cfg = "vety", {}
        d = CAPTION_DEFAULTS[styl]
        res, t0 = [], 0.0
        for i, seg in enumerate(self.edl["segments"]):
            if hasattr(self, "real"):
                t0 = self.real[i]
            dur = seg_dur(seg)
            if "karta" not in seg and not seg.get("mute") and (seg.get("text") or self.p.words(seg["clip"])):
                toks = self.tokens(seg, t0)
                chunks = self.chunk(toks, cfg.get("max_znaku", d["max_znaku"]), orphans=(styl == "slova"))
                for ci, c in enumerate(chunks):
                    start = c[0][1]
                    nxt = chunks[ci + 1][0][1] if ci + 1 < len(chunks) else None
                    end = nxt if nxt is not None and nxt - c[-1][2] < 0.6 else c[-1][2] + 0.2
                    end = min(max(end, start + 0.25), t0 + dur)
                    res.append((start, end, c))
            t0 += dur
        return res

    def caption_events(self, cfg: dict, chunks: list) -> list:
        if has_anim(cfg.get("animace")):
            return self.caption_anim_events(cfg, chunks)
        styl = cfg.get("styl", "karaoke")
        d = CAPTION_DEFAULTS[styl]
        y = cfg.get("y", d["y"])
        x = self.W // 2
        upper = cfg.get("verzalky", styl == "slova")
        hi = [h.lower() for h in cfg.get("zvyraznit", [])]
        hc = ass_color(cfg.get("barva", self.c_hi))
        disp = [[re.sub(r"[.,;:]+$", "", t[0]) for t in c] for _, _, c in chunks]
        if upper:
            disp = [[w.upper() for w in ws] for ws in disp]
        ev = []
        for (s, e, c), ws in zip(chunks, disp):
            pos = rf"\pos({x},{y})"
            if styl == "karaoke":
                ev.append(f"Dialogue: 1,{ass_time(s)},{ass_time(e)},Tit,,0,0,0,,{{{pos}}}{esc_ass(' '.join(ws))}")
                for i, t in enumerate(c):
                    ws_i = max(t[1], s)
                    we_i = c[i + 1][1] if i + 1 < len(c) else e
                    if we_i <= ws_i:
                        continue
                    # Mezery musí být mimo zvýrazněný úsek, jinak box přesahuje na další slovo.
                    line = ""
                    for j, w in enumerate(ws):
                        gap = " " if j else ""
                        line += (rf"{{\alpha&HFF&}}{gap}{{\alpha&H00&}}{esc_ass(w)}{{\alpha&HFF&}}" if j == i
                                 else rf"{{\alpha&HFF&}}{gap}{esc_ass(w)}")
                    ev.append(f"Dialogue: 2,{ass_time(ws_i)},{ass_time(we_i)},TitBox,,0,0,0,,{{{pos}}}{line}")
            else:
                parts = []
                wc = ass_color(self.c_text)
                for t, w in zip(c, ws):
                    key = re.search(r"\d", w) or t[0].lower().strip(".,!?") in hi
                    parts.append((rf"{{\1c{hc}}}" + esc_ass(w) + rf"{{\1c{wc}}}") if key else esc_ass(w))
                anim = WORD_ANIM if styl == "slova" else ""
                style = "TitBig" if styl == "slova" else "Tit"
                ev.append(f"Dialogue: 1,{ass_time(s)},{ass_time(e)},{style},,0,0,0,,{{{pos}{anim}}}" + " ".join(parts))
        return ev

    def caption_anim_events(self, cfg: dict, chunks: list) -> list:
        """Titulky s "animace": animace na každý řádek (u karaoke i na zvýraznění slova, psací stroj = fade)."""
        styl = cfg.get("styl", "karaoke")
        d = CAPTION_DEFAULTS[styl]
        y = cfg.get("y", d["y"])
        x = self.W // 2
        upper = cfg.get("verzalky", styl == "slova")
        hi = [h.lower() for h in cfg.get("zvyraznit", [])]
        hc = ass_color(cfg.get("barva", self.c_hi))
        wc = ass_color(self.c_text)
        disp = [[re.sub(r"[.,;:]+$", "", t[0]) for t in c] for _, _, c in chunks]
        if upper:
            disp = [[w.upper() for w in ws] for ws in disp]
        a = anim_normalize(cfg["animace"])
        ev = []
        for (s, e, c), ws in zip(chunks, disp):
            cs0, cs1 = round(max(s, 0) * 100), round(max(e, 0) * 100)
            ctx = {"x": x, "y": y, "dur": (cs1 - cs0) * 10, "exit": 0, "hasBox": False,
                   "n": len(" ".join(ws)), "textColor": wc, "noType": styl == "karaoke"}

            def span(k, end_t):
                end = ass_cs(cs0 + k["to"] // 10) if k["to"] is not None else ass_time(end_t)
                return f"{ass_cs(cs0 + k['from'] // 10)},{end}"
            if styl == "karaoke":
                for k in anim_tags(a, ctx):
                    ev.append(f"Dialogue: 1,{span(k, e)},Tit,,0,0,0,,{{{k['pos']}{k['tags']}}}{esc_ass(' '.join(ws))}")
                for i, t in enumerate(c):
                    ws_i = max(t[1], s)
                    we_i = c[i + 1][1] if i + 1 < len(c) else e
                    if we_i <= ws_i:
                        continue
                    line = ""
                    for j, w in enumerate(ws):
                        gap = " " if j else ""
                        line += (rf"{{\alpha&HFF&}}{gap}{{\alpha&H00&}}{esc_ass(w)}{{\alpha&HFF&}}" if j == i
                                 else rf"{{\alpha&HFF&}}{gap}{esc_ass(w)}")
                    win = [(round(max(ws_i, 0) * 100) - cs0) * 10, (round(max(we_i, 0) * 100) - cs0) * 10]
                    for k in anim_tags(a, {**ctx, "layers": ["kbox"], "window": win}):
                        ev.append(f"Dialogue: 2,{span(k, we_i)},TitBox,,0,0,0,,{{{k['pos']}{k['tags']}}}{line}")
            else:
                words = [(w, bool(re.search(r"\d", w) or t[0].lower().strip(".,!?") in hi)) for t, w in zip(c, ws)]
                style = "TitBig" if styl == "slova" else "Tit"
                for k in anim_tags(a, ctx):
                    ev.append(f"Dialogue: 1,{span(k, e)},{style},,0,0,0,,{{{k['pos']}{k['tags']}}}"
                              + self.cap_line(words, k["chars"], k["hide"], hc, wc))
        return ev

    @staticmethod
    def cap_line(words: list, chars, hide, hc: str, wc: str) -> str:
        """Řádek titulků (zvýrazněná slova barvou) – při psacím stroji prvních `chars` znaků, zbytek skrytý."""
        seq = []
        for j, (w, key) in enumerate(words):
            if j:
                seq.append((False, " "))
            seq += [(True, rf"\1c{hc}"), (False, w), (True, rf"\1c{wc}")] if key else [(False, w)]
        out, left = "", chars
        for tag, txt in seq:
            if tag:
                out += "{" + txt + "}"
            elif left is None or left >= len(txt):
                out += esc_ass(txt)
                left = None if left is None else left - len(txt)
            else:
                out += esc_ass(txt[:left]) + "{" + hide + "}" + esc_ass(txt[left:])
                left = None
        return out

    def ass_header(self, cap: dict) -> str:
        f = self.font
        d = CAPTION_DEFAULTS.get(cap.get("styl", "karaoke"), CAPTION_DEFAULTS["karaoke"])
        size = cap.get("velikost", d["velikost"])
        white, black = ass_color(self.c_text), "&H00000000"
        box, hi = ass_color(self.c_box), ass_color(self.c_hi)
        fmt = ("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
               "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
               "Alignment, MarginL, MarginR, MarginV, Encoding")
        return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {self.W}
PlayResY: {self.H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
{fmt}
Style: Box,{f},110,{white},&H000000FF,{box},{box},-1,0,0,0,100,100,8,0,3,26,0,5,0,0,0,1
Style: Sub,{f},46,{white},&H000000FF,{box},{box},0,0,0,0,100,100,3,0,3,18,0,5,0,0,0,1
Style: Tit,{f},{size},{white},&H000000FF,{black},&H80000000,-1,0,0,0,100,100,1,0,1,5,2,5,0,0,0,1
Style: TitBig,{f},{size},{white},&H000000FF,{black},&H80000000,-1,0,0,0,100,100,1,0,1,6,3,5,0,0,0,1
Style: TitBox,{f},{size},{white},&H000000FF,{hi},{hi},-1,0,0,0,100,100,1,0,3,7,0,5,0,0,0,1
Style: Karta,{f},74,{white},&H000000FF,{black},{black},-1,0,0,0,100,100,6,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def popup_events(self) -> list:
        ev = []
        for p in self.edl.get("popups", []):
            if has_anim(p.get("animace")):
                ev += self.popup_anim_events(p)
                continue
            anim = POP_ANIM if p.get("pop", True) else STILL_ANIM
            tags = rf"\pos({p.get('x', self.W // 2)},{p['y']})"
            if "size" in p:
                tags += rf"\fs{p['size']}"
            if "barva" in p:
                tags += rf"\3c{ass_color(p['barva'])}\4c{ass_color(p['barva'])}"
            if "barva_textu" in p:
                tags += rf"\1c{ass_color(p['barva_textu'])}"
            if "font" in p:
                tags += rf"\fn{p['font']}"
            if "tucne" in p:
                tags += rf"\b{1 if p['tucne'] else 0}"
            if "obrys" in p:                       # tloušťka obrysu (0 = bez obrysu)
                tags += rf"\bord{p['obrys']}"
            if "proklad" in p:                     # mezery mezi písmeny (px)
                tags += rf"\fsp{p['proklad']}"
            if "stin" in p:
                # Měkký stín jako samostatná rozmazaná vrstva pod textem ({"posun": 3, "alfa": 0.5, "rozmazani": 6}).
                # \blur na hlavní vrstvě bez obrysu by rozmazal i písmo.
                s = p["stin"]
                a = int(round((1 - float(s.get("alfa", 0.5))) * 255))
                off = float(s.get("posun", 3))
                stags = (tags.replace(rf"\pos({p.get('x', self.W // 2)},{p['y']})",
                                      rf"\pos({p.get('x', self.W // 2) + off},{p['y'] + off})")
                         + rf"\bord0\shad0\1c&H000000&\1a&H{a:02X}&\blur{s.get('rozmazani', 6)}")
                ev.append(f"Dialogue: 2,{ass_time(p['t_from'])},{ass_time(p['t_to'])},{p.get('style', 'Box')},,0,0,0,,"
                          f"{{{stags}{anim}}}{esc_ass(p['text'])}")
                tags += r"\shad0"
            ev.append(f"Dialogue: 3,{ass_time(p['t_from'])},{ass_time(p['t_to'])},{p.get('style', 'Box')},,0,0,0,,"
                      f"{{{tags}{anim}}}{esc_ass(p['text'])}")
        return ev

    def popup_anim_events(self, p) -> list:
        """Popup s "animace" (anim_tags): víc vrstev / navazujících událostí, vzhled stejně jako popup_events."""
        x, y = p.get("x", self.W // 2), p["y"]
        look = ""
        if "size" in p:
            look += rf"\fs{p['size']}"
        if "barva" in p:
            look += rf"\3c{ass_color(p['barva'])}\4c{ass_color(p['barva'])}"
        if "barva_textu" in p:
            look += rf"\1c{ass_color(p['barva_textu'])}"
        if "font" in p:
            look += rf"\fn{p['font']}"
        if "tucne" in p:
            look += rf"\b{1 if p['tucne'] else 0}"
        if "obrys" in p:
            look += rf"\bord{p['obrys']}"
        if "proklad" in p:
            look += rf"\fsp{p['proklad']}"
        style = p.get("style", "Box")
        cs0, cs1 = round(max(p["t_from"], 0) * 100), round(max(p["t_to"], 0) * 100)
        ctx = {"x": x, "y": y, "dur": (cs1 - cs0) * 10, "exit": ANIM_EXIT, "hasBox": style in ("Box", "Sub"),
               "n": len(p["text"].replace("\n", "")), "textColor": ass_color(p.get("barva_textu", self.c_text))}
        stin = ""
        if "stin" in p:
            s = p["stin"]
            a = int(round((1 - float(s.get("alfa", 0.5))) * 255))
            ctx["shadowOff"] = float(s.get("posun", 3))
            stin = rf"\bord0\shad0\1c&H000000&\1a&H{a:02X}&\blur{s.get('rozmazani', 6)}"
        ev = []
        for k in anim_tags(anim_normalize(p["animace"]), ctx):
            extra = stin if k["layer"] == "shadow" else (r"\shad0" if stin else "")
            end = ass_cs(cs0 + k["to"] // 10) if k["to"] is not None else ass_time(p["t_to"])
            ev.append(f"Dialogue: {2 if k['layer'] == 'shadow' else 3},{ass_cs(cs0 + k['from'] // 10)},{end},{style},,0,0,0,,"
                      f"{{{k['pos']}{look}{extra}{k['tags']}}}{anim_text(p['text'], k['chars'], k['hide'])}")
        return ev

    # ---------- celé video ----------
    def build(self, export_dir: Path, tmp_dir: Path):
        name = self.edl["name"]
        export_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp = tmp_dir / f"{name}_mezikrok.mov"
        final = export_dir / f"{name}.mp4"

        card_events = []
        total = self.segments(card_events)
        self.exact, self.real = self.frame_starts()
        self.edl = {**self.edl,
                    "overlays": [{**o, "t_from": self.snap(self.retime(o["t_from"])), "t_to": self.snap(self.retime(o["t_to"]))}
                                 for o in self.edl.get("overlays", [])],
                    "popups": [{**q, "t_from": self.retime(q["t_from"]), "t_to": self.retime(q["t_to"])}
                               for q in self.edl.get("popups", [])]}
        vlast = self.overlays("base")

        cap = self.edl.get("titulky")
        chunks = self.caption_chunks(cap or {"styl": "vety"})
        events = self.popup_events()
        if cap and cap.get("styl", "karaoke") != "zadne":
            events += self.caption_events(cap, chunks)
        for s, e, c in card_events:
            events.append(f"Dialogue: 3,{ass_time(s)},{ass_time(e)},Karta,,0,0,0,,"
                          f"{{\\pos({self.W // 2},{int(self.H * c.get('y_text', 0.62))})"
                          f"\\1c{ass_color(c.get('barva_textu', '#FFFFFF'))}{STILL_ANIM}}}{esc_ass(c['text'])}")
        if events:
            ass = tmp_dir / f"{name}.ass"
            ass.write_text(self.ass_header(cap or {}) + "\n".join(events) + "\n", encoding="utf-8")
            self.chains.append(f"[{vlast}]ass='{ass}':fontsdir='{self.p.cfg['fonty']}'[vout]")
            vlast = "vout"

        pops = [p["t_from"] for p in self.edl.get("popups", []) if p.get("pop", True) and p.get("sfx", True)]
        alast = "voice"
        if pops:
            kp = self.add_input("-i", str(ASSETS / "pop.wav"))
            self.chains.append(f"[{kp}:a]aresample=48000,pan=mono|c0=c0,asplit={len(pops)}"
                               + "".join(f"[p{m}]" for m in range(len(pops))))
            for m, t in enumerate(pops):
                self.chains.append(f"[p{m}]adelay={round(t * 1000)}:all=1,volume={POP_GAIN}[pd{m}]")
            self.chains.append("[voice]" + "".join(f"[pd{m}]" for m in range(len(pops)))
                               + f"amix=inputs={len(pops) + 1}:normalize=0:duration=first[aout]")
            alast = "aout"

        n_ov = len(self.edl.get("overlays", []))
        print(f"Render {name}: {len(self.edl['segments'])} úseků, {n_ov} B-rollů, {len(events)} textů, {total:.1f} s…",
              flush=True)
        run(["ffmpeg", "-v", "error", "-y", *self.inputs, "-filter_complex", ";".join(self.chains),
             "-map", f"[{vlast}]", "-map", f"[{alast}]", "-c:v", "libx264", "-crf", "14",
             "-preset", "veryfast" if self.fast else "medium", "-c:a", "pcm_s16le", str(tmp)])

        mix = self.mix_music(tmp, tmp_dir, total)
        audio_src = mix or tmp
        m = loudnorm_measure(audio_src)
        ln = (f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:linear=true:measured_I={m['input_i']}:"
              f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
              f"offset={m['target_offset']}") if valid_lufs(m) else "anull"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-i", str(audio_src), "-map", "0:v", "-map", "1:a",
             "-af", f"{ln},aresample=48000", "-c:v", "libx264", "-crf", "20" if self.fast else "17",
             "-preset", "veryfast" if self.fast else "slow", "-profile:v", "high", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)])
        write_srt(chunks, final.with_suffix(".srt"))
        tmp.unlink()
        if mix:
            mix.unlink()
        print(final)
        return final

    def mix_music(self, tmp: Path, tmp_dir: Path, total: float):
        h = self.edl.get("hudba")
        if not h:
            return None
        src = self.p.path(h["soubor"])
        od = float(h.get("od", 0))
        voice = loudnorm_measure(tmp)
        has_voice = valid_lufs(voice) and float(voice["input_i"]) > -45
        music = loudnorm_measure(src, ["-ss", f"{od:.3f}", "-t", f"{total:.3f}"])
        v_target = -15.0
        m_target = (v_target - float(h.get("pod_reci_db", 12))) if has_voice else -14.0
        gain = m_target - float(music["input_i"])
        out = tmp_dir / f"{tmp.stem}_mix.wav"
        mchain = (f"[1:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,aresample=48000,"
                  f"aformat=channel_layouts=stereo,volume={gain:.2f}dB,"
                  f"afade=t=in:st=0:d=0.25,afade=t=out:st={max(total - 1.0, 0):.3f}:d=1.0[m]")
        if has_voice:
            vchain = (f"[0:a]loudnorm=I={v_target}:TP=-2:LRA=11:linear=true:measured_I={voice['input_i']}:"
                      f"measured_TP={voice['input_tp']}:measured_LRA={voice['input_lra']}:"
                      f"measured_thresh={voice['input_thresh']}:offset={voice['target_offset']},"
                      f"aresample=48000,pan=stereo|c0=c0|c1=c0")
            if h.get("ducking", True):
                graph = (f"{vchain},asplit=2[vm][vk];{mchain};"
                         "[m][vk]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350[md];"
                         "[vm][md]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.84:level=false[a]")
            else:
                graph = f"{vchain}[vm];{mchain};[vm][m]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.84:level=false[a]"
        else:
            graph = f"{mchain};[m]alimiter=limit=0.84:level=false[a]"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-ss", f"{od:.3f}", "-i", str(src),
             "-filter_complex", graph, "-map", "[a]", "-c:a", "pcm_s16le", str(out)])
        return out


def loudnorm_measure(path: Path, pre: list | None = None) -> dict:
    err = run(["ffmpeg", "-hide_banner", *(pre or []), "-i", str(path), "-vn", "-af",
               f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:print_format=json", "-f", "null", "-"]).stderr
    return json.loads(err[err.rindex("{"): err.rindex("}") + 1])


def valid_lufs(m: dict) -> bool:
    try:
        return float(m["input_i"]) > -70
    except (ValueError, KeyError):
        return False


def write_srt(chunks: list, path: Path):
    lines = []
    for n, (s, e, c) in enumerate(chunks, 1):
        lines.append(f"{n}\n{srt_time(s)} --> {srt_time(e)}\n{' '.join(t[0] for t in c)}\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def expand(edl: dict) -> list:
    """Varianty hooků: každý hook + společné tělo = samostatné video (A/B test v Meta Ads).
    Hook je seznam segmentů, nebo {"segments": [...], "popups": [...], "overlays": [...]}.
    Časy overlays/popups těla se u verzí s hooky počítají od začátku těla a posunou se o délku hooku;
    časy uvnitř hooku jsou od začátku videa."""
    if "hooks" not in edl:
        return [edl]
    out = []
    for key, hook in edl["hooks"].items():
        h = hook if isinstance(hook, dict) else {"segments": hook}
        shift = sum(seg_dur(s) for s in h["segments"])

        def moved(items):
            return [{**o, "t_from": o["t_from"] + shift, "t_to": o["t_to"] + shift} for o in items]

        out.append({**edl, "name": f"{edl['name']}_{key}",
                    "segments": h["segments"] + edl["segments"],
                    "overlays": h.get("overlays", []) + moved(edl.get("overlays", [])),
                    "popups": h.get("popups", []) + moved(edl.get("popups", []))})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--rychle", action="store_true", help="rychlý náhled (horší komprese)")
    a = ap.parse_args()
    edl_path = Path(a.edl)
    proj = Projekt(edl_path.parent)
    for variant in expand(json.loads(edl_path.read_text())):
        Render(proj, variant, a.rychle).build(proj.root / "export", proj.root / "tmp")
