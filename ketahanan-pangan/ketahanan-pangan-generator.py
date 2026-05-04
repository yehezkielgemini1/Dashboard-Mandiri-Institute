"""
ketahanan-pangan-generator.py
Dashboard Ketahanan Pangan FIES Kabupaten/Kota Indonesia 2019-2025
Mandiri Institute
Generated: 2026-05-02
Python: Anaconda (C:/Users/LENOVO/anaconda3/python.exe)

Output: ketahanan-pangan-dashboard.html (single portable HTML)
"""

import pandas as pd
import numpy as np
import geopandas as gpd
import json
import os

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE     = r"C:\Users\LENOVO\OneDrive - PT Bank Mandiri (Persero) Tbk\Desktop\Mandiri"
PARQUET  = os.path.join(BASE, r"Mandiri Institute\Deck\Ketahanan Pangan\Output\fies_kabkota_2019_2025.parquet")
MW_2025  = os.path.join(BASE, r"Data\Python\master_wilayah_2025.csv")
SHP_ADM2 = os.path.join(BASE, r"Software\IDN_shp\idn_admbnda_adm2_bps_20200401.shp")
OUT_DIR  = os.path.join(BASE, r"Mandiri Institute\Dashboard\ketahanan-pangan")
DATA_DIR = os.path.join(OUT_DIR, "data")
OUT_HTML = os.path.join(OUT_DIR, "ketahanan-pangan-dashboard.html")

os.makedirs(DATA_DIR, exist_ok=True)

print("Loading data...")

# ── Load FIES ─────────────────────────────────────────────────────────────────
df = pd.read_parquet(PARQUET)

# ── Name lookup ───────────────────────────────────────────────────────────────
mw = pd.read_csv(MW_2025)
mw_lookup = mw[["value_prov","value_kab","nama_prov_display","nama_kab_display"]].copy()
mw_lookup.columns = ["kode_prov","kode_kabkota","nama_prov","nama_kabkota"]

# Manual Papua names not in master_wilayah_2025 (pre/post pemekaran codes)
manual_names = [
    (91, 9106, "Papua",            "Kab Puncak Jaya"),
    (91, 9107, "Papua",            "Kab Boven Digoel"),
    (91, 9108, "Papua",            "Kab Mappi"),
    (91, 9109, "Papua",            "Kab Asmat"),
    (91, 9110, "Papua",            "Kab Yahukimo"),
    (91, 9171, "Papua",            "Kota Jayapura"),
    (92, 9201, "Papua Barat",      "Kab Manokwari"),
    (92, 9202, "Papua Barat",      "Kab Sorong Selatan"),
    (92, 9203, "Papua Barat",      "Kab Sorong"),
    (92, 9204, "Papua Barat",      "Kab Raja Ampat"),
    (92, 9205, "Papua Barat",      "Kab Teluk Bintuni"),
    (92, 9271, "Papua Barat",      "Kota Sorong"),
    (94, 9401, "Papua Selatan",    "Kab Merauke"),
    (94, 9402, "Papua Selatan",    "Kab Boven Digoel"),
    (94, 9404, "Papua Selatan",    "Kab Asmat"),
    (94, 9410, "Papua Pegunungan", "Kab Jayawijaya"),
    (94, 9411, "Papua Pegunungan", "Kab Pegunungan Bintang"),
    (94, 9412, "Papua Pegunungan", "Kab Tolikara"),
    (94, 9413, "Papua Pegunungan", "Kab Sarmi"),
    (94, 9414, "Papua Pegunungan", "Kab Keerom"),
    (94, 9415, "Papua Pegunungan", "Kab Waropen"),
    (94, 9416, "Papua Pegunungan", "Kab Supiori"),
    (94, 9417, "Papua Pegunungan", "Kab Memberamo Raya"),
    (94, 9418, "Papua Pegunungan", "Kab Yalimo"),
    (94, 9429, "Papua Pegunungan", "Kab Intan Jaya"),
    (94, 9430, "Papua Pegunungan", "Kab Deiyai"),
    (94, 9431, "Papua Tengah",     "Kab Nabire"),
    (94, 9432, "Papua Tengah",     "Kab Paniai"),
    (94, 9433, "Papua Tengah",     "Kab Puncak Jaya"),
    (94, 9434, "Papua Tengah",     "Kab Puncak"),
    (94, 9435, "Papua Tengah",     "Kab Dogiyai"),
    (94, 9436, "Papua Tengah",     "Kab Lanny Jaya"),
    (95, 9501, "Papua Barat Daya", "Kab Sorong"),
    (95, 9502, "Papua Barat Daya", "Kab Maybrat"),
    (95, 9503, "Papua Barat Daya", "Kab Tambrauw"),
    (95, 9504, "Papua Barat Daya", "Kab Sorong Barat"),
    (96, 9601, "Papua Tengah",     "Kab Nabire"),
    (96, 9602, "Papua Tengah",     "Kab Paniai"),
    (96, 9603, "Papua Tengah",     "Kab Puncak Jaya"),
    (96, 9604, "Papua Tengah",     "Kab Mimika"),
    (96, 9605, "Papua Tengah",     "Kab Puncak"),
    (96, 9606, "Papua Tengah",     "Kab Intan Jaya"),
    (96, 9607, "Papua Tengah",     "Kab Dogiyai"),
    (96, 9608, "Papua Tengah",     "Kab Deiyai"),
    (97, 9701, "Papua Pegunungan", "Kab Jayawijaya"),
    (97, 9702, "Papua Pegunungan", "Kab Pegunungan Bintang"),
    (97, 9703, "Papua Pegunungan", "Kab Tolikara"),
    (97, 9704, "Papua Pegunungan", "Kab Boven Digoel"),
    (97, 9705, "Papua Pegunungan", "Kab Mappi"),
    (97, 9706, "Papua Pegunungan", "Kab Asmat"),
    (97, 9707, "Papua Pegunungan", "Kab Yahukimo"),
    (97, 9708, "Papua Pegunungan", "Kab Lanny Jaya"),
]
manual_df = pd.DataFrame(manual_names, columns=["kode_prov","kode_kabkota","nama_prov","nama_kabkota"])
full_lookup = pd.concat([mw_lookup, manual_df], ignore_index=True)
# Deduplicate: keep first occurrence per (kode_prov, kode_kabkota) — master_wilayah_2025 takes priority
full_lookup = full_lookup.drop_duplicates(subset=["kode_prov","kode_kabkota"], keep="first")

# Merge names into FIES — use (kode_prov, kode_kabkota) exact match
df = df.merge(full_lookup, on=["kode_prov","kode_kabkota"], how="left")

# Round floats
float_cols = df.select_dtypes(float).columns
df[float_cols] = df[float_cols].round(4)

print(f"FIES rows: {len(df)}, coverage: {df['nama_kabkota'].notna().sum()}/{len(df)}")

# ── GeoJSON (shapefile simplified) ────────────────────────────────────────────
print("Building GeoJSON...")
shp = gpd.read_file(SHP_ADM2)
shp["kode_kabkota"] = shp["ADM2_PCODE"].str.replace("ID","").astype(int)
shp_slim = shp[["kode_kabkota","ADM2_EN","ADM1_EN","geometry"]].copy()
shp_slim["geometry"] = shp_slim["geometry"].simplify(0.02)
geojson_str = shp_slim.to_json()
geojson_data = json.loads(geojson_str)
print(f"GeoJSON features: {len(geojson_data['features'])}, size: {len(geojson_str)/1024:.0f} KB")

# ── Precompute aggregates ──────────────────────────────────────────────────────
print("Computing aggregates...")

# National trend
nat_cols = ["year","n_tahan","n_ringan","n_sedang","n_parah","n_total",
            "share_tahan","share_ringan","share_sedang","share_parah",
            "share_rawan_total","share_rawan_moderate_severe","share_rawan_severe"]

nat = df.groupby("year").agg(
    n_tahan=("n_tahan","sum"),
    n_ringan=("n_ringan","sum"),
    n_sedang=("n_sedang","sum"),
    n_parah=("n_parah","sum"),
    n_total=("n_total","sum"),
).reset_index()
nat["share_tahan"] = (nat["n_tahan"] / nat["n_total"] * 100).round(2)
nat["share_ringan"] = (nat["n_ringan"] / nat["n_total"] * 100).round(2)
nat["share_sedang"] = (nat["n_sedang"] / nat["n_total"] * 100).round(2)
nat["share_parah"] = (nat["n_parah"] / nat["n_total"] * 100).round(2)
nat["share_rawan_total"] = ((nat["n_sedang"]+nat["n_parah"]+nat["n_ringan"]) / nat["n_total"] * 100).round(2)
nat["share_rawan_moderate_severe"] = ((nat["n_sedang"]+nat["n_parah"]) / nat["n_total"] * 100).round(2)
nat["share_rawan_severe"] = (nat["n_parah"] / nat["n_total"] * 100).round(2)
for col in nat.select_dtypes(float).columns:
    nat[col] = nat[col].round(2)

