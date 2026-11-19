"""
Generator kosmetyk Moddy: modele 3D (.obj + .mtl), podglądy (.png), pelerynki (64x32 .png) i catalog.json.

Uruchom:   py cosmetics/make_cosmetics.py
Wynik:     cosmetics/models/*.obj|*.mtl, cosmetics/previews/*.png, cosmetics/capes/*.png, cosmetics/catalog.json
           (+ kopia podglądów i katalogu do assets/cosmetics/ – stamtąd launcher bierze miniatury offline)

Modele są w stylu Minecrafta (same prostopadłościany). Jednostka w kodzie = 1/16 bloku; w plikach .obj 1.0 = 1 blok.
Układ współrzędnych: Y w górę, +Z = przód (twarz), +X = prawa strona modelu.
"""
from __future__ import annotations

import json
import math
import os
import shutil

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# ── materiały: nazwa → (kolor, alfa, świeci) ────────────────────────────────────
MAT = {
    "orange": ("#ff7a2f", 1, 0), "orange_dark": ("#c9531a", 1, 0), "dark": ("#2b2b30", 1, 0),
    "gray": ("#8d949e", 1, 0), "cyan": ("#35e6ff", 1, 1), "black": ("#141418", 1, 0), "white": ("#f4f4f4", 1, 0),
    "slime": ("#7be36b", 0.9, 0), "slime_dark": ("#3fa84a", 1, 0), "slime_light": ("#c8ffb8", 1, 0),
    "green": ("#4fb35a", 1, 0), "green_dark": ("#2f7a3b", 1, 0), "green_light": ("#8be08f", 1, 0),
    "cream": ("#f6e7c1", 1, 0), "yellow": ("#ffd84a", 1, 1), "ghost": ("#eef3ff", 0.88, 0),
    "cat": ("#e8943a", 1, 0), "cat_dark": ("#b86a1f", 1, 0), "pink": ("#ff9fb5", 1, 0), "eye_green": ("#4be06a", 1, 1),
    "gold": ("#ffc933", 1, 0), "gold_dark": ("#c9951a", 1, 0), "red": ("#e5383b", 1, 1),
    "purple": ("#6a3fb5", 1, 0), "purple_dark": ("#4a2a85", 1, 0), "star": ("#fff27a", 1, 1),
    "neon": ("#3df2ff", 0.95, 1), "neon2": ("#b44cff", 0.95, 1), "flame": ("#ff8a1f", 1, 1), "flame2": ("#ffe066", 1, 1),
    "halo": ("#fff2a8", 0.95, 1), "frame": ("#1c1c22", 1, 0), "lens": ("#101018", 0.92, 0), "glint": ("#ffffff", 1, 1),
}


def _box(cx, y0, cz, sx, sy, sz, mat):
    """Prostopadłościan: środek w X/Z, dół na Y=y0, rozmiary sx/sy/sz."""
    return (cx - sx / 2, y0, cz - sz / 2, cx + sx / 2, y0 + sy, cz + sz / 2, mat)


def _mirror(cx, y0, cz, sx, sy, sz, mat):
    """Para lustrzana względem X (lewa + prawa)."""
    return [_box(-cx, y0, cz, sx, sy, sz, mat), _box(cx, y0, cz, sx, sy, sz, mat)]


def _flat(*parts):
    out = []
    for p in parts:
        out.extend(p if isinstance(p, list) else [p])
    return out


# ── modele ──────────────────────────────────────────────────────────────────────
def pet_bot():
    return _flat(
        _box(0, 3, 0, 8, 7, 6, "orange"), _box(0, 10, 0, 6, 5, 5, "gray"),
        _mirror(1.5, 12, 2.7, 1.6, 1.6, 0.6, "cyan"), _box(0, 15, 0, 1, 3, 1, "dark"), _box(0, 18, 0, 2, 2, 2, "cyan"),
        _mirror(2, 0, 0, 2.4, 3, 2.4, "dark"), _mirror(5.2, 4.5, 0, 2, 4.5, 2, "gray"),
        _box(0, 5, 3.1, 4, 3, 0.4, "orange_dark"), _box(0, 6, 3.4, 1.4, 1.4, 0.4, "cyan"))


