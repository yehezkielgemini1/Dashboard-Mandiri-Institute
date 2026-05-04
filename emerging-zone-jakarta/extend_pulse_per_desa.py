"""
Extend NTL Recent Pulse 2025->2026 dari 16 named area ke semua 270 desa
via spatial join pixel ke polygon desa.

Output:
- Update kolom pulse_badge dan pulse_yoy_2026 di 260503_FINAL_eczi_per_desa.csv
- Re-run aggregate_kawasan.py untuk update 260503_FINAL_eczi_per_kawasan.csv
"""
import pandas as pd
import numpy as np
import geopandas as gpd
import rasterio
from pathlib import Path

DATA = Path(r"C:/Users/LENOVO/OneDrive - PT Bank Mandiri (Persero) Tbk/Desktop/Mandiri/Mandiri Institute/Dashboard/emerging-zone-jakarta/data")
RAW = Path(r"C:/Users/LENOVO/OneDrive - PT Bank Mandiri (Persero) Tbk/Desktop/Mandiri/Mandiri Institute/Scraping/NASA/nighttime-lights/raw/monthly")
SHP = r"C:/Users/LENOVO/OneDrive - PT Bank Mandiri (Persero) Tbk/Desktop/Mandiri/Software/IDN_shp/idn_admbnda_adm4_bps_20200401.shp"

# Step 1: Read all 8 TIFs and extract pixel-level lum values
print("[1] Loading TIF files Jan-Apr 2025 + 2026...")

def tif_to_pixels(year, month):
    fp = RAW / f"jakarta_ntl_{year}_{month:02d}.tif"
    with rasterio.open(fp) as src:
        data = src.read(1).astype(float)
        nodata = src.nodata
        transform = src.transform
        height, width = data.shape
    if nodata is not None:
        data[data == nodata] = np.nan
    data[data <= 0] = np.nan
    rows = []
    for r in range(height):
        for c in range(width):
            v = data[r, c]
            if np.isnan(v):
                continue
            lon, lat = transform * (c + 0.5, r + 0.5)
            rows.append({"lat": lat, "lon": lon, "lum": v, "year": year, "month": month})
    return pd.DataFrame(rows)

dfs = []
for y in [2025, 2026]:
    for m in [1, 2, 3, 4]:
        sub = tif_to_pixels(y, m)
        dfs.append(sub)
        print(f"  {y}-{m:02d}: {len(sub):,} pixels")
all_pixels = pd.concat(dfs, ignore_index=True)
print(f"  Total: {len(all_pixels):,}")

# Step 2: Spatial join ke desa polygon
print("\n[2] Spatial join ke desa polygon...")
gdf = gpd.read_file(SHP)
dki = gdf[gdf['ADM1_PCODE']=='ID31'][['ADM4_EN','ADM4_PCODE','geometry']].copy()
dki = dki.rename(columns={'ADM4_EN':'nama_desa', 'ADM4_PCODE':'desa_pcode'})

pixels_gdf = gpd.GeoDataFrame(all_pixels,
    geometry=gpd.points_from_xy(all_pixels.lon, all_pixels.lat), crs="EPSG:4326")
joined = gpd.sjoin(pixels_gdf, dki[['nama_desa','desa_pcode','geometry']],
                    how='inner', predicate='within')
print(f"  Pixels matched: {len(joined):,}")

# Step 3: Aggregate per desa per year (median Jan-Apr)
print("\n[3] Computing YoY pulse per desa...")
agg = joined.groupby(['desa_pcode','nama_desa','year'])['lum'].median().reset_index()
piv = agg.pivot(index=['desa_pcode','nama_desa'], columns='year', values='lum').reset_index()

# Compute YoY pulse
piv['pulse_yoy_pct'] = ((piv[2026] - piv[2025]) / piv[2025] * 100).round(2)

def badge(p):
    if pd.isna(p): return "tidak tersedia"
    if p >= 5:    return "Trend Lanjut Tumbuh"
    if p >= -5:   return "Stabil"
    return "Mulai Melambat"

piv['pulse_badge'] = piv['pulse_yoy_pct'].apply(badge)

print(f"  Total desa with pulse: {piv['pulse_yoy_pct'].notna().sum()} of {len(piv)}")
print(f"\nBadge distribution:")
print(piv['pulse_badge'].value_counts().to_string())

# Step 4: Update FINAL_eczi_per_desa.csv with new pulse
print("\n[4] Updating 260503_FINAL_eczi_per_desa.csv...")
final_desa = pd.read_csv(DATA / "260503_FINAL_eczi_per_desa.csv")

# Merge new pulse data
pulse_update = piv[['desa_pcode','pulse_yoy_pct','pulse_badge']].rename(
    columns={'pulse_yoy_pct':'pulse_yoy_2026_NEW', 'pulse_badge':'pulse_badge_NEW'})

final_desa = final_desa.merge(pulse_update, on='desa_pcode', how='left')

# Update pulse columns: prefer new value if available
final_desa['pulse_yoy_2026'] = final_desa['pulse_yoy_2026_NEW'].fillna(final_desa['pulse_yoy_2026'])
final_desa['pulse_badge'] = final_desa['pulse_badge_NEW'].fillna(final_desa['pulse_badge'])
final_desa = final_desa.drop(columns=['pulse_yoy_2026_NEW','pulse_badge_NEW'])

# Save updated
final_desa.to_csv(DATA / "260503_FINAL_eczi_per_desa.csv", index=False)
print(f"  Saved 270 desa with extended pulse")
print(f"\n  Final badge distribution per desa:")
print(final_desa['pulse_badge'].value_counts().to_string())
