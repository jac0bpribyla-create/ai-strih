"""Měření třesu kamery a stabilizace záběrů (ffmpeg v tomhle stroji nemá vidstab → OpenCV).

Použití:
  uv run --with "opencv-python-headless==4.10.0.84" --with "numpy<2.3" python stabil.py mereni KLIP.mp4 […]
      → po sekundách: třes (% výšky obrazu, vysokofrekvenční chvění) a pohyb (plynulý posun, % výšky za s).
        Třes < 0.15 % = klidné, 0.15–0.35 % = jde stabilizovat, > 0.35 % = radši nebrat.
  uv run … python stabil.py stab KLIP.mp4 OD DO VYSTUP.mov [--rezim plynule|zamek] [--polomer 25] [--strop 1.15] [--otocit clock|cclock] [--maska x0,y0,x1,y1] [--jen-posun]
      → stabilizovaný úsek: ProRes 422 HQ 10 bit v plném rozlišení, bez zvuku, barvy beze změny
        (LUT dál řeší strih.py přes "lut": true). Dvě měření (hrubá + jemná korekce), ale jediné převzorkování
        (Lanczos) a nejmenší možný zoom (strop 1.15). plynule = vyhladí chvění, nechá vedení kamery
        (polomer v snímcích, 25 ≈ 1 s); zamek = jako ze stativu (chce víc zoomu).
        Nikdy nestabilizuj do 8bit H.264 – po LUTu a zesvětlení S-Logu je obraz zrnitý a rozmazaný.
Otočení podle metadat řeší ffmpeg (autorotate), takže svislé Sony záběry vyjdou na výšku.
"""
import json
import subprocess
import sys

import cv2
import numpy as np


MASKA = None  # (x0, y0, x1, y1) v 0–1: sledovat jen statickou část obrazu (přes záběr jde člověk)
JEN_POSUN = False  # True = jen posun (bez otáčení) – když otáčení chytá pohyb lidí v záběru
OTOC = ""  # "clock" | "cclock" – klip bez příznaku otočení (Sony občas nezapíše)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", path],
                         capture_output=True, text=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    w, h = s["width"], s["height"]
    rot = 0
    for sd in s.get("side_data_list", []):
        rot = int(sd.get("rotation", 0))
    if abs(rot) == 90 or OTOC in ("clock", "cclock"):
        w, h = h, w
    return w, h, float(d["format"]["duration"])


def frames(path, w, h, od=None, do=None, fps=25):
    cmd = ["ffmpeg", "-v", "error"]
    if od is not None:
        cmd += ["-ss", f"{od:.3f}"]
    cmd += ["-i", path]
    if do is not None:
        cmd += ["-t", f"{do - (od or 0):.3f}"]
    tr = f"transpose={OTOC}," if OTOC else ""
    cmd += ["-vf", f"{tr}fps={fps},scale={w}:{h}", "-pix_fmt", "bgr24", "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = w * h * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()


def transforms(grays):
    """Mezisnímkové posuny (dx, dy, úhel) z optického toku."""
    out = []
    prev = grays[0]
    mask = None
    if MASKA:
        h, w = prev.shape
        mask = np.zeros_like(prev)
        x0, y0, x1, y1 = MASKA
        mask[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = 255
    for g in grays[1:]:
        pts = cv2.goodFeaturesToTrack(prev, maxCorners=300, qualityLevel=0.01, minDistance=12, blockSize=3, mask=mask)
        m = None
        if pts is not None and len(pts) >= 8:
            nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, pts, None)
            ok = st.reshape(-1) == 1
            if ok.sum() >= 8:
                m, _ = cv2.estimateAffinePartial2D(pts[ok], nxt[ok])
        if m is None:
            out.append((0.0, 0.0, 0.0))
        else:
            out.append((m[0, 2], m[1, 2], 0.0 if JEN_POSUN else np.arctan2(m[1, 0], m[0, 0])))
        prev = g
    return np.array(out) if out else np.zeros((0, 3))


def smooth(traj, r):
    if len(traj) == 0:
        return traj
    k = np.ones(2 * r + 1) / (2 * r + 1)
    pad = np.pad(traj, ((r, r), (0, 0)), mode="edge")
    return np.stack([np.convolve(pad[:, i], k, mode="valid") for i in range(traj.shape[1])], axis=1)


def mereni(path, fps=25):
    w0, h0, dur = probe(path)
    h = 480
    w = int(round(w0 * h / h0 / 2) * 2)
    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames(path, w, h, fps=fps)]
    t = transforms(grays)
    traj = np.cumsum(t, axis=0)
    hf = traj - smooth(traj, 6)                # chvění (< ~0,25 s)
    vel = np.diff(smooth(traj, 12), axis=0, prepend=smooth(traj, 12)[:1])
    print(f"\n{path}  ({dur:.1f} s)\n   s   třes%  pohyb%/s")
    for s in range(int(len(t) / fps) + 1):
        sl = slice(s * fps, (s + 1) * fps)
        if len(hf[sl]) == 0:
            break
        jit = np.sqrt((hf[sl, :2] ** 2).sum(axis=1)).mean() / h * 100
        mov = np.sqrt((vel[sl, :2] ** 2).sum(axis=1)).mean() * fps / h * 100
        flag = "" if jit < 0.15 else ("  ~" if jit < 0.35 else "  ✗")
        print(f"{s:4d}  {jit:5.2f}  {mov:6.1f}{flag}")