def pet_jelly():
    return _flat(
        _box(0, 0, 0, 10, 8, 10, "slime"), _box(0, 2, 0, 5, 4, 5, "slime_dark"), _box(0, 8, 0, 3, 2, 3, "slime_light"),
        _mirror(2.4, 4.5, 5.2, 2, 2.2, 0.5, "black"), _box(0, 2.5, 5.2, 3, 1, 0.5, "black"),
        _mirror(2.4, 5.2, 5.5, 0.7, 0.7, 0.3, "white"))


def pet_dragon():
    return _flat(
        _box(0, 3, 0, 6, 5, 10, "green"), _box(0, 3, 0, 5.4, 1, 9, "cream"),
        _box(0, 6, 6, 5, 5, 5, "green"), _box(0, 6, 9.5, 3, 2, 2, "green_light"),
        _mirror(1.6, 8.5, 8.6, 1, 1, 0.6, "yellow"), _mirror(1.6, 11, 6, 1, 2, 1, "cream"),
        _box(0, 3, -7, 3, 3, 4, "green"), _box(0, 3, -10.5, 2, 2, 3, "green"), _box(0, 3, -13, 3, 3, 2, "orange"),
        _mirror(2, 0, 3, 2, 3, 2, "green_dark"), _mirror(2, 0, -3, 2, 3, 2, "green_dark"),
        _mirror(5.5, 7.5, -1, 5, 0.8, 6, "orange"), _mirror(3.2, 7.5, -1, 1, 1.4, 1.4, "green_dark"),
        _box(0, 8, -2.5, 1, 1.4, 1.4, "orange_dark"), _box(0, 8, 0.5, 1, 1.4, 1.4, "orange_dark"))


def pet_ghost():
    return _flat(
        _box(0, 3, 0, 8, 10, 6, "ghost"), _box(-3, 0, 0, 2, 3, 6, "ghost"), _box(0, 0, 0, 2, 3, 6, "ghost"),
        _box(3, 0, 0, 2, 3, 6, "ghost"), _mirror(2, 9, 3.1, 1.5, 2.6, 0.5, "black"), _box(0, 6, 3.1, 2, 2, 0.5, "black"),
        _mirror(5, 6.5, 0, 2, 1.5, 2, "ghost"), _mirror(2.8, 7.2, 3.3, 1, 0.8, 0.3, "pink"))


def pet_cat():
    return _flat(
        _box(0, 3, 0, 5, 5, 9, "cat"), _box(0, 7, 5, 6, 5, 5, "cat"), _mirror(2, 12, 5, 2, 2, 1, "cat"),
        _mirror(2, 12, 5.2, 1, 1.2, 0.6, "pink"), _mirror(1.5, 9.4, 7.6, 1.2, 1.2, 0.5, "eye_green"),
        _box(0, 8.4, 7.6, 1.2, 1, 0.5, "pink"), _mirror(1.5, 0, 3, 2, 3, 2, "cat"), _mirror(1.5, 0, -3, 2, 3, 2, "cat"),
        _box(0, 3, -6.5, 1.5, 1.5, 4, "cat"), _box(0, 3, -8.5, 1.5, 6, 1.5, "cat"), _box(0, 8.5, -8.5, 1.5, 1.5, 1.5, "cat_dark"),
        _box(0, 8.1, -2, 5.2, 0.3, 1, "cat_dark"), _box(0, 8.1, 0.5, 5.2, 0.3, 1, "cat_dark"), _box(0, 8.1, 3, 5.2, 0.3, 1, "cat_dark"))


def pet_penguin():
    return _flat(
        _box(0, 3, 0, 7, 9, 5, "black"), _box(0, 3.5, 2.6, 5, 7, 0.5, "white"), _box(0, 12, 0, 6, 5, 5, "black"),
        _mirror(1.5, 14, 2.6, 1.4, 1.4, 0.5, "white"), _mirror(1.5, 14.2, 3, 0.7, 0.7, 0.4, "black"),
        _box(0, 12.8, 3.4, 2, 1, 1.6, "orange"), _mirror(2, 0, 1.5, 3, 1, 4, "orange"),
        _mirror(4.4, 5, 0, 1.2, 5, 3, "black"))


