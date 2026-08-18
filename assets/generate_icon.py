"""Erzeugt das App-Icon (assets/icon.ico) programmatisch mit Pillow.

Motiv: abgerundetes Quadrat im Teal-Farbverlauf (passend zum qt-material
dark_teal-Theme) mit stilisiertem Dokument + Lupe (Sinnbild fuer Jobsuche).
Wird bei Bedarf einmalig ausgefuehrt: python assets/generate_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 1024  # hochaufgeloest zeichnen, dann fuer ICO herunterskalieren
OUT_PATH = Path(__file__).parent / "icon.ico"

TEAL_LIGHT = (29, 233, 182)  # #1DE9B6
TEAL_DARK = (0, 121, 107)  # #00796B
WHITE = (255, 255, 255, 255)


def _rounded_square_gradient() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gradient = Image.new("RGBA", (SIZE, SIZE))
    for y in range(SIZE):
        t = y / SIZE
        r = int(TEAL_LIGHT[0] + (TEAL_DARK[0] - TEAL_LIGHT[0]) * t)
        g = int(TEAL_LIGHT[1] + (TEAL_DARK[1] - TEAL_LIGHT[1]) * t)
        b = int(TEAL_LIGHT[2] + (TEAL_DARK[2] - TEAL_LIGHT[2]) * t)
        for x in range(SIZE):
            gradient.putpixel((x, y), (r, g, b, 255))

    mask = Image.new("L", (SIZE, SIZE), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = int(SIZE * 0.22)
    mask_draw.rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=radius, fill=255)

    img.paste(gradient, (0, 0), mask)
    return img


def _draw_document_and_magnifier(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)

    # Dokument (leicht rotiert wirkendes, simples Rechteck mit umgeknickter Ecke)
    doc_left = int(SIZE * 0.24)
    doc_top = int(SIZE * 0.18)
    doc_right = int(SIZE * 0.66)
    doc_bottom = int(SIZE * 0.72)
    fold = int(SIZE * 0.12)

    doc_points = [
        (doc_left, doc_top),
        (doc_right - fold, doc_top),
        (doc_right, doc_top + fold),
        (doc_right, doc_bottom),
        (doc_left, doc_bottom),
    ]
    draw.polygon(doc_points, fill=WHITE)
    # umgeknickte Ecke leicht abdunkeln
    draw.polygon(
        [(doc_right - fold, doc_top), (doc_right, doc_top + fold), (doc_right - fold, doc_top + fold)],
        fill=(220, 240, 235, 255),
    )

    # Textzeilen im Dokument
    line_color = (0, 121, 107, 255)
    line_left = doc_left + int(SIZE * 0.06)
    line_right = doc_right - int(SIZE * 0.10)
    line_height = int(SIZE * 0.025)
    for i, y_frac in enumerate([0.32, 0.40, 0.48, 0.56]):
        y = int(SIZE * y_frac)
        right = line_right if i < 3 else line_left + int((line_right - line_left) * 0.6)
        draw.rounded_rectangle([line_left, y, right, y + line_height], radius=line_height // 2, fill=line_color)

    # Lupe (Kreis + Griff), ueberlappt die untere rechte Ecke des Dokuments
    circle_center = (int(SIZE * 0.70), int(SIZE * 0.68))
    circle_radius = int(SIZE * 0.16)
    ring_width = int(SIZE * 0.045)
    bbox = [
        circle_center[0] - circle_radius,
        circle_center[1] - circle_radius,
        circle_center[0] + circle_radius,
        circle_center[1] + circle_radius,
    ]
    draw.ellipse(bbox, outline=WHITE, width=ring_width)

    handle_start = (
        circle_center[0] + int(circle_radius * 0.75),
        circle_center[1] + int(circle_radius * 0.75),
    )
    handle_end = (int(SIZE * 0.90), int(SIZE * 0.90))
    draw.line([handle_start, handle_end], fill=WHITE, width=int(SIZE * 0.06))


def generate() -> Path:
    img = _rounded_square_gradient()
    _draw_document_and_magnifier(img)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(OUT_PATH, format="ICO", sizes=sizes)
    return OUT_PATH


if __name__ == "__main__":
    path = generate()
    print(f"Icon erzeugt: {path}")