def corr_matrix(dx, dy, da, cx, cy):
    """3×3 korekce: otočení o da kolem středu + posun (dx, dy)."""
    c, s = np.cos(da), np.sin(da)
    return np.array([[c, -s, cx - c * cx + s * cy + dx],
                     [s, c, cy - s * cx - c * cy + dy],
                     [0, 0, 1.0]])


def corrections(grays, rezim, r):
    """Korekce pro každý snímek včetně prvního (trajektorie začíná snímkem 0 = nula).
    Dřív měl snímek 0 korekci 0 i v režimu zamek → první snímek klipu poskočil (problik na každém střihu)."""
    t = transforms(grays)
    traj = np.vstack([np.zeros((1, 3)), np.cumsum(t, axis=0)]) if len(t) else np.zeros((len(grays), 3))
    target = (np.repeat(traj.mean(axis=0, keepdims=True), len(traj), axis=0) if rezim == "zamek"
              else smooth(traj, r))
    return target - traj, traj


def fits(mats, W, H, z):
    """True = při zoomu z žádný snímek nemá v obraze prázdný (zrcadlený) okraj."""
    corners = np.array([[0, 0, 1], [W, 0, 1], [0, H, 1], [W, H, 1]], float).T
    Z = np.array([[z, 0, W / 2 * (1 - z)], [0, z, H / 2 * (1 - z)], [0, 0, 1]])
    for m in mats:
        src = np.linalg.inv(Z @ m) @ corners
        if src[0].min() < -0.5 or src[1].min() < -0.5 or src[0].max() > W + 0.5 or src[1].max() > H + 0.5:
            return False
    return True


def min_zoom(mats, W, H, cap):
    """Nejmenší zoom, při kterém žádný snímek nemá v obraze prázdný (zrcadlený) okraj."""
    lo, hi = 1.0, cap
    for _ in range(20):
        z = (lo + hi) / 2
        lo, hi = (lo, z) if fits(mats, W, H, z) else (z, hi)
    return hi


