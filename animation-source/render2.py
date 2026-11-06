"""Second batch of Vidravo animations. Reuses helpers from render.py."""
import sys, os, math, importlib.util, subprocess
OUT = sys.argv[1]; ONLY = sys.argv[2].split(",") if len(sys.argv) > 2 else None
_argv = sys.argv; sys.argv = ["render.py", OUT, "__none__"]
spec = importlib.util.spec_from_file_location("R", os.path.join(os.path.dirname(__file__), "render.py"))
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R); sys.argv = _argv
globals().update({k: v for k, v in vars(R).items() if not k.startswith("__") and k not in ("OUT", "ONLY", "ANIMS")})
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from global_land_mask import globe as GLM

def DR(im): return ImageDraw.Draw(im, "RGBA")
from PIL import ImageFont as _IF
_EMO = _IF.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109); _EC = {}
def EMOJI(ch, size):
    if (ch, size) not in _EC:
        im = Image.new("RGBA", (136, 128), (0, 0, 0, 0)); ImageDraw.Draw(im).text((0, 0), ch, font=_EMO, embedded_color=True)
        _EC[(ch, size)] = im.resize((int(s(size) * 136 / 128), int(s(size))), Image.LANCZOS)
    return _EC[(ch, size)]
YEL = "#FACC15"; GREEN = "#22C55E"

# ---------- world map helpers ----------
LAT_T, LAT_B = 78, -58
MX0, MW = 60, 1160; MH = MW * (LAT_T - LAT_B) / 360; MY0 = 150
def proj(lat, lon): return (MX0 + (lon + 180) / 360 * MW, MY0 + (LAT_T - lat) / (LAT_T - LAT_B) * MH)
_DOTS = []
for lat in np.arange(LAT_T - 1, LAT_B, -2.6):
    for lon in np.arange(-178, 180, 2.6):
        if GLM.is_land(lat, lon): _DOTS.append(proj(lat, lon))
_DOTS = np.array(_DOTS)
def world(bg, alpha=110, col=(90, 130, 200), r=2.6, dots=None):
    d = DR(bg)
    for x, y in (_DOTS if dots is None else dots):
        d.ellipse([s(x - r), s(y - r), s(x + r), s(y + r)], fill=(*col, alpha))
CITY = {"New York": (40.7, -74.0), "Paris": (48.9, 2.35), "Tokyo": (35.7, 139.7), "London": (51.5, -0.13), "Dubai": (25.2, 55.3),
        "Rome": (41.9, 12.5), "Cairo": (30.0, 31.2), "Bangkok": (13.8, 100.5), "Sydney": (-33.9, 151.2), "Rio": (-22.9, -43.2),
        "Cape Town": (-33.9, 18.4), "Mumbai": (19.1, 72.9), "Los Angeles": (34.05, -118.2)}
