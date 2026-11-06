"""Render Vidravo motion graphics.

Each animation draws one RGBA frame at time t (design units 1280x720, drawn at
K x for antialiasing, then downscaled). Overlays are exported three ways:
preview MP4 (on a dark backdrop), green-screen MP4, and transparent WebM.
"""
import math, subprocess, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1280, 720, 25
K = 1.5
CW, CH = int(W * K), int(H * K)
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
ONLY = sys.argv[2].split(",") if len(sys.argv) > 2 else None
os.makedirs(OUT, exist_ok=True)

FD = "/usr/share/fonts/truetype/google-fonts/"
_fc = {}
def font(size, w="Bold"):
    k = (size, w)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FD + f"Poppins-{w}.ttf", int(size * K))
    return _fc[k]

# ---------- helpers ----------
def s(v): return v * K
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, start, dur): return clamp((t - start) / dur)
def out_cubic(x): return 1 - (1 - x) ** 3
def in_cubic(x): return x ** 3
def inout_cubic(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def out_back(x, c=1.7):
    c3 = c + 1
    return 1 + c3 * (x - 1) ** 3 + c * (x - 1) ** 2
def out_elastic(x):
    if x in (0, 1): return x
    return 2 ** (-10 * x) * math.sin((x * 10 - .75) * (2 * math.pi / 3)) + 1
def lerp(a, b, x): return a + (b - a) * x
def hexc(h, a=255):
    h = h.lstrip("#"); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)
def mix(c1, c2, x): return tuple(int(lerp(a, b, x)) for a, b in zip(c1, c2))

def over(bg, layer): bg.paste(layer, (0, 0), layer)

def new(): return Image.new("RGBA", (CW, CH), (0, 0, 0, 0))