def plan_mats(small, rezim, polomer, sw, sh, s):
    c1, traj = corrections(small, rezim, polomer)
    m1 = [corr_matrix(*c, sw / 2, sh / 2) for c in c1[: len(small)]]
    warped = [cv2.warpAffine(g, m[:2], (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
              for g, m in zip(small, m1)]
    c2, _ = corrections(warped, "plynule", 12)
    S, Si = np.diag([s, s, 1.0]), np.diag([1 / s, 1 / s, 1.0])
    return [Si @ corr_matrix(*b, sw / 2, sh / 2) @ a @ S for a, b in zip(m1, c2[: len(m1)])], traj


def stab(path, od, do, out, rezim="plynule", zoom=1.0, sirka=0, fps=25, polomer=25, strop=1.15):
    """Dva průchody měření (hrubá + jemná korekce), ale jediné převzorkování v plném rozlišení a 10 bitech.
    Výstup ProRes 422 HQ 10 bit, aby LUT a zesvětlení neodhalily pruhy a zrno."""
    w0, h0, _ = probe(path)
    W = sirka or w0
    H = int(round(h0 * W / w0 / 2) * 2)
    sh = 480
    sw = int(round(W * sh / H / 2) * 2)
    s = sh / H
    small = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames(path, sw, sh, od, do, fps)]
    # Když korekce nejde schovat do zoomu `strop`, zrcadlený okraj je vidět (zrcadlený člověk u kraje).
    # Proto postupně povolit plynulejší vedení kamery (menší poloměr), dokud se korekce do stropu nevejde.
    pokusy = [(rezim, polomer)] + [("plynule", r) for r in (25, 15, 10, 6, 3, 1)
                                   if rezim == "zamek" or r < polomer]
    for rz, r in pokusy:
        mats, traj = plan_mats(small, rz, r, sw, sh, s)
        if fits(mats, W, H, strop):
            break
        print(f"  {rz} r={r}: korekce se nevejde do zoomu {strop:.2f}, zkouším plynulejší")
    else:
        print(f"  pozor: ani nejplynulejší korekce se nevejde do zoomu {strop:.2f} – zrcadlený okraj, zkrať úsek")
    rezim = f"{rz} r={r}" if (rz, r) != (rezim, polomer) else rezim
    z = max(zoom, min_zoom(mats, W, H, strop))
    Z = np.array([[z, 0, W / 2 * (1 - z)], [0, z, H / 2 * (1 - z)], [0, 0, 1]])
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", f"{W}x{H}",
                          "-r", str(fps), "-i", "-", "-c:v", "prores_ks", "-profile:v", "3",
                          "-pix_fmt", "yuv422p10le", out], stdin=subprocess.PIPE)
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{od:.3f}", "-i", path, "-t", f"{do - od:.3f}",
           "-vf", (f"transpose={OTOC}," if OTOC else "") + f"fps={fps},scale={W}:{H}:flags=lanczos",
           "-pix_fmt", "rgb48le", "-f", "rawvideo", "-"]
    dec = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H * 3 * 2
    i = 0
    while True:
        b = dec.stdout.read(n)
        if len(b) < n:
            break
        f = np.frombuffer(b, np.uint16).reshape(H, W, 3)
        m = Z @ mats[min(i, len(mats) - 1)]
        p.stdin.write(cv2.warpAffine(f, m[:2], (W, H), flags=cv2.INTER_LANCZOS4,
                                     borderMode=cv2.BORDER_REFLECT).tobytes())
        i += 1
    dec.wait()
    p.stdin.close()
    p.wait()
    hf = traj - smooth(traj, 6)
    pred = np.sqrt((hf[:, :2] ** 2).sum(axis=1)).mean() / sh * 100 if len(hf) else 0
    print(f"{out}  ({i} sn., třes před {pred:.2f} %, režim {rezim}, zoom {z:.3f}, {W}×{H} ProRes 10 bit)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "mereni":
        for f in a[1:]:
            mereni(f)
    elif a and a[0] == "stab":
        opts = {"rezim": "plynule", "zoom": 1.0, "sirka": 0, "polomer": 25, "strop": 1.15, "otocit": "", "maska": "", "jen-posun": ""}
        pos = []
        i = 1
        while i < len(a):
            if a[i].startswith("--"):
                k = a[i][2:]
                if k == "jen-posun":
                    opts[k] = "1"
                    i += 1
                    continue
                opts[k] = a[i + 1] if k in ("rezim", "otocit", "maska") else float(a[i + 1])
                i += 2
            else:
                pos.append(a[i])
                i += 1
        OTOC = opts["otocit"]
        JEN_POSUN = bool(opts["jen-posun"])
        MASKA = tuple(float(x) for x in opts["maska"].split(",")) if opts["maska"] else None
        stab(pos[0], float(pos[1]), float(pos[2]), pos[3], opts["rezim"], float(opts["zoom"]), int(opts["sirka"]),
             polomer=int(opts["polomer"]), strop=float(opts["strop"]))
    else:
        print(__doc__)
