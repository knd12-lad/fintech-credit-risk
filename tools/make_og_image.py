"""
Script to generate Open Graph image for social sharing (1200x630).
Run once to create static/images/og-image.png.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = BASE_DIR / "static" / "images" / "og-image.png"

WIDTH = 1200
HEIGHT = 630

NAVY = (11, 19, 43)        # #0B132B
DARK_NAVY = (28, 37, 65)   # #1C2541
TEAL = (20, 184, 166)      # #14B8A6
ACCENT_TEAL = (15, 118, 110) # #0F766E
WHITE = (255, 255, 255)
LIGHT_GRAY = (203, 213, 225) # #CBD5E1
GOLD = (249, 211, 66)      # #F9D342


def generate_og_image():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (WIDTH, HEIGHT), color=NAVY)
    draw = ImageDraw.Draw(img)

    # Decorative background elements
    # Subtle top & bottom accent borders
    draw.rectangle([0, 0, WIDTH, 8], fill=TEAL)
    draw.rectangle([0, HEIGHT - 8, WIDTH, HEIGHT], fill=TEAL)

    # Soft glowing radial/gradient corner accents
    draw.ellipse([-150, -150, 350, 350], fill=(15, 30, 60))
    draw.ellipse([WIDTH - 300, HEIGHT - 300, WIDTH + 200, HEIGHT + 200], fill=(15, 30, 60))

    # Inner container card
    card_margin_x = 80
    card_margin_y = 60
    draw.rounded_rectangle(
        [card_margin_x, card_margin_y, WIDTH - card_margin_x, HEIGHT - card_margin_y],
        radius=24,
        fill=DARK_NAVY,
        outline=ACCENT_TEAL,
        width=2,
    )

    # Decorative Shield Icon (Teal & Gold)
    shield_cx = WIDTH // 2
    shield_top = card_margin_y + 60
    shield_w = 64
    shield_h = 76

    shield_pts = [
        (shield_cx, shield_top),
        (shield_cx + shield_w // 2, shield_top + 16),
        (shield_cx + shield_w // 2, shield_top + 48),
        (shield_cx, shield_top + shield_h),
        (shield_cx - shield_w // 2, shield_top + 48),
        (shield_cx - shield_w // 2, shield_top + 16),
    ]
    draw.polygon(shield_pts, fill=TEAL)
    # Inner checkmark or highlight
    draw.line([(shield_cx - 14, shield_top + 36), (shield_cx - 4, shield_top + 48), (shield_cx + 16, shield_top + 26)], fill=WHITE, width=4)

    # Load system or default font
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 76)
        sub_font = ImageFont.truetype("arialbd.ttf", 34)
        tagline_font = ImageFont.truetype("arial.ttf", 26)
    except IOError:
        try:
            title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 76)
            sub_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
            tagline_font = ImageFont.truetype("DejaVuSans.ttf", 26)
        except IOError:
            title_font = ImageFont.load_default()
            sub_font = ImageFont.load_default()
            tagline_font = ImageFont.load_default()

    # Title: RiskWise
    title_text = "RiskWise"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(((WIDTH - title_w) // 2, shield_top + shield_h + 30), title_text, font=title_font, fill=WHITE)

    # Tagline: Smarter Credit Decisions, Lower Risk
    tagline_text = "Smarter Credit Decisions, Lower Risk"
    tag_bbox = draw.textbbox((0, 0), tagline_text, font=sub_font)
    tag_w = tag_bbox[2] - tag_bbox[0]
    draw.text(((WIDTH - tag_w) // 2, shield_top + shield_h + 125), tagline_text, font=sub_font, fill=TEAL)

    # Secondary descriptor
    desc_text = "Machine Learning Credit Scoring & Explainable Loan Default Prediction"
    desc_bbox = draw.textbbox((0, 0), desc_text, font=tagline_font)
    desc_w = desc_bbox[2] - desc_bbox[0]
    draw.text(((WIDTH - desc_w) // 2, shield_top + shield_h + 185), desc_text, font=tagline_font, fill=LIGHT_GRAY)

    # Save
    img.save(OUTPUT_PATH, format="PNG", optimize=True)
    print(f"Generated OG image at {OUTPUT_PATH} ({WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    generate_og_image()
