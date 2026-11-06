"""Batch 3: the most-used animations for Reels, Shorts and YouTube videos."""
import sys, os, math, importlib.util, subprocess
OUT = sys.argv[1]; ONLY = sys.argv[2].split(",") if len(sys.argv) > 2 else None
_argv = sys.argv; sys.argv = ["render.py", OUT, "__none__"]
spec = importlib.util.spec_from_file_location("R", os.path.join(os.path.dirname(__file__), "render.py"))
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R); sys.argv = _argv
globals().update({k: v for k, v in vars(R).items() if not k.startswith("__") and k not in ("OUT", "ONLY", "ANIMS", "W", "H", "CW", "CH")})
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def setdim(w, h):
    global W, H, CW, CH
    W, H = w, h; CW, CH = int(w * K), int(h * K)
    R.W, R.H, R.CW, R.CH = W, H, CW, CH
def DR(im): return ImageDraw.Draw(im, "RGBA")
def bgv(c1, c2):
    a = np.linspace(0, 1, CH)[:, None, None]; arr = (np.array(hexc(c1), float) * (1 - a) + np.array(hexc(c2), float) * a).repeat(CW, 1)
    return Image.fromarray(arr.astype(np.uint8), "RGBA").convert("RGB")
YEL = "#FACC15"; GREEN = "#22C55E"
EMO = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109)
_ec = {}
def emoji(ch, size):
    key = (ch, int(size))
    if key not in _ec:
        im = Image.new("RGBA", (136, 128), (0, 0, 0, 0)); ImageDraw.Draw(im).text((0, 0), ch, font=EMO, embedded_color=True)
        _ec[key] = im.resize((int(s(size) * 136 / 128), int(s(size))), Image.LANCZOS)
    return _ec[key]
def paste_emoji(layer, ch, x, y, size, rot=0, alpha=1.0):
    e = emoji(ch, size)
    if rot: e = e.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1: a = np.array(e); a[..., 3] = (a[..., 3] * alpha).astype(np.uint8); e = Image.fromarray(a)
    layer.alpha_composite(e, (int(s(x) - e.width / 2), int(s(y) - e.height / 2))) if s(x) - e.width / 2 >= 0 and s(y) - e.height / 2 >= 0 else layer.paste(e, (int(s(x) - e.width / 2), int(s(y) - e.height / 2)), e)
def cursor(layer, x, y):
    C = new(); c = DR(C); pts = [(0, 0), (0, 40), (10, 31), (18, 48), (26, 45), (18, 28), (32, 28)]
    c.polygon([(s(x + a), s(y + b)) for a, b in pts], fill=WHITE, outline=(20, 20, 20, 255), width=int(s(2.5))); layer.alpha_composite(shadow(C, 4, (2, 3), .5))
def stroke_text(d, xy, t, size, fill, sw=6, w="Bold", anchor="mm"):
    d.text((s(xy[0]), s(xy[1])), t, font=font(size, w), fill=fill, anchor=anchor, stroke_width=int(s(sw)), stroke_fill=(0, 0, 0, 255))