# Kab/kota full (for all years)
kab_all = df[["kode_prov","kode_kabkota","year","nama_prov","nama_kabkota",
               "share_tahan","share_ringan","share_sedang","share_parah",
               "share_rawan_total","share_rawan_moderate_severe","share_rawan_severe",
               "n_tahan","n_ringan","n_sedang","n_parah","n_total"]].copy()

# Add ranking (for 2025)
df2025 = kab_all[kab_all["year"]==2025].copy()
df2025["rank_rawan_moderate_severe"] = df2025["share_rawan_moderate_severe"].rank(ascending=False).astype(int)
df2025["rank_rawan_total"] = df2025["share_rawan_total"].rank(ascending=False).astype(int)
df2025["rank_rawan_severe"] = df2025["share_rawan_severe"].rank(ascending=False).astype(int)

# Top-10 and bottom-10 (2025, rawan_moderate_severe)
top10 = df2025.nlargest(10, "share_rawan_moderate_severe")[
    ["kode_kabkota","nama_prov","nama_kabkota","share_rawan_moderate_severe","share_rawan_severe","share_rawan_total"]
].round(4)
bot10 = df2025.nsmallest(10, "share_rawan_moderate_severe")[
    ["kode_kabkota","nama_prov","nama_kabkota","share_rawan_moderate_severe","share_rawan_severe","share_rawan_total"]
].round(4)

# Province list for filter
prov_list = df[["kode_prov","nama_prov"]].drop_duplicates().sort_values("nama_prov")
prov_list = prov_list[prov_list["nama_prov"].notna()]

# Kab list for filter (with prov name)
kab_list = df[["kode_kabkota","kode_prov","nama_prov","nama_kabkota"]].drop_duplicates().sort_values(["nama_prov","nama_kabkota"])
kab_list = kab_list[kab_list["nama_kabkota"].notna()]

# Province aggregate for province page
prov_agg = df.groupby(["kode_prov","year","nama_prov"]).agg(
    n_tahan=("n_tahan","sum"), n_ringan=("n_ringan","sum"),
    n_sedang=("n_sedang","sum"), n_parah=("n_parah","sum"),
    n_total=("n_total","sum"),
).reset_index()
prov_agg["share_rawan_moderate_severe"] = ((prov_agg["n_sedang"]+prov_agg["n_parah"]) / prov_agg["n_total"] * 100).round(2)
prov_agg["share_rawan_total"] = ((prov_agg["n_sedang"]+prov_agg["n_parah"]+prov_agg["n_ringan"]) / prov_agg["n_total"] * 100).round(2)
prov_agg["share_rawan_severe"] = (prov_agg["n_parah"] / prov_agg["n_total"] * 100).round(2)
prov_agg["share_tahan"] = (prov_agg["n_tahan"] / prov_agg["n_total"] * 100).round(2)

# Change from 2024 to 2025
df2024 = kab_all[kab_all["year"]==2024][["kode_kabkota","share_rawan_moderate_severe","share_rawan_total","share_rawan_severe"]].copy()
df2024.columns = ["kode_kabkota","rms_2024","rt_2024","rs_2024"]
df2025_change = df2025.merge(df2024, on="kode_kabkota", how="left")
df2025_change["delta_rms"] = (df2025_change["share_rawan_moderate_severe"] - df2025_change["rms_2024"]).round(2)
df2025_change["delta_rt"] = (df2025_change["share_rawan_total"] - df2025_change["rt_2024"]).round(2)

# ── Save CSVs ──────────────────────────────────────────────────────────────────
print("Saving data CSVs...")
df.to_csv(os.path.join(DATA_DIR, "fies_kabkota_2019_2025.csv"), index=False)
nat.to_csv(os.path.join(DATA_DIR, "fies_nasional_2019_2025.csv"), index=False)
df2025_change.to_csv(os.path.join(DATA_DIR, "fies_2025_with_change.csv"), index=False)

