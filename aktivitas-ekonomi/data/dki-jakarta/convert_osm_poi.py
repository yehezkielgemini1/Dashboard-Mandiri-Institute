"""Convert OSM POI xlsx ke compact JSON untuk dashboard."""
import json
from pathlib import Path
import pandas as pd

DATA_DIR = Path('../../../emerging-zone-jakarta/data')
OUT_PATH = Path('osm-poi.json')

GROUP_MAP = {
    # F&B
    'restaurant': 'FNB', 'cafe': 'FNB', 'fast_food': 'FNB', 'food_court': 'FNB',
    'bar': 'FNB', 'pub': 'FNB', 'ice_cream': 'FNB',
    # Retail
    'convenience': 'RETAIL', 'supermarket': 'RETAIL', 'mall': 'RETAIL',
    'marketplace': 'RETAIL', 'department': 'RETAIL', 'clothes': 'RETAIL',
    'electronics': 'RETAIL', 'mobile': 'RETAIL', 'books': 'RETAIL',
    'photo': 'RETAIL', 'jewelry': 'RETAIL', 'optician': 'RETAIL',
    'shoes': 'RETAIL', 'sports_shop': 'RETAIL', 'toys': 'RETAIL',
    'florist': 'RETAIL', 'bicycle': 'RETAIL',
    # Entertainment
    'cinema': 'ENT', 'theatre': 'ENT', 'nightclub': 'ENT', 'karaoke': 'ENT',
    'arts_centre': 'ENT', 'bowling': 'ENT', 'theme_park': 'ENT',
    'attraction': 'ENT', 'viewpoint': 'ENT', 'museum': 'ENT',
    'gallery': 'ENT', 'zoo': 'ENT', 'aquarium': 'ENT',
    # Health/Wellness
    'clinic': 'HEALTH', 'pharmacy': 'HEALTH', 'hairdresser': 'HEALTH',
    'beauty': 'HEALTH', 'massage': 'HEALTH', 'fitness': 'HEALTH',
    'sports': 'HEALTH', 'swimming': 'HEALTH',
    # Finance
    'bank': 'FIN', 'atm': 'FIN', 'post_office': 'FIN',
    # Fuel
    'fuel': 'FUEL', 'car_wash': 'FUEL',
}

CATEGORY_LABELS = {
    'restaurant': 'Restoran', 'cafe': 'Kafe', 'fast_food': 'Restoran Cepat Saji',
    'food_court': 'Food Court', 'bar': 'Bar', 'pub': 'Pub', 'ice_cream': 'Toko Es Krim',
    'convenience': 'Minimarket', 'supermarket': 'Supermarket', 'mall': 'Mall',
    'marketplace': 'Pasar Tradisional', 'department': 'Department Store', 'clothes': 'Toko Pakaian',
    'electronics': 'Toko Elektronik', 'mobile': 'Toko Gadget', 'books': 'Toko Buku',
    'photo': 'Studio Fotografi', 'jewelry': 'Toko Perhiasan', 'optician': 'Optik',
    'shoes': 'Toko Sepatu', 'sports_shop': 'Toko Olahraga', 'toys': 'Toko Mainan',
    'florist': 'Toko Bunga', 'bicycle': 'Toko Sepeda',
    'cinema': 'Bioskop', 'theatre': 'Teater', 'nightclub': 'Klub Malam',
    'karaoke': 'Karaoke', 'arts_centre': 'Pusat Seni', 'bowling': 'Bowling',
    'theme_park': 'Taman Hiburan', 'attraction': 'Atraksi Wisata', 'viewpoint': 'Titik Pandang',
    'museum': 'Museum', 'gallery': 'Galeri Seni', 'zoo': 'Kebun Binatang',
    'aquarium': 'Akuarium',
    'clinic': 'Klinik', 'pharmacy': 'Apotek', 'hairdresser': 'Salon Rambut',
    'beauty': 'Salon Kecantikan', 'massage': 'Tempat Pijat', 'fitness': 'Gym & Fitness',
    'sports': 'Tempat Olahraga', 'swimming': 'Kolam Renang',
    'bank': 'Bank', 'atm': 'ATM', 'post_office': 'Kantor Pos',
    'fuel': 'SPBU', 'car_wash': 'Cuci Mobil',
}

points = []
seen = set()  # dedupe by lat+lng+name

for fname in ['260502_OSM_poi-commercial-jakarta.xlsx', '260503_OSM_poi-lifestyle-jakarta.xlsx']:
    df = pd.read_excel(DATA_DIR / fname)
    for _, row in df.iterrows():
        cat = row.get('category')
        if not isinstance(cat, str):
            continue
        group = GROUP_MAP.get(cat)
        if not group:
            continue
        lat = row.get('lat')
        lng = row.get('lon')
        if pd.isna(lat) or pd.isna(lng):
            continue
        name = row.get('name')
        name_str = str(name) if isinstance(name, str) else ''
        # Dedupe: same lat+lng (5dp) + name
        key = (round(float(lat), 5), round(float(lng), 5), name_str)
        if key in seen:
            continue
        seen.add(key)
        points.append([
            round(float(lat), 5),
            round(float(lng), 5),
            cat,
            name_str[:40]  # truncate long names
        ])

# Stats
from collections import Counter
group_counts = Counter()
cat_counts = Counter()
for p in points:
    cat_counts[p[2]] += 1
    group_counts[GROUP_MAP[p[2]]] += 1

print('Total points:', len(points))
print('By group:', dict(group_counts.most_common()))
print('By category:', dict(cat_counts.most_common(15)))

out = {
    'groups': {
        'FNB': {'label': 'F&B (Resto, Kafe)', 'color': '#FF6B35'},
        'RETAIL': {'label': 'Retail (Mall, Toko)', 'color': '#4D96FF'},
        'ENT': {'label': 'Hiburan', 'color': '#9B5DE5'},
        'HEALTH': {'label': 'Kesehatan & Wellness', 'color': '#00B894'},
        'FIN': {'label': 'Finansial (Bank, ATM)', 'color': '#FDCB6E'},
        'FUEL': {'label': 'SPBU & Otomotif', 'color': '#E84545'}
    },
    'categories': {cat: {'label': CATEGORY_LABELS.get(cat, cat), 'group': GROUP_MAP[cat]} for cat in cat_counts.keys()},
    'points': points
}

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

print(f'Output: {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.1f} KB)')