def hat_crown():
    pts = [_box(x, 2, z, 2, 3, 2, "gold") for x, z in ((-3.5, -3.5), (3.5, -3.5), (-3.5, 3.5), (3.5, 3.5),
                                                      (0, -3.5), (0, 3.5), (-3.5, 0), (3.5, 0))]
    return _flat(_box(0, 0, 0, 9, 2, 9, "gold"), _box(0, 0, 0, 9.4, 0.6, 9.4, "gold_dark"), pts,
                 _box(0, 0.6, 4.7, 1.6, 1.2, 0.4, "red"), _box(-3, 0.6, 4.7, 1.2, 1.2, 0.4, "neon"),
                 _box(3, 0.6, 4.7, 1.2, 1.2, 0.4, "neon"), _box(0, 5, -3.5, 1.2, 1.2, 1.2, "red"),
                 _box(0, 5, 3.5, 1.2, 1.2, 1.2, "red"))


def hat_wizard():
    return _flat(
        _box(0, 0, 0, 13, 1, 13, "purple_dark"), _box(0, 1, 0, 9, 3, 9, "purple"), _box(0, 4, 0, 7, 3, 7, "purple"),
        _box(0, 7, 0, 5, 3, 5, "purple"), _box(0.6, 10, 0, 3, 3, 3, "purple"), _box(1.8, 13, 0, 2, 2, 2, "purple"),
        _box(0, 1, 0, 9.4, 1, 9.4, "gold"), _box(0, 2.2, 4.6, 1.2, 1.2, 0.3, "star"), _box(2.4, 5.2, 3.6, 1, 1, 0.3, "star"))


def hat_cap():
    return _flat(
        _box(0, 0, 0, 9, 4, 9, "orange"), _box(0, 4, 0, 7, 0.8, 7, "orange_dark"), _box(0, 4.8, 0, 1.6, 0.8, 1.6, "dark"),
        _box(0, 0, 6.5, 9, 1, 5, "orange_dark"), _box(0, 1.2, 4.6, 3.4, 2, 0.3, "white"), _box(0, 1.6, 4.8, 1.6, 1.2, 0.3, "orange"))


def back_wings():
    parts = []
    for i, (xo, h) in enumerate(((4.5, 11), (7, 13), (9.5, 11), (12, 9), (14.5, 6))):
        mat = "neon" if i % 2 == 0 else "neon2"
        parts.append(_mirror(xo, -5 + (13 - h) / 2 + 2, -2.4, 2.2, h, 0.8, mat))
    parts.append(_mirror(2.6, -2, -1.4, 3, 5, 1.6, "gray"))
    return _flat(*parts)


def back_jetpack():
    return _flat(
        _mirror(2.6, -5, -3.2, 4, 10, 4, "gray"), _mirror(2.6, 5, -3.2, 4, 1, 4, "orange"),
        _mirror(2.6, -6.6, -3.2, 3, 1.8, 3, "dark"), _mirror(2.6, -9.4, -3.2, 2, 2.8, 2, "flame"),
        _mirror(2.6, -11.6, -3.2, 1, 2.2, 1, "flame2"), _box(0, 1.5, -1.2, 11, 1.4, 1.4, "dark"),
        _box(0, -3.5, -1.2, 11, 1.4, 1.4, "dark"), _box(0, -1, -5.4, 6, 1.4, 0.6, "cyan"))


def head_halo():
    return _flat(
        _box(0, 3, -4.2, 6, 1, 1.6, "halo"), _box(0, 3, 4.2, 6, 1, 1.6, "halo"),
        _box(-4.2, 3, 0, 1.6, 1, 6, "halo"), _box(4.2, 3, 0, 1.6, 1, 6, "halo"),
        [_box(x, 3, z, 2, 1, 2, "halo") for x, z in ((-3.4, -3.4), (3.4, -3.4), (-3.4, 3.4), (3.4, 3.4))])


def face_shades():
    return _flat(
        _mirror(2.2, -1.6, 4.4, 3.4, 3.2, 0.8, "lens"), _box(0, -0.4, 4.4, 1.2, 0.8, 0.8, "frame"),
        _box(0, 1.2, 4.4, 8.6, 0.7, 0.8, "frame"), _box(0, -1.9, 4.4, 8.6, 0.5, 0.8, "frame"),
        _mirror(4.3, -0.6, 2.2, 0.6, 0.8, 4, "frame"), _mirror(2.9, 0.2, 4.9, 0.9, 0.9, 0.1, "glint"))