def vgrad(c1, c2, w=CW, h=CH):
    a = np.linspace(0, 1, h)[:, None, None]
    c1 = np.array(hexc(c1), float); c2 = np.array(hexc(c2), float)
    arr = (c1 * (1 - a) + c2 * a).repeat(w, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGBA").convert("RGB")

def radial(cin, cout, cx=.5, cy=.45, r=.85):
    y, x = np.mgrid[0:CH, 0:CW]
    d = np.sqrt(((x / CW - cx) * (CW / CH)) ** 2 + (y / CH - cy) ** 2) / r
    d = np.clip(d, 0, 1)[..., None]
    a = np.array(hexc(cin), float); b = np.array(hexc(cout), float)
    return Image.fromarray((a * (1 - d) + b * d).astype(np.uint8), "RGBA").convert("RGB")

def text(d, xy, txt, size, fill, w="Bold", anchor="mm", spacing=0):
    f = font(size, w)
    if spacing:
        # manual letter spacing
        total = sum(d.textlength(ch, font=f) for ch in txt) + s(spacing) * (len(txt) - 1)
        x = s(xy[0]) - (total / 2 if anchor[0] == "m" else 0)
        for ch in txt:
            d.text((x, s(xy[1])), ch, font=f, fill=fill, anchor="l" + anchor[1])
            x += d.textlength(ch, font=f) + s(spacing)
        return
    d.text((s(xy[0]), s(xy[1])), txt, font=f, fill=fill, anchor=anchor)

def tw(txt, size, w="Bold"):
    return font(size, w).getlength(txt) / K

def rrect(d, box, r, fill=None, outline=None, width=0):
    x0, y0, x1, y1 = box
    if x1 - x0 <= 0 or y1 - y0 <= 0: return
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    d.rounded_rectangle([s(x0), s(y0), s(x1), s(y1)], radius=s(r), fill=fill, outline=outline, width=int(s(width)))

def glow(layer, radius=18, strength=1.0):
    g = layer.filter(ImageFilter.GaussianBlur(s(radius)))
    if strength != 1.0:
        a = np.array(g); a[..., 3] = np.clip(a[..., 3] * strength, 0, 255); g = Image.fromarray(a)
    out = new(); out.alpha_composite(g); out.alpha_composite(layer); return out

def shadow(layer, radius=16, offset=(0, 10), alpha=.45):
    a = np.array(layer)[..., 3].astype(float) * alpha
    sh = np.zeros((CH, CW, 4), np.uint8); sh[..., 3] = a.astype(np.uint8)
    sh = Image.fromarray(sh).filter(ImageFilter.GaussianBlur(s(radius)))
    out = new(); out.alpha_composite(sh, (int(s(offset[0])), int(s(offset[1])))); out.alpha_composite(layer); return out

def scaled(layer, scale, cx, cy, rot=0):
    """Scale/rotate a full-canvas layer about design point (cx, cy)."""
    if scale <= 0.001: return new()
    if abs(scale - 1) < 1e-3 and not rot: return layer
    img = layer
    if rot: img = img.rotate(rot, resample=Image.BICUBIC, center=(s(cx), s(cy)))
    w, h = int(CW * scale), int(CH * scale)
    img = img.resize((max(1, w), max(1, h)), Image.BICUBIC)
    out = new()
    out.alpha_composite(img, (int(s(cx) - s(cx) * scale), int(s(cy) - s(cy) * scale))) if True else None
    return out

def fade(layer, a):
    if a >= 1: return layer
    arr = np.array(layer); arr[..., 3] = (arr[..., 3] * clamp(a)).astype(np.uint8); return Image.fromarray(arr)

def arc_pts(cx, cy, r, a0, a1, n=120, wobble=0, seed=0):
    pts = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        rr = r + (math.sin(a * 3 + seed) * wobble)
        pts.append((s(cx + math.cos(a) * rr * 1.25), s(cy + math.sin(a) * rr)))
    return pts

def check(d, cx, cy, size, fill, width, p=1.0):
    pts = [(cx - size * .5, cy), (cx - size * .12, cy + size * .38), (cx + size * .55, cy - size * .4)]
    seg1 = clamp(p * 2); seg2 = clamp(p * 2 - 1)
    a = pts[0]; b = (lerp(pts[0][0], pts[1][0], seg1), lerp(pts[0][1], pts[1][1], seg1))
    d.line([(s(a[0]), s(a[1])), (s(b[0]), s(b[1]))], fill=fill, width=int(s(width)), joint="curve")
    if seg2 > 0:
        c = (lerp(pts[1][0], pts[2][0], seg2), lerp(pts[1][1], pts[2][1], seg2))
        d.line([(s(pts[1][0]), s(pts[1][1])), (s(c[0]), s(c[1]))], fill=fill, width=int(s(width)), joint="curve")

BRAND = "#1E7BFF"; CYAN = "#22D3EE"; VIOLET = "#8B5CF6"; PINK = "#F472B6"; RED = "#EF2B2B"
WHITE = (255, 255, 255, 255)

# ---------- animations ----------
def subscribe(t, T):
    L = new(); d = ImageDraw.Draw(L, "RGBA")
    cx, cy = 600, 360
    intro = out_back(prog(t, 0, .6)); outro = 1 - in_cubic(prog(t, T - .6, .6))
    clicked = t >= 2.0
    press = 1 - .06 * math.sin(math.pi * prog(t, 1.85, .25))
    bw, bh = 470, 120
    col = hexc("#2A2A2E") if clicked else hexc(RED)
    rrect(d, (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2), 24, fill=col)
    if clicked:
        check(d, cx - 160, cy, 34, WHITE, 8, out_cubic(prog(t, 2.0, .4)))
        text(d, (cx + 22, cy + 3), "SUBSCRIBED", 44, (220, 220, 225, 255))
    else:
        # play glyph + label
        d.polygon([(s(cx - 178), s(cy - 22)), (s(cx - 178), s(cy + 22)), (s(cx - 142), s(cy))], fill=WHITE)
        text(d, (cx + 28, cy + 3), "SUBSCRIBE", 48, WHITE)
    # ripple
    rp = prog(t, 1.95, .6)
    if 0 < rp < 1:
        r = 30 + 160 * out_cubic(rp)
        R = new(); ImageDraw.Draw(R).ellipse([s(cx + 60 - r), s(cy + 20 - r), s(cx + 60 + r), s(cy + 20 + r)], outline=(255, 255, 255, int(200 * (1 - rp))), width=int(s(5)))
        L.alpha_composite(R)
    btn = scaled(L, intro * press * outro, cx, cy)
    btn = shadow(btn, 20, (0, 14), .5)
    # bell
    B = new(); bd = ImageDraw.Draw(B, "RGBA")
    bx, by = cx + bw / 2 + 90, cy
    bi = out_back(prog(t, .35, .6)) * outro
    bd.ellipse([s(bx - 58), s(by - 58), s(bx + 58), s(by + 58)], fill=hexc("#2A2A2E"))
    bd.pieslice([s(bx - 26), s(by - 34), s(bx + 26), s(by + 18)], 180, 360, fill=WHITE)
    bd.polygon([(s(bx - 26), s(by - 8)), (s(bx + 26), s(by - 8)), (s(bx + 34), s(by + 18)), (s(bx - 34), s(by + 18))], fill=WHITE)
    rrect(bd, (bx - 36, by + 14, bx + 36, by + 24), 5, fill=WHITE)
    bd.ellipse([s(bx - 8), s(by + 24), s(bx + 8), s(by + 38)], fill=WHITE)
    bd.ellipse([s(bx - 5), s(by - 44), s(bx + 5), s(by - 34)], fill=WHITE)
    ring = prog(t, 2.25, 1.2)
    rot = 22 * math.sin(ring * math.pi * 6) * (1 - ring) if 0 < ring < 1 else 0
    if 0 < ring < 1:
        for side in (-1, 1):
            for k in (0, 1):
                a = int(255 * (1 - ring))
                x = bx + side * (68 + k * 16)
                bd.arc([s(x - 14), s(by - 24), s(x + 14), s(by + 10)], 300 if side > 0 else 120, 60 if side > 0 else 240, fill=(255, 255, 255, a), width=int(s(4)))
    bell = scaled(B.rotate(rot, resample=Image.BICUBIC, center=(s(bx), s(by - 40))), bi, bx, by)
    out = new(); out.alpha_composite(btn); out.alpha_composite(shadow(bell, 16, (0, 10), .45))
    # cursor
    cp = inout_cubic(prog(t, .8, 1.0))
    if t < T - .7 and t > .8:
        sx, sy = lerp(1060, cx + 60, cp), lerp(640, cy + 20, cp)
        if 1.85 < t < 2.1: sx += 0; sy += 3
        C = new(); cd = ImageDraw.Draw(C, "RGBA")
        pts = [(0, 0), (0, 46), (12, 35), (21, 55), (30, 51), (21, 32), (37, 32)]
        cd.polygon([(s(sx + x), s(sy + y)) for x, y in pts], fill=WHITE, outline=(20, 20, 20, 255), width=int(s(3)))
        out.alpha_composite(shadow(fade(C, prog(t, .8, .25) * (1 - prog(t, T - 1.0, .3))), 6, (2, 4), .5))
    return out

def lower_third(t, T):
    out = new(); d = ImageDraw.Draw(out, "RGBA")
    x0, y0 = 90, 520
    enter = out_cubic(prog(t, .1, .7)); leave = in_cubic(prog(t, T - .8, .6))
    bar = enter * (1 - leave)
    # accent stripe
    stripe_h = 120 * out_back(prog(t, 0, .45)) * (1 - leave)
    rrect(d, (x0, y0 + 60 - stripe_h / 2, x0 + 12, y0 + 60 + stripe_h / 2), 4, fill=hexc(BRAND))
    name = "Sarah Johnson"; role = "Founder · Bright Studio"
    pw = tw(name, 52) + 70
    w = pw * bar
    if w > 4:
        P = new(); pd = ImageDraw.Draw(P, "RGBA")
        rrect(pd, (x0 + 20, y0, x0 + 20 + w, y0 + 78), 10, fill=(255, 255, 255, 245))
        rw = (tw(role, 25, "Medium") + 60) * bar
        rrect(pd, (x0 + 20, y0 + 84, x0 + 20 + rw, y0 + 124), 8, fill=hexc("#0E1424", 235))
        # text clipped to panels
        T1 = new(); td = ImageDraw.Draw(T1, "RGBA")
        ty = 18 * (1 - out_cubic(prog(t, .45, .5)))
        text(td, (x0 + 52, y0 + 41 + ty), name, 50, hexc("#0E1424"), anchor="lm")
        text(td, (x0 + 50, y0 + 105 + ty * .6), role, 25, hexc(CYAN), "Medium", anchor="lm")
        mask = Image.new("L", (CW, CH), 0); md = ImageDraw.Draw(mask)
        md.rectangle([s(x0 + 20), s(y0), s(x0 + 20 + w), s(y0 + 78)], fill=255)
        md.rectangle([s(x0 + 20), s(y0 + 84), s(x0 + 20 + rw), s(y0 + 124)], fill=255)
        P.paste(T1, (0, 0), Image.composite(T1, Image.new("RGBA", (CW, CH)), mask).split()[3])
        out.alpha_composite(shadow(P, 18, (0, 12), .35))
    return out

def countdown(t, T):
    bg = radial("#16203A", "#05070D")
    d = ImageDraw.Draw(bg, "RGBA")
    cx, cy, r = 640, 360, 190
    n = 5 - int(t) if t < 5 else 0
    frac = 1 - (t % 1) if t < 5 else 0
    # ticks
    for i in range(60):
        a = i / 60 * 2 * math.pi
        l = 16 if i % 5 == 0 else 8
        c = (255, 255, 255, 90 if i % 5 == 0 else 40)
        d.line([(s(cx + math.cos(a) * (r + 40)), s(cy + math.sin(a) * (r + 40))), (s(cx + math.cos(a) * (r + 40 + l)), s(cy + math.sin(a) * (r + 40 + l)))], fill=c, width=int(s(2)))
    d.ellipse([s(cx - r), s(cy - r), s(cx + r), s(cy + r)], outline=(255, 255, 255, 30), width=int(s(18)))
    G = new(); gd = ImageDraw.Draw(G, "RGBA")
    if t < 5:
        gd.arc([s(cx - r), s(cy - r), s(cx + r), s(cy + r)], -90, -90 + 360 * frac, fill=hexc(CYAN), width=int(s(18)))
    over(bg, glow(G, 14))
    N = new(); nd = ImageDraw.Draw(N, "RGBA")
    if t < 5:
        pop = out_back(prog(t % 1, 0, .35), 2.2)
        text(nd, (cx, cy + 10), str(n), 190, WHITE)
        num = scaled(N, .4 + .6 * pop, cx, cy)
        num = fade(num, 1 - in_cubic(prog(t % 1, .75, .25)))
    else:
        pop = out_elastic(prog(t, 5, .8))
        text(nd, (cx, cy + 8), "GO!", 150, hexc(CYAN))
        num = glow(scaled(N, pop, cx, cy), 20, .8)
    over(bg, num)
    text(d, (cx, 90), "STARTING IN", 26, (255, 255, 255, 160), "Medium", spacing=8)
    return bg

def title_reveal(t, T):
    bg = vgrad("#130B2E", "#061226"); d = ImageDraw.Draw(bg, "RGBA")
    # soft orbs
    O = new(); od = ImageDraw.Draw(O, "RGBA")
    for i, (x, y, r, c) in enumerate([(300, 220, 220, VIOLET), (1000, 520, 260, BRAND), (980, 160, 140, PINK)]):
        dx = math.sin(t * .6 + i) * 30
        od.ellipse([s(x + dx - r), s(y - r), s(x + dx + r), s(y + r)], fill=hexc(c, 90))
    over(bg, O.filter(ImageFilter.GaussianBlur(s(90))))
    leave = in_cubic(prog(t, T - .7, .7))
    L = new(); ld = ImageDraw.Draw(L, "RGBA")
    a = int(255 * prog(t, .2, .5) * (1 - leave))
    text(ld, (640, 250), "CHAPTER 03", 26, (180, 200, 255, a), "Medium", spacing=10)
    words = ["How", "Volcanoes", "Work"]
    widths = [tw(w, 96) for w in words]; gap = 28
    x = 640 - (sum(widths) + gap * 2) / 2
    for i, w in enumerate(words):
        p = out_cubic(prog(t, .45 + i * .14, .7))
        W1 = new(); wd = ImageDraw.Draw(W1, "RGBA")
        text(wd, (x, 360 + 90 * (1 - p) + 60 * leave), w, 96, WHITE, anchor="lm")
        mask = Image.new("L", (CW, CH), 0); ImageDraw.Draw(mask).rectangle([0, s(290), CW, s(420)], fill=255)
        W1.putalpha(Image.fromarray((np.array(W1.split()[3]) * (np.array(mask) / 255)).astype(np.uint8)))
        L.alpha_composite(W1)
        x += widths[i] + gap
    ul = out_cubic(prog(t, 1.2, .8)) * (1 - leave)
    uw = 420 * ul
    rrect(ld, (640 - uw / 2, 440, 640 + uw / 2, 448), 4, fill=hexc(CYAN))
    a2 = int(255 * prog(t, 1.5, .6) * (1 - leave))
    text(ld, (640, 492), "Magma, pressure and the science of eruptions", 26, (200, 210, 235, a2), "Regular")
    over(bg, L)
    return bg

def _blobs(t, T, cols, n=4, base="#050816"):
    w, h = 320, 180
    y, x = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None]
    img = np.zeros((h, w, 3)) + np.array(hexc(base)[:3], float)
    ph = 2 * math.pi * t / T
    for i, c in enumerate(cols):
        cx = .5 + .32 * math.cos(ph + i * 1.7) * (1 if i % 2 else -1)
        cy = .5 + .3 * math.sin(ph * (1 if i % 2 else 2) + i)
        r2 = ((x - cx) * 1.7) ** 2 + (y - cy) ** 2
        wgt = np.exp(-r2 / .07)[..., None]
        img = img * (1 - wgt * .85) + np.array(hexc(c)[:3], float) * wgt * .85
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((CW, CH), Image.BICUBIC)
    # fine grain
    return im.convert("RGB")

