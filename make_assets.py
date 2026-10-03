# Dijalankan di GitHub Actions: bikin ikon & splash dari gambar maskot.
# icons.png = kumpulan 25 ikon (grid 5x5). Nomor tile dihitung per baris, mulai 0.
from PIL import Image, ImageFilter
import os

SHEET = "icons.png"
# kotak tiap tile (x0, y0, x1, y1), urut baris demi baris
BOXES = [
    (22,64,259,289),(276,61,505,289),(516,62,744,289),(757,62,987,289),(1002,61,1233,289),
    (20,313,257,538),(275,314,503,538),(514,314,744,539),(756,315,983,538),(1001,315,1229,538),
    (22,560,257,778),(274,561,501,777),(517,560,741,777),(758,560,986,778),(1003,560,1232,778),
    (23,799,256,1004),(275,800,501,1003),(518,799,743,1004),(759,799,984,1004),(1002,799,1231,1005),
    (24,1025,257,1231),(274,1025,501,1231),(518,1023,741,1231),(759,1025,985,1231),(1003,1024,1230,1231),
]
_sheet = None

def tile(i):
    """Potongan persegi tile ke-i, tanpa sudut membulat putih."""
    global _sheet
    if _sheet is None:
        _sheet = Image.open(SHEET).convert("RGB")
    x0, y0, x1, y1 = BOXES[i]
    s = min(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half = s / 2 - s * 0.07
    return _sheet.crop((round(cx - half), round(cy - half), round(cx + half), round(cy + half)))

def bgcolor(im):
    """Warna latar tile: warna paling sering di tepi atas dan kiri."""
    w, h = im.size
    px = [im.getpixel((x, 3)) for x in range(w)] + [im.getpixel((3, y)) for y in range(h)]
    buckets = {}
    for p in px:
        buckets.setdefault(tuple(v // 16 for v in p), []).append(p)
    best = max(buckets.values(), key=len)
    return tuple(sum(c[k] for c in best) // len(best) for k in range(3))

def square(im, px):
    return im.resize((px, px), Image.LANCZOS)

def foreground(im, canvas, frac=0.68):
    """Tile mengecil di tengah kanvas transparan, tepinya dipudarkan supaya menyatu dengan latar."""
    t = max(1, round(canvas * frac))
    k = im.resize((t, t), Image.LANCZOS).convert("RGBA")
    f = max(1, round(t * 0.05))
    m = Image.new("L", (t, t), 0)
    m.paste(255, (f, f, t - f, t - f))
    m = m.filter(ImageFilter.GaussianBlur(f / 2))
    k.putalpha(m)
    c = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    c.alpha_composite(k, ((canvas - t) // 2, (canvas - t) // 2))
    return c

if __name__ == "__main__":
    os.makedirs("assets", exist_ok=True)
    # ikon utama = tile 0 (ceria)
    t0 = tile(0)
    square(t0, 1024).save("assets/icon-only.png")
    foreground(t0, 1024).save("assets/icon-foreground.png")
    Image.new("RGBA", (1024, 1024), bgcolor(t0) + (255,)).save("assets/icon-background.png")
    # thumbnail untuk pilihan ikon di Pengaturan (dipakai www/index.html)
    for i in range(len(BOXES)):
        square(tile(i), 120).save("www/i%d.png" % i)
    # splash: maskot di tengah, warna sama dengan layar loading
    BG = (217, 221, 251, 255)
    cat = Image.open("www/m0.png").convert("RGBA")
    cat = cat.crop(cat.getbbox())
    r = min(700 / cat.width, 700 / cat.height)
    k = cat.resize((round(cat.width * r), round(cat.height * r)), Image.LANCZOS)
    for name in ("splash.png", "splash-dark.png"):
        c = Image.new("RGBA", (2732, 2732), BG)
        c.alpha_composite(k, ((2732 - k.width) // 2, (2732 - k.height) // 2))
        c.save("assets/" + name)