# Metadata
meta = {
    "title": "FIES Ketahanan Pangan Kabupaten/Kota Indonesia 2019-2025",
    "source": "Susenas Maret 2019-2025, BPS",
    "model": "IRT 1PL (Rasch), imputasi per provinsi, bobot individu weind",
    "coverage": "514 kab/kota, 7 tahun",
    "generated": "2026-05-02",
    "generator": "ketahanan-pangan-generator.py"
}
with open(os.path.join(DATA_DIR, "metadata.json"), "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)

# ── Serialize data for HTML ────────────────────────────────────────────────────
print("Serializing data for HTML...")

def df_to_json(dataframe):
    return json.dumps(dataframe.to_dict(orient="records"), ensure_ascii=False, default=str)

nat_json       = df_to_json(nat)
kab_json       = df_to_json(kab_all)
kab2025_json   = df_to_json(df2025_change)
top10_json     = df_to_json(top10)
bot10_json     = df_to_json(bot10)
prov_list_json = df_to_json(prov_list)
kab_list_json  = df_to_json(kab_list)
prov_agg_json  = df_to_json(prov_agg)
geojson_js     = geojson_str  # already string

total_kb = (len(nat_json)+len(kab_json)+len(kab2025_json)+len(geojson_js)) / 1024
print(f"Approx data payload: {total_kb:.0f} KB")

# ── Build HTML ────────────────────────────────────────────────────────────────
print("Building HTML...")

html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ketahanan Pangan Indonesia 2019-2025 | Mandiri Institute</title>
<script src="../_assets/plotly.min.js"></script>
<script src="../_assets/tailwind.min.js"></script>
<script src="../_assets/iconify-icon.min.js"></script>
<script src="../_assets/icons.js"></script>
<link href="../_assets/fonts/fonts.css" rel="stylesheet">
<style>
  :root {{
    /* Color tokens — single source of truth */
    --navy: #003D79;
    --navy-deep: #002852;
    --navy-soft: #1A5394;
    --sky: #67B2E8;
    --sky-soft: #A9C4DF;
    --yellow: #FFB700;
    --yellow-soft: #FFE08A;
    --ink: #051C2C;
    --ink-soft: #2A3F52;
    --rule: #E5E8EC;
    --rule-strong: #D0D5DD;
    --muted: #667085;
    --muted-soft: #98A2B3;
    --paper: #FFFFFF;
    --cream: #F8F6F0;
    --mist: #F0F6FC;
    /* Extended palette for ketahanan pangan */
    --orange: #EA7200;
    --green: #00DC5C;
    --red: #C8102E;
    /* Semantic */
    --positive: #00875A;
    --negative: #C8102E;
    --warning: #EA7200;
    /* Spacing tokens (4-base) */
    --sp-1: 4px;
    --sp-2: 8px;
    --sp-3: 12px;
    --sp-4: 16px;
    --sp-5: 24px;
    --sp-6: 32px;
    --sp-8: 48px;
    --sp-10: 64px;
    --sp-12: 96px;
    /* Elevation tokens */
    --elev-1: 0 1px 2px rgba(5,28,44,0.04);
    --elev-2: 0 2px 8px rgba(5,28,44,0.06);
    --elev-3: 0 8px 24px rgba(5,28,44,0.10);
    --elev-4: 0 16px 48px rgba(5,28,44,0.14);
    /* Type scale (1.25 modular) */
    --fs-xs: 11px;
    --fs-sm: 13px;
    --fs-base: 14px;
    --fs-md: 16px;
    --fs-lg: 20px;
    --fs-xl: 25px;
    --fs-2xl: 31px;
    --fs-3xl: 39px;
    --fs-4xl: 49px;
    --fs-5xl: 61px;
    --fs-6xl: 76px;
    /* Transition */
    --tr-fast: 0.12s ease;
    --tr-base: 0.2s ease;
    --tr-slow: 0.4s ease;
  }}
  html, body {{ background: var(--paper); color: var(--ink); }}
  body {{ font-family: 'Inter', system-ui, sans-serif; font-weight: 400; letter-spacing: -0.003em; }}
  .serif-display {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.015em; line-height: 1.08; font-feature-settings: 'liga' 1, 'kern' 1; text-rendering: optimizeLegibility; }}
  .serif {{ font-family: 'Source Serif 4', Georgia, serif; }}
  .stat-num {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.02em; line-height: 1; font-feature-settings: 'tnum' 1, 'lnum' 1; }}
  .eyebrow {{ font-size: 11px; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; color: var(--navy); }}
  .eyebrow-roman {{ font-family: 'Source Serif 4', Georgia, serif; font-style: italic; font-size: var(--fs-md); font-weight: 500; letter-spacing: 0.02em; text-transform: none; color: var(--navy); }}
  .eyebrow-roman::before {{ content: ''; display: inline-block; width: 24px; height: 1px; background: var(--navy); vertical-align: middle; margin-right: 12px; }}
  .rule-top {{ border-top: 1px solid var(--rule); }}
  .rule-bottom {{ border-bottom: 1px solid var(--rule); }}
  .hair-accent {{ border-top: 2px solid var(--sky); }}
  .ink {{ color: var(--ink); }}
  .muted {{ color: var(--muted); }}
  .num {{ font-variant-numeric: tabular-nums; }}
  .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; font-size: var(--fs-xs); font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--navy); background: var(--mist); border: 1px solid var(--sky); }}
  .badge-dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--sky); display: inline-block; }}
  .badge-green {{ background: var(--mist); color: var(--positive); border-color: var(--green); }}
  .badge-red {{ background: #FEF0F0; color: var(--red); border-color: var(--red); }}
  .badge-yellow {{ background: #FFF9E6; color: #7A5600; border-color: var(--yellow); }}
  .callout, .story-box {{ border-left: 3px solid var(--sky); background: var(--mist); padding: var(--sp-4) var(--sp-5); border-radius: 0; }}
  .callout .label {{ font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--navy); }}
  .callout .text {{ font-family: 'Source Serif 4', Georgia, serif; font-size: var(--fs-md); line-height: 1.45; color: var(--ink); margin-top: 6px; font-weight: 500; }}
  .chart-footer {{ border-top: 1px solid var(--rule); margin-top: var(--sp-5); padding-top: var(--sp-4); display: flex; flex-wrap: wrap; gap: var(--sp-5); font-size: var(--fs-xs); color: var(--muted); }}
  .chart-footer .label {{ font-weight: 600; color: var(--ink); text-transform: uppercase; letter-spacing: 0.06em; margin-right: 4px; }}
  .hairline {{ border: none; border-top: 1px solid var(--rule); margin: 20px 0; }}

  /* Tab nav */
  .tab-btn {{
    padding: 10px 20px; border-bottom: 3px solid transparent;
    cursor: pointer; white-space: nowrap; font-weight: 500;
    font-size: var(--fs-base); font-family: 'Inter', sans-serif;
    color: var(--muted); transition: all var(--tr-base);
    background: none; border-top: none; border-left: none; border-right: none;
  }}
  .tab-btn:hover {{ color: var(--navy); border-bottom-color: var(--sky); }}
  .tab-btn.active {{ color: var(--navy); border-bottom-color: var(--navy); font-weight: 600; }}
  .tab-page {{ display: none; }}
  .tab-page.active {{ display: block; }}

  /* KPI cards — border order fixed: border first, then border-top override */
  .kpi-card {{
    background: white; padding: 20px 24px;
    border: 1px solid var(--rule);
    border-top: 3px solid var(--navy);
    box-shadow: var(--elev-2); transition: all var(--tr-base);
  }}
  .kpi-card:hover {{ box-shadow: var(--elev-3); transform: translateY(-2px); }}
  .kpi-eyebrow {{ font-size: var(--fs-xs); font-weight: 700; letter-spacing: 0.14em; color: var(--muted); text-transform: uppercase; }}
  .kpi-num {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 2.2rem; font-weight: 600; color: var(--navy); line-height: 1.1; font-variant-numeric: tabular-nums; }}
  .kpi-sub {{ font-size: var(--fs-xs); color: var(--muted); margin-top: 2px; }}

  /* Select / input */
  select {{
    border: 0; border-bottom: 1px solid var(--ink); background: transparent;
    padding: 6px 24px 6px 0; font-size: var(--fs-base); font-weight: 500;
    color: var(--ink); appearance: none; font-family: 'Inter', sans-serif;
    background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%23051C2C'%3e%3cpath fill-rule='evenodd' d='M5.23 7.21a.75.75 0 011.06.02L10 11.06l3.71-3.83a.75.75 0 111.08 1.04l-4.25 4.39a.75.75 0 01-1.08 0L5.21 8.27a.75.75 0 01.02-1.06z' clip-rule='evenodd'/%3e%3c/svg%3e");
    background-repeat: no-repeat; background-position: right 0 center; background-size: 18px; width: 100%;
  }}
  input[type=text] {{
    border: 1px solid var(--rule); padding: 7px 10px;
    font-size: var(--fs-base); background: white; color: var(--ink);
    font-family: 'Inter', sans-serif; width: 100%;
  }}
  select:focus, input[type=text]:focus {{ outline: none; border-bottom-color: var(--sky); }}
  .filter-label {{ font-size: var(--fs-xs); font-weight: 700; color: var(--muted); margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.1em; }}

  /* Table */
  .table-sm {{ font-size: var(--fs-sm); }}
  .table-sm th {{ background: var(--mist); font-weight: 700; color: var(--ink); padding: 8px 10px; text-align: left; border-bottom: 2px solid var(--sky); font-size: var(--fs-xs); letter-spacing: 0.06em; text-transform: uppercase; }}
  .table-sm td {{ padding: 7px 10px; border-bottom: 1px solid var(--rule); }}
  .table-sm tr:hover td {{ background: var(--mist); }}

  /* Content panels */
  .content-panel {{ background: white; padding: var(--sp-5); border: 1px solid var(--rule); box-shadow: var(--elev-1); }}
  .chart-card {{ background: white; border: 1px solid var(--rule); padding: var(--sp-4); box-shadow: var(--elev-1); }}
  .chart-card:hover {{ box-shadow: var(--elev-2); }}

  /* Slider */
  .slider-wrap input[type=range] {{ width: 100%; accent-color: var(--navy); }}
  #map-spinner {{ display: none; }}

  /* Kab tag */
  .kab-tag {{
    display: inline-flex; align-items: center; gap: 4px;
    background: var(--mist); border: 1px solid var(--sky);
    padding: 3px 8px; font-size: var(--fs-xs); margin: 2px; font-weight: 500;
  }}
  .kab-tag button {{ background: none; border: none; cursor: pointer; color: var(--muted); font-size: var(--fs-base); line-height: 1; padding: 0; }}
  .prov-drilldown-table {{ overflow-x: auto; }}

  /* Folio header — running small caps, sticky top:0 */
  .folio {{ position: sticky; top: 0; z-index: 30; background: rgba(255,255,255,0.92); backdrop-filter: blur(8px); border-bottom: 1px solid var(--rule); padding: 8px 0; }}
  .folio-inner {{ max-width: 1280px; margin: 0 auto; padding: 0 32px; display: flex; justify-content: space-between; font-size: 10px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); }}
  .folio .left {{ color: var(--ink); }}
  .folio .right {{ color: var(--muted); }}

  /* Hero band — navy gradient + yellow accent */
  .hero-band {{ background: linear-gradient(180deg, var(--navy) 0%, #002852 100%); color: white; position: relative; }}
  .hero-band::after {{ content: ''; position: absolute; bottom: -1px; left: 0; right: 0; height: 1px; background: var(--yellow); opacity: 0.4; }}
  .hero-band .eyebrow {{ color: var(--sky); }}
  .hero-band h1, .hero-band h2 {{ color: white; }}
  .hero-band p {{ color: rgba(255,255,255,0.78); }}

  /* Hero band craft — multi-layer gradient (matches kelas-kabkota canon) */
  .hero-band-craft {{
    background:
      linear-gradient(180deg,
        #003D79 0%,
        #003D79 30%,
        #00498A 50%,
        #00407C 70%,
        #002852 100%);
    position: relative;
  }}
  .hero-band-craft::before {{ content: ''; position: absolute; inset: 0; background-image:
    radial-gradient(ellipse at 20% 30%, rgba(255,255,255,0.04), transparent 50%),
    radial-gradient(ellipse at 80% 70%, rgba(103,178,232,0.06), transparent 50%);
    pointer-events: none;
  }}
  .hero-band-craft::after {{ content: ''; position: absolute; bottom: -1px; left: 0; right: 0; height: 1px; background: var(--yellow); opacity: 0.4; }}

  /* Tab bar — sticky, offset below folio (folio ~33px padding+content = ~49px) */
  .tab-bar-wrap {{ background: white; border-bottom: 1px solid var(--rule); position: sticky; top: 33px; z-index: 25; }}

  /* Global filter bar — sticky below tab bar (~33+48=81px) */
  .global-filter-bar {{ background: white; border-bottom: 1px solid var(--rule); position: sticky; top: 81px; z-index: 20; padding: 12px 0; }}

  /* Heritage tag (yellow pill) */
  .heritage-tag {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; font-size: 10px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--yellow); background: rgba(255,183,0,0.08); border: 1px solid rgba(255,183,0,0.3); border-radius: 0; }}

  /* Smooth transitions */
  button, .tab-btn, .kpi-card, a, select, input {{ transition: all var(--tr-base); }}
  *:focus-visible {{ outline: 2px solid var(--sky); outline-offset: 3px; border-radius: 1px; }}

  /* Footer */
  .dash-footer {{ border-top: 1px solid var(--rule); color: var(--muted); margin-top: var(--sp-10); padding-top: var(--sp-5); padding-bottom: var(--sp-5); display: flex; align-items: center; justify-content: space-between; font-size: var(--fs-xs); font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; }}
</style>
</head>
<body class="min-h-screen" style="background:var(--paper)">

<!-- Folio running header -->
<div class="folio">
  <div class="folio-inner">
    <span class="left">Mandiri Institute &middot; Ketahanan Pangan</span>
    <span class="right">Susenas BPS &middot; 514 Kab/Kota &middot; 2019-2025</span>
  </div>
</div>

<!-- Hero band -->
<div class="hero-band hero-band-craft">
  <div class="max-w-screen-xl mx-auto px-6 pt-14 pb-14" style="position:relative;z-index:1;">
    <a href="../../index.html" style="display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--sky);text-transform:uppercase;letter-spacing:0.1em;font-weight:700;text-decoration:none;margin-bottom:14px;">
      <iconify-icon icon="mdi:arrow-left"></iconify-icon><span>Beranda</span>
    </a>
    <div class="eyebrow" style="margin-bottom:8px;">Riset Mandiri Institute &middot; Ketahanan Pangan</div>
    <h1 class="serif-display" style="font-size:clamp(28px,4vw,44px);color:white;margin:0 0 10px 0;max-width:800px;">
      Ketahanan Pangan Indonesia 2019-2025
    </h1>
    <p style="font-size:14px;max-width:640px;line-height:1.6;color:rgba(255,255,255,0.78);margin:0 0 10px 0;">
      Distribusi status ketahanan pangan (FIES) per kabupaten/kota, 514 wilayah, Susenas Maret BPS.
      Tren spasial dan temporal rawan pangan.
    </p>
    <span class="heritage-tag">Susenas Maret BPS &bull; Model FIES-IRT</span>
  </div>
</div>

<!-- Tab bar -->
<div class="tab-bar-wrap">
  <div class="max-w-screen-xl mx-auto px-6">
    <div class="flex gap-0 overflow-x-auto" id="tab-bar">
      <button class="tab-btn active" onclick="switchTab('overview')">Gambaran Umum</button>
      <button class="tab-btn" onclick="switchTab('map')">Peta Sebaran</button>
      <button class="tab-btn" onclick="switchTab('trend')">Tren Kab/Kota</button>
      <button class="tab-btn" onclick="switchTab('province')">Analisis Provinsi</button>
      <button class="tab-btn" onclick="switchTab('methodology')">Metodologi</button>
    </div>
  </div>
</div>

<!-- Global filter bar -->
<div class="global-filter-bar" id="global-filters">
  <div class="max-w-screen-xl mx-auto px-6">
    <div class="flex flex-wrap gap-6 items-end">
      <div>
        <div class="filter-label">Tahun</div>
        <select id="g-year" onchange="applyGlobalFilters()">
          <option value="2025" selected>2025</option>
          <option value="2024">2024</option>
          <option value="2023">2023</option>
          <option value="2022">2022</option>
          <option value="2021">2021</option>
          <option value="2020">2020</option>
          <option value="2019">2019</option>
        </select>
      </div>
      <div>
        <div class="filter-label">Provinsi</div>
        <select id="g-prov" onchange="onProvChange()">
          <option value="">Semua Provinsi</option>
        </select>
      </div>
      <div>
        <div class="filter-label">Kab/Kota</div>
        <select id="g-kab">
          <option value="">Semua Kab/Kota</option>
        </select>
      </div>
      <div>
        <div class="filter-label">Definisi Rawan</div>
        <select id="g-metric" onchange="applyGlobalFilters()">
          <option value="share_rawan_moderate_severe" selected>Rawan Pangan Sedang-Parah (FAO)</option>
          <option value="share_rawan_total">Rawan Pangan Total</option>
          <option value="share_rawan_severe">Rawan Pangan Parah</option>
        </select>
      </div>
      <div>
        <div class="filter-label">Tampilan Unit</div>
        <select id="g-unit" onchange="applyGlobalFilters()">
          <option value="pct" selected>% Penduduk</option>
          <option value="jiwa">Jumlah Jiwa</option>
        </select>
      </div>
    </div>
  </div>
</div>

<!-- ── Main content ────────────────────────────────────────────────────────── -->
<main class="max-w-screen-xl mx-auto px-6 py-8">

  <!-- ──────────────────── PAGE 1: GAMBARAN UMUM ──────────────────────────── -->
  <div class="tab-page active" id="page-overview">
    <!-- KPI Cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-5 mb-8" id="kpi-cards">
      <div class="kpi-card" style="border-top-color:var(--navy)">
        <div class="kpi-eyebrow">Tahan Pangan</div>
        <div class="kpi-num" id="kpi-tahan">-</div>
        <div class="kpi-sub">% penduduk, 2025</div>
      </div>
      <div class="kpi-card" style="border-top-color:var(--yellow)">
        <div class="kpi-eyebrow">Rawan Pangan (Total)</div>
        <div class="kpi-num" id="kpi-rawan-total" style="color:var(--orange)">-</div>
        <div class="kpi-sub">% penduduk, 2025</div>
      </div>
      <div class="kpi-card" style="border-top-color:var(--red)">
        <div class="kpi-eyebrow">Rawan Sedang-Parah (FAO)</div>
        <div class="kpi-num" id="kpi-rawan-fao" style="color:var(--red)">-</div>
        <div class="kpi-sub">% penduduk, 2025</div>
      </div>
      <div class="kpi-card" style="border-top-color:var(--sky)">
        <div class="kpi-eyebrow">Penduduk Rawan Total</div>
        <div class="kpi-num" id="kpi-jiwa-rawan" style="color:var(--navy)">-</div>
        <div class="kpi-sub">juta jiwa, 2025</div>
      </div>
    </div>

    <!-- Story box -->
    <div class="story-box mb-8">
      <div class="font-semibold text-sm mb-1" style="color:var(--navy)">Catatan Analitis</div>
      <p class="text-sm leading-relaxed">
        Setelah lima tahun perbaikan berturut-turut (2019-2024), Indonesia mencatat peningkatan penduduk rawan pangan pada 2025,
        terutama pada kategori rawan ringan (+1,9 juta jiwa). Rawan pangan parah relatif stabil sepanjang 2019-2025 (~3 juta jiwa).
        Peningkatan rawan ringan 2025 perlu dicermati sebagai sinyal dini ketahanan pangan rumah tangga, meski
        angka rawan sedang-parah (standar FAO) masih di bawah puncak 2019.
      </p>
    </div>

    <!-- National trend line -->
    <div class="chart-card mb-8">
      <div class="kpi-eyebrow mb-1">Tren Nasional 2019-2025</div>
      <div class="serif text-base font-semibold mb-3" style="color:var(--navy)">Komposisi Status Ketahanan Pangan Penduduk (%)</div>
      <div id="chart-nat-trend" style="height:360px"></div>
    </div>

    <!-- Top/Bottom 10 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      <div class="chart-card">
        <div class="kpi-eyebrow mb-1">Top 10 Tertinggi — 2025</div>
        <div class="serif text-sm font-semibold mb-3" style="color:var(--red)">Rawan Pangan Sedang-Parah Terbesar</div>
        <div id="chart-top10" style="height:320px"></div>
      </div>
      <div class="chart-card">
        <div class="kpi-eyebrow mb-1">Top 10 Terendah — 2025</div>
        <div class="serif text-sm font-semibold mb-3" style="color:var(--green)" style="color:var(--green)">Rawan Pangan Sedang-Parah Terendah</div>
        <div id="chart-bot10" style="height:320px"></div>
      </div>
    </div>
  </div>

  <!-- ──────────────────── PAGE 2: PETA SEBARAN ───────────────────────────── -->
  <div class="tab-page" id="page-map">
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- Sidebar -->
      <div class="content-panel lg:col-span-1">
        <div class="eyebrow mb-4">Filter Peta</div>
        <div class="mb-4">
          <div class="filter-label">Tahun</div>
          <div class="slider-wrap">
            <input type="range" id="map-year-slider" min="2019" max="2025" value="2025" step="1" oninput="onMapYearSlide(this.value)">
            <div class="text-center font-bold text-lg mt-1" style="color:var(--navy)" id="map-year-label">2025</div>
          </div>
        </div>
        <div class="mb-4">
          <div class="filter-label">Metrik</div>
          <select id="map-metric" onchange="renderMap()">
            <option value="share_rawan_moderate_severe" selected>Rawan Sedang-Parah (FAO)</option>
            <option value="share_rawan_total">Rawan Pangan Total</option>
            <option value="share_rawan_severe">Rawan Pangan Parah</option>
            <option value="share_tahan">Tahan Pangan</option>
          </select>
        </div>
        <div class="mb-4">
          <div class="filter-label">Unit</div>
          <select id="map-unit" onchange="renderMap()">
            <option value="pct" selected>% Penduduk</option>
            <option value="jiwa">Jumlah Jiwa</option>
          </select>
        </div>
        <hr class="hairline">
        <div class="text-xs leading-relaxed" style="color:var(--muted)">
          Peta menampilkan 514 kab/kota berdasarkan shapefile BPS 2020. Kab/kota baru hasil pemekaran 2022 (Papua) ditampilkan menggunakan batas administratif sebelum pemekaran.
        </div>
      </div>
      <!-- Map -->
      <div class="chart-card lg:col-span-3">
        <div class="kpi-eyebrow mb-1">Peta Choropleth</div>
        <div class="serif text-base font-semibold mb-2" style="color:var(--navy)" id="map-title">Rawan Pangan Sedang-Parah (FAO), 2025</div>
        <div id="chart-map" style="height:520px"></div>
      </div>
    </div>
  </div>

  <!-- ──────────────────── PAGE 3: TREN KAB/KOTA ─────────────────────────── -->
  <div class="tab-page" id="page-trend">
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- Sidebar -->
      <div class="content-panel lg:col-span-1">
        <div class="eyebrow mb-3">Pilih Kab/Kota (maks 10)</div>
        <div class="mb-2">
          <input type="text" id="kab-search" placeholder="Cari kab/kota..." oninput="filterKabDropdown()" autocomplete="off">
        </div>
        <div class="mb-3" style="max-height:220px;overflow-y:auto;border:1px solid var(--rule);">
          <div id="kab-dropdown-list" class="text-sm"></div>
        </div>
        <div class="font-label text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">Dipilih:</div>
        <div id="kab-selected-tags" class="mb-3"></div>
        <hr class="hairline">
        <div class="mb-3">
          <div class="filter-label">Metrik Tren</div>
          <select id="trend-metric" onchange="renderTrend()">
            <option value="share_rawan_moderate_severe" selected>Rawan Sedang-Parah (FAO)</option>
            <option value="share_rawan_total">Rawan Pangan Total</option>
            <option value="share_rawan_severe">Rawan Pangan Parah</option>
            <option value="share_tahan">Tahan Pangan</option>
          </select>
        </div>
        <div class="mb-3">
          <div class="filter-label">Unit</div>
          <select id="trend-unit" onchange="renderTrend()">
            <option value="pct" selected>% Penduduk</option>
            <option value="jiwa">Jumlah Jiwa</option>
          </select>
        </div>
        <div class="mt-3">
          <div class="filter-label">Stacked Area: Pilih 1 Kab/Kota</div>
          <select id="trend-stacked-kab" onchange="renderStackedArea()">
            <option value="">-- Pilih --</option>
          </select>
        </div>
      </div>
      <!-- Charts -->
      <div class="lg:col-span-3 flex flex-col gap-6">
        <div class="chart-card">
          <div class="kpi-eyebrow mb-1">Tren Komparasi</div>
          <div class="serif text-base font-semibold mb-2" style="color:var(--navy)">Tren 2019-2025 per Kab/Kota Terpilih</div>
          <div id="chart-trend-line" style="height:340px">
            <div class="flex items-center justify-center h-full text-slate-400 text-sm">Pilih kab/kota dari sidebar untuk menampilkan tren</div>
          </div>
        </div>
        <div class="chart-card">
          <div class="kpi-eyebrow mb-1">Komposisi Detail</div>
          <div class="serif text-base font-semibold mb-2" style="color:var(--navy)" id="stacked-title">Stacked Area — 4 Kategori per Kab/Kota</div>
          <div id="chart-stacked" style="height:300px">
            <div class="flex items-center justify-center h-full text-slate-400 text-sm">Pilih 1 kab/kota di sidebar (Stacked Area)</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ──────────────────── PAGE 4: ANALISIS PROVINSI ──────────────────────── -->
  <div class="tab-page" id="page-province">
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- Sidebar -->
      <div class="content-panel lg:col-span-1">
        <div class="eyebrow mb-3">Pilih Provinsi</div>
        <select id="prov-select" onchange="renderProvince()">
          <option value="">-- Pilih Provinsi --</option>
        </select>
        <hr class="hairline">
        <div class="mb-3">
          <div class="filter-label">Metrik</div>
          <select id="prov-metric" onchange="renderProvince()">
            <option value="share_rawan_moderate_severe" selected>Rawan Sedang-Parah (FAO)</option>
            <option value="share_rawan_total">Rawan Pangan Total</option>
            <option value="share_rawan_severe">Rawan Pangan Parah</option>
            <option value="share_tahan">Tahan Pangan</option>
          </select>
        </div>
        <div class="text-xs leading-relaxed mt-4" style="color:var(--muted)">
          Menampilkan semua kab/kota dalam provinsi terpilih untuk tahun 2025, diranking berdasarkan metrik terpilih. Tabel juga menampilkan perubahan dari 2024 ke 2025.
        </div>
      </div>
      <!-- Content -->
      <div class="lg:col-span-3 flex flex-col gap-6">
        <div class="chart-card">
          <div class="kpi-eyebrow mb-1">Ranking Kab/Kota dalam Provinsi</div>
          <div class="serif text-base font-semibold mb-2" style="color:var(--navy)" id="prov-chart-title">Pilih provinsi untuk menampilkan data</div>
          <div id="chart-prov-bar" style="height:380px">
            <div class="flex items-center justify-center h-full text-slate-400 text-sm">Pilih provinsi dari sidebar</div>
          </div>
        </div>
        <div class="chart-card">
          <div class="kpi-eyebrow mb-1">Tabel Indikator Lengkap</div>
          <div class="serif text-sm font-semibold mb-3" style="color:var(--navy)">Semua Kab/Kota — 2025 vs 2024</div>
          <div class="prov-drilldown-table">
            <table class="table-sm w-full" id="prov-table">
              <thead>
                <tr>
                  <th>Kab/Kota</th>
                  <th class="text-right">Tahan Pangan</th>
                  <th class="text-right">Rawan Ringan</th>
                  <th class="text-right">Rawan Sedang</th>
                  <th class="text-right">Rawan Parah</th>
                  <th class="text-right">Sedang-Parah (FAO)</th>
                  <th class="text-right">Delta 2024→25</th>
                </tr>
              </thead>
              <tbody id="prov-table-body">
                <tr><td colspan="7" class="text-center text-slate-400 py-8">Pilih provinsi untuk menampilkan data</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ──────────────────── PAGE 5: METODOLOGI ─────────────────────────────── -->
  <div class="tab-page" id="page-methodology">
    <div class="max-w-3xl mx-auto">
      <div class="chart-card" style="padding:var(--sp-8)">
        <div class="kpi-eyebrow mb-2">Metodologi</div>
        <h2 class="serif text-2xl font-bold mb-6" style="color:var(--navy)">
          Food Insecurity Experience Scale (FIES)
        </h2>

        <h3 class="serif text-lg font-semibold mt-6 mb-2" style="color:var(--navy)">Apa itu FIES?</h3>
        <p class="text-sm leading-relaxed mb-4">
          FIES adalah instrumen pengukuran ketahanan pangan berbasis pengalaman (experience-based) yang dikembangkan oleh FAO.
          FIES terdiri dari 8 pertanyaan yang mengukur pengalaman ketidakcukupan pangan di tingkat rumah tangga dalam 12 bulan terakhir,
          mulai dari kekhawatiran tentang pangan, kualitas makanan, hingga kelaparan dan melewatkan makan.
        </p>

        <div class="mb-6" style="background:var(--mist);padding:var(--sp-4);">
          <div class="font-semibold text-sm mb-2">8 Pertanyaan FIES (singkat)</div>
          <ol class="text-xs leading-relaxed text-slate-600 list-decimal pl-4 space-y-1">
            <li>Khawatir kehabisan makanan</li>
            <li>Tidak bisa makan makanan bergizi</li>
            <li>Hanya makan sedikit jenis makanan</li>
            <li>Melewatkan makan</li>
            <li>Makan lebih sedikit dari yang seharusnya</li>
            <li>Kehabisan makanan di rumah</li>
            <li>Merasa lapar tapi tidak makan</li>
            <li>Tidak makan seharian penuh</li>
          </ol>
        </div>

        <h3 class="serif text-lg font-semibold mt-6 mb-2" style="color:var(--navy)">Klasifikasi 4 Kategori</h3>
        <table class="table-sm w-full mb-6">
          <thead>
            <tr>
              <th>Kategori</th>
              <th>Raw Score (item "Ya")</th>
              <th>Interpretasi</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><span class="font-semibold text-green-700">Tahan Pangan</span></td>
              <td>0-2 item</td>
              <td>Tidak mengalami ketidakcukupan pangan yang signifikan</td>
            </tr>
            <tr>
              <td><span class="font-semibold text-yellow-700">Rawan Pangan Ringan</span></td>
              <td>3-4 item</td>
              <td>Khawatir kekurangan pangan, kualitas & variasi menurun</td>
            </tr>
            <tr>
              <td><span class="font-semibold text-orange-700">Rawan Pangan Sedang</span></td>
              <td>5-6 item</td>
              <td>Mengurangi kuantitas makan; orang dewasa terpengaruh</td>
            </tr>
            <tr>
              <td><span class="font-semibold text-red-700">Rawan Pangan Parah</span></td>
              <td>7-8 item</td>
              <td>Kehabisan makanan, lapar, tidak makan seharian penuh</td>
            </tr>
          </tbody>
        </table>

        <h3 class="serif text-lg font-semibold mt-6 mb-2" style="color:var(--navy)">Definisi Rawan Pangan</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
          <div class="text-sm" style="background:var(--mist);border:1px solid var(--sky);padding:var(--sp-3);">
            <div class="font-semibold mb-1">Rawan Pangan Total</div>
            <p class="text-xs text-slate-600">Gabungan Ringan + Sedang + Parah. Mencerminkan cakupan seluas mungkin. Dipakai untuk estimasi beban ketahanan pangan secara umum.</p>
          </div>
          <div class="text-sm" style="background:#FEF0F0;border:1px solid var(--red);padding:var(--sp-3);">
            <div class="font-semibold mb-1 text-red-800">Rawan Sedang-Parah (FAO)</div>
            <p class="text-xs text-slate-600">Standar internasional FAO (SDG 2.1.2). Hanya mencakup pengurangan kuantitas makan hingga kelaparan. Indikator utama dashboard ini.</p>
          </div>
          <div class="text-sm" style="background:#FFF3E0;border:1px solid var(--orange);padding:var(--sp-3);">
            <div class="font-semibold mb-1 text-orange-800">Rawan Pangan Parah</div>
            <p class="text-xs text-slate-600">Hanya kategori terparah: kehabisan makanan, lapar, tidak makan seharian. Indikator kedaruratan pangan.</p>
          </div>
        </div>

        <h3 class="serif text-lg font-semibold mt-6 mb-2" style="color:var(--navy)">Populasi yang Dimaksud</h3>
        <p class="text-sm leading-relaxed mb-4">
          Angka jumlah jiwa (n_xxx) mencerminkan estimasi <strong>jumlah individu</strong> yang tinggal dalam rumah tangga dengan status FIES tersebut
          (bukan jumlah rumah tangga). Perhitungan menggunakan bobot individu Susenas (<code>weind</code>).
        </p>

        <h3 class="serif text-lg font-semibold mt-6 mb-2" style="color:var(--navy)">Model dan Pipeline</h3>
        <ul class="text-sm leading-relaxed list-disc pl-5 space-y-1 mb-4">
          <li>Model: <strong>IRT 1PL (Rasch)</strong> — mengkalibrasi kesulitan setiap item FIES agar dapat dibandingkan antar tahun</li>
          <li>Imputasi: missing values diimputasi per provinsi sebelum estimasi Rasch</li>
          <li>Raw score FIES setelah IRT dikonversi ke 4 kategori (cutoff berbasis probabilitas Rasch)</li>
          <li>Agregasi kab/kota menggunakan bobot individu Susenas (<code>weind</code>)</li>
        </ul>

        <h3 class="serif text-lg font-semibold mt-6 mb-2" style="color:var(--navy)">Sumber Data</h3>
        <ul class="text-sm leading-relaxed list-disc pl-5 space-y-1 mb-4">
          <li>Survei Sosial Ekonomi Nasional (Susenas) Maret 2019-2025, Badan Pusat Statistik</li>
          <li>Modul Konsumsi dan Pengeluaran (KP) — blok pertanyaan FIES 8 item</li>
          <li>Data mencerminkan kondisi 12 bulan sebelum bulan Maret tahun survei</li>
        </ul>

        <h3 class="serif text-lg font-semibold mt-6 mb-2" style="color:var(--navy)">Catatan Interpretasi</h3>
        <ul class="text-sm leading-relaxed list-disc pl-5 space-y-1 mb-6">
          <li>Kode wilayah mengikuti BPS 2025 (514 kab/kota). Kab/kota hasil pemekaran Papua 2022 dimunculkan dengan kode baru.</li>
          <li>Perbandingan antar tahun valid karena model IRT menjaga konsistensi skala.</li>
          <li>Angka 2025 perlu dicermati: terjadi uptick rawan ringan yang mendorong kenaikan rawan total.</li>
          <li>Peta menggunakan shapefile BPS 2020 — batas administratif Papua baru belum tersedia di shapefile.</li>
        </ul>

        <hr class="hairline">
        <div class="text-xs mt-4" style="color:var(--muted)">
          Dashboard dibuat oleh Mandiri Institute menggunakan Python (pandas, geopandas, Plotly.js) dari data Susenas BPS.
          Diperbarui: Mei 2026.
        </div>
      </div>
    </div>
  </div>

  <footer class="dash-footer">
    <div>Mandiri Institute &middot; Ketahanan Pangan</div>
    <div>Plotly.js &middot; Tailwind CSS &middot; Susenas BPS</div>
    <div>Palette: Mandiri Official</div>
  </footer>
</main>

<!-- ── Data ──────────────────────────────────────────────────────────────── -->
<script>
const DATA_NAT     = {nat_json};
const DATA_KAB     = {kab_json};
const DATA_KAB2025 = {kab2025_json};
const DATA_TOP10   = {top10_json};
const DATA_BOT10   = {bot10_json};
const DATA_PROV    = {prov_list_json};
const DATA_KAB_LIST= {kab_list_json};
const DATA_PROV_AGG= {prov_agg_json};
const GEOJSON      = {geojson_js};
</script>

<!-- ── App JS ─────────────────────────────────────────────────────────────── -->
<script>
// ── Palette
const C = {{
  blue   : '#003D79',
  yellow : '#FFB700',
  sky    : '#67B2E8',
  orange : '#EA7200',
  grey   : '#B6B8BA',
  green  : '#00DC5C',
  red    : '#C8102E',
}};

// ── Metric label map
const METRIC_LABELS = {{
  share_tahan                   : 'Tahan Pangan',
  share_ringan                  : 'Rawan Pangan Ringan',
  share_sedang                  : 'Rawan Pangan Sedang',
  share_parah                   : 'Rawan Pangan Parah',
  share_rawan_total             : 'Rawan Pangan (Total)',
  share_rawan_moderate_severe   : 'Rawan Pangan Sedang-Parah',
  share_rawan_severe            : 'Rawan Pangan Parah',
}};
const N_LABELS = {{
  n_tahan  : 'Penduduk Tahan Pangan',
  n_ringan : 'Penduduk Rawan Ringan',
  n_sedang : 'Penduduk Rawan Sedang',
  n_parah  : 'Penduduk Rawan Parah',
  n_total  : 'Total Penduduk',
}};

// ── Helpers
function fmtPct(v) {{ return v == null ? '-' : (v*100).toFixed(2)+'%'; }}
function fmtPctRaw(v) {{ return v == null ? '-' : v.toFixed(2)+'%'; }}  // already in %
function fmtJiwa(v) {{
  if (v == null) return '-';
  if (v >= 1e6)  return (v/1e6).toFixed(1)+' juta jiwa';
  if (v >= 1e3)  return (v/1e3).toFixed(0)+' ribu jiwa';
  return Math.round(v)+' jiwa';
}}
function fmtDelta(v) {{
  if (v == null) return '-';
  const pct = v * 100;  // delta_rms is in 0-1 format, convert to pp
  const sign = pct > 0 ? '+' : '';
  return sign + pct.toFixed(2) + ' pp';
}}
function deltaClass(v) {{
  if (v == null) return '';
  const pct = v * 100;
  if (pct > 0.5) return 'badge badge-red';
  if (pct < -0.5) return 'badge badge-green';
  return 'badge badge-yellow';
}}

// ── Tab switching
function switchTab(tab) {{
  document.querySelectorAll('.tab-page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + tab).classList.add('active');
  const btns = document.querySelectorAll('.tab-btn');
  const labels = ['overview','map','trend','province','methodology'];
  btns[labels.indexOf(tab)].classList.add('active');

  if (tab === 'map' && !mapRendered) {{ renderMap(); mapRendered = true; }}
  if (tab === 'overview') {{ renderOverview(); }}
  if (tab === 'trend') {{ renderTrend(); }}
  if (tab === 'province') {{ populateProvSelect(); }}
}}

// ── Populate global filters
function populateGlobalFilters() {{
  const provSel = document.getElementById('g-prov');
  DATA_PROV.forEach(p => {{
    const o = document.createElement('option');
    o.value = p.kode_prov;
    o.textContent = p.nama_prov;
    provSel.appendChild(o);
  }});

  const kabSel = document.getElementById('g-kab');
  DATA_KAB_LIST.forEach(k => {{
    const o = document.createElement('option');
    o.value = k.kode_kabkota;
    o.textContent = k.nama_kabkota + ' (' + k.nama_prov + ')';
    kabSel.appendChild(o);
  }});
}}

function onProvChange() {{
  const prov = document.getElementById('g-prov').value;
  const kabSel = document.getElementById('g-kab');
  kabSel.innerHTML = '<option value="">Semua Kab/Kota</option>';
  const filtered = prov ? DATA_KAB_LIST.filter(k => k.kode_prov == prov) : DATA_KAB_LIST;
  filtered.forEach(k => {{
    const o = document.createElement('option');
    o.value = k.kode_kabkota;
    o.textContent = k.nama_kabkota + ' (' + k.nama_prov + ')';
    kabSel.appendChild(o);
  }});
  applyGlobalFilters();
}}

function applyGlobalFilters() {{
  renderOverview();
}}

// ── KPI computation
function getKPI(year) {{
  const row = DATA_NAT.find(r => r.year == year);
  if (!row) return null;
  return row;
}}

function updateKPICards(year) {{
  const r = getKPI(year);
  if (!r) return;
  document.getElementById('kpi-tahan').textContent = r.share_tahan.toFixed(1) + '%';
  document.getElementById('kpi-rawan-total').textContent = r.share_rawan_total.toFixed(1) + '%';
  document.getElementById('kpi-rawan-fao').textContent = r.share_rawan_moderate_severe.toFixed(1) + '%';
  const jiwaRawan = r.n_ringan + r.n_sedang + r.n_parah;
  document.getElementById('kpi-jiwa-rawan').textContent = fmtJiwa(jiwaRawan);
}}

// ── Overview page
function renderOverview() {{
  const year = parseInt(document.getElementById('g-year').value);
  updateKPICards(year);
  renderNatTrend();
  renderTop10();
  renderBot10();
}}

function renderNatTrend() {{
  const years = DATA_NAT.map(r => r.year);
  const traces = [
    {{ name: 'Tahan Pangan',          y: DATA_NAT.map(r=>r.share_tahan),                    line:{{color:C.blue,  width:2.5}}, mode:'lines+markers' }},
    {{ name: 'Rawan Pangan Ringan',   y: DATA_NAT.map(r=>r.share_ringan),                   line:{{color:C.yellow,width:2}},   mode:'lines+markers' }},
    {{ name: 'Rawan Pangan Sedang',   y: DATA_NAT.map(r=>r.share_sedang),                   line:{{color:C.orange,width:2}},   mode:'lines+markers' }},
    {{ name: 'Rawan Pangan Parah',    y: DATA_NAT.map(r=>r.share_parah),                    line:{{color:C.red,   width:2}},   mode:'lines+markers' }},
    {{ name: 'Rawan Sedang-Parah',    y: DATA_NAT.map(r=>r.share_rawan_moderate_severe),    line:{{color:'#8B0000',width:2,dash:'dot'}}, mode:'lines+markers', visible:'legendonly' }},
  ];
  traces.forEach(t => {{ t.x = years; t.type = 'scatter'; t.hovertemplate = '%{{y:.2f}}%<extra>%{{fullData.name}}</extra>'; }});

  Plotly.newPlot('chart-nat-trend', traces, {{
    margin:{{t:10,b:40,l:50,r:10}},
    paper_bgcolor:'transparent', plot_bgcolor:'transparent',
    yaxis:{{title:'% Penduduk', gridcolor:'#F1F5F9', ticksuffix:'%'}},
    xaxis:{{tickvals:[2019,2020,2021,2022,2023,2024,2025]}},
    legend:{{orientation:'h', y:-0.15}},
    hovermode:'x unified',
    font:{{family:'Inter'}},
  }}, {{responsive:true}});
}}

function renderTop10() {{
  const top = DATA_TOP10.slice().reverse();
  Plotly.newPlot('chart-top10',
    [{{ type:'bar', orientation:'h',
        x: top.map(r=>r.share_rawan_moderate_severe*100),
        y: top.map(r=>r.nama_kabkota),
        text: top.map(r=>(r.share_rawan_moderate_severe*100).toFixed(1)+'%'),
        textposition:'outside',
        marker:{{color:C.red, opacity:0.85}},
        hovertemplate:'%{{y}}<br>%{{x:.2f}}%<extra></extra>',
    }}],
    {{
      margin:{{t:10,b:30,l:160,r:60}},
      paper_bgcolor:'transparent', plot_bgcolor:'transparent',
      xaxis:{{title:'%', gridcolor:'#F1F5F9', ticksuffix:'%'}},
      yaxis:{{tickfont:{{size:11}}}},
      font:{{family:'Inter'}},
    }}, {{responsive:true}});
}}

function renderBot10() {{
  const bot = DATA_BOT10.slice();
  Plotly.newPlot('chart-bot10',
    [{{ type:'bar', orientation:'h',
        x: bot.map(r=>r.share_rawan_moderate_severe*100),
        y: bot.map(r=>r.nama_kabkota),
        text: bot.map(r=>(r.share_rawan_moderate_severe*100).toFixed(1)+'%'),
        textposition:'outside',
        marker:{{color:C.green, opacity:0.85}},
        hovertemplate:'%{{y}}<br>%{{x:.2f}}%<extra></extra>',
    }}],
    {{
      margin:{{t:10,b:30,l:160,r:60}},
      paper_bgcolor:'transparent', plot_bgcolor:'transparent',
      xaxis:{{title:'%', gridcolor:'#F1F5F9', ticksuffix:'%'}},
      yaxis:{{tickfont:{{size:11}}}},
      font:{{family:'Inter'}},
    }}, {{responsive:true}});
}}

// ── Map page
let mapRendered = false;
let mapYear = 2025;

function onMapYearSlide(val) {{
  mapYear = parseInt(val);
  document.getElementById('map-year-label').textContent = val;
  renderMap();
}}

function renderMap() {{
  const metric = document.getElementById('map-metric').value;
  const unit   = document.getElementById('map-unit').value;
  const metricLabel = METRIC_LABELS[metric] || metric;
  document.getElementById('map-title').textContent = metricLabel + ', ' + mapYear;

  // Filter data
  const kabData = DATA_KAB.filter(r => r.year === mapYear);
  const kabIndex = {{}};
  kabData.forEach(r => {{ kabIndex[r.kode_kabkota] = r; }});

  // Build values for features
  const locations = [], z = [], text = [], customdata = [];
  GEOJSON.features.forEach((f, i) => {{
    const kode = f.properties.kode_kabkota;
    const row  = kabIndex[kode];
    if (row) {{
      const rawVal = row[metric];
      const val = unit === 'pct' ? rawVal * 100 : getJiwaForMetric(row, metric);
      locations.push(kode);
      z.push(val != null ? val : null);
      text.push(
        '<b>' + (row.nama_kabkota||kode) + '</b><br>' +
        (row.nama_prov||'') + '<br>' +
        metricLabel + ': ' + (unit==='pct' ? (rawVal*100).toFixed(2)+'%' : fmtJiwa(val))
      );
    }}
  }});

  // Plotly choropleth using scattergeo workaround — use choroplethmapbox
  // Since we have GeoJSON we use choroplethmapbox style
  const colorscale = metric === 'share_tahan'
    ? [['0','#FEF3C7'],['1',C.blue]]
    : [['0','#FFFBEB'],['0.5','#FCA5A5'],['1',C.red]];

  const trace = {{
    type: 'choroplethmapbox',
    geojson: GEOJSON,
    featureidkey: 'properties.kode_kabkota',
    locations: GEOJSON.features.map(f => f.properties.kode_kabkota),
    z: GEOJSON.features.map(f => {{
      const row = kabIndex[f.properties.kode_kabkota];
      if (!row) return null;
      const rawVal = row[metric];
      return unit === 'pct' ? (rawVal != null ? rawVal*100 : null) : getJiwaForMetric(row, metric);
    }}),
    text: GEOJSON.features.map(f => {{
      const kode = f.properties.kode_kabkota;
      const row  = kabIndex[kode];
      if (!row) return (f.properties.ADM2_EN||kode) + '<br>Data tidak tersedia';
      const rawVal = row[metric];
      const val = unit==='pct' ? rawVal*100 : getJiwaForMetric(row, metric);
      return '<b>' + (row.nama_kabkota||kode) + '</b><br>' +
             (row.nama_prov||'') + '<br>' +
             metricLabel + ': ' + (unit==='pct' ? (rawVal*100).toFixed(2)+'%' : fmtJiwa(val));
    }}),
    colorscale: colorscale,
    marker:{{ line:{{ width:0.3, color:'white' }} }},
    colorbar:{{ title:{{ text: unit==='pct' ? '(%)' : '(jiwa)' }} }},
    hoverinfo: 'text',
  }};

  Plotly.newPlot('chart-map', [trace], {{
    mapbox:{{ style:'white-bg', center:{{ lat:-2.5, lon:118 }}, zoom:3.8 }},
    margin:{{t:0,b:0,l:0,r:0}},
    paper_bgcolor:'transparent',
  }}, {{responsive:true}});
}}

function getJiwaForMetric(row, metric) {{
  const map = {{
    share_tahan                 : row.n_tahan,
    share_ringan                : row.n_ringan,
    share_sedang                : row.n_sedang,
    share_parah                 : row.n_parah,
    share_rawan_total           : row.n_ringan + row.n_sedang + row.n_parah,
    share_rawan_moderate_severe : row.n_sedang + row.n_parah,
    share_rawan_severe          : row.n_parah,
  }};
  return map[metric] || null;
}}

// ── Trend page
let selectedKabs = [];

function populateKabDropdown() {{
  const list = document.getElementById('kab-dropdown-list');
  list.innerHTML = '';
  DATA_KAB_LIST.forEach(k => {{
    const div = document.createElement('div');
    div.className = 'px-3 py-2 cursor-pointer text-sm';div.onmouseenter=function(){{this.style.background='var(--mist)';}};div.onmouseleave=function(){{this.style.background='';}};
    div.textContent = k.nama_kabkota + ' — ' + k.nama_prov;
    div.dataset.kode = k.kode_kabkota;
    div.dataset.nama = k.nama_kabkota;
    div.onclick = () => selectKab(k.kode_kabkota, k.nama_kabkota);
    list.appendChild(div);
  }});

  // Also populate stacked area select
  const stackSel = document.getElementById('trend-stacked-kab');
  DATA_KAB_LIST.forEach(k => {{
    const o = document.createElement('option');
    o.value = k.kode_kabkota;
    o.textContent = k.nama_kabkota + ' (' + k.nama_prov + ')';
    stackSel.appendChild(o);
  }});
}}

function filterKabDropdown() {{
  const q = document.getElementById('kab-search').value.toLowerCase();
  const items = document.querySelectorAll('#kab-dropdown-list > div');
  items.forEach(item => {{
    item.style.display = item.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}

function selectKab(kode, nama) {{
  if (selectedKabs.length >= 10) {{ alert('Maksimal 10 kab/kota'); return; }}
  if (selectedKabs.find(k => k.kode === kode)) return;
  selectedKabs.push({{ kode, nama }});
  renderKabTags();
  renderTrend();
}}

function removeKab(kode) {{
  selectedKabs = selectedKabs.filter(k => k.kode !== kode);
  renderKabTags();
  renderTrend();
}}

function renderKabTags() {{
  const container = document.getElementById('kab-selected-tags');
  if (selectedKabs.length === 0) {{
    container.innerHTML = '<span class="text-xs" style="color:var(--muted)">Belum ada kab/kota dipilih</span>';
    return;
  }}
  container.innerHTML = selectedKabs.map(k =>
    '<span class="kab-tag">' + k.nama +
    '<button onclick="removeKab(' + k.kode + ')" title="Hapus">&times;</button></span>'
  ).join('');
}}

const TREND_COLORS = [C.blue, C.red, C.yellow, C.orange, C.sky, C.green, C.grey, '#8B5CF6', '#EC4899', '#14B8A6'];

function renderTrend() {{
  if (selectedKabs.length === 0) {{
    document.getElementById('chart-trend-line').innerHTML =
      '<div class="flex items-center justify-center h-full text-slate-400 text-sm">Pilih kab/kota dari sidebar untuk menampilkan tren</div>';
    return;
  }}
  const metric = document.getElementById('trend-metric').value;
  const unit   = document.getElementById('trend-unit').value;
  const metricLabel = METRIC_LABELS[metric] || metric;

  const traces = selectedKabs.map((k, i) => {{
    const rows = DATA_KAB.filter(r => r.kode_kabkota == k.kode).sort((a,b) => a.year - b.year);
    const vals = unit === 'pct'
      ? rows.map(r => r[metric] != null ? r[metric]*100 : null)
      : rows.map(r => getJiwaForMetric(r, metric));
    return {{
      type: 'scatter', mode: 'lines+markers', name: k.nama,
      x: rows.map(r => r.year), y: vals,
      line: {{ color: TREND_COLORS[i % TREND_COLORS.length], width: 2 }},
      hovertemplate: '%{{y:.2f}}' + (unit==='pct'?'%':'') + '<extra>%{{fullData.name}}</extra>',
    }};
  }});

  Plotly.newPlot('chart-trend-line', traces, {{
    margin:{{t:10,b:40,l:60,r:10}},
    paper_bgcolor:'transparent', plot_bgcolor:'transparent',
    yaxis:{{title: unit==='pct' ? metricLabel+' (%)' : metricLabel, gridcolor:'#F1F5F9', ticksuffix: unit==='pct'?'%':''}},
    xaxis:{{tickvals:[2019,2020,2021,2022,2023,2024,2025]}},
    legend:{{orientation:'h', y:-0.2}},
    hovermode:'x unified',
    font:{{family:'Inter'}},
  }}, {{responsive:true}});
}}

function renderStackedArea() {{
  const kode = document.getElementById('trend-stacked-kab').value;
  if (!kode) return;
  const kab  = DATA_KAB_LIST.find(k => k.kode_kabkota == kode);
  const rows = DATA_KAB.filter(r => r.kode_kabkota == kode).sort((a,b) => a.year - b.year);
  if (!rows.length) return;

  document.getElementById('stacked-title').textContent = 'Komposisi 4 Kategori — ' + (kab ? kab.nama_kabkota : kode);

  const cats = [
    {{ key:'share_tahan', label:'Tahan Pangan', color:C.blue }},
    {{ key:'share_ringan', label:'Rawan Ringan', color:C.yellow }},
    {{ key:'share_sedang', label:'Rawan Sedang', color:C.orange }},
    {{ key:'share_parah',  label:'Rawan Parah',  color:C.red }},
  ];

  const traces = cats.map(c => ({{
    type: 'scatter', mode: 'lines', name: c.label, stackgroup:'one',
    x: rows.map(r => r.year),
    y: rows.map(r => r[c.key] != null ? r[c.key]*100 : 0),
    fillcolor: c.color, line:{{ color:c.color, width:1 }},
    hovertemplate: '%{{y:.2f}}%<extra>%{{fullData.name}}</extra>',
  }}));

  Plotly.newPlot('chart-stacked', traces, {{
    margin:{{t:10,b:40,l:50,r:10}},
    paper_bgcolor:'transparent', plot_bgcolor:'transparent',
    yaxis:{{title:'% Penduduk', range:[0,100], ticksuffix:'%', gridcolor:'#F1F5F9'}},
    xaxis:{{tickvals:[2019,2020,2021,2022,2023,2024,2025]}},
    legend:{{orientation:'h', y:-0.2}},
    hovermode:'x unified',
    font:{{family:'Inter'}},
  }}, {{responsive:true}});
}}

// ── Province page
function populateProvSelect() {{
  const sel = document.getElementById('prov-select');
  if (sel.options.length > 1) return;
  DATA_PROV.forEach(p => {{
    const o = document.createElement('option');
    o.value = p.kode_prov;
    o.textContent = p.nama_prov;
    sel.appendChild(o);
  }});
}}

function renderProvince() {{
  const prov   = document.getElementById('prov-select').value;
  const metric = document.getElementById('prov-metric').value;
  if (!prov) return;

  const metricLabel = METRIC_LABELS[metric] || metric;
  const provName = DATA_PROV.find(p => p.kode_prov == prov)?.nama_prov || prov;

  document.getElementById('prov-chart-title').textContent = provName + ' — ' + metricLabel + ' (2025)';

  // Filter kab/kota in prov, 2025
  const rows2025 = DATA_KAB2025.filter(r => r.kode_prov == prov).sort((a,b) => a[metric] - b[metric]);

  // Bar chart
  Plotly.newPlot('chart-prov-bar',
    [{{ type:'bar', orientation:'h',
        x: rows2025.map(r => r[metric] != null ? r[metric]*100 : null),
        y: rows2025.map(r => r.nama_kabkota || r.kode_kabkota),
        text: rows2025.map(r => r[metric] != null ? (r[metric]*100).toFixed(2)+'%' : '-'),
        textposition: 'outside',
        marker:{{ color: metric==='share_tahan' ? C.blue : C.orange, opacity:0.85 }},
        hovertemplate: '%{{y}}<br>%{{x:.2f}}%<extra></extra>',
    }}],
    {{
      margin:{{t:10, b:30, l:170, r:70}},
      paper_bgcolor:'transparent', plot_bgcolor:'transparent',
      xaxis:{{title:'%', gridcolor:'#F1F5F9', ticksuffix:'%'}},
      yaxis:{{tickfont:{{size:11}}}},
      font:{{family:'Inter'}},
      height: Math.max(300, rows2025.length * 30 + 60),
    }}, {{responsive:true}});

  // Table
  const tbody = document.getElementById('prov-table-body');
  if (!rows2025.length) {{
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-slate-400 py-8">Tidak ada data</td></tr>';
    return;
  }}
  const sorted = [...rows2025].sort((a,b) => b.share_rawan_moderate_severe - a.share_rawan_moderate_severe);
  tbody.innerHTML = sorted.map(r => {{
    const delta = r.delta_rms;
    return '<tr>' +
      '<td class="font-medium">' + (r.nama_kabkota||r.kode_kabkota) + '</td>' +
      '<td class="text-right">' + (r.share_tahan!=null?(r.share_tahan*100).toFixed(1)+'%':'-') + '</td>' +
      '<td class="text-right">' + (r.share_ringan!=null?(r.share_ringan*100).toFixed(1)+'%':'-') + '</td>' +
      '<td class="text-right">' + (r.share_sedang!=null?(r.share_sedang*100).toFixed(1)+'%':'-') + '</td>' +
      '<td class="text-right">' + (r.share_parah!=null?(r.share_parah*100).toFixed(1)+'%':'-') + '</td>' +
      '<td class="text-right font-semibold">' + (r.share_rawan_moderate_severe!=null?(r.share_rawan_moderate_severe*100).toFixed(2)+'%':'-') + '</td>' +
      '<td class="text-right"><span class="' + deltaClass(delta) + '">' + fmtDelta(delta) + '</span></td>' +
      '</tr>';
  }}).join('');
}}

// ── Init
populateGlobalFilters();
populateKabDropdown();
renderKabTags();
renderOverview();
</script>

</body>
</html>"""

print("Writing HTML...")
with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

size_kb = os.path.getsize(OUT_HTML) / 1024
print(f"Done! HTML saved: {OUT_HTML}")
print(f"File size: {size_kb:.0f} KB")