def gradient_loop(t, T):
    return _blobs(t, T, [BRAND, VIOLET, CYAN, PINK])

def aurora_loop(t, T):
    return _blobs(t, T, ["#00E5A0", "#1E7BFF", "#7C3AED", "#06B6D4"], base="#020617")

_rng = np.random.default_rng(7)
_P = _rng.random((70, 4))
def plexus(t, T):
    bg = radial("#0B1736", "#02040A", .5, .5, 1.0)
    d = ImageDraw.Draw(bg, "RGBA")
    ph = 2 * math.pi * t / T
    pts = []
    for (a, b, c, e) in _P:
        x = (a * 1280 + math.cos(ph + c * 6.28) * 60) % 1280
        y = (b * 720 + math.sin(ph + e * 6.28) * 50) % 720
        pts.append((x, y))
    P = np.array(pts)
    for i in range(len(P)):
        dd = np.hypot(*(P - P[i]).T)
        for j in np.where((dd < 170) & (np.arange(len(P)) > i))[0]:
            a = int(140 * (1 - dd[j] / 170))
            d.line([(s(P[i][0]), s(P[i][1])), (s(P[j][0]), s(P[j][1]))], fill=(90, 170, 255, a), width=int(s(1.4)))
    G = new(); gd = ImageDraw.Draw(G, "RGBA")
    for x, y in P:
        gd.ellipse([s(x - 4), s(y - 4), s(x + 4), s(y + 4)], fill=hexc(CYAN))
    over(bg, glow(G, 6, 1.2))
    return bg

