"""One-off generator for site/assets/og-card.png (1200x630 OG/Twitter card)."""
from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1200, 630
INK = (11, 31, 77)
ACCENT = (47, 91, 234)
PASTEL_BLUE = (234, 241, 255)
WHITE = (255, 255, 255)

img = Image.new("RGB", (W, H), INK)
draw = ImageDraw.Draw(img)

draw.rectangle([W - 480, 0, W, H], fill=PASTEL_BLUE)

photo = Image.open("site/assets/photo.jpg").convert("RGB")
photo = ImageOps.fit(photo, (380, 380), method=Image.Resampling.LANCZOS)

mask = Image.new("L", (380, 380), 0)
mdraw = ImageDraw.Draw(mask)
mdraw.rounded_rectangle([0, 0, 380, 380], radius=48, fill=255)

photo_pos = (W - 440, (H - 380) // 2)
img.paste(photo, photo_pos, mask)

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

name_font = ImageFont.truetype(FONT_BOLD, 64)
role_font = ImageFont.truetype(FONT_REG, 32)
tag_font = ImageFont.truetype(FONT_REG, 26)

left_x = 80
draw.text((left_x, 190), "Zakaria Fadli", font=name_font, fill=WHITE)
draw.text((left_x, 270), "Senior Embedded Toolchain Engineer", font=role_font, fill=(214, 226, 255))
draw.text((left_x, 320), "AdaCore · ex-Netatmo/Legrand · RISC-V, Ada, C++", font=tag_font, fill=ACCENT)

img.save("site/assets/og-card.png", optimize=True)