def P(c): return proj(*CITY[c])
def bez(a, b, lift, u):
    c = ((a[0] + b[0]) / 2, min(a[1], b[1]) - lift)
    return ((1 - u) ** 2 * a[0] + 2 * (1 - u) * u * c[0] + u * u * b[0], (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * c[1] + u * u * b[1])
def pin(bg, x, y, label, q, col=RED):
    if q <= .01: return
    L = new(); ld = DR(L)
    ld.ellipse([s(x - 22), s(y - 64), s(x + 22), s(y - 20)], fill=hexc(col))
    ld.polygon([(s(x - 19), s(y - 36)), (s(x + 19), s(y - 36)), (s(x), s(y))], fill=hexc(col))
    ld.ellipse([s(x - 8), s(y - 50), s(x + 8), s(y - 34)], fill=WHITE)
    if label:
        lw = tw(label, 22) + 30
        rrect(ld, (x - lw / 2, y + 10, x + lw / 2, y + 46), 18, fill=(255, 255, 255, 245)); text(ld, (x, y + 28), label, 22, hexc("#0E1424"))
    over(bg, shadow(scaled(L, q, x, y), 8, (0, 6), .45))
def map_bg(): return vgrad("#0A1222", "#0D1A30")

# ---------- maps ----------
def travel_route(t, T):
    bg = map_bg(); world(bg)
    A, B = P("New York"), P("Tokyo"); p = inout_cubic(prog(t, .8, 2.2))
    G = new(); g = DR(G); n = 140; pts = [bez(A, B, 170, i / n) for i in range(int(n * p) + 1)]
    for i in range(0, len(pts) - 1, 3):
        j = min(i + 2, len(pts) - 1); g.line([(s(pts[i][0]), s(pts[i][1])), (s(pts[j][0]), s(pts[j][1]))], fill=hexc(CYAN), width=int(s(5)))
    if len(pts) > 2: x, y = pts[-1]; g.ellipse([s(x - 8), s(y - 8), s(x + 8), s(y + 8)], fill=WHITE)
    over(bg, glow(G, 8, .9)); pin(bg, *A, "New York", out_back(prog(t, .2, .5))); pin(bg, *B, "Tokyo", out_back(prog(t, 2.9, .5)))
    return bg

def map_flight(t, T):
    bg = map_bg(); world(bg)
    A, B = P("London"), P("Dubai"); A2 = P("Los Angeles")
    A = P("Los Angeles"); B = P("Paris")
    p = inout_cubic(prog(t, .5, 3.2)); n = 160
    G = new(); g = DR(G)
    allp = [bez(A, B, 200, i / n) for i in range(n + 1)]
    for i in range(0, n, 4): g.line([(s(allp[i][0]), s(allp[i][1])), (s(allp[i + 2][0]), s(allp[i + 2][1]))], fill=(255, 255, 255, 50), width=int(s(3)))
    k = int(n * p)
    if k > 1: g.line([(s(x), s(y)) for x, y in allp[:k + 1]], fill=hexc(YEL), width=int(s(5)), joint="curve")
    over(bg, glow(G, 8, .8))
    x, y = allp[k]; x2, y2 = allp[min(k + 1, n)] if k < n else (x + 1, y)
    ang = math.degrees(math.atan2(y2 - y, x2 - x))
    PL = new(); pd = DR(PL)  # plane pointing right, rotated
    shape = [(30, 0), (8, -6), (-4, -30), (-12, -30), (-6, -6), (-22, -6), (-28, -16), (-34, -16), (-30, 0), (-34, 16), (-28, 16), (-22, 6), (-6, 6), (-12, 30), (-4, 30), (8, 6)]
    a = math.radians(ang); ca, sa = math.cos(a), math.sin(a)
    pd.polygon([(s(x + px * ca - py * sa), s(y + px * sa + py * ca)) for px, py in shape], fill=WHITE)
    if .02 < p < .995: over(bg, shadow(PL, 6, (0, 8), .5))
    pin(bg, *A, "Los Angeles", out_back(prog(t, .1, .5)), BRAND); pin(bg, *B, "Paris", out_back(prog(t, 3.6, .5)))
    d = DR(bg); lab = int(255 * prog(t, .3, .5))
    rrect(d, (MX0, 70, MX0 + 300, 118), 24, fill=(255, 255, 255, int(lab * .12)))
    text(d, (MX0 + 24, 94), "Flight · 11h 05m", 24, (255, 255, 255, lab), "Medium", anchor="lm")
    return bg

def map_pin_zoom(t, T):
    z = 1 + 1.6 * inout_cubic(prog(t, .3, 2.0)); cx, cy = P("Rome")
    bg = map_bg(); L = new(); world(L, 140)
    ZL = L.resize((int(CW * z), int(CH * z)), Image.BICUBIC)
    ox = int(s(640) - s(cx) * z); oy = int(s(380) - s(cy) * z)
    canvas = new(); canvas.paste(ZL, (ox, oy), ZL); over(bg, canvas)
    x, y = 640, 380; pulse = prog((t - 2.3) % 1.4, 0, 1.4) if t > 2.3 else 0
    G = new(); g = DR(G)
    if pulse:
        r = 20 + 90 * out_cubic(pulse); g.ellipse([s(x - r), s(y - r * .45), s(x + r), s(y + r * .45)], outline=hexc(RED, int(220 * (1 - pulse))), width=int(s(4)))
    over(bg, G); pin(bg, x, y, None, out_back(prog(t, 2.2, .5)))
    q = out_back(prog(t, 2.6, .5))
    if q > .01:
        C = new(); c = DR(C); rrect(c, (x + 40, y - 120, x + 380, y - 40), 18, fill=(255, 255, 255, 248))
        text(c, (x + 62, y - 96), "Your location", 28, hexc("#0E1424"), anchor="lm"); text(c, (x + 62, y - 62), "Rome, Italy", 20, hexc("#4B5563"), "Medium", anchor="lm")
        over(bg, shadow(scaled(C, q, x + 40, y - 80), 12, (0, 8), .4))
    return bg

def map_multi_stop(t, T):
    bg = map_bg(); world(bg)
    stops = ["London", "Cairo", "Mumbai", "Bangkok", "Sydney"]; pts = [P(c) for c in stops]
    G = new(); g = DR(G); seg = 3.6 / (len(stops) - 1)
    for i in range(len(stops) - 1):
        p = inout_cubic(prog(t, .6 + i * seg, seg * .9)); n = 50
        line = [bez(pts[i], pts[i + 1], 60, k / n) for k in range(int(n * p) + 1)]
        if len(line) > 1: g.line([(s(x), s(y)) for x, y in line], fill=hexc(CYAN), width=int(s(4)), joint="curve")
    over(bg, glow(G, 6, .9))
    for i, (c, (x, y)) in enumerate(zip(stops, pts)):
        q = out_back(prog(t, .3 + i * seg, .5))
        if q < .01: continue
        L = new(); ld = DR(L)
        ld.ellipse([s(x - 20), s(y - 20), s(x + 20), s(y + 20)], fill=hexc(BRAND)); ld.ellipse([s(x - 20), s(y - 20), s(x + 20), s(y + 20)], outline=WHITE, width=int(s(3)))
        text(ld, (x, y + 1), str(i + 1), 20, WHITE)
        lw = tw(c, 20) + 26; ly = y + 30 if i % 2 == 0 else y - 64
        rrect(ld, (x - lw / 2, ly, x + lw / 2, ly + 34), 17, fill=(255, 255, 255, 240)); text(ld, (x, ly + 17), c, 20, hexc("#0E1424"))
        over(bg, shadow(scaled(L, q, x, y), 8, (0, 6), .4))
    d = DR(bg); text(d, (MX0, 92), "World tour · 5 stops", 30, (255, 255, 255, int(255 * prog(t, 0, .5))), anchor="lm")
    return bg

_GL = []
for lat in np.arange(-84, 85, 3.0):
    step = 3.0 / max(.15, math.cos(math.radians(lat)))
    for lon in np.arange(-180, 180, step):
        if GLM.is_land(lat, lon if lon < 180 else lon - 360): _GL.append((math.radians(lat), math.radians(lon)))
_GL = np.array(_GL)
def map_globe(t, T):
    bg = radial("#0E1E3F", "#02050C", .5, .5, .9); cx, cy, r = 640, 380, 270
    G0 = new(); g0 = DR(G0); g0.ellipse([s(cx - r - 14), s(cy - r - 14), s(cx + r + 14), s(cy + r + 14)], fill=hexc(BRAND, 70)); over(bg, G0.filter(ImageFilter.GaussianBlur(s(26))))
    d = DR(bg); d.ellipse([s(cx - r), s(cy - r), s(cx + r), s(cy + r)], fill=hexc("#0B1733"))
    lon0 = -2 * math.pi * t / T; lat0 = math.radians(18)
    la, lo = _GL[:, 0], _GL[:, 1] + lon0
    x = np.cos(la) * np.sin(lo); y = np.cos(lat0) * np.sin(la) - np.sin(lat0) * np.cos(la) * np.cos(lo)
    z = np.sin(lat0) * np.sin(la) + np.cos(lat0) * np.cos(la) * np.cos(lo)
    for xi, yi, zi in zip(x, y, z):
        if zi <= 0: continue
        px, py = cx + xi * r, cy - yi * r; rr = 2.2 + 2.0 * zi; a = int(130 + 125 * zi)
        d.ellipse([s(px - rr), s(py - rr), s(px + rr), s(py + rr)], fill=(110, 190, 255, a))
    # arcs between cities
    def sp(lat, lon, h=1.0):
        la, lo = math.radians(lat), math.radians(lon) + lon0
        X = math.cos(la) * math.sin(lo); Y = math.cos(lat0) * math.sin(la) - math.sin(lat0) * math.cos(la) * math.cos(lo)
        Z = math.sin(lat0) * math.sin(la) + math.cos(lat0) * math.cos(la) * math.cos(lo); return X * h, Y * h, Z * h
    A = new(); ad = DR(A)
    for k, (c1, c2) in enumerate([("New York", "London"), ("London", "Dubai"), ("Dubai", "Tokyo"), ("Tokyo", "Sydney"), ("Rio", "Cape Town"), ("Los Angeles", "Tokyo")]):
        (la1, lo1), (la2, lo2) = CITY[c1], CITY[c2]; ph = ((t / T) * 2 + k * .37) % 1; seg = []
        for i in range(41):
            u = i / 40; h = 1 + .18 * math.sin(math.pi * u)
            la_ = lerp(la1, la2, u); lo_ = lerp(lo1, lo2 if abs(lo2 - lo1) < 180 else lo2 - 360 * np.sign(lo2 - lo1), u)
            X, Y, Z = sp(la_, lo_, h); seg.append((X, Y, Z, u))
        for i in range(40):
            X, Y, Z, u = seg[i]; X2, Y2, Z2, _ = seg[i + 1]
            if Z < .02 or Z2 < .02: continue
            a = int(255 * max(0, 1 - abs(u - ph) * 3)) if True else 255
            base = 60
            ad.line([(s(cx + X * r), s(cy - Y * r)), (s(cx + X2 * r), s(cy - Y2 * r))], fill=(250, 204, 21, max(base, a)), width=int(s(3)))
    over(bg, glow(A, 5, 1.0))
    d = DR(bg); text(d, (cx, 60), "GLOBAL REACH", 22, (255, 255, 255, 170), "Medium", spacing=8)
    return bg

# ---------- lower thirds ----------
def lt_gradient(t, T):
    out = new(); x0, y0 = 90, 530; en = out_cubic(prog(t, .1, .6)); lv = in_cubic(prog(t, T - .7, .6)); k = en * (1 - lv)
    name, role = "Daniel Kim", "Fitness Coach · 1.2M followers"
    w = (max(tw(name, 40), tw(role, 21, "Medium")) + 160) * k
    if w > 60:
        P_ = new(); pd = DR(P_)
        g = Image.new("RGBA", (CW, CH)); arr = np.zeros((CH, CW, 4), np.uint8)
        xs = np.linspace(0, 1, CW)[None, :, None]; c1 = np.array(hexc(BRAND), float); c2 = np.array(hexc(VIOLET), float)
        arr[:] = (c1 * (1 - xs) + c2 * xs).astype(np.uint8)
        mask = Image.new("L", (CW, CH), 0); ImageDraw.Draw(mask).rounded_rectangle([s(x0), s(y0), s(x0 + w), s(y0 + 104)], radius=s(52), fill=255)
        P_.paste(Image.fromarray(arr), (0, 0), mask)
        pd.ellipse([s(x0 + 10), s(y0 + 10), s(x0 + 94), s(y0 + 94)], fill=WHITE)
        text(pd, (x0 + 52, y0 + 54), "DK", 30, hexc(BRAND))
        T1 = new(); td = DR(T1); ty = 14 * (1 - out_cubic(prog(t, .45, .5)))
        text(td, (x0 + 118, y0 + 40 + ty), name, 40, WHITE, anchor="lm"); text(td, (x0 + 120, y0 + 76 + ty), role, 21, (230, 235, 255, 230), "Medium", anchor="lm")
        T1.putalpha(Image.fromarray(np.minimum(np.array(T1.split()[3]), np.array(mask))))
        P_.alpha_composite(T1); out.alpha_composite(shadow(P_, 16, (0, 10), .4))
    return out

def lt_minimal(t, T):
    out = new(); d = DR(out); x0, y = 100, 580; lv = in_cubic(prog(t, T - .7, .6))
    lw = 420 * out_cubic(prog(t, .1, .6)) * (1 - lv)
    if lw > 1: rrect(d, (x0, y - 2, x0 + lw, y + 2), 2, fill=WHITE)
    for txt, sz, w_, yy, st, up in (("Maya Patel", 52, "Bold", y - 40, .35, 1), ("Travel Photographer", 24, "Medium", y + 28, .55, -1)):
        p = out_cubic(prog(t, st, .5)) * (1 - lv)
        L = new(); ld = DR(L); text(ld, (x0, yy + up * 24 * (1 - p)), txt, sz, (255, 255, 255, int(255 * p)), w_, anchor="lm")
        mask = Image.new("L", (CW, CH), 0); md = ImageDraw.Draw(mask)
        md.rectangle([0, 0, CW, s(y - 3)] if up == 1 else [0, s(y + 3), CW, CH], fill=255)
        L.putalpha(Image.fromarray(np.minimum(np.array(L.split()[3]), np.array(mask))))
        out.alpha_composite(L)
    return shadow(out, 6, (0, 3), .55)

# ---------- titles ----------
def title_neon(t, T):
    bg = vgrad("#0B0710", "#120A1A"); d = DR(bg)
    for yy in range(0, 720, 36):  # brick rows
        off = 0 if (yy // 36) % 2 else 40
        for xx in range(-80, 1360, 80): rrect(d, (xx + off + 2, yy + 2, xx + off + 78, yy + 34), 3, fill=(255, 255, 255, 7))
    flick = 1.0
    for a, b in ((.9, 1.0), (1.15, 1.22), (1.5, 1.55)):
        if a < t < b: flick = .15
    on = prog(t, .6, .2) * flick * (1 - prog(t, T - .4, .4))
    N = new(); nd = DR(N); text(nd, (640, 330), "COMING", 120, hexc(PINK, int(255 * on))); text(nd, (640, 460), "SOON", 120, hexc(CYAN, int(255 * prog(t, 1.7, .15) * (1 - prog(t, T - .4, .4)))))
    over(bg, glow(glow(N, 6, 1.4), 26, 1.1)); return bg

def title_top5(t, T):
    bg = radial("#2A0E0E", "#090303", .5, .5, .9); lv = 1 - in_cubic(prog(t, T - .5, .5))
    for i in range(14):  # rays
        L = new(); ld = DR(L); a = math.radians(i * 360 / 14 + t * 12)
        ld.polygon([(s(640), s(330)), (s(640 + math.cos(a - .09) * 1200), s(330 + math.sin(a - .09) * 1200)), (s(640 + math.cos(a + .09) * 1200), s(330 + math.sin(a + .09) * 1200))], fill=(255, 80, 60, 18))
        over(bg, L)
    N = new(); nd = DR(N); text(nd, (520, 330), "TOP", 110, WHITE); text(nd, (790, 320), "5", 250, hexc(YEL))
    over(bg, shadow(scaled(N, out_back(prog(t, .2, .5), 2.4) * lv, 640, 330), 18, (0, 14), .6))
    q = out_cubic(prog(t, .9, .6)) * lv; w = 760 * q
    B = new(); bd = DR(B); rrect(bd, (640 - w / 2, 500, 640 + w / 2, 576), 12, fill=hexc(RED))
    if q > .6: text(bd, (640, 538), "Things you need to know", 36, (255, 255, 255, int(255 * prog(t, 1.2, .4))))
    over(bg, shadow(B, 12, (0, 8), .5)); return bg

# ---------- transitions ----------
def tr_circle(t, T):
    out = new(); d = DR(out); R_ = 760
    a = inout_cubic(prog(t, 0, .9)) * R_; b = inout_cubic(prog(t, 1.0, .9)) * R_
    if a > 1: d.ellipse([s(640 - a), s(360 - a), s(640 + a), s(360 + a)], fill=hexc(BRAND))
    a2 = inout_cubic(prog(t, .12, .9)) * R_
    if a2 > 1: d.ellipse([s(640 - a2), s(360 - a2), s(640 + a2), s(360 + a2)], fill=hexc("#0B1020"))
    if b > 1:
        arr = np.array(out); m = Image.new("L", (CW, CH), 0); ImageDraw.Draw(m).ellipse([s(640 - b), s(360 - b), s(640 + b), s(360 + b)], fill=255)
        arr[..., 3] = np.where(np.array(m) > 0, 0, arr[..., 3]); out = Image.fromarray(arr)
    return out

def tr_blinds(t, T):
    out = new(); d = DR(out); n = 6; cols = [BRAND, CYAN, VIOLET, "#0B1020", PINK, BRAND]
    for i in range(n):
        x0 = i * 1280 / n; w = 1280 / n + 1
        pin_ = inout_cubic(prog(t, .05 + i * .06, .5)); pout = inout_cubic(prog(t, 1.0 + i * .06, .5))
        top = lerp(-720, 0, pin_) + lerp(0, 720, pout) * (1 if i % 2 else -1)
        d.rectangle([s(x0), s(top), s(x0 + w), s(top + 720)], fill=hexc(cols[i]))
    return out

# ---------- overlays ----------
def ov_like_share(t, T):
    out = new(); lv = in_cubic(prog(t, T - .5, .5)); cy = 600
    items = [("like", "Like"), ("comment", "Comment"), ("share", "Share")]
    xs = [390, 640, 890]
    for i, ((k, lab), x) in enumerate(zip(items, xs)):
        q = out_back(prog(t, .2 + i * .18, .5)) * (1 - lv)
        if q < .01: continue
        L = new(); ld = DR(L); active = k == "like" and t > 1.6
        press = 1 - .1 * math.sin(math.pi * prog(t, 1.45, .25)) if k == "like" else 1
        rrect(ld, (x - 112, cy - 36, x + 112, cy + 36), 36, fill=hexc(BRAND) if active else (255, 255, 255, 245))
        ic = WHITE if active else hexc("#0E1424")
        e = EMOJI({"like": "👍", "comment": "💬", "share": "📤"}[k], 34); L.alpha_composite(e, (int(s(x - 72) - e.width / 2), int(s(cy) - e.height / 2)))
        text(ld, (x + 18, cy + 2), lab, 26, ic, anchor="mm")
        over(out, shadow(scaled(L, q * press, x, cy), 12, (0, 8), .45))
    if t > 1.45 and t < T - .5:
        cp = inout_cubic(prog(t, .7, .75)); sx, sy = lerp(700, 400, cp), lerp(700, cy + 6, cp)
        C = new(); cd = DR(C); pts = [(0, 0), (0, 40), (10, 31), (18, 48), (26, 45), (18, 28), (32, 28)]
        cd.polygon([(s(sx + a), s(sy + b)) for a, b in pts], fill=WHITE, outline=(20, 20, 20, 255), width=int(s(2.5))); out.alpha_composite(shadow(C, 4, (2, 3), .5))
    elif .7 < t <= 1.45:
        cp = inout_cubic(prog(t, .7, .75)); sx, sy = lerp(700, 400, cp), lerp(700, cy + 6, cp)
        C = new(); cd = DR(C); pts = [(0, 0), (0, 40), (10, 31), (18, 48), (26, 45), (18, 28), (32, 28)]
        cd.polygon([(s(sx + a), s(sy + b)) for a, b in pts], fill=WHITE, outline=(20, 20, 20, 255), width=int(s(2.5))); out.alpha_composite(shadow(C, 4, (2, 3), .5))
    return out

def ov_live(t, T):
    out = new(); lv = in_cubic(prog(t, T - .5, .5)); q = out_back(prog(t, .1, .5)) * (1 - lv)
    L = new(); ld = DR(L); x, y = 60, 50
    rrect(ld, (x, y, x + 128, y + 52), 10, fill=hexc(RED))
    blink = .35 + .65 * (.5 + .5 * math.cos(t * 6))
    ld.ellipse([s(x + 18), s(y + 18), s(x + 34), s(y + 34)], fill=(255, 255, 255, int(255 * blink)))
    text(ld, (x + 80, y + 27), "LIVE", 26, WHITE)
    viewers = int(1200 + 3100 * out_cubic(prog(t, .5, 3)))
    rrect(ld, (x + 138, y, x + 300, y + 52), 10, fill=(0, 0, 0, 170))
    ld.ellipse([s(x + 154), s(y + 16), s(x + 174), s(y + 36)], outline=WHITE, width=int(s(3))); ld.ellipse([s(x + 160), s(y + 22), s(x + 168), s(y + 30)], fill=WHITE)
    text(ld, (x + 186, y + 27), f"{viewers:,}", 24, WHITE, "Medium", anchor="lm")
    over(out, shadow(scaled(L, q, x + 150, y + 26), 10, (0, 6), .45)); return out

# ---------- backgrounds / education ----------
_BK = np.random.default_rng(11).random((60, 5))
def bg_bokeh(t, T):
    bg = vgrad("#160B05", "#05030A"); G = new(); g = DR(G)
    for a, b, c, e, f in _BK:
        y = 720 + 80 - ((t / T + a) % 1) * 880; x = b * 1280 + math.sin(t * 2 * math.pi / T + e * 6) * 30; r = 6 + 30 * c ** 2
        col = [(255, 190, 90), (255, 120, 80), (255, 230, 170)][int(f * 3)]
        g.ellipse([s(x - r), s(y - r), s(x + r), s(y + r)], fill=(*col, int(70 + 120 * (1 - c))))
    over(bg, glow(G.filter(ImageFilter.GaussianBlur(s(2))), 12, 1.0)); return bg

def edu_timeline(t, T):
    bg = vgrad("#0F172A", "#0B1120"); d = DR(bg); lv = 1 - in_cubic(prog(t, T - .5, .5))
    text(d, (640, 130), "How to make a video", 46, (255, 255, 255, int(255 * prog(t, 0, .5) * lv)))
    steps = [("1", "Plan", "Pick one idea"), ("2", "Script", "Write the hook"), ("3", "Record", "Film in good light"), ("4", "Publish", "Thumbnail + title")]
    x0, x1, y = 190, 1090, 360; fill = inout_cubic(prog(t, .5, 3.2)) * lv
    rrect(d, (x0, y - 4, x1, y + 4), 4, fill=(255, 255, 255, 30))
    G = new(); g = DR(G); rrect(g, (x0, y - 4, x0 + (x1 - x0) * fill, y + 4), 4, fill=hexc(CYAN)); over(bg, glow(G, 6, .8))
    for i, (n, a, b) in enumerate(steps):
        x = x0 + i * (x1 - x0) / 3; reached = fill >= i / 3 - .001; q = out_back(prog(t, .5 + i * 3.2 / 3 * .97, .4)) * lv
        L = new(); ld = DR(L)
        ld.ellipse([s(x - 54), s(y - 34), s(x + 34), s(y + 34)], fill=hexc(CYAN) if reached else hexc("#1E293B"), outline=WHITE if reached else (255, 255, 255, 60), width=int(s(3)))
        text(ld, (x, y + 1), n, 28, hexc("#0B1120") if reached else (255, 255, 255, 150))
        over(bg, scaled(L, max(q, .001) if reached else 1 * lv, x, y))
        if reached and q > .05:
            text(d, (x, y + 76), a, 32, (255, 255, 255, int(255 * clamp(q))))
            text(d, (x, y + 114), b, 20, (160, 175, 210, int(255 * clamp(q))), "Regular")
    return bg

def dark(t, T): return vgrad("#1a1f2e", "#0a0d14")

NEW = [
    ("travel-route", travel_route, 4.5, False),
    ("map-flight", map_flight, 4.8, False),
    ("map-pin-zoom", map_pin_zoom, 4.5, False),
    ("map-multi-stop", map_multi_stop, 5.2, False),
    ("map-globe", map_globe, 8, False),
    ("lower-third-gradient", lt_gradient, 5, True),
    ("lower-third-minimal", lt_minimal, 5, True),
    ("title-neon", title_neon, 4.5, False),
    ("title-top5", title_top5, 4, False),
    ("transition-circle", tr_circle, 2.0, True),
    ("transition-blinds", tr_blinds, 1.9, True),
    ("like-comment-share", ov_like_share, 4, True),
    ("live-badge", ov_live, 4, True),
    ("bokeh-loop", bg_bokeh, 6, False),
    ("edu-timeline", edu_timeline, 5, False),
]
for aid, fn, dur, overlay in NEW:
    if ONLY and aid not in ONLY: continue
    n = int(dur * FPS); procs = {"preview": enc(f"{OUT}/{aid}.mp4", H264)}
    if overlay:
        procs["green"] = enc(f"{OUT}/{aid}-green.mp4", H264)
        procs["alpha"] = enc(f"{OUT}/{aid}-alpha.webm", ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "34", "-deadline", "realtime", "-cpu-used", "8", "-auto-alt-ref", "0"])
        if os.environ.get("MOV"): procs["mov"] = enc(f"{OUT}/{aid}.mov", ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-qscale:v", "11", "-vendor", "apl0"])
    for i in range(n):
        t = i / FPS; fr = fn(t, dur)
        if fr.mode != "RGBA": fr = fr.convert("RGBA")
        fr = fr.resize((W, H), Image.LANCZOS)
        if overlay:
            procs["alpha"].stdin.write(fr.tobytes())
            if "mov" in procs: procs["mov"].stdin.write(fr.tobytes())
            g = Image.new("RGBA", (W, H), (0, 177, 64, 255)); g.alpha_composite(fr); procs["green"].stdin.write(g.tobytes())
            b = dark(t, dur).convert("RGBA").resize((W, H)); b.alpha_composite(fr); fr = b
        procs["preview"].stdin.write(fr.tobytes())
        if i == int(n * .6): fr.convert("RGB").resize((640, 360), Image.LANCZOS).save(f"{OUT}/{aid}.jpg", quality=84)
    for p in procs.values(): p.stdin.close(); p.wait()
    print("done", aid, flush=True)