def swipe(t, T):
    out = new(); d = ImageDraw.Draw(out, "RGBA")
    cols = ["#0B1020", CYAN, BRAND]
    for i, c in enumerate(cols):
        pin = inout_cubic(prog(t, .05 + i * .1, .7)); pout = inout_cubic(prog(t, 1.15 + i * .1, .7))
        x0 = lerp(-1700, -200, pin) + lerp(0, 1900, pout)
        slant = 300
        d.polygon([(s(x0), 0), (s(x0 + 1700), 0), (s(x0 + 1700 - slant), CH), (s(x0 - slant), CH)], fill=hexc(c))
    return out

def swipe_preview_bg(t, T):
    bg = vgrad("#1b2235", "#0b0f19"); d = ImageDraw.Draw(bg, "RGBA")
    label = "Scene A" if t < 1.0 else "Scene B"
    text(d, (640, 360), label, 80, (255, 255, 255, 220))
    return bg

def bar_chart(t, T):
    bg = vgrad("#0E1424", "#070A14"); d = ImageDraw.Draw(bg, "RGBA")
    leave = in_cubic(prog(t, T - .5, .5))
    a = int(255 * prog(t, 0, .5) * (1 - leave))
    text(d, (140, 96), "Channel growth", 44, (255, 255, 255, a), anchor="lm")
    text(d, (140, 142), "Monthly subscribers, thousands", 22, (160, 175, 210, a), "Regular", anchor="lm")
    base, top = 610, 220
    for i in range(5):
        y = base - i * (base - top) / 4
        d.line([(s(140), s(y)), (s(1140), s(y))], fill=(255, 255, 255, int(28 * prog(t, 0, .5))), width=int(s(1.5)))
    vals = [12, 19, 27, 34, 48, 63]; months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    G = new(); gd = ImageDraw.Draw(G, "RGBA")
    bw = 110
    for i, v in enumerate(vals):
        p = out_back(prog(t, .4 + i * .18, .8), 1.2) * (1 - leave)
        h = (base - top) * v / 70 * p
        x = 190 + i * 160
        col = mix(hexc(BRAND), hexc(CYAN), i / 5)
        rrect(gd, (x, base - h, x + bw, base), 12, fill=col)
        rrect(gd, (x, base - min(h, 14), x + bw, base), 0, fill=col)
        if p > .05:
            text(d, (x + bw / 2, 644), months[i], 22, (170, 185, 215, a), "Medium")
            num = int(v * clamp(p))
            text(gd, (x + bw / 2, base - h - 26), f"{num}k", 26, (255, 255, 255, int(255 * clamp(p * 1.4))))
    over(bg, glow(G, 10, .6))
    return bg

