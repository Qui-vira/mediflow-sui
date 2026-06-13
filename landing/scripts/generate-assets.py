"""Generate placeholder PNG assets for MedBand landing page."""
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "-q"])
    from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "public" / "static"
OUT.mkdir(parents=True, exist_ok=True)

BG = (18, 24, 38)  # dark navy-ish
TEAL = (14, 124, 123)
LABEL_COLOR = (255, 255, 255, 128)

ASSETS = [
    ("noise.png", 200, 200, None, True),
    ("band-room-screenshot.png", 640, 400, "Band Room"),
    ("form-screenshot.png", 400, 300, "Patient Form"),
    ("dashboard-screenshot.png", 640, 400, "Dashboard"),
    ("sector-pharmacy.png", 200, 200, "Pharmacy"),
    ("sector-emergency.png", 200, 200, "Emergency"),
    ("sector-triage.png", 200, 200, "Triage"),
    ("sector-lab.png", 200, 200, "Lab"),
    ("sector-mental.png", 200, 200, "Mental Health"),
    ("sector-hmo.png", 200, 200, "HMO"),
]


def make_noise(w: int, h: int) -> Image.Image:
    import random

    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            v = random.randint(0, 255)
            px[x, y] = (v, v, v)
    return img


def make_placeholder(w: int, h: int, label: str | None) -> Image.Image:
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([2, 2, w - 3, h - 3], outline=TEAL, width=2)
    if label:
        try:
            font = ImageFont.truetype("arial.ttf", max(12, min(w, h) // 12))
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(((w - tw) / 2, (h - th) / 2), label, fill=TEAL, font=font)
    return img


for name, w, h, label, *rest in ASSETS:
    is_noise = rest[0] if rest else False
    img = make_noise(w, h) if is_noise else make_placeholder(w, h, label)
    img.save(OUT / name, "PNG")
    print(f"Created {name} ({w}x{h})")

print(f"Done — {len(ASSETS)} files in {OUT}")
