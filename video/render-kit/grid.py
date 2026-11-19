"""Layout grid and type scale for 1920x1080 explainer videos.

Built for "Cave or Hold?" (long and short cuts) and meant to be reused for later videos in the same style.
Every y value is the TOP of the element unless a comment says baseline.

Zones (top to bottom):
  0-40      top margin, empty
  40        note line: small all-caps label (e.g. "THE CAVING TEST · PRE-REGISTERED", "EXPLORATORY")
  90        title (Lora 600, 56 px, centered)
  170       optional subtitle (Inter Medium, one line)
  230-940   content (180-940 when there is no subtitle); text-heavy slides size type to fill it
  955-1080  caption band, at least 120 px: on-screen captions only, kept free for platform closed captions
Exceptions: full-frame designs (hook, title card, big statements) skip the note/title rows but keep the caption band clear.
"""
import render as R

W, H = 1920, 1080
MARGIN_X = 50
NOTE_Y = 40
TITLE_Y = 90
SUB_Y = 170
CONTENT_TOP = 230
CONTENT_TOP_NOSUB = 180
CONTENT_BOTTOM = 940
CAPTION_TOP = 955
CAP_BASE_1 = 1022            # baseline of a one-line caption
CAP_BASE_2 = (994, 1046)     # baselines of a two-line caption

# type scale: role -> (family, size, weight); Lora = serif, Inter = sans
TYPE = {
    "display":   ("Lora", 128, 400),       # title card
    "title":     ("Lora", 56, 600),        # slide titles
    "statement": ("Lora", 64, 700),        # key statements and the last close line
    "quote":     ("Lora", 44, 500),        # quotes, italic
    "note":      ("Inter", 24, "SemiBold"),  # note line, all caps, muted
    "subtitle":  ("Inter", 30, "Medium"),
    "body":      ("Inter", 32, "Regular"),
    "label":     ("Inter", 30, "SemiBold"),
    "small":     ("Inter", 28, "Regular"),  # floor: nothing smaller on screen
    "number":    ("Inter", 56, "Bold"),
    "caption":   ("Inter", 42, "Medium"),
}

def font(role, italic=False):
    fam, size, w = TYPE[role]
    return R.SF(size, w, italic) if fam == "Lora" else R.F(size, w)

def note(c, text, a=1.0, color=None):
    c.text((W // 2, NOTE_Y), text.upper(), font("note"), color or R.MUTED, a, "ma")

def title(c, text, a=1.0, color=None):
    c.text((W // 2, TITLE_Y), text, font("title"), color or R.INK, a, "ma")

def subtitle(c, text, a=1.0, color=None):
    c.text((W // 2, SUB_Y), text, font("subtitle"), color or R.SOFT, a, "ma")

def box(c, x0, y0, x1, y1, a=1.0, outline=None):
    """The shared panel style (Strengths / Limitations / Next questions rows)."""
    c.rrect((x0, y0, x1, y1), 24, fill=(255, 255, 255), outline=outline or R.MUTED, ow=1.5, a=a, fa=0.04)

def guides(img, a=90):
    """Draw the zones faintly on a still, for review only (never in the video)."""
    from PIL import Image, ImageDraw
    im = img.convert("RGBA"); layer = Image.new("RGBA", im.size, (0, 0, 0, 0)); ov = ImageDraw.Draw(layer)
    sx = im.size[0] / W
    for y, col in ((NOTE_Y, (120, 200, 255)), (TITLE_Y, (120, 200, 255)), (SUB_Y, (120, 200, 255)),
                   (CONTENT_TOP, (140, 255, 160)), (CONTENT_BOTTOM, (140, 255, 160)), (CAPTION_TOP, (255, 120, 120))):
        for x in range(0, W, 24):
            ov.line([(x * sx, y * sx), ((x + 12) * sx, y * sx)], fill=col + (a,), width=max(1, int(2 * sx)))
    ov.rectangle([(0, CAPTION_TOP * sx), (W * sx, H * sx)], fill=(255, 120, 120, 22))
    im = Image.alpha_composite(im, layer)
    return im.convert("RGB")
