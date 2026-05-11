"""Fix carousel surround slots (add white card overlay) + dashboard cards (focus subject + navy tint).
- Carousel 4 surround: replace text-only overlay dengan white card overlay style center spotlight (smaller scale)
- Dashboard cards: shift background-position ke bottom (fokus orang/object), add navy filter
"""
import re
from pathlib import Path

fp = Path("index.html")
text = fp.read_text(encoding="utf-8")

# ============================================================
# CAROUSEL SURROUND SLOTS — add white card overlay mirror center
# ============================================================

# Replace slot 1 (Monthly Gazette far left, w-48 h-300)
old_slot1 = '''<!-- Slot 1: Monthly Gazette (far left) -->
<div class="carousel-item carousel-tinted hidden lg:block w-48 h-[300px] relative opacity-70 transform scale-90 transition-all duration-700 ease-in-out shrink-0" data-pos="1">
<img alt="Monthly Gazette" class="w-full h-full object-cover rounded-sm" src="_assets/foto/kelas-masyarakat-clean.jpg" style="object-position: center 30%;"/>
<div class="absolute inset-0 bg-gradient-to-t from-mandiri-deep/95 via-mandiri-deep/70 to-mandiri-deep/55 rounded-sm"></div>
<div class="absolute top-3 left-3 right-3 text-center">
<div class="text-[9px] text-ice-blue font-bold uppercase tracking-[0.15em] mb-1">Monthly Gazette</div>
</div>
<div class="absolute bottom-3 left-3 right-3 text-center">
<div class="text-xs text-white font-serif font-medium leading-tight">Edisi Maret 2026</div>
</div>
</div>'''
new_slot1 = '''<!-- Slot 1: Monthly Gazette (far left) -->
<div class="carousel-item carousel-tinted hidden lg:block w-48 h-[300px] relative opacity-80 transform scale-90 transition-all duration-700 ease-in-out shrink-0" data-pos="1">
<img alt="Monthly Gazette" class="w-full h-full object-cover rounded-sm" src="_assets/foto/kelas-masyarakat-clean.jpg" style="object-position: center 30%;"/>
<div class="absolute inset-0 bg-gradient-to-t from-mandiri-deep/85 via-mandiri-deep/50 to-mandiri-deep/30 rounded-sm"></div>
<div class="absolute top-3 left-3 border border-ice-blue text-ice-blue text-[8.5px] font-bold px-2 py-0.5 rounded-sm uppercase tracking-widest bg-white/90 backdrop-blur-sm">Monthly Gazette</div>
<div class="absolute bottom-3 left-3 right-3 bg-white/95 backdrop-blur-sm p-3 rounded-sm shadow-md border-l-2 border-ice-blue">
<p class="text-[8.5px] text-ice-blue uppercase tracking-[0.15em] mb-1 font-bold">Edisi Maret · 2026</p>
<h3 class="text-xs font-serif text-mandiri-deep leading-tight font-medium">Mandiri Outlook</h3>
</div>
</div>'''
text = text.replace(old_slot1, new_slot1)