def social_handle(t, T):
    out = new()
    cx, cy = 640, 600
    enter = out_back(prog(t, 0, .6)); leave = in_cubic(prog(t, T - .6, .6))
    handle = "@brightstudio"
    typed = handle[:int(len(handle) * prog(t, .6, .9))]
    pw = 110 + tw(handle, 44) + 40
    P = new(); pd = ImageDraw.Draw(P, "RGBA")
    x0 = cx - pw / 2
    rrect(pd, (x0, cy - 48, x0 + pw, cy + 48), 48, fill=(255, 255, 255, 250))
    # icon: gradient circle with play
    I = new(); idr = ImageDraw.Draw(I, "RGBA")
    idr.ellipse([s(x0 + 12), s(cy - 36), s(x0 + 84), s(cy + 36)], fill=hexc(RED))
    idr.polygon([(s(x0 + 40), s(cy - 16)), (s(x0 + 40), s(cy + 16)), (s(x0 + 64), s(cy))], fill=WHITE)
    P.alpha_composite(I)
    text(pd, (x0 + 104, cy + 3), typed, 44, hexc("#0E1424"), anchor="lm")
    if int(t * 3) % 2 == 0 and t < 1.8:
        cxp = x0 + 106 + tw(typed, 44)
        pd.rectangle([s(cxp), s(cy - 22), s(cxp + 4), s(cy + 24)], fill=hexc(BRAND))
    P = scaled(P, enter * (1 - leave), cx, cy)
    out.alpha_composite(shadow(P, 18, (0, 12), .45))
    # caption chip
    cp = out_back(prog(t, 1.6, .5)) * (1 - leave)
    if cp > .01:
        C = new(); cd = ImageDraw.Draw(C, "RGBA")
        rrect(cd, (cx - 120, cy - 112, cx + 120, cy - 66), 23, fill=hexc(BRAND))
        text(cd, (cx, cy - 87), "Follow for more", 24, WHITE, "Medium")
        out.alpha_composite(shadow(scaled(C, cp, cx, cy - 89), 10, (0, 6), .35))
    return out