# id, kategoria, nazwa, emoji, opis, funkcja, miejsce przypięcia
ITEMS = [
    ("pet_bot", "pet", "Mini Bot", "🤖", "Mały pomarańczowy robot z antenką, który truchta za Tobą.", pet_bot, "Chodzi obok gracza (podłoga)."),
    ("pet_jelly", "pet", "Galaretka", "🟢", "Przyjazna, galaretowata kulka z uśmiechem.", pet_jelly, "Skacze obok gracza (podłoga)."),
    ("pet_dragon", "pet", "Smoczek", "🐲", "Maleńki zielony smok ze skrzydłami i pomarańczowym ogonem.", pet_dragon, "Lata przy ramieniu gracza."),
    ("pet_ghost", "pet", "Duszek", "👻", "Przezroczysty duszek, który unosi się nad ziemią.", pet_ghost, "Unosi się obok gracza."),
    ("pet_cat", "pet", "Kotek", "🐱", "Rudy kotek w paski z długim ogonem.", pet_cat, "Chodzi obok gracza (podłoga)."),
    ("pet_penguin", "pet", "Pingwin", "🐧", "Pingwinek, który człapie za graczem.", pet_penguin, "Chodzi obok gracza (podłoga)."),
    ("hat_crown", "hat", "Korona", "👑", "Złota korona z rubinami.", hat_crown, "Na głowie: y=0 to czubek głowy."),
    ("hat_wizard", "hat", "Kapelusz czarodzieja", "🧙", "Fioletowy kapelusz z gwiazdkami.", hat_wizard, "Na głowie: y=0 to czubek głowy."),
    ("hat_cap", "hat", "Czapka Moddy", "🧢", "Pomarańczowa czapka z daszkiem i logo.", hat_cap, "Na głowie: y=0 to czubek głowy."),
    ("head_halo", "hat", "Aureola", "😇", "Świecąca aureola unosząca się nad głową.", head_halo, "Nad głową: y=0 to czubek głowy."),
    ("back_wings", "back", "Skrzydła Neon", "🪽", "Świecące, neonowe skrzydła.", back_wings, "Na plecach: y=0 środek tułowia, z=0 plecy, skrzydła w stronę −Z."),
    ("back_jetpack", "back", "Plecak odrzutowy", "🚀", "Plecak z dwoma dyszami i płomieniami.", back_jetpack, "Na plecach: y=0 środek tułowia, z=0 plecy."),
    ("face_shades", "face", "Okulary przeciwsłoneczne", "🕶", "Ciemne okulary dla każdego.", face_shades, "Na twarzy: y=0 linia oczu, z=+4 przód głowy."),
]
CATEGORY_LABEL = {"pet": "Zwierzaki", "hat": "Czapki i nakrycia głowy", "back": "Plecy", "face": "Twarz"}


# ── eksport OBJ / MTL ────────────────────────────────────────────────────────────
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def write_obj(item_id, boxes, out_dir):
    mats = sorted({b[6] for b in boxes})
    with open(os.path.join(out_dir, item_id + ".mtl"), "w", encoding="utf-8") as f:
        f.write(f"# Moddy – materiały dla {item_id}\n")
        for m in mats:
            col, alpha, glow = MAT[m]
            r, g, b = (c / 255 for c in _rgb(col))
            f.write(f"newmtl {m}\nKd {r:.3f} {g:.3f} {b:.3f}\nKa 0.2 0.2 0.2\nKs 0 0 0\nd {alpha}\n")
            if glow:
                f.write(f"Ke {r * .8:.3f} {g * .8:.3f} {b * .8:.3f}\n")
            f.write("\n")
    with open(os.path.join(out_dir, item_id + ".obj"), "w", encoding="utf-8") as f:
        f.write(f"# Moddy Cosmetics – {item_id} (1.0 = 1 blok, Y w górę, +Z = przód)\nmtllib {item_id}.mtl\no {item_id}\n")
        n = 0
        for mat in mats:
            f.write(f"usemtl {mat}\n")
            for (x0, y0, z0, x1, y1, z1, m) in (b for b in boxes if b[6] == mat):
                v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
                for p in v:
                    f.write("v %.5f %.5f %.5f\n" % (p[0] / 16, p[1] / 16, p[2] / 16))
                # ściany (CCW patrząc z zewnątrz): tył, przód, lewa, prawa, dół, góra
                faces = ((1, 4, 3, 2), (5, 6, 7, 8), (1, 5, 8, 4), (2, 3, 7, 6), (1, 2, 6, 5), (4, 8, 7, 3))
                for q in faces:
                    f.write("f " + " ".join(str(n + i) for i in q) + "\n")
                n += 8


