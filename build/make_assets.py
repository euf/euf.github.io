#!/usr/bin/env python3
"""
Generate site brand assets (favicon set + OpenGraph card) for euf.github.io.
Uses the exact site fonts (Commissioner 600) and palette so the mark matches the H1.

Outputs into ../ (repo root, served by GitHub Pages):
  favicon.ico, favicon.svg, favicon-16.png, favicon-32.png,
  apple-touch-icon.png, icon-192.png, icon-512.png, site.webmanifest, og.jpg

Run:  ./.venv/bin/python make_assets.py
"""
import os
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(HERE, "fonts")
GOLOS = os.path.join(FONTS, "Commissioner-600.ttf")  # display font (name/role/ЕФ monogram)
CUTOUT = "/Users/eugene/Downloads/headshot.opt.png"

# --- site palette (from index.html :root) ---
PAPER = (250, 247, 240)   # #FAF7F0  --bg
INK   = (26, 26, 23)      # #1A1A17  --ink
ACCENT= (19, 58, 124)     # #133A7C  --accent
MUTED = (90, 87, 80)      # #5A5750  --muted
HAIR  = (226, 222, 212)   # #E2DED4  --hairline

# Cyrillic monogram: Е (identical to Latin E) + Ф. Reads "EF" to a Latin
# audience, but the Ф gives a distinctive, ownable circle-and-bar mark.
MONO = "ЕФ"

# ----------------------------------------------------------------------------
# FAVICON (raster): deep-blue rounded tile, cream "ЕФ", Commissioner 600
# ----------------------------------------------------------------------------
def fit_font(text, target_w, target_h, path):
    """Largest font size whose text fits target box."""
    size = 10
    while True:
        f = ImageFont.truetype(path, size)
        l, t, r, b = f.getbbox(text)
        if (r - l) >= target_w or (b - t) >= target_h:
            return ImageFont.truetype(path, size - 1)
        size += 2

def render_tile(px, rounded=True, pad_ratio=0.0):
    """Render a single square favicon tile at px resolution (supersampled)."""
    S = 8
    W = px * S
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        rad = int(W * 0.22)
        d.rounded_rectangle([0, 0, W - 1, W - 1], radius=rad, fill=ACCENT + (255,))
    else:  # apple-touch: full-bleed square, iOS applies its own mask
        d.rectangle([0, 0, W, W], fill=ACCENT + (255,))
    # letters
    inner = W * (1 - pad_ratio)
    f = fit_font(MONO, inner * 0.88, inner * 0.62, GOLOS)  # width-governed for "ЕФ"; ~88% fill so the mark reads at 16px (was 0.80 → looked small next to peers)
    l, t, r, b = d.textbbox((0, 0), MONO, font=f)
    tw, th = r - l, b - t
    x = (W - tw) / 2 - l
    y = (W - th) / 2 - t - W * 0.015          # optical nudge up
    d.text((x, y), MONO, font=f, fill=PAPER + (255,))
    return img.resize((px, px), Image.LANCZOS)

def build_favicons():
    ico_master = render_tile(256)
    ico_master.save(os.path.join(ROOT, "favicon.ico"),
                    sizes=[(16, 16), (32, 32), (48, 48)])
    render_tile(16).save(os.path.join(ROOT, "favicon-16.png"))
    render_tile(32).save(os.path.join(ROOT, "favicon-32.png"))
    render_tile(192).save(os.path.join(ROOT, "icon-192.png"))
    render_tile(512).save(os.path.join(ROOT, "icon-512.png"))
    # apple-touch: opaque, square (iOS rounds it), small safe padding
    at = Image.new("RGBA", (180, 180), ACCENT + (255,))
    tile = render_tile(180, rounded=False)
    at.paste(tile, (0, 0), tile)
    at.convert("RGB").save(os.path.join(ROOT, "apple-touch-icon.png"))
    print("favicons: ico, 16, 32, 192, 512, apple-touch")

# ----------------------------------------------------------------------------
# FAVICON (svg): crisp, scalable, glyph outlines traced from Golos Text 600
# ----------------------------------------------------------------------------
def build_svg():
    tt = TTFont(GOLOS)
    upm = tt["head"].unitsPerEm
    cmap = tt.getBestCmap()
    glyphset = tt.getGlyphSet()

    # lay out E then F, capture combined path + advance
    paths, x_cursor = [], 0
    bounds = BoundsPen(glyphset)
    for ch in MONO:
        gname = cmap[ord(ch)]
        # path (translated by x_cursor)
        spen = SVGPathPen(glyphset)
        glyphset[gname].draw(spen)
        paths.append((spen.getCommands(), x_cursor))
        # bounds accumulation
        bpen = BoundsPen(glyphset)
        glyphset[gname].draw(bpen)
        if bpen.bounds:
            x0, y0, x1, y1 = bpen.bounds
            bounds.bounds = (min(bounds.bounds[0], x0 + x_cursor) if bounds.bounds else x0 + x_cursor,
                             min(bounds.bounds[1], y0) if bounds.bounds else y0,
                             max(bounds.bounds[2], x1 + x_cursor) if bounds.bounds else x1 + x_cursor,
                             max(bounds.bounds[3], y1) if bounds.bounds else y1)
        x_cursor += glyphset[gname].width
    bx0, by0, bx1, by1 = bounds.bounds
    gw, gh = bx1 - bx0, by1 - by0

    VB = 100.0
    box = 88.0                      # target extent inside tile (matches raster ~88% fill; 60 rendered too small in-tab, esp. Chrome which uses the SVG)
    s = box / max(gw, gh)
    tx = (VB - gw * s) / 2 - bx0 * s
    ty = (VB - gh * s) / 2 + by1 * s - VB * 0.012   # y-flip anchor + optical nudge

    glyph_svg = "".join(
        f'<path transform="translate({tx + dx*s:.3f} {ty}) scale({s:.5f} {-s:.5f})" '
        f'd="{cmds}"/>' for cmds, dx in paths
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<rect width="100" height="100" rx="22" fill="#133A7C"/>'
        f'<g fill="#FAF7F0">{glyph_svg}</g>'
        f'</svg>'
    )
    with open(os.path.join(ROOT, "favicon.svg"), "w") as fh:
        fh.write(svg)
    print("favicon.svg (traced outlines)")