def callout(t, T):
    out = new(); d = ImageDraw.Draw(out, "RGBA")
    cx, cy, r = 760, 330, 120
    p = out_cubic(prog(t, .1, .9)); leave = prog(t, T - .5, .5)
    a = int(255 * (1 - leave))
    if p > 0:
        pts = arc_pts(cx, cy, r, -2.2, -2.2 + 2 * math.pi * 1.06 * p, wobble=6, seed=1.3)
        d.line(pts, fill=hexc("#FFD43B", a), width=int(s(10)), joint="curve")
    # arrow from bottom-left
    q = out_cubic(prog(t, .8, .7))
    if q > 0:
        sx, sy, ex, ey = 360, 600, cx - r * 1.25 - 30, cy + 60
        cx1, cy1 = 420, 380
        n = 40; seg = []
        for i in range(int(n * q) + 1):
            u = i / n
            x = (1 - u) ** 2 * sx + 2 * (1 - u) * u * cx1 + u * u * ex
            y = (1 - u) ** 2 * sy + 2 * (1 - u) * u * cy1 + u * u * ey
            seg.append((s(x), s(y)))
        if len(seg) > 1: d.line(seg, fill=hexc("#FFD43B", a), width=int(s(10)), joint="curve")
        if q > .95:
            x1, y1 = seg[-1]; x0_, y0_ = seg[-4]
            ang = math.atan2(y1 - y0_, x1 - x0_)
            for da in (2.6, -2.6):
                d.line([(x1, y1), (x1 + math.cos(ang + da) * s(34), y1 + math.sin(ang + da) * s(34))], fill=hexc("#FFD43B", a), width=int(s(10)))
    lp = out_back(prog(t, 1.4, .5)) * (1 - leave)
    if lp > .01:
        L = new(); ld = ImageDraw.Draw(L, "RGBA")
        rrect(ld, (230, 610, 500, 674), 32, fill=hexc("#FFD43B"))
        text(ld, (365, 644), "Click here!", 32, hexc("#111111"))
        out.alpha_composite(shadow(scaled(L, lp, 365, 642), 10, (0, 8), .4))
    return out

def callout_bg(t, T):
    bg = vgrad("#e9edf5", "#cfd6e4"); d = ImageDraw.Draw(bg, "RGBA")
    rrect(d, (120, 110, 1160, 640), 18, fill=(255, 255, 255, 255))
    rrect(d, (160, 150, 560, 200), 10, fill=hexc("#dfe5f0"))
    rrect(d, (160, 230, 520, 250), 8, fill=hexc("#edf1f7")); rrect(d, (160, 270, 480, 290), 8, fill=hexc("#edf1f7"))
    rrect(d, (640, 280, 880, 380), 14, fill=hexc(BRAND)); text(d, (760, 332), "Download", 30, WHITE)
    return bg

