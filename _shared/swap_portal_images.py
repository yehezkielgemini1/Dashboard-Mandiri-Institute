"""Swap Stitch placeholder images dengan asset local Mandiri Institute.
- Carousel 5 slots: produk rutin (Monthly Gazette, Policy Brief, EXECUTIVE BRIEF=Demographic 2025 center, Infografis, Demographic alt)
- Annual cards (3): Konsumsi Masyarakat, Kelas Masyarakat, UMKM Nasional
- Thematic cards (4): BBM, Pangan, Demografi-Kesehatan, MBG
- Key Insights cards (2): Peta Potensi Kendaraan, Aktivitas Ekonomi
"""
import re
from pathlib import Path

fp = Path("index.html")
text = fp.read_text(encoding="utf-8")

# ============================================================
# CAROUSEL — 5 IMG tags, replace src + labels
# ============================================================

# Carousel image mapping (slot 1 far left → slot 5 far right)
carousel_imgs = [
    # (alt label, image path)
    ("Monthly Gazette", "_assets/foto/kelas-masyarakat-clean.jpg"),         # slot 1 far left
    ("Policy Brief",    "_assets/foto/kendaraan-clean.jpg"),               # slot 2 mid left
    ("Demographic & Consumption 2025", "_assets/foto/Demographic & Consumption 2025.png"),  # slot 3 CENTER
    ("Infografis",      "_assets/foto/bbm-clean.jpg"),                     # slot 4 mid right
    ("Publikasi",       "_assets/foto/demographic-consumption-clean.jpg"), # slot 5 far right
]

# Find all <img ... src="https://lh3.googleusercontent.com/..."/> in carousel order
# Replace src and alt
img_pattern = re.compile(r'(<img\s+alt=")([^"]+)("\s+class="w-full h-full object-cover rounded-sm"\s+src=")(https://lh3[^"]+)("\s*/>)')
matches = list(img_pattern.finditer(text))
print(f"Found {len(matches)} carousel <img> tags")

# Replace in reverse order (preserves indices)
for i, m in enumerate(reversed(matches)):
    idx = len(matches) - 1 - i  # original index
    new_alt, new_src = carousel_imgs[idx]
    new_tag = f'{m.group(1)}{new_alt}{m.group(3)}{new_src}{m.group(5)}'
    text = text[:m.start()] + new_tag + text[m.end():]
print(f"Replaced {len(matches)} carousel images")

# Update center spotlight overlay card (slot 3 currently has "EXECUTIVE BRIEF" + Article | Nov 18 2025 + "Membaca Indonesia melalui data")
# Re-label to: "EXECUTIVE BRIEF" + "Edisi 2025" + "Demographic & Consumption 2025"
text = text.replace(
    '<p class="text-[10px] text-ice-blue uppercase tracking-[0.15em] mb-2 font-bold">Artikel | 18 November 2025</p>\n<h2 class="text-2xl font-serif text-mandiri-deep leading-tight font-medium">Membaca Indonesia melalui data</h2>',
    '<p class="text-[10px] text-ice-blue uppercase tracking-[0.15em] mb-2 font-bold">Riset Tahunan | 2025</p>\n<h2 class="text-2xl font-serif text-mandiri-deep leading-tight font-medium">Demographic &amp; Consumption 2025</h2>'
)

# ============================================================
# DASHBOARD CARDS — replace bg-gray-200 image layer dengan asset bg
# ============================================================

card_imgs = {
    # 9 cards by category label uniqueness
    "Konsumsi Masyarakat": "_assets/foto/demographic-consumption-clean.jpg",
    "Kelas Masyarakat":    "_assets/foto/kelas-masyarakat-clean.jpg",
    "UMKM Nasional":       "_assets/foto/kendaraan-clean.jpg",  # placeholder reuse
    "Konsumsi BBM":        "_assets/foto/bbm-clean.jpg",
    "Ketahanan Pangan":    "_assets/foto/demographic-consumption-clean.jpg",  # placeholder
    "Demografi-Kesehatan": "_assets/foto/kelas-masyarakat-clean.jpg",  # placeholder
    "Pemetaan Prioritas MBG": "_assets/foto/bbm-clean.jpg",  # placeholder
    "Peta Potensi Kendaraan": "_assets/foto/kendaraan-clean.jpg",
    "Aktivitas Ekonomi":   "_assets/foto/demographic-consumption-clean.jpg",  # placeholder
}

# For each card, find <article ... bg-gray-200>...<h3 ...>TITLE</h3> and replace inner bg-gray-200 div
# Article structure: <article class="...bg-gray-200"><div class="absolute inset-0 bg-gray-200"></div>...<h3 class="...">TITLE</h3>...
for title, img_path in card_imgs.items():
    # Pattern: find <article ... > then <div class="absolute inset-0 bg-gray-200"></div> then later <h3 ...>TITLE</h3>
    # Find article block by searching for <h3 ...>title</h3>
    title_pat = re.compile(r'<h3 [^>]*>' + re.escape(title) + r'</h3>')
    m = title_pat.search(text)
    if not m:
        print(f"SKIP not found: {title}")
        continue
    # Search backward for the nearest <div class="absolute inset-0 bg-gray-200"></div>
    snippet = text[:m.start()]
    div_idx = snippet.rfind('<div class="absolute inset-0 bg-gray-200"></div>')
    if div_idx == -1:
        print(f"SKIP no bg div: {title}")
        continue
    # Replace this div with img bg styled
    old_div = '<div class="absolute inset-0 bg-gray-200"></div>'
    new_div = f'<div class="absolute inset-0 bg-cover bg-center group-hover:scale-105 transition-transform duration-700" style="background-image: url(\'{img_path}\');"></div>'
    text = text[:div_idx] + new_div + text[div_idx + len(old_div):]
    print(f"OK: {title} -> {img_path.split('/')[-1]}")

# Write
fp.write_text(text, encoding="utf-8")
print("\nDone. index.html updated.")
