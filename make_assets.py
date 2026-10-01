# Dijalankan di GitHub Actions: bikin ikon & splash dari gambar maskot.
from PIL import Image
import os

BG = (217, 221, 251, 255)  # #D9DDFB, sama dengan layar loading
os.makedirs("assets", exist_ok=True)
cat = Image.open("www/m0.png").convert("RGBA")
cat = cat.crop(cat.getbbox())

def put(size, bg, box, name):
    r = min(box / cat.width, box / cat.height)
    k = cat.resize((round(cat.width * r), round(cat.height * r)), Image.LANCZOS)
    c = Image.new("RGBA", (size, size), bg)
    c.alpha_composite(k, ((size - k.width) // 2, (size - k.height) // 2))
    c.save(name)

put(1024, BG, 760, "assets/icon-only.png")
put(1024, (0, 0, 0, 0), 620, "assets/icon-foreground.png")
Image.new("RGBA", (1024, 1024), BG).save("assets/icon-background.png")
put(2732, BG, 700, "assets/splash.png")
put(2732, BG, 700, "assets/splash-dark.png")