def loading(t, T):
    bg = radial("#111827", "#030712"); d = ImageDraw.Draw(bg, "RGBA")
    p = inout_cubic(prog(t, .3, 3.0))
    x0, x1, y = 290, 990, 380
    rrect(d, (x0, y - 16, x1, y + 16), 16, fill=(255, 255, 255, 25))
    G = new(); gd = ImageDraw.Draw(G, "RGBA")
    w = (x1 - x0) * p
    if w > 2:
        rrect(gd, (x0, y - 16, x0 + max(w, 32), y + 16), 16, fill=hexc(BRAND))
        # moving stripes
        S = new(); sd = ImageDraw.Draw(S, "RGBA")
        off = (t * 60) % 40
        for k in range(-2, 40):
            xs = x0 + k * 40 + off
            sd.polygon([(s(xs), s(y - 16)), (s(xs + 18), s(y - 16)), (s(xs + 4), s(y + 16)), (s(xs - 14), s(y + 16))], fill=(255, 255, 255, 45))
        m = Image.new("L", (CW, CH), 0); ImageDraw.Draw(m).rounded_rectangle([s(x0), s(y - 16), s(x0 + max(w, 32)), s(y + 16)], radius=s(16), fill=255)
        G.paste(S, (0, 0), Image.fromarray(np.minimum(np.array(S.split()[3]), np.array(m))))
    over(bg, glow(G, 12, .7))
    done = t > 3.4
    if not done:
        dots = "." * (1 + int(t * 3) % 3)
        text(d, (x0, 300), "Loading" + dots, 40, WHITE, anchor="lm")
        text(d, (x1, 300), f"{int(p * 100)}%", 40, hexc(CYAN), anchor="rm")
    else:
        cp = out_back(prog(t, 3.4, .5))
        C = new(); cd = ImageDraw.Draw(C, "RGBA")
        cd.ellipse([s(640 - 46), s(270 - 46), s(640 + 46), s(270 + 46)], fill=hexc("#22C55E"))
        check(cd, 640, 270, 44, WHITE, 9, out_cubic(prog(t, 3.55, .4)))
        over(bg, scaled(C, cp, 640, 270))
        text(d, (640, 470), "Ready", 36, (255, 255, 255, int(255 * prog(t, 3.6, .4))), "Medium")
    return bg

def quiz(t, T):
    bg = vgrad("#0F172A", "#1E1B4B"); d = ImageDraw.Draw(bg, "RGBA")
    tag = out_back(prog(t, 0, .5))
    Tg = new(); td = ImageDraw.Draw(Tg, "RGBA")
    rrect(td, (540, 70, 740, 116), 23, fill=hexc("#FACC15")); text(td, (640, 94), "QUIZ TIME", 24, hexc("#111111"))
    over(bg, scaled(Tg, tag, 640, 93))
    qa = int(255 * prog(t, .3, .5))
    text(d, (640, 186), "Which planet is the largest?", 46, (255, 255, 255, qa))
    opts = [("A", "Mars"), ("B", "Jupiter"), ("C", "Venus"), ("D", "Earth")]
    reveal = t > 4.0
    for i, (k, v) in enumerate(opts):
        p = out_cubic(prog(t, .6 + i * .15, .5))
        col, row = i % 2, i // 2
        x = 190 + col * 460 + (1 - p) * (-60 if col == 0 else 60); y = 270 + row * 120
        correct = k == "B"
        fill = (255, 255, 255, int(22 * p)); txtc = (255, 255, 255, int(255 * p)); badge = hexc(BRAND, int(255 * p))
        if reveal:
            rp = prog(t, 4.0, .3)
            if correct: fill = mix((255, 255, 255, 22), hexc("#16A34A"), rp); badge = hexc("#FFFFFF");
            else: txtc = (255, 255, 255, int(255 * lerp(1, .35, rp)))
        O = new(); od = ImageDraw.Draw(O, "RGBA")
        rrect(od, (x, y, x + 440, y + 92), 18, fill=fill, outline=(255, 255, 255, int(40 * p)), width=2)
        od.ellipse([s(x + 20), s(y + 20), s(x + 72), s(y + 72)], fill=badge)
        text(od, (x + 46, y + 47), k, 26, hexc("#16A34A") if (reveal and correct) else WHITE)
        text(od, (x + 96, y + 48), v, 34, txtc, "Medium", anchor="lm")
        if reveal and correct:
            check(od, x + 395, y + 46, 30, WHITE, 7, out_cubic(prog(t, 4.1, .4)))
        over(bg, O)
    # timer bar
    tp = 1 - prog(t, .9, 3.0)
    rrect(d, (190, 540, 1090, 552), 6, fill=(255, 255, 255, 30))
    if tp > 0: rrect(d, (190, 540, 190 + 900 * tp, 552), 6, fill=hexc("#FACC15" if tp > .3 else "#F87171"))
    return bg

def dark_bg(t, T): return vgrad("#1a1f2e", "#0a0d14")