# ── podgląd (izometryczny rendering programowy) ──────────────────────────────────
def _shade(col, k):
    r, g, b = _rgb(col)
    return (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)))


def render_preview(boxes, category, out_path, size=256, yaw=-32, pitch=24):
    S = size * 4
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    light = (-0.45, 0.85, 0.55)
    ln = math.sqrt(sum(c * c for c in light))
    light = tuple(c / ln for c in light)

    def proj(p):
        x, y, z = p
        x2, z2 = x * cy + z * sy, -x * sy + z * cy
        y3, z3 = y * cp - z2 * sp, y * sp + z2 * cp
        return x2, y3, z3

    faces = []
    for (x0, y0, z0, x1, y1, z1, m) in boxes:
        c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        for idx, nrm in (((0, 3, 2, 1), (0, 0, -1)), ((4, 5, 6, 7), (0, 0, 1)), ((0, 4, 7, 3), (-1, 0, 0)),
                         ((1, 2, 6, 5), (1, 0, 0)), ((0, 1, 5, 4), (0, -1, 0)), ((3, 7, 6, 2), (0, 1, 0))):
            nz = -nrm[0] * sy + nrm[2] * cy
            ny = nrm[1] * cp - nz * sp
            nzz = nrm[1] * sp + nz * cp
            if nzz <= 0.001:
                continue                                   # tył – niewidoczny
            pts = [proj(c[i]) for i in idx]
            depth = sum(p[2] for p in pts) / 4
            k = 0.5 + 0.5 * max(0.0, nrm[0] * light[0] + nrm[1] * light[1] + nrm[2] * light[2])
            faces.append((depth, pts, m, k))
    allp = [p for f in faces for p in f[1]]
    minx, maxx = min(p[0] for p in allp), max(p[0] for p in allp)
    miny, maxy = min(p[1] for p in allp), max(p[1] for p in allp)
    scale = (S * 0.84) / max(maxx - minx, maxy - miny, 1e-6)
    ox = S / 2 - (minx + maxx) / 2 * scale
    oy = S / 2 + (miny + maxy) / 2 * scale

    def to_px(p):
        return (p[0] * scale + ox, oy - p[1] * scale)

    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    if category == "pet":                                   # cień pod zwierzakiem
        w = (maxx - minx) * scale * 0.55
        cx = S / 2
        by = oy - miny * scale
        d.ellipse((cx - w, by - w * 0.22, cx + w, by + w * 0.22), fill=(0, 0, 0, 70))
    for depth, pts, m, k in sorted(faces, key=lambda f: f[0]):
        col, alpha, glow = MAT[m]
        rgb = _shade(col, 1.0 if glow else k)
        poly = [to_px(p) for p in pts]
        d.polygon(poly, fill=rgb + (int(255 * alpha),), outline=_shade(col, 0.45) + (int(230 * alpha),))
    img = img.resize((size, size), Image.LANCZOS)
    img.save(out_path)


