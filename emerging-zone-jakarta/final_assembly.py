"""
Final assembly: combine semua data per desa ke 1 file siap pakai Dashboard agent.
Output: 260503_FINAL_eczi_per_desa.csv

Akan di-run setelah data_processing deliver:
- 260503_composite-potensi-weighted-DKI.csv (weighted by kategori)
- 260503_sakernas-revenue-5vintage-DKI.csv (5-vintage CAGR)

Hasil akhir per desa:
- Identitas: desa_pcode, nama_desa, kecamatan, kabkota, centroid lat/lon
- Komponen Layer 1 NTL: cagr, change, level, recovery, n_pixels, quality_flag
- Komponen Layer 2 Podes: count_total_2025, cagr, change, level, diversity_shannon
- Komponen Layer 3 Magnitude: potensi_2025, cagr, change, level
- Komponen Layer 4 OSM: count_hiburan, count_wellness, count_specialty, count_tourism
- Komponen Layer 5 Aksesibilitas: transport_score, count_layanan, catchment
- Pulse sidecar: pulse_yoy_2026, pulse_badge
- Normalized scores 0-100 per komponen
- Group scores g1-g5
- Composite ECZI score
- Composite Magnitude score (secondary leaderboard)
- Quadrant kategori (4 tipe kawasan)
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

DATA = Path(r"C:/Users/LENOVO/OneDrive - PT Bank Mandiri (Persero) Tbk/Desktop/Mandiri/Mandiri Institute/Dashboard/emerging-zone-jakarta/data")

# Bobot composite ECZI v2.1 (24/33/11/12/20)
# Update: magnitude_change_2024_2025 di-DROP karena 75% desa di -60% (sistemik noise Sakernas).
# Realokasi: mag_cagr 5%→6%, mag_level 3%→5%. Total Group 3 tetap 11%.
W = {
    "ntl_cagr": 0.13, "ntl_change": 0.07, "ntl_level": 0.04,
    "podes_cagr": 0.13, "podes_change": 0.07, "podes_level": 0.09, "podes_div": 0.04,
    "mag_cagr": 0.06, "mag_level": 0.05,  # mag_change DROPPED v2.1
    "osm_ent": 0.04, "osm_well": 0.03, "osm_spec": 0.03, "osm_tour": 0.02,
    "tra_access": 0.12, "tra_auto": 0.05, "tra_catch": 0.03,
}
GROUP_TOTALS = {"g1": 0.24, "g2": 0.33, "g3": 0.11, "g4": 0.12, "g5": 0.20}

# Bobot Magnitude composite (level-only, 50/30/20)
W_MAG = {"mag_level": 0.50, "podes_level": 0.30, "osm_lifestyle_density": 0.20}

# Symmetric winsorize untuk growth metrics — cap 5th-95th percentile
# (audit: change_2024_2025 distribution skewed median -65%, max +977% Pulau Harapan)
def winsorize(s, low_q=0.05, high_q=0.95):
    s = pd.to_numeric(s, errors="coerce")
    lo, hi = s.quantile(low_q), s.quantile(high_q)
    return s.clip(lower=lo, upper=hi)

def minmax(s):
    s = pd.to_numeric(s, errors="coerce")
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return pd.Series(50.0, index=s.index)
    return (s - mn) / (mx - mn) * 100

def minmax_log(s):
    s = pd.to_numeric(s, errors="coerce").fillna(0).clip(lower=0)
    return minmax(np.log1p(s))

def shannon(counts):
    counts = np.array(counts, dtype=float)
    counts = counts[counts > 0]
    if len(counts) == 0:
        return 0.0
    p = counts / counts.sum()
    return float(-np.sum(p * np.log(p + 1e-12)))

print("="*72)
print("FINAL ASSEMBLY — 260503_FINAL_eczi_per_desa.csv")
print("="*72)

# 1. Load all per-desa files
print("\n[1] Loading per-desa data files...")

ntl = pd.read_csv(DATA / "260503_NTL_per_desa.csv")
osm = pd.read_csv(DATA / "260503_OSM_per_desa.csv")
print(f"  NTL: {len(ntl)} desa")
print(f"  OSM: {len(osm)} desa")

# Podes per desa: count + diversity
podes = pd.read_csv(DATA / "podes-business-DKI.csv")

# Per desa per vintage: total count, plus CAGR, change, level, diversity at 2025
def podes_metrics_per_desa():
    rows = []
    for nama_desa, sub in podes.groupby("nama_desa"):
        # Total count per vintage
        totals = sub.groupby("vintage_year")["count"].sum()
        v2018 = totals.get(2018, 0)
        v2020 = totals.get(2020, 0)
        v2021 = totals.get(2021, 0)
        v2024 = totals.get(2024, 0)
        v2025 = totals.get(2025, 0)
        # Use median(2018, 2020, 2021) as robust baseline if 2021 anomali (drop > 50%)
        # Tapi audit menunjukkan 79% wajar, jadi pakai 2021 standard
        cagr = ((v2025 / v2021) ** (1/4) - 1) if v2021 > 0 else 0.0
        change = (v2025 - v2024) / v2024 if v2024 > 0 else 0.0
        # Diversity Shannon dari 10 kategori di 2025
        cat_counts = sub[sub.vintage_year == 2025].groupby("kategori")["count"].sum().values
        div = shannon(cat_counts)
        # Kabkota
        kabkota = sub["nama_kabkota"].iloc[0]
        rows.append({
            "nama_desa": nama_desa, "nama_kabkota_podes": kabkota,
            "podes_count_2025": v2025,
            "podes_cagr_2021_2025": round(cagr, 4),
            "podes_change_2024_2025": round(change, 4),
            "podes_level_2025": v2025,
            "podes_diversity_shannon": round(div, 4),
        })
    return pd.DataFrame(rows)

print("\n[2] Computing Podes metrics per desa...")
pod_df = podes_metrics_per_desa()
print(f"  Podes per desa: {len(pod_df)}")

# WINSORIZE Podes CAGR di 99th percentile (light intervention untuk 23 baris anomali)
cagr_99 = pod_df["podes_cagr_2021_2025"].quantile(0.99)
n_winsor = (pod_df["podes_cagr_2021_2025"] > cagr_99).sum()
pod_df["podes_winsorize_flag"] = pod_df["podes_cagr_2021_2025"] > cagr_99
pod_df.loc[pod_df["podes_winsorize_flag"], "podes_cagr_2021_2025"] = cagr_99
print(f"  Winsorized {n_winsor} desa with CAGR > 99th percentile ({cagr_99:.3f})")

# 3. Composite Potensi (Magnitude) — pakai existing composite-potensi (weighted version pending data_processing)
# Kalau weighted version available, pakai itu. Kalau belum, pakai existing.
print("\n[3] Loading Composite Magnitude...")
weighted_path = DATA / "260503_composite-potensi-weighted-DKI.csv"
if weighted_path.exists():
    print(f"  Using WEIGHTED version: {weighted_path.name}")
    comp = pd.read_csv(weighted_path)
    pot_col = "potensi_weighted"
    sektor_col = "sektor"  # weighted file pakai 'sektor'
else:
    print(f"  WEIGHTED version not found, using existing composite-potensi-DKI.csv")
    comp = pd.read_csv(DATA / "composite-potensi-DKI.csv")
    pot_col = "potensi_total"
    sektor_col = "kbli2"  # legacy file pakai 'kbli2'

# Aggregate magnitude per desa
def magnitude_per_desa():
    rows = []
    for nama_desa, sub in comp.groupby("nama_desa"):
        # Total potensi per vintage_year (sum sektor)
        totals = sub.groupby("vintage_year")[pot_col].sum()
        v2021 = float(totals.get(2021, 0))
        v2024 = float(totals.get(2024, 0))
        v2025 = float(totals.get(2025, 0))
        cagr = ((v2025 / v2021) ** (1/4) - 1) if v2021 > 0 else 0.0
        change = (v2025 - v2024) / v2024 if v2024 > 0 else 0.0
        # Per sektor (kbli2 atau sektor tergantung file)
        per_sek = sub[sub.vintage_year == 2025].groupby(sektor_col)[pot_col].sum()
        rows.append({
            "nama_desa": nama_desa,
            "magnitude_2025": v2025,
            "magnitude_cagr_2021_2025": round(cagr, 4),
            "magnitude_change_2024_2025": round(change, 4),
            "magnitude_perdagangan_2025": float(per_sek.get(7, 0)),
            "magnitude_akomamin_2025": float(per_sek.get(9, 0)),
        })
    return pd.DataFrame(rows)

mag_df = magnitude_per_desa()
print(f"  Magnitude per desa: {len(mag_df)}")

# 4. NTL Pulse (sidecar) — currently per 16 named area, need to map ke desa
# For Phase 0: hanya area utama yang dapat pulse, sisanya N/A
print("\n[4] Loading NTL Pulse sidecar...")
pulse_df = pd.read_excel(DATA / "260503_NASA_jakarta-recent-pulse.xlsx")
pulse_dict = pulse_df.set_index("area").to_dict("index")
# Map 16 named area ke desa terdekat (centroid match)
NAMED_AREA_TO_DESA = {
    "Blok M": "Melawai", "SCBD/Sudirman": "Senayan", "Kemang": "Bangka",
    "Cipete/Urban Forest": "Cipete Selatan", "Pesanggrahan": "Pesanggrahan",
    "PIK (Pantai Indah Kapuk)": "Kapuk Muara",
    "PIK 2 (Pantai Maju)": "Kamal Muara",
    "Kelapa Gading": "Kelapa Gading Timur", "Pluit/Penjaringan": "Pluit",
    "Ancol": "Ancol", "Kalideres": "Kalideres",
    "Cengkareng": "Cengkareng Timur", "Cilincing": "Cilincing",
    "Cawang": "Cawang", "Thamrin": "Gondangdia", "Pantai Mutiara": "Pluit",
}

# 5. Merge all
print("\n[5] Merging all data...")
final = ntl.copy()
final = final.merge(pod_df, on="nama_desa", how="left")
final = final.merge(mag_df, on="nama_desa", how="left")
final = final.merge(osm[["desa_pcode","centroid_lat","centroid_lon",
                          "count_hiburan_nightlife","count_gaya_hidup_wellness",
                          "count_retail_khusus","count_wisata_budaya","count_layanan_penunjang",
                          "transport_access_score_raw","catchment_density_1km"]],
                     on="desa_pcode", how="left")

# Fill missing with 0
fill_cols = ["count_hiburan_nightlife","count_gaya_hidup_wellness","count_retail_khusus",
             "count_wisata_budaya","count_layanan_penunjang","transport_access_score_raw",
             "catchment_density_1km","podes_count_2025","podes_cagr_2021_2025",
             "podes_change_2024_2025","podes_level_2025","podes_diversity_shannon",
             "magnitude_2025","magnitude_cagr_2021_2025","magnitude_change_2024_2025",
             "magnitude_perdagangan_2025","magnitude_akomamin_2025"]
for c in fill_cols:
    if c in final.columns:
        final[c] = final[c].fillna(0)

# Add NTL Pulse
final["pulse_badge"] = "tidak tersedia"
final["pulse_yoy_2026"] = 0.0
for area, desa in NAMED_AREA_TO_DESA.items():
    info = pulse_dict.get(area, {})
    if info:
        mask = final.nama_desa == desa
        final.loc[mask, "pulse_badge"] = {
            "Continuing growth": "Trend Lanjut Tumbuh",
            "Steady": "Stabil",
            "Slowing/reversing": "Mulai Melambat"
        }.get(info.get("pulse_badge"), "tidak tersedia")
        final.loc[mask, "pulse_yoy_2026"] = info.get("pulse_yoy_pct", 0)

# 6. Symmetric winsorize semua growth metrics (5-95th percentile)
# Tindak lanjut audit: change_2024_2025 sistemik noise (median -65%, max +977%)
print("\n[6a] Symmetric winsorize 5th-95th percentile pada growth metrics...")
growth_cols = ["ntl_cagr_2021_2025","ntl_change_2024_2025",
                "podes_cagr_2021_2025","podes_change_2024_2025",
                "magnitude_cagr_2021_2025","magnitude_change_2024_2025"]
for col in growth_cols:
    if col in final.columns:
        before_min, before_max = final[col].min(), final[col].max()
        final[col + "_w"] = winsorize(final[col], 0.05, 0.95)
        n_capped = ((final[col] != final[col + "_w"])).sum()
        print(f"  {col}: before [{before_min:.3f}, {before_max:.3f}] -> "
              f"after [{final[col + '_w'].min():.3f}, {final[col + '_w'].max():.3f}] "
              f"({n_capped} desa capped)")

# Flag low_reliability untuk Kep Seribu (kabkota = Kepulauan Seribu)
final["low_reliability_flag"] = (final["nama_kabkota"] == "Kepulauan Seribu").astype(int)
print(f"\n  Flag low_reliability: {int(final['low_reliability_flag'].sum())} desa (Kepulauan Seribu)")

# 6b. Normalize per komponen (level → log1p min-max; growth → direct min-max via winsorized)
print("\n[6b] Normalizing scores...")

# Growth (direct min-max via winsorized values)
final["n_ntl_cagr"]    = minmax(final["ntl_cagr_2021_2025_w"])
final["n_ntl_change"]  = minmax(final["ntl_change_2024_2025_w"])
final["n_podes_cagr"]  = minmax(final["podes_cagr_2021_2025_w"])
final["n_podes_change"]= minmax(final["podes_change_2024_2025_w"])
final["n_mag_cagr"]    = minmax(final["magnitude_cagr_2021_2025_w"])
# n_mag_change tidak digunakan di composite (DROPPED v2.1 karena sistemik noise Sakernas)

# Level (log1p min-max)
final["n_ntl_level"]   = minmax_log(final["ntl_level_2025"])
final["n_podes_level"] = minmax_log(final["podes_level_2025"])
final["n_podes_div"]   = minmax(final["podes_diversity_shannon"])
final["n_mag_level"]   = minmax_log(final["magnitude_2025"])
final["n_osm_ent"]     = minmax_log(final["count_hiburan_nightlife"])
final["n_osm_well"]    = minmax_log(final["count_gaya_hidup_wellness"])
final["n_osm_spec"]    = minmax_log(final["count_retail_khusus"])
final["n_osm_tour"]    = minmax_log(final["count_wisata_budaya"])
final["n_tra_access"]  = minmax_log(final["transport_access_score_raw"])
final["n_tra_auto"]    = minmax_log(final["count_layanan_penunjang"])
final["n_tra_catch"]   = minmax_log(final["catchment_density_1km"])

# 7. Group scores (0-100 per group)
print("\n[7] Computing group scores...")
final["g1"] = ((W["ntl_cagr"]*final["n_ntl_cagr"] + W["ntl_change"]*final["n_ntl_change"] +
                W["ntl_level"]*final["n_ntl_level"]) / GROUP_TOTALS["g1"]).round(2)
final["g2"] = ((W["podes_cagr"]*final["n_podes_cagr"] + W["podes_change"]*final["n_podes_change"] +
                W["podes_level"]*final["n_podes_level"] + W["podes_div"]*final["n_podes_div"]) / GROUP_TOTALS["g2"]).round(2)
final["g3"] = ((W["mag_cagr"]*final["n_mag_cagr"] +
                W["mag_level"]*final["n_mag_level"]) / GROUP_TOTALS["g3"]).round(2)
final["g4"] = ((W["osm_ent"]*final["n_osm_ent"] + W["osm_well"]*final["n_osm_well"] +
                W["osm_spec"]*final["n_osm_spec"] + W["osm_tour"]*final["n_osm_tour"]) / GROUP_TOTALS["g4"]).round(2)
final["g5"] = ((W["tra_access"]*final["n_tra_access"] + W["tra_auto"]*final["n_tra_auto"] +
                W["tra_catch"]*final["n_tra_catch"]) / GROUP_TOTALS["g5"]).round(2)

# 8. Composite ECZI score (weighted sum of group scores)
print("\n[8] Computing composite ECZI score...")
final["eczi_score"] = (
    GROUP_TOTALS["g1"]*final["g1"] + GROUP_TOTALS["g2"]*final["g2"] +
    GROUP_TOTALS["g3"]*final["g3"] + GROUP_TOTALS["g4"]*final["g4"] +
    GROUP_TOTALS["g5"]*final["g5"]
).round(2)

# Validate weights sum to 100% (check internal consistency)
total_w = sum(W.values())
print(f"  Total weights = {total_w:.4f} (should be 1.0)")
assert abs(total_w - 1.0) < 0.001, f"Weights don't sum to 1.0! Got {total_w}"

# 9. Composite Magnitude score (secondary leaderboard)
print("\n[9] Computing composite Magnitude score...")
osm_lifestyle_density = (final["count_hiburan_nightlife"] + final["count_gaya_hidup_wellness"] +
                         final["count_retail_khusus"] + final["count_wisata_budaya"])
final["n_osm_lifestyle_density"] = minmax_log(osm_lifestyle_density)
final["magnitude_score"] = (
    W_MAG["mag_level"]*final["n_mag_level"] +
    W_MAG["podes_level"]*final["n_podes_level"] +
    W_MAG["osm_lifestyle_density"]*final["n_osm_lifestyle_density"]
).round(2)

# 10. Quadrant classification (4 tipe kawasan)
print("\n[10] Quadrant classification...")
med_x = final["n_ntl_cagr"].median()
med_y = final["g4"].median()
def quad(row):
    hi_x = row["n_ntl_cagr"] >= med_x
    hi_y = row["g4"] >= med_y
    if hi_x and hi_y:   return "Kawasan Komersial Sedang Naik Daun"
    if hi_x and not hi_y: return "Awal Pertumbuhan"
    if not hi_x and hi_y: return "Kawasan Komersial Mapan"
    return "Aktivitas Rendah"
final["tipe_kawasan"] = final.apply(quad, axis=1)

# 11. Sort by ECZI
final = final.sort_values("eczi_score", ascending=False).reset_index(drop=True)
final.insert(0, "rank_eczi", final.index + 1)

# Magnitude rank
final = final.sort_values("magnitude_score", ascending=False).reset_index(drop=True)
final.insert(0, "rank_magnitude", final.index + 1)

# Re-sort by ECZI for save
final = final.sort_values("rank_eczi").reset_index(drop=True)

# 12. Save
print("\n[11] Saving final file...")
final.to_csv(DATA / "260503_FINAL_eczi_per_desa.csv", index=False)
print(f"  Total desa: {len(final)}")

# 13. Sanity check
print("\n=== SANITY CHECK ===")
print("\nTOP 10 by Skor Potensi Zona Komersial Berkembang (ECZI):")
print(final.nsmallest(10, "rank_eczi")[["nama_desa","nama_kabkota","eczi_score","tipe_kawasan","pulse_badge"]].to_string(index=False))

print("\nTOP 10 by Skor Magnitude Aktivitas Komersial:")
print(final.nsmallest(10, "rank_magnitude")[["nama_desa","nama_kabkota","magnitude_score","magnitude_2025","tipe_kawasan"]].to_string(index=False))

print("\nDistribusi tipe kawasan:")
print(final.tipe_kawasan.value_counts().to_string())

print("\nKuadran median split:")
print(f"  median NTL growth score: {med_x:.2f}")
print(f"  median POI lifestyle score (g4): {med_y:.2f}")

print(f"\n[+] Saved: 260503_FINAL_eczi_per_desa.csv")