# Slot 2 (Policy Brief, mid left, w-56 h-380)
old_slot2 = '''<!-- Slot 2: Policy Brief (mid left) -->
<div class="carousel-item carousel-tinted hidden md:block w-56 h-[380px] relative opacity-85 transform scale-95 transition-all duration-700 ease-in-out shrink-0" data-pos="2">
<img alt="Policy Brief" class="w-full h-full object-cover rounded-sm" src="_assets/foto/kendaraan-clean.jpg" style="object-position: center 40%;"/>
<div class="absolute inset-0 bg-gradient-to-t from-mandiri-deep/92 via-mandiri-deep/60 to-mandiri-deep/45 rounded-sm"></div>
<div class="absolute top-3 left-3 right-3 text-center">
<div class="text-[9.5px] text-ice-blue font-bold uppercase tracking-[0.15em]">Policy Brief</div>
</div>
<div class="absolute bottom-4 left-3 right-3 text-center">
<div class="text-sm text-white font-serif font-medium leading-tight">Subsidi BBM Tertarget</div>
<div class="text-[10px] text-white/70 mt-1 uppercase tracking-wider">No. 2 · Februari 2026</div>
</div>
</div>'''
new_slot2 = '''<!-- Slot 2: Policy Brief (mid left) -->
<div class="carousel-item carousel-tinted hidden md:block w-56 h-[380px] relative opacity-90 transform scale-95 transition-all duration-700 ease-in-out shrink-0" data-pos="2">
<img alt="Policy Brief" class="w-full h-full object-cover rounded-sm" src="_assets/foto/kendaraan-clean.jpg" style="object-position: center 40%;"/>
<div class="absolute inset-0 bg-gradient-to-t from-mandiri-deep/75 via-mandiri-deep/35 to-mandiri-deep/20 rounded-sm"></div>
<div class="absolute top-3 left-3 border border-ice-blue text-ice-blue text-[9px] font-bold px-2 py-0.5 rounded-sm uppercase tracking-widest bg-white/90 backdrop-blur-sm">Policy Brief</div>
<div class="absolute bottom-3 left-3 right-3 bg-white/95 backdrop-blur-sm p-4 rounded-sm shadow-md border-l-2 border-ice-blue">
<p class="text-[9px] text-ice-blue uppercase tracking-[0.15em] mb-1 font-bold">No. 2 · Februari 2026</p>
<h3 class="text-sm font-serif text-mandiri-deep leading-tight font-medium">Subsidi BBM Tertarget</h3>
</div>
</div>'''
text = text.replace(old_slot2, new_slot2)

# Slot 4 (Infografis, mid right)
old_slot4 = '''<!-- Slot 4: Infografis (mid right) -->
<div class="carousel-item carousel-tinted hidden md:block w-56 h-[380px] relative opacity-85 transform scale-95 transition-all duration-700 ease-in-out shrink-0" data-pos="4">
<img alt="Infografis" class="w-full h-full object-cover rounded-sm" src="_assets/foto/bbm-clean.jpg" style="object-position: center 50%;"/>
<div class="absolute inset-0 bg-gradient-to-t from-mandiri-deep/92 via-mandiri-deep/60 to-mandiri-deep/45 rounded-sm"></div>
<div class="absolute top-3 left-3 right-3 text-center">
<div class="text-[9.5px] text-ice-blue font-bold uppercase tracking-[0.15em]">Infografis</div>
</div>
<div class="absolute bottom-4 left-3 right-3 text-center">
<div class="text-sm text-white font-serif font-medium leading-tight">Kerentanan Middle Class</div>
<div class="text-[10px] text-white/70 mt-1 uppercase tracking-wider">Carousel IG · 2026</div>
</div>
</div>'''
new_slot4 = '''<!-- Slot 4: Infografis (mid right) -->
<div class="carousel-item carousel-tinted hidden md:block w-56 h-[380px] relative opacity-90 transform scale-95 transition-all duration-700 ease-in-out shrink-0" data-pos="4">
<img alt="Infografis" class="w-full h-full object-cover rounded-sm" src="_assets/foto/bbm-clean.jpg" style="object-position: center 50%;"/>
<div class="absolute inset-0 bg-gradient-to-t from-mandiri-deep/75 via-mandiri-deep/35 to-mandiri-deep/20 rounded-sm"></div>
<div class="absolute top-3 left-3 border border-ice-blue text-ice-blue text-[9px] font-bold px-2 py-0.5 rounded-sm uppercase tracking-widest bg-white/90 backdrop-blur-sm">Infografis</div>
<div class="absolute bottom-3 left-3 right-3 bg-white/95 backdrop-blur-sm p-4 rounded-sm shadow-md border-l-2 border-ice-blue">
<p class="text-[9px] text-ice-blue uppercase tracking-[0.15em] mb-1 font-bold">Carousel IG · 2026</p>
<h3 class="text-sm font-serif text-mandiri-deep leading-tight font-medium">Kerentanan Middle Class</h3>
</div>
</div>'''
text = text.replace(old_slot4, new_slot4)