# ── pelerynki 64x32 ──────────────────────────────────────────────────────────────
M_GLYPH = ("X...X", "XX.XX", "X.X.X", "X...X", "X...X")
STAR = ("...X...", "...X...", "XXXXXXX", ".XXXXX.", "..XXX..", ".XX.XX.", ".X...X.")


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def make_cape(name, top, bottom, border, emblem):
    img = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    px = img.load()
    top_c, bot_c, bor_c = _rgb(top), _rgb(bottom), _rgb(border)

    def fill(x0, y0, w, h, fn):
        for yy in range(h):
            for xx in range(w):
                px[x0 + xx, y0 + yy] = fn(xx, yy, w, h) + (255,)

    def base(xx, yy, w, h):
        edge = xx in (0, w - 1) or yy in (0, h - 1)
        return bor_c if edge else _lerp(top_c, bot_c, yy / (h - 1))

    fill(1, 1, 10, 16, base)              # zewnętrzna strona (widoczna z tyłu gracza)
    fill(12, 1, 10, 16, lambda xx, yy, w, h: _lerp(bot_c, (0, 0, 0), 0.35))      # wewnętrzna
    fill(1, 0, 10, 1, lambda *a: bor_c)
    fill(11, 0, 10, 1, lambda *a: bor_c)
    fill(0, 1, 1, 16, lambda xx, yy, w, h: bor_c)
    fill(11, 1, 1, 16, lambda xx, yy, w, h: bor_c)
    if emblem == "M":
        for yy, row in enumerate(M_GLYPH):
            for xx, ch in enumerate(row):
                if ch == "X":
                    px[1 + 2 + xx + 0, 1 + 5 + yy] = (255, 255, 255, 255)
        for xx in range(2, 8):
            px[1 + xx, 1 + 12] = _rgb(border) + (255,)
    elif emblem == "stripe":
        for xx in range(1, 9):
            for yy in (7, 8):
                px[1 + xx, 1 + yy] = (255, 122, 47, 255)
        for yy, row in enumerate(M_GLYPH):
            for xx, ch in enumerate(row):
                if ch == "X":
                    px[1 + 2 + xx, 1 + 2 + yy] = (255, 122, 47, 255)
    elif emblem == "wave":
        for yy in range(2, 14):
            for xx in range(1, 9):
                if (yy + round(math.sin(xx * 0.95) * 1.6)) % 4 == 0:
                    px[1 + xx, 1 + yy] = (190, 235, 255, 255)
    elif emblem == "star":
        for yy, row in enumerate(STAR):
            for xx, ch in enumerate(row):
                if ch == "X":
                    px[1 + 1 + xx, 1 + 4 + yy] = (255, 250, 200, 255)
    img.save(os.path.join(HERE, "capes", name + ".png"))
    # podgląd: sama zewnętrzna strona powiększona
    front = img.crop((1, 1, 11, 17)).resize((160, 256), Image.NEAREST)
    prev = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    prev.paste(front, (48, 0), front)
    prev.save(os.path.join(HERE, "previews", "cape_" + name + ".png"))


CAPES = [
    ("orange", "Moddy Orange", "🟠", "#ff8a50", "#e04e10", "#a83000", "M"),
    ("dark", "Moddy Dark", "⬛", "#33333a", "#101014", "#000000", "stripe"),
    ("wave", "Moddy Wave", "🌊", "#4aa8ff", "#1c4fb0", "#0f2f73", "wave"),
    ("gold", "Moddy Gold", "⭐", "#ffd45a", "#d19a14", "#8a6208", "star"),
]


def main():
    for d in ("models", "previews", "capes"):
        os.makedirs(os.path.join(HERE, d), exist_ok=True)
    catalog = {"version": 1, "categories": CATEGORY_LABEL, "capes": [], "items": []}
    for cid, name, emoji, top, bottom, border, emblem in CAPES:
        make_cape(cid, top, bottom, border, emblem)
        catalog["capes"].append({"id": cid, "name": name, "emoji": emoji,
                                 "file": f"capes/{cid}.png", "preview": f"previews/cape_{cid}.png"})
    for item_id, cat, name, emoji, desc, fn, anchor in ITEMS:
        boxes = fn()
        write_obj(item_id, boxes, os.path.join(HERE, "models"))
        render_preview(boxes, cat, os.path.join(HERE, "previews", item_id + ".png"))
        catalog["items"].append({"id": item_id, "category": cat, "name": name, "emoji": emoji, "desc": desc,
                                 "model": f"models/{item_id}.obj", "material": f"models/{item_id}.mtl",
                                 "preview": f"previews/{item_id}.png", "anchor": anchor})
    with open(os.path.join(HERE, "catalog.json"), "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    # kopia dla launchera (miniatury + katalog offline)
    bundle = os.path.join(REPO, "assets", "cosmetics")
    if os.path.isdir(os.path.join(REPO, "assets")):
        os.makedirs(bundle, exist_ok=True)
        shutil.copy2(os.path.join(HERE, "catalog.json"), bundle)
        for fn in os.listdir(os.path.join(HERE, "previews")):
            shutil.copy2(os.path.join(HERE, "previews", fn), bundle)
    print(f"OK: {len(ITEMS)} modeli, {len(CAPES)} pelerynek → {HERE}")


if __name__ == "__main__":
    main()