# ================= vertical (720x1280) =================
def captions(t, T):
    out = new(); groups = [["THIS", "IS", "HOW"], ["YOU", "GROW", "FAST"], ["ON", "SHORTS", "AND", "REELS"]]
    seg = T / len(groups); gi = min(int(t // seg), len(groups) - 1); lt = t - gi * seg; words = groups[gi]
    per = (seg - .3) / len(words); k = min(int(lt // per), len(words) - 1)
    sz = 64; sp = 22; widths = [tw(w_, sz) for w_ in words]; total = sum(widths) + sp * (len(words) - 1)
    if total > W - 80: sz = int(sz * (W - 80) / total); widths = [tw(w_, sz) for w_ in words]; total = sum(widths) + sp * (len(words) - 1)
    x = W / 2 - total / 2; y = 860; d = DR(out)
    for i, w_ in enumerate(words):
        cx_ = x + widths[i] / 2
        if i < k or (i == k):
            pop = out_back(prog(lt - i * per, 0, .18), 2.5) if i == k else 1
            L = new(); ld = DR(L)
            stroke_text(ld, (cx_, y), w_, sz, hexc(YEL) if i == k else WHITE, 7)
            out.alpha_composite(scaled(L, .7 + .3 * pop if i == k else 1, cx_, y))
        x += widths[i] + sp
    return out

def follow_tap(t, T):
    out = new(); cx, cy = W / 2, 980; lv = in_cubic(prog(t, T - .5, .5))
    q = out_back(prog(t, .1, .5)) * (1 - lv); on = t > 1.6
    press = 1 - .08 * math.sin(math.pi * prog(t, 1.45, .25))
    L = new(); ld = DR(L)
    rrect(ld, (cx - 290, cy - 60, cx + 290, cy + 60), 60, fill=(20, 20, 24, 235))
    ld.ellipse([s(cx - 278), s(cy - 48), s(cx - 182), s(cy + 48)], fill=hexc(BRAND)); text(ld, (cx - 230, cy + 2), "MC", 34, WHITE)
    text(ld, (cx - 164, cy - 14), "@maya.creates", 28, WHITE, anchor="lm"); text(ld, (cx - 164, cy + 20), "12.4K followers", 20, (180, 180, 190, 255), "Medium", anchor="lm")
    B = new(); bd = DR(B)
    rrect(bd, (cx + 118, cy - 32, cx + 272, cy + 32), 32, fill=hexc("#3A3A42") if on else hexc(RED))
    text(bd, (cx + 195, cy + 2), "Following" if on else "Follow", 22 if on else 24, WHITE)
    L.alpha_composite(scaled(B, press, cx + 195, cy))
    out.alpha_composite(shadow(scaled(L, q, cx, cy), 14, (0, 10), .5))
    if .6 < t < T - .5:
        cp = inout_cubic(prog(t, .6, .8)); cursor(out, lerp(560, cx + 190, cp), lerp(1200, cy + 4, cp))
    if 1.6 < t < 2.4:
        b = prog(t, 1.6, .8); E = new()
        for i in range(6):
            a = -math.pi / 2 + (i - 2.5) * .35; dist = 40 + 110 * out_cubic(b)
            paste_emoji(E, "❤️", cx + 195 + math.cos(a) * dist, cy - 40 + math.sin(a) * dist, 30, alpha=1 - b)
        out.alpha_composite(E)
    return out

def link_bio(t, T):
    out = new(); cx = W / 2; lv = in_cubic(prog(t, T - .5, .5)); q = out_back(prog(t, .1, .5)) * (1 - lv)
    L = new(); ld = DR(L); y = 1000
    rrect(ld, (cx - 190, y - 46, cx + 190, y + 46), 46, fill=(255, 255, 255, 250))
    text(ld, (cx + 24, y + 2), "Link in bio", 36, hexc("#111111"))
    ld.ellipse([s(cx - 172), s(y - 30), s(cx - 112), s(y + 30)], fill=hexc(BRAND))
    for dx in (-8, 8): ld.arc([s(cx - 142 + dx - 14), s(y - 8), s(cx - 142 + dx + 14), s(y + 8)], 0, 360, fill=WHITE, width=int(s(4)))
    out.alpha_composite(shadow(scaled(L, q, cx, y), 14, (0, 10), .45))
    bounce = abs(math.sin(t * math.pi * 1.6)) * 26
    A = new(); ad = DR(A); ay = 1110 + bounce
    for k in range(2):
        yy = ay + k * 34
        ad.line([(s(cx - 34), s(yy)), (s(cx), s(yy + 30)), (s(cx + 34), s(yy))], fill=(255, 255, 255, int(255 * (1 - lv) * prog(t, .5 + k * .15, .3) * (1 - .35 * k))), width=int(s(9)), joint="curve")
    out.alpha_composite(shadow(A, 6, (0, 4), .5)); return out

def wait_for_it(t, T):
    out = new(); cx, cy = W / 2, 360; lv = in_cubic(prog(t, T - .4, .4)); q = out_back(prog(t, .05, .4), 2.4) * (1 - lv)
    shake = (math.sin(t * 60) * 5 * (.5 + .5 * math.sin(t * 3))) if t > .5 else 0
    L = new(); ld = DR(L); dots = "." * (1 + int(t * 2.5) % 3)
    rrect(ld, (cx - 280, cy - 70, cx + 280, cy + 70), 20, fill=hexc(YEL))
    text(ld, (cx - 236, cy + 2), "WAIT FOR IT" + dots, 52, hexc("#111111"), anchor="lm")
    paste_emoji(L, "👀", cx + 230, cy - 74, 64)
    out.alpha_composite(shadow(scaled(L, q, cx, cy, rot=-3 + shake * .4), 14, (0, 10), .5))
    d = DR(out); pw = 440; p = prog(t, .3, T - .9)
    rrect(d, (cx - pw / 2, cy + 100, cx + pw / 2, cy + 112), 6, fill=(255, 255, 255, int(90 * (1 - lv))))
    rrect(d, (cx - pw / 2, cy + 100, cx - pw / 2 + pw * p, cy + 112), 6, fill=(255, 255, 255, int(255 * (1 - lv))))
    return out

def part_two(t, T):
    out = new(); cx, cy = W / 2, 330; lv = in_cubic(prog(t, T - .5, .5))
    st = prog(t, .05, .35); sc = lerp(2.4, 1, out_cubic(st)) if st < 1 else 1 + .03 * math.sin(math.pi * prog(t, .4, .2))
    L = new(); ld = DR(L)
    rrect(ld, (cx - 220, cy - 92, cx + 220, cy + 92), 22, fill=hexc(RED))
    text(ld, (cx, cy + 4), "PART 2", 104, WHITE)
    out.alpha_composite(shadow(fade(scaled(L, sc * (1 - lv), cx, cy, rot=-4), st), 16, (0, 12), .55))
    q = out_back(prog(t, .9, .5)) * (1 - lv)
    F = new(); fd = DR(F); rrect(fd, (cx - 200, cy + 130, cx + 200, cy + 190), 30, fill=(255, 255, 255, 245))
    text(fd, (cx, cy + 161), "Follow for part 3", 28, hexc("#111111"))
    out.alpha_composite(shadow(scaled(F, q, cx, cy + 160), 10, (0, 8), .4)); return out

def reply_comment(t, T):
    out = new(); x0, y0 = 70, 380; lv = in_cubic(prog(t, T - .5, .5)); q = out_back(prog(t, .1, .55)) * (1 - lv)
    L = new(); ld = DR(L)
    rrect(ld, (x0, y0, x0 + 520, y0 + 170), 22, fill=(255, 255, 255, 250))
    ld.polygon([(s(x0 + 40), s(y0 + 168)), (s(x0 + 80), s(y0 + 168)), (s(x0 + 34), s(y0 + 206))], fill=(255, 255, 255, 250))
    ld.ellipse([s(x0 + 22), s(y0 + 22), s(x0 + 78), s(y0 + 78)], fill=hexc(VIOLET)); text(ld, (x0 + 50, y0 + 51), "S", 28, WHITE)
    text(ld, (x0 + 96, y0 + 38), "Reply to sam_creates's comment", 21, hexc("#6B7280"), "Medium", anchor="lm")
    full = "How did you make this edit? 😍"; n = int(len(full) * prog(t, .6, 1.2)); typed = full[:n].replace("😍", "")
    text(ld, (x0 + 96, y0 + 82), typed, 28, hexc("#111111"), anchor="lm")
    if n >= len(full): paste_emoji(L, "😍", x0 + 96 + tw("How did you make this edit? ", 28) + 18, y0 + 82, 28)
    ld.ellipse([s(x0 + 440), s(y0 + 112), s(x0 + 470), s(y0 + 142)], outline=hexc("#9CA3AF"), width=int(s(3)))
    text(ld, (x0 + 455, y0 + 160 - 30), "", 10, WHITE)
    text(ld, (x0 + 96, y0 + 132), "2,431 likes", 18, hexc("#9CA3AF"), "Medium", anchor="lm")
    out.alpha_composite(shadow(scaled(L, q, x0 + 60, y0 + 190), 16, (0, 10), .4)); return out

def notify(t, T):
    out = new(); cx = W / 2; en = out_back(prog(t, .1, .55), 1.2); ex = in_cubic(prog(t, T - .6, .45)); y = lerp(-140, 70, en) - 220 * ex
    L = new(); ld = DR(L)
    rrect(ld, (cx - 320, y, cx + 320, y + 128), 30, fill=(245, 245, 247, 240))
    rrect(ld, (cx - 296, y + 24, cx - 216, y + 104), 20, fill=hexc(RED))
    ld.polygon([(s(cx - 266), s(y + 46)), (s(cx - 266), s(y + 82)), (s(cx - 236), s(y + 64))], fill=WHITE)
    text(ld, (cx - 196, y + 40), "CREATOR STUDIO", 18, hexc("#6B7280"), "Medium", anchor="lm"); text(ld, (cx + 296, y + 40), "now", 18, hexc("#6B7280"), "Medium", anchor="rm")
    text(ld, (cx - 196, y + 72), "You hit 10,000 subscribers!", 25, hexc("#111111"), anchor="lm")
    text(ld, (cx - 196, y + 102), "Thank you for the support", 21, hexc("#374151"), "Regular", anchor="lm")
    out.alpha_composite(shadow(L, 18, (0, 10), .35))
    if 1.0 < t < 3.2:
        b = prog(t, 1.0, 2.2); E = new()
        for i, ch in enumerate(["🎉", "🎊", "✨", "🥳", "🎉", "✨"]):
            a = math.radians(30 + i * 24); dist = 60 + 340 * out_cubic(b)
            paste_emoji(E, ch, cx + (i - 2.5) * 110 * (.4 + out_cubic(b)), y + 170 + 520 * b * b, 52, rot=b * 120 * (1 if i % 2 else -1), alpha=1 - ic3(b))
        out.alpha_composite(E)
    return out
def ic3(x): return x ** 3

_ER = np.random.default_rng(21).random((18, 4))
def emoji_rain(t, T):
    out = new(); chars = ["❤️", "😂", "🔥", "😍", "👏", "💯"]
    for i, (a, b, c, e) in enumerate(_ER):
        ph = (t / T + a) % 1; y = 1240 - ph * 900; x = W - 150 + math.sin(t * 3 + i) * 50 + (b - .5) * 120
        al = clamp(ph * 5) * (1 - clamp((ph - .7) / .3)); paste_emoji(out, chars[i % len(chars)], x, y, 40 + 24 * c, rot=math.sin(t * 2 + i) * 15, alpha=al)
    return out

_CF = np.random.default_rng(4).random((140, 6))
def confetti(t, T):
    out = new(); d = DR(out); cols = [BRAND, CYAN, YEL, PINK, "#22C55E", RED, VIOLET]
    for a, b, c, e, f, g in _CF:
        start = .1 + a * .25; lt = t - start
        if lt < 0: continue
        side = -1 if b < .5 else 1; x0 = W / 2 + side * (W / 2 + 20); y0 = H * .78
        vx = -side * (180 + 420 * c); vy = -(900 + 600 * e)
        x = x0 + vx * lt; y = y0 + vy * lt + 900 * lt * lt; sz = 9 + 10 * f; rot = lt * (6 + 10 * g)
        if y > H + 40: continue
        al = int(255 * (1 - clamp((t - (T - .6)) / .6)))
        w_ = sz * abs(math.cos(rot)) + 2; h_ = sz * .55
        ca, sa = math.cos(rot * .7), math.sin(rot * .7)
        pts = [(-w_ / 2, -h_ / 2), (w_ / 2, -h_ / 2), (w_ / 2, h_ / 2), (-w_ / 2, h_ / 2)]
        d.polygon([(s(x + px * ca - py * sa), s(y + px * sa + py * ca)) for px, py in pts], fill=hexc(cols[int(g * 7) % 7], al))
    return out

# ================= landscape (1280x720) =================
def end_screen(t, T):
    bg = radial("#16203A", "#05070D", .5, .4, 1.0); lv = 1 - in_cubic(prog(t, T - .5, .5))
    O = new(); od = DR(O)
    for i, (x, y, r, c) in enumerate([(200, 150, 220, VIOLET), (1100, 600, 260, BRAND)]):
        od.ellipse([s(x - r), s(y - r), s(x + r), s(y + r)], fill=hexc(c, 70))
    over(bg, O.filter(ImageFilter.GaussianBlur(s(80))))
    d = DR(bg); a = int(255 * prog(t, 0, .5) * lv)
    text(d, (640, 96), "THANKS FOR WATCHING", 48, (255, 255, 255, a))
    for i, x in enumerate((110, 690)):
        q = out_cubic(prog(t, .3 + i * .15, .6)) * lv
        L = new(); ld = DR(L); y = 200 + 40 * (1 - q)
        rrect(ld, (x, y, x + 480, y + 270), 18, fill=(255, 255, 255, int(16 * q)), outline=(255, 255, 255, int(160 * q)), width=3)
        for k in range(0, 480, 24): ld.line([(s(x + k), s(y + 270)), (s(x + k + 12), s(y + 270))], fill=(0, 0, 0, 0))
        ld.polygon([(s(x + 220), s(y + 110)), (s(x + 220), s(y + 160)), (s(x + 262), s(y + 135))], fill=(255, 255, 255, int(200 * q)))
        text(ld, (x + 240, y + 300), "Watch next" if i == 0 else "Best video", 26, (255, 255, 255, int(220 * q)), "Medium")
        over(bg, L)
    q = out_back(prog(t, .8, .5)) * lv; cx, cy = 640, 600
    S = new(); sd = DR(S); sd.ellipse([s(cx - 56), s(cy - 56), s(cx + 56), s(cy + 56)], fill=hexc(RED))
    sd.polygon([(s(cx - 16), s(cy - 24)), (s(cx - 16), s(cy + 24)), (s(cx + 24), s(cy))], fill=WHITE)
    over(bg, shadow(scaled(S, q, cx, cy), 12, (0, 8), .5))
    text(d, (cx, cy + 86), "Subscribe", 24, (255, 255, 255, int(220 * prog(t, 1.0, .4) * lv)), "Medium")
    return bg

def light_leak(t, T):
    out = new(); p = prog(t, 0, T); env = math.sin(math.pi * p) ** 1.5
    arr = np.zeros((CH // 4, CW // 4, 4), float); h, w = arr.shape[:2]
    y, x = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None]
    for cx_, cy_, r, col in ((lerp(-.2, 1.2, p), .4, .45, (255, 140, 40)), (lerp(1.1, -.1, p), .7, .35, (255, 60, 90)), (lerp(.2, .9, p), .1, .3, (255, 220, 120))):
        g = np.exp(-(((x - cx_) * 1.6) ** 2 + (y - cy_) ** 2) / (r * r))
        arr[..., :3] = np.maximum(arr[..., :3], np.array(col) * g[..., None]); arr[..., 3] = np.maximum(arr[..., 3], g * 255)
    arr[..., 3] *= env * .95
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA").resize((CW, CH), Image.BICUBIC)
    return im

def checklist(t, T):
    bg = bgv("#0F172A", "#111827"); d = DR(bg); lv = 1 - in_cubic(prog(t, T - .5, .5))
    text(d, (180, 110), "Before you post", 48, (255, 255, 255, int(255 * prog(t, 0, .5) * lv)), anchor="lm")
    items = ["Hook in the first 3 seconds", "Add captions", "Use a strong thumbnail", "End with a call to action"]
    for i, it in enumerate(items):
        y = 230 + i * 110; q = out_cubic(prog(t, .3 + i * .25, .5)) * lv; ck = prog(t, 1.4 + i * .5, .35)
        L = new(); ld = DR(L); x = 180 - 60 * (1 - q)
        rrect(ld, (x, y - 38, x + 920, y + 38), 16, fill=(255, 255, 255, int(14 * q)))
        rrect(ld, (x + 24, y - 20, x + 64, y + 20), 10, fill=hexc(GREEN, int(255 * q)) if ck > 0 else None, outline=(255, 255, 255, int(160 * q)) if ck <= 0 else None, width=3)
        if ck > 0: check(ld, x + 44, y, 24, WHITE, 5, out_cubic(ck))
        text(ld, (x + 92, y + 2), it, 32, (255, 255, 255, int(255 * q * (1 - .4 * clamp(ck)))), "Medium", anchor="lm")
        if ck > 0: ld.line([(s(x + 92), s(y + 2)), (s(x + 92 + tw(it, 32, "Medium") * out_cubic(ck)), s(y + 2))], fill=(255, 255, 255, int(160 * q)), width=int(s(3)))
        over(bg, L)
    return bg

def before_after(t, T):
    out = new(); d = DR(out); p = .5 + .32 * math.sin(2 * math.pi * prog(t, .6, T - 1.0)) if t > .6 else lerp(1.0, .5, out_cubic(prog(t, 0, .6)))
    lv = 1 - in_cubic(prog(t, T - .4, .4)); x = 1280 * p; a = int(255 * lv)
    d.rectangle([s(x - 3), 0, s(x + 3), CH], fill=(255, 255, 255, a))
    d.ellipse([s(x - 30), s(330), s(x + 30), s(390)], fill=(255, 255, 255, a))
    for sgn in (-1, 1): d.polygon([(s(x + sgn * 8), s(348)), (s(x + sgn * 8), s(372)), (s(x + sgn * 20), s(360))], fill=(17, 17, 17, a))
    for lab, xx, anc in (("BEFORE", 40, "lm"), ("AFTER", 1240, "rm")):
        w_ = tw(lab, 26) + 36; x0 = xx if anc == "lm" else xx - w_
        rrect(d, (x0, 40, x0 + w_, 92), 26, fill=(0, 0, 0, int(160 * lv))); text(d, (x0 + w_ / 2, 66), lab, 26, (255, 255, 255, a))
    return out

V = [("captions-pop", captions, 4.5, True), ("follow-tap", follow_tap, 4, True), ("link-in-bio", link_bio, 4, True), ("wait-for-it", wait_for_it, 3.5, True),
     ("part-two", part_two, 3.5, True), ("reply-comment", reply_comment, 4, True), ("notify-milestone", notify, 4.5, True),
     ("emoji-rain", emoji_rain, 5, True), ("confetti-burst", confetti, 3.5, True)]
L_ = [("end-screen", end_screen, 6, False), ("light-leak", light_leak, 2.4, True), ("checklist", checklist, 5, False), ("before-after", before_after, 4.5, True)]

def run(items, w, h):
    setdim(w, h)
    for aid, fn, dur, overlay in items:
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
                b = Image.new("RGBA", (W, H), (22, 26, 36, 255)); b.alpha_composite(fr); fr = b
            procs["preview"].stdin.write(fr.tobytes())
        for p in procs.values(): p.stdin.close(); p.wait()
        print("done", aid, flush=True)

if __name__ == "__main__":
    which = os.environ.get("ORIENT", "both")
    if which in ("both", "v"): run(V, 720, 1280)
    if which in ("both", "l"): run(L_, 1280, 720)