# Slot 5 (Econmark, far right, w-48 h-300)
old_slot5 = '''<!-- Slot 5: Publikasi (far right) -->
<div class="carousel-item carousel-tinted hidden lg:block w-48 h-[300px] relative opacity-70 transform scale-90 transition-all duration-700 ease-in-out shrink-0" data-pos="5">
<img alt="Publikasi" class="w-full h-full object-cover rounded-sm" src="_assets/foto/demographic-consumption-clean.jpg" style="object-position: center 30%;"/>
<div class="absolute inset-0 bg-gradient-to-t from-mandiri-deep/95 via-mandiri-deep/70 to-mandiri-deep/55 rounded-sm"></div>
<div class="absolute top-3 left-3 right-3 text-center">
<div class="text-[9px] text-ice-blue font-bold uppercase tracking-[0.15em] mb-1">Econmark</div>
</div>
<div class="absolute bottom-3 left-3 right-3 text-center">
<div class="text-xs text-white font-serif font-medium leading-tight">Q1 2026</div>
</div>
</div>'''
new_slot5 = '''<!-- Slot 5: Econmark (far right) -->
<div class="carousel-item carousel-tinted hidden lg:block w-48 h-[300px] relative opacity-80 transform scale-90 transition-all duration-700 ease-in-out shrink-0" data-pos="5">
<img alt="Econmark" class="w-full h-full object-cover rounded-sm" src="_assets/foto/demographic-consumption-clean.jpg" style="object-position: center 65%;"/>
<div class="absolute inset-0 bg-gradient-to-t from-mandiri-deep/85 via-mandiri-deep/50 to-mandiri-deep/30 rounded-sm"></div>
<div class="absolute top-3 left-3 border border-ice-blue text-ice-blue text-[8.5px] font-bold px-2 py-0.5 rounded-sm uppercase tracking-widest bg-white/90 backdrop-blur-sm">Econmark</div>
<div class="absolute bottom-3 left-3 right-3 bg-white/95 backdrop-blur-sm p-3 rounded-sm shadow-md border-l-2 border-ice-blue">
<p class="text-[8.5px] text-ice-blue uppercase tracking-[0.15em] mb-1 font-bold">Q1 · 2026</p>
<h3 class="text-xs font-serif text-mandiri-deep leading-tight font-medium">Outlook Triwulanan</h3>
</div>
</div>'''
text = text.replace(old_slot5, new_slot5)

print("Slots 1, 2, 4, 5 updated with white card overlay")

# ============================================================
# DASHBOARD CARDS — focus subject (orang) + navy gradient overlay
# ============================================================
# Pattern: <div class="absolute inset-0 bg-cover bg-center group-hover:scale-105 ..." style="background-image: url('...');"></div>
# Replace with: same div but background-position: center bottom (fokus orang) + add navy filter via class

old_pattern = re.compile(
    r'<div class="absolute inset-0 bg-cover bg-center group-hover:scale-105 transition-transform duration-700" '
    r'style="background-image: url\(\'([^\']+)\'\);"></div>\n'
    r'<div class="absolute inset-0 bg-gradient-to-t from-gray-900/80 to-transparent"></div>'
)
matches = list(old_pattern.finditer(text))
print(f"Found {len(matches)} dashboard card image+gradient pairs")

def replace_card(m):
    img_url = m.group(1)
    # New: shift background-position based on image type
    if 'demographic-consumption' in img_url.lower() or 'demographic & consumption' in img_url.lower():
        bg_pos = 'center 78%'  # push image up so "Depok Citayam" label off-top, fokus orang
    elif 'kelas-masyarakat' in img_url.lower():
        bg_pos = 'center 55%'
    elif 'kendaraan-clean' in img_url.lower():
        bg_pos = 'center 50%'
    elif 'bbm-clean' in img_url.lower():
        bg_pos = 'center 55%'
    else:
        bg_pos = 'center 50%'
    return (
        f'<div class="absolute inset-0 bg-cover group-hover:scale-105 transition-transform duration-700" '
        f'style="background-image: url(\'{img_url}\'); background-position: {bg_pos}; filter: brightness(0.85) saturate(0.85);"></div>\n'
        f'<div class="absolute inset-0 bg-gradient-to-t from-mandiri-deep/85 via-mandiri-deep/40 to-mandiri-deep/15"></div>'
    )

text = old_pattern.sub(replace_card, text)

fp.write_text(text, encoding="utf-8")
print(f"Updated {len(matches)} dashboard cards with focus + navy tint")
print("Done.")