# ----------------------------------------------------------------------------
# WEB MANIFEST
# ----------------------------------------------------------------------------
def build_manifest():
    m = (
        '{"name":"Evgeny Fayvuzhinskiy","short_name":"EF",'
        '"icons":[{"src":"/icon-192.png","sizes":"192x192","type":"image/png"},'
        '{"src":"/icon-512.png","sizes":"512x512","type":"image/png"}],'
        '"theme_color":"#133A7C","background_color":"#FAF7F0","display":"browser"}'
    )
    with open(os.path.join(ROOT, "site.webmanifest"), "w") as fh:
        fh.write(m)
    print("site.webmanifest")

# ----------------------------------------------------------------------------
# OPENGRAPH CARD 1200x630 — paper bg, cutout right, text left (site fonts)
# ----------------------------------------------------------------------------
def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines

def build_og():
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # cutout on the right; bleed off the right + bottom edges so the source's
    # hard crop edges fall off-canvas, and feather the one interior (left) edge
    # into the paper so there is no vertical seam facing the text.
    text_right = W - 96                 # default text-column edge if no portrait
    if os.path.exists(CUTOUT):
        c = Image.open(CUTOUT).convert("RGBA")
        target_h = 592
        scale = target_h / c.height
        c = c.resize((round(c.width * scale), target_h), Image.LANCZOS)
        px = W - c.width + 44          # bleed ~44px off the right edge
        py = H - c.height + 22         # bleed ~22px off the bottom edge
        # feather the left edge: ramp a horizontal alpha gradient into existing alpha
        aband = c.split()[3]
        ap = aband.load()
        feather = 90
        for x in range(min(feather, c.width)):
            k = x / feather            # 0 at left edge -> 1 at feather end
            for y in range(c.height):
                ap[x, y] = int(ap[x, y] * k)
        c.putalpha(aband)
        img.paste(c, (px, py), c)
        # portrait's real left edge at head height (top 60%, ignoring the wider
        # shoulders below) so the name can run right up to the face, not the padding
        head = aband.crop((0, 0, c.width, int(c.height * 0.60)))
        head = head.point(lambda a: 255 if a > 140 else 0)
        hb = head.getbbox()
        if hb:
            text_right = px + hb[0] - 36

    # TEXT: name (2 lines) + role only, no tagline. Sized to fill the column to the
    # left of the portrait so it stays legible when LinkedIn/Slack shrink the card.
    # PADX is a *safe margin*: Safari's desktop Start Page tile center-crops the
    # 1.905:1 card to ~1.68:1, shaving ~71px off each side. A small left pad put the
    # name hard against that crop edge; 132 keeps a comfortable margin even toward a
    # 1.6:1 crop, while the full card stays balanced against the right-anchored face.
    PADX = 100
    avail_w = text_right - PADX         # fills right up to the portrait's real edge

    def fit_width(text, target_w, path):   # largest size whose line fits target_w
        s = 48
        while d.textlength(text, font=ImageFont.truetype(path, s)) < target_w:
            s += 2
        return ImageFont.truetype(path, s - 2)

    name_f = fit_width("Fayvuzhinskiy", avail_w, GOLOS)  # the long line drives the size
    ns = name_f.size
    role   = "CHIEF PRODUCT OFFICER"
    def fit_tracked(text, target_w, path, tr_ratio):  # size so the tracked caps span target_w
        s = 24
        while True:
            f  = ImageFont.truetype(path, s)
            tr = s * tr_ratio
            w  = sum(d.textlength(ch, font=f) + tr for ch in text) - tr
            if w >= target_w:
                return ImageFont.truetype(path, s - 2), (s - 2) * tr_ratio
            s += 2
    role_f, track = fit_tracked(role, avail_w, GOLOS, 0.14)  # role spans the name's width

    line_h = round(ns * 1.02)
    gap    = round(ns * 0.56)           # name block -> role: clears the descenders
    role_h = round(role_f.size * 1.25)
    block_h = line_h * 2 + gap + role_h
    y = (H - block_h) // 2 - 18         # a touch above center — sits with the eyes without leaving a bottom void

    for line in ["Evgeny", "Fayvuzhinskiy"]:
        d.text((PADX, y), line, font=name_f, fill=INK)
        y += line_h
    y += gap
    x = PADX
    for ch in role:  # stroke in the same colour fakes a ~700 weight (no heavier static cut on hand)
        d.text((x, y), ch, font=role_f, fill=ACCENT, stroke_width=1, stroke_fill=ACCENT)
        x += d.textlength(ch, font=role_f) + track

    img.save(os.path.join(ROOT, "og.jpg"), quality=90, optimize=True, progressive=True)
    print("og.jpg (1200x630)")

if __name__ == "__main__":
    build_favicons()
    build_svg()
    build_manifest()
    build_og()
    print("done ->", ROOT)
