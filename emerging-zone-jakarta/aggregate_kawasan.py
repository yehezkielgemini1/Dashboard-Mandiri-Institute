"""
Aggregate FINAL_eczi_per_desa.csv ke level Kawasan Utama (informal commercial zones).
Output: 260503_FINAL_eczi_per_kawasan.csv

Rule agregasi:
- Volume metrics (count, total, magnitude): SUM
- Growth metrics (CAGR, change): MEAN weighted by volume desa
- Score metrics (0-100): MEAN dari desa member, atau re-computed dari aggregated raw
- Quadrant: re-classify dari aggregated NTL growth + POI lifestyle
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path

DATA = Path(r"C:/Users/LENOVO/OneDrive - PT Bank Mandiri (Persero) Tbk/Desktop/Mandiri/Mandiri Institute/Dashboard/emerging-zone-jakarta/data")

# Load FINAL desa-level
final_desa = pd.read_csv(DATA / "260503_FINAL_eczi_per_desa.csv")
print(f"Loaded final per desa: {len(final_desa)} desa")

# Load mapping
with open(DATA / "kawasan_utama_mapping.json", encoding="utf-8") as f:
    mapping = json.load(f)
kawasan_dict = mapping["kawasan"]
print(f"Total kawasan utama: {len(kawasan_dict)}")

# Aggregate per kawasan
rows = []
for kawasan_name, info in kawasan_dict.items():
    members = info["desa_member"]
    sub = final_desa[final_desa["nama_desa"].isin(members)]
    members_found = sub["nama_desa"].tolist()
    members_missing = [m for m in members if m not in members_found]

    if len(sub) == 0:
        print(f"  WARNING: {kawasan_name} - no members found in data!")
        continue

    # Volume metrics — SUM
    podes_count_sum = sub["podes_count_2025"].sum()
    magnitude_sum   = sub["magnitude_2025"].sum()
    osm_ent_sum     = sub["count_hiburan_nightlife"].sum()
    osm_well_sum    = sub["count_gaya_hidup_wellness"].sum()
    osm_spec_sum    = sub["count_retail_khusus"].sum()
    osm_tour_sum    = sub["count_wisata_budaya"].sum()
    osm_auto_sum    = sub["count_layanan_penunjang"].sum()
    catchment_sum   = sub["catchment_density_1km"].sum()
    n_pixels_sum    = sub["n_pixels"].sum()

    # NTL: weighted by n_pixels (kalau pixel banyak, NTL lebih reliable)
    if n_pixels_sum > 0:
        weights = sub["n_pixels"].values
        ntl_cagr_w  = float(np.average(sub["ntl_cagr_2021_2025"].fillna(0).values, weights=weights))
        ntl_change_w = float(np.average(sub["ntl_change_2024_2025"].fillna(0).values, weights=weights))
        ntl_level_w = float(np.average(sub["ntl_level_2025"].fillna(0).values, weights=weights))
    else:
        ntl_cagr_w = ntl_change_w = ntl_level_w = 0.0

    # Podes growth: weighted by count_2025
    if podes_count_sum > 0:
        weights_p = sub["podes_count_2025"].fillna(0).values
        if weights_p.sum() > 0:
            podes_cagr_w = float(np.average(sub["podes_cagr_2021_2025"].fillna(0).values, weights=weights_p))
            podes_change_w = float(np.average(sub["podes_change_2024_2025"].fillna(0).values, weights=weights_p))
        else:
            podes_cagr_w = podes_change_w = 0.0
    else:
        podes_cagr_w = podes_change_w = 0.0

    # Magnitude growth: weighted by magnitude_2025
    if magnitude_sum > 0:
        weights_m = sub["magnitude_2025"].fillna(0).values
        if weights_m.sum() > 0:
            mag_cagr_w = float(np.average(sub["magnitude_cagr_2021_2025"].fillna(0).values, weights=weights_m))
        else:
            mag_cagr_w = 0.0
    else:
        mag_cagr_w = 0.0

    # Diversity: max dari member (kawasan reflect highest diversity desa-nya)
    diversity_max = sub["podes_diversity_shannon"].max()

    # Transport access: max (best access among members)
    transport_max = sub["transport_access_score_raw"].max()

    # Score 0-100: simple mean of member scores
    eczi_mean = sub["eczi_score"].mean()
    magnitude_mean = sub["magnitude_score"].mean()
    g1_mean = sub["g1"].mean()
    g2_mean = sub["g2"].mean()
    g3_mean = sub["g3"].mean()
    g4_mean = sub["g4"].mean()
    g5_mean = sub["g5"].mean()

    # Aggregate Pulse: weighted mean pulse_yoy across desa members (weighted by n_pixels)
    # Then apply standard threshold for badge
    valid_pulse = sub[sub["pulse_badge"].fillna("tidak tersedia") != "tidak tersedia"].copy()
    if len(valid_pulse) > 0 and valid_pulse["n_pixels"].sum() > 0:
        weights_pulse = valid_pulse["n_pixels"].values
        pulse_yoy_avg = float(np.average(valid_pulse["pulse_yoy_2026"].fillna(0).values, weights=weights_pulse))
        if pulse_yoy_avg >= 5:
            best = "Trend Lanjut Tumbuh"
        elif pulse_yoy_avg >= -5:
            best = "Stabil"
        else:
            best = "Mulai Melambat"
    else:
        pulse_yoy_avg = 0.0
        best = "tidak tersedia"

    rows.append({
        "kawasan": kawasan_name,
        "pulse_yoy_2026": round(pulse_yoy_avg, 2),
        "kabkota": info["kabkota"],
        "deskripsi": info["deskripsi"],
        "n_desa_member": len(sub),
        "desa_members": ", ".join(members_found),
        "desa_missing": ", ".join(members_missing) if members_missing else "",
        # Volume
        "podes_count_total": int(podes_count_sum),
        "magnitude_total": float(magnitude_sum),
        "count_hiburan_nightlife": int(osm_ent_sum),
        "count_gaya_hidup_wellness": int(osm_well_sum),
        "count_retail_khusus": int(osm_spec_sum),
        "count_wisata_budaya": int(osm_tour_sum),
        "count_layanan_penunjang": int(osm_auto_sum),
        "catchment_density_1km_total": int(catchment_sum),
        "n_pixels_total": int(n_pixels_sum),
        # Growth (weighted)
        "ntl_cagr_2021_2025": round(ntl_cagr_w, 4),
        "ntl_change_2024_2025": round(ntl_change_w, 4),
        "ntl_level_2025": round(ntl_level_w, 3),
        "podes_cagr_2021_2025": round(podes_cagr_w, 4),
        "podes_change_2024_2025": round(podes_change_w, 4),
        "magnitude_cagr_2021_2025": round(mag_cagr_w, 4),
        "podes_diversity_shannon": round(float(diversity_max), 4),
        "transport_access_score_raw": round(float(transport_max), 2),
        # Composite scores (mean of members)
        "g1_cahaya_malam": round(g1_mean, 2),
        "g2_tempat_usaha": round(g2_mean, 2),
        "g3_magnitude": round(g3_mean, 2),
        "g4_gaya_hidup": round(g4_mean, 2),
        "g5_aksesibilitas": round(g5_mean, 2),
        "eczi_score": round(eczi_mean, 2),
        "magnitude_score": round(magnitude_mean, 2),
        # Pulse
        "pulse_badge": best,
    })

kawasan_df = pd.DataFrame(rows)

# Re-classify quadrant berdasar aggregated NTL CAGR + POI lifestyle (g4)
med_x = kawasan_df["ntl_cagr_2021_2025"].median()
med_y = kawasan_df["g4_gaya_hidup"].median()

def classify(row):
    hi_x = row["ntl_cagr_2021_2025"] >= med_x
    hi_y = row["g4_gaya_hidup"] >= med_y
    if hi_x and hi_y:   return "Kawasan Komersial Sedang Naik Daun"
    if hi_x and not hi_y: return "Awal Pertumbuhan"
    if not hi_x and hi_y: return "Kawasan Komersial Mapan"
    return "Aktivitas Rendah"
kawasan_df["tipe_kawasan"] = kawasan_df.apply(classify, axis=1)

# Sort by ECZI
kawasan_df = kawasan_df.sort_values("eczi_score", ascending=False).reset_index(drop=True)
kawasan_df.insert(0, "rank_eczi", kawasan_df.index + 1)

# Magnitude rank
kawasan_df = kawasan_df.sort_values("magnitude_score", ascending=False).reset_index(drop=True)
kawasan_df.insert(0, "rank_magnitude", kawasan_df.index + 1)

# Re-sort by ECZI for save
kawasan_df = kawasan_df.sort_values("rank_eczi").reset_index(drop=True)

# Save
fout = DATA / "260503_FINAL_eczi_per_kawasan.csv"
kawasan_df.to_csv(fout, index=False)
print(f"\n[+] Saved: {fout}")

# Sanity check
print("\n=== SANITY CHECK KAWASAN UTAMA ===")
print(f"\nTotal kawasan: {len(kawasan_df)}")
print(f"Median NTL CAGR threshold: {med_x:.4f}")
print(f"Median POI lifestyle threshold: {med_y:.2f}")

print(f"\nTOP by ECZI (Skor Potensi):")
print(kawasan_df.nsmallest(10, "rank_eczi")[
    ["kawasan","kabkota","eczi_score","tipe_kawasan","pulse_badge","n_desa_member"]
].to_string(index=False))

print(f"\nTOP by Magnitude (Skor Aktivitas Komersial):")
print(kawasan_df.nsmallest(10, "rank_magnitude")[
    ["kawasan","kabkota","magnitude_score","podes_count_total","tipe_kawasan"]
].to_string(index=False))

print(f"\nDistribusi tipe kawasan:")
print(kawasan_df.tipe_kawasan.value_counts().to_string())

print(f"\nDesa member tidak ditemukan (perlu review mapping):")
missing = kawasan_df[kawasan_df.desa_missing != ""]
if len(missing) > 0:
    for _, r in missing.iterrows():
        print(f"  {r['kawasan']}: {r['desa_missing']}")
else:
    print("  (none)")