def map_route(t, T):
    bg = vgrad("#0B1220", "#0E1A30"); d = ImageDraw.Draw(bg, "RGBA")
    # dotted world grid
    for gx in range(40, 1280, 36):
        for gy in range(40, 720, 36):
            v = math.sin(gx * .011) * math.cos(gy * .017) + math.sin((gx + gy) * .006)
            if v > .35: d.ellipse([s(gx - 3), s(gy - 3), s(gx + 3), s(gy + 3)], fill=(90, 130, 200, 90))
    A, B = (300, 470), (980, 260)
    c = (640, 120)
    p = inout_cubic(prog(t, .8, 2.2))
    G = new(); gd = ImageDraw.Draw(G, "RGBA")
    n = 120; pts = []
    for i in range(int(n * p) + 1):
        u = i / n
        pts.append(((1 - u) ** 2 * A[0] + 2 * (1 - u) * u * c[0] + u * u * B[0], (1 - u) ** 2 * A[1] + 2 * (1 - u) * u * c[1] + u * u * B[1]))
    for i in range(0, len(pts) - 1, 3):
        gd.line([(s(pts[i][0]), s(pts[i][1])), (s(pts[min(i + 2, len(pts) - 1)][0]), s(pts[min(i + 2, len(pts) - 1)][1]))], fill=hexc(CYAN), width=int(s(5)))
    if len(pts) > 2:
        x, y = pts[-1]; gd.ellipse([s(x - 9), s(y - 9), s(x + 9), s(y + 9)], fill=WHITE)
    over(bg, glow(G, 8, .9))
    def pin(P, label, start):
        q = out_back(prog(t, start, .5))
        if q <= .01: return
        L = new(); ld = ImageDraw.Draw(L, "RGBA")
        x, y = P
        ld.ellipse([s(x - 26), s(y - 74), s(x + 26), s(y - 22)], fill=hexc(RED))
        ld.polygon([(s(x - 22), s(y - 40)), (s(x + 22), s(y - 40)), (s(x), s(y))], fill=hexc(RED))
        ld.ellipse([s(x - 10), s(y - 58), s(x + 10), s(y - 38)], fill=WHITE)
        lw = tw(label, 26) + 36
        rrect(ld, (x - lw / 2, y + 14, x + lw / 2, y + 56), 21, fill=(255, 255, 255, 245))
        text(ld, (x, y + 36), label, 26, hexc("#0E1424"))
        over(bg, shadow(scaled(L, q, x, y), 10, (0, 8), .4))
    pin(A, "Lisbon", .2); pin(B, "Tokyo", 2.9)
    return bg

# id, func, seconds, overlay?, preview-bg func
ANIMS = [
    ("subscribe-bell", subscribe, 5, True, dark_bg),
    ("lower-third-clean", lower_third, 5, True, None),
    ("countdown-5", countdown, 6, False, None),
    ("title-reveal", title_reveal, 5, False, None),
    ("gradient-loop", gradient_loop, 6, False, None),
    ("aurora-loop", aurora_loop, 6, False, None),
    ("plexus-network", plexus, 6, False, None),
    ("swipe-transition", swipe, 2.2, True, swipe_preview_bg),
    ("bar-chart", bar_chart, 5, False, None),
    ("social-handle", social_handle, 5, True, dark_bg),
    ("callout-arrow", callout, 4, True, callout_bg),
    ("loading-bar", loading, 4.5, False, None),
    ("quiz-reveal", quiz, 6, False, None),
    ("travel-route", map_route, 4.5, False, None),
]

def lower_third_bg(t, T):
    # a softly blurred "scene" so the lower third reads in the preview
    return _blobs(1.3, 6, ["#335C67", "#E09F3E", "#9E2A2B", "#540B0E"], base="#1b1b1b")

def enc(path, args):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"] + args + [path], stdin=subprocess.PIPE)

H264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]

for aid, fn, dur, overlay, pbg in ANIMS:
    if ONLY and aid not in ONLY: continue
    if aid == "lower-third-clean": pbg = lower_third_bg
    n = int(dur * FPS)
    procs = {"preview": enc(f"{OUT}/{aid}.mp4", H264)}
    if overlay:
        procs["green"] = enc(f"{OUT}/{aid}-green.mp4", H264)
        procs["alpha"] = enc(f"{OUT}/{aid}-alpha.webm", ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "34", "-deadline", "realtime", "-cpu-used", "8", "-auto-alt-ref", "0"])
        if os.environ.get("MOV"): procs["mov"] = enc(f"{OUT}/{aid}.mov", ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-qscale:v", "11", "-vendor", "apl0"])
    poster_at = int(n * (.55 if aid not in ("swipe-transition",) else .3))
    for i in range(n):
        t = i / FPS
        fr = fn(t, dur).resize((W, H), Image.LANCZOS)
        if overlay:
            procs["alpha"].stdin.write(fr.tobytes())
            if "mov" in procs: procs["mov"].stdin.write(fr.tobytes())
            g = Image.new("RGBA", (W, H), (0, 177, 64, 255)); g.alpha_composite(fr); procs["green"].stdin.write(g.tobytes())
            b = pbg(t, dur).resize((W, H), Image.BILINEAR).convert("RGBA"); b.alpha_composite(fr); fr = b
        procs["preview"].stdin.write(fr.convert("RGBA").tobytes())
        if i == poster_at:
            fr.convert("RGB").resize((640, 360), Image.LANCZOS).save(f"{OUT}/{aid}.jpg", quality=84)
    for p in procs.values():
        p.stdin.close(); p.wait()
    print("done", aid, flush=True)
