"""
Generator dashboard MBG Gap Analysis (Phase 0 + Phase 2 stunting overlay).
Input:
  - data/mbg-gap.csv (Phase 0, 514 rows x 18 cols)
  - ../../Riset Initiatives/MBG Gap Analysis/Output/mbg-gap-score-with-stunting.parquet (Phase 2)
  - ../kelas-kabkota/kabkota_bps_simplified.geojson (REUSED)
  - metadata.json
Output:
  - dashboard.html (5 page: Ringkasan, Peta Gap, Ranking, Drilldown Provinsi, Metodologi)
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd
import numpy as np

HERE = Path(__file__).parent
CSV_PHASE0 = HERE / "data" / "mbg-gap.csv"
PARQUET_PHASE2 = HERE.parent.parent / "Riset Initiatives" / "MBG Gap Analysis" / "Output" / "mbg-gap-score-with-stunting.parquet"
GEOJSON = HERE.parent / "kelas-kabkota" / "kabkota_bps_simplified.geojson"
META = HERE / "metadata.json"
OUT = HERE / "dashboard.html"

TIER_COLORS = {
    "Tier 1 - Prioritas Tinggi": "#C8102E",
    "Tier 2 - Prioritas Sedang": "#EA7200",
    "Tier 3 - Cukup Tertangani": "#A9C4DF",
    "Tier 4 - Low Priority":     "#67B2E8",
}
QUADRANT_COLORS = {
    "GAP":              "#C8102E",
    "Over-served":      "#67B2E8",
    "Sudah Tertangani": "#003D79",
    "Low Priority":     "#A9C4DF",
}
STUNTING_TIER_COLORS = {
    "S1 High": "#C8102E",
    "S2":      "#EA7200",
    "S3":      "#FFB700",
    "S4 Low":  "#67B2E8",
}
# Bivariate matrix (4 MBG tier x 4 stunting tier) -> 16 cells
# Diagonal high = darkest (Tier1 + S1) -> super priority
BIVARIATE_MATRIX = {
    ("Tier 1 - Prioritas Tinggi", "S1 High"): "#3B0F1A",  # super priority
    ("Tier 1 - Prioritas Tinggi", "S2"):      "#7A1A2D",
    ("Tier 1 - Prioritas Tinggi", "S3"):      "#B22A45",
    ("Tier 1 - Prioritas Tinggi", "S4 Low"):  "#E63950",
    ("Tier 2 - Prioritas Sedang", "S1 High"): "#7E3B16",
    ("Tier 2 - Prioritas Sedang", "S2"):      "#B45F2A",
    ("Tier 2 - Prioritas Sedang", "S3"):      "#D88A4A",
    ("Tier 2 - Prioritas Sedang", "S4 Low"):  "#EAB17C",
    ("Tier 3 - Cukup Tertangani", "S1 High"): "#3F6FA6",
    ("Tier 3 - Cukup Tertangani", "S2"):      "#5E8DC4",
    ("Tier 3 - Cukup Tertangani", "S3"):      "#8DB1D9",
    ("Tier 3 - Cukup Tertangani", "S4 Low"):  "#BCD2EA",
    ("Tier 4 - Low Priority",     "S1 High"): "#1A5394",
    ("Tier 4 - Low Priority",     "S2"):      "#3F7AB8",
    ("Tier 4 - Low Priority",     "S3"):      "#67B2E8",
    ("Tier 4 - Low Priority",     "S4 Low"):  "#A9C4DF",
}


def load():
    """Load Phase 0 CSV + merge stunting from parquet."""
    df = pd.read_csv(CSV_PHASE0)
    if PARQUET_PHASE2.exists():
        st = pd.read_parquet(PARQUET_PHASE2)[
            ["kode_kabkota", "prev_stunting", "prev_wasting", "prev_underweight", "stunting_tier"]
        ]
        df = df.merge(st, on="kode_kabkota", how="left")
        print(f"Merged stunting: {df['prev_stunting'].notna().sum()}/{len(df)} kabkota")
    else:
        print("WARNING: Phase 2 parquet not found, no stunting overlay")
        df["prev_stunting"] = np.nan
        df["prev_wasting"] = np.nan
        df["prev_underweight"] = np.nan
        df["stunting_tier"] = None
    df["pcode"] = "ID" + df["kode_kabkota"].astype(int).astype(str).str.zfill(4)
    df["nama_prov"] = df["nama_prov"].str.replace("Sumatera", "Sumatra", regex=False)
    return df


def build_payload(df, meta):
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "pcode": r["pcode"],
            "kode_prov": int(r["kode_prov"]),
            "nama_prov": r["nama_prov"],
            "nama_kab": r["nama_kab"],
            "n_sppg": int(r["n_sppg"]),
            "pop_anak": int(round(r["pop_anak_6_18_2025"])) if pd.notna(r["pop_anak_6_18_2025"]) else 0,
            "pop_total": int(round(r["pop_total_2025"])) if pd.notna(r["pop_total_2025"]) else 0,
            "fies": round(float(r["share_rawan_moderate_severe_2025"]) * 100, 2),
            "fies_severe": round(float(r["share_rawan_severe_2025"]) * 100, 2),
            "sppg_10k_anak": round(float(r["sppg_per_10k_anak"]), 2),
            "sppg_10k_total": round(float(r["sppg_per_10k_total"]), 2),
            "gap_score": round(float(r["gap_score"]), 4),
            "rank": int(r["rank_gap"]),
            "tier": r["tier"],
            "tier_short": r["tier"].split(" - ")[0],
            "quadrant": r["quadrant"],
            "stunting": round(float(r["prev_stunting"]), 1) if pd.notna(r.get("prev_stunting")) else None,
            "stunting_tier": r["stunting_tier"] if pd.notna(r.get("stunting_tier")) else None,
        })
    rows.sort(key=lambda x: x["rank"])

    # Aggregates per provinsi (Drilldown)
    prov_agg = df.groupby(["kode_prov", "nama_prov"]).agg(
        n_kabkota=("pcode", "count"),
        avg_gap=("gap_score", "mean"),
        total_sppg=("n_sppg", "sum"),
        total_anak=("pop_anak_6_18_2025", "sum"),
        avg_fies=("share_rawan_moderate_severe_2025", "mean"),
        avg_stunting=("prev_stunting", "mean"),
    ).reset_index()
    prov_agg["sppg_10k_anak"] = (prov_agg["total_sppg"] / prov_agg["total_anak"] * 10000).round(2)
    prov_agg["avg_gap"] = prov_agg["avg_gap"].round(4)
    prov_agg["avg_fies"] = (prov_agg["avg_fies"] * 100).round(2)
    prov_agg["avg_stunting"] = prov_agg["avg_stunting"].round(1)
    prov_agg["total_anak"] = prov_agg["total_anak"].round().astype(int)

    # Tier distribution per provinsi
    tier_dist = (df.groupby(["kode_prov", "tier"]).size().unstack(fill_value=0)
                 .reset_index().to_dict(orient="records"))

    prov_list = []
    for _, r in prov_agg.iterrows():
        prov_list.append({
            "kode_prov": int(r["kode_prov"]),
            "nama_prov": r["nama_prov"],
            "n_kabkota": int(r["n_kabkota"]),
            "avg_gap": float(r["avg_gap"]),
            "total_sppg": int(r["total_sppg"]),
            "total_anak": int(r["total_anak"]),
            "sppg_10k_anak": float(r["sppg_10k_anak"]),
            "avg_fies": float(r["avg_fies"]),
            "avg_stunting": float(r["avg_stunting"]) if pd.notna(r["avg_stunting"]) else None,
        })
    prov_list.sort(key=lambda x: -x["avg_gap"])

    # Aggregate national totals
    totals = {
        "n_kabkota": int(len(df)),
        "n_sppg_total": int(df["n_sppg"].sum()),
        "pop_anak_total": int(round(df["pop_anak_6_18_2025"].sum())),
        "pop_total": int(round(df["pop_total_2025"].sum())),
        "tier_count": df["tier"].value_counts().to_dict(),
        "quadrant_count": df["quadrant"].value_counts().to_dict(),
        "tier_x_stunting": (df.groupby(["tier", "stunting_tier"]).size().unstack(fill_value=0)
                            .reindex(index=list(TIER_COLORS.keys()),
                                     columns=["S1 High","S2","S3","S4 Low"], fill_value=0)
                            .to_dict(orient="index")),
        "avg_stunt_per_tier": df.groupby("tier")["prev_stunting"].mean().round(1).to_dict(),
        "avg_stunt_per_quadrant": df.groupby("quadrant")["prev_stunting"].mean().round(1).to_dict(),
    }

    # Top 10 super-priority (Tier 1 + GAP + high stunting)
    sup = df[(df["tier"] == "Tier 1 - Prioritas Tinggi") &
             (df["quadrant"] == "GAP")].copy()
    sup = sup.sort_values("prev_stunting", ascending=False, na_position="last").head(10)
    super_priority = []
    for _, r in sup.iterrows():
        super_priority.append({
            "pcode": r["pcode"],
            "nama_prov": r["nama_prov"],
            "nama_kab": r["nama_kab"],
            "fies": round(float(r["share_rawan_moderate_severe_2025"]) * 100, 1),
            "n_sppg": int(r["n_sppg"]),
            "sppg_10k_anak": round(float(r["sppg_per_10k_anak"]), 2),
            "stunting": round(float(r["prev_stunting"]), 1) if pd.notna(r["prev_stunting"]) else None,
            "rank": int(r["rank_gap"]),
            "gap_score": round(float(r["gap_score"]), 4),
        })

    # Top 10 GAP overall (rank 1-10)
    top10_gap = [r for r in rows[:10]]

    return {
        "rows": rows,
        "prov_list": prov_list,
        "totals": totals,
        "super_priority": super_priority,
        "top10_gap": top10_gap,
        "thresholds": meta["methodology"]["thresholds"],
        "caveats": meta["caveats"],
    }


def build_html(payload, _unused_geojson, generated):
    t = payload["totals"]
    n_gap = t["quadrant_count"].get("GAP", 0)
    n_tier1 = t["tier_count"].get("Tier 1 - Prioritas Tinggi", 0)
    pop_anak_jt = t["pop_anak_total"] / 1e6
    pop_total_jt = t["pop_total"] / 1e6

    # Embed payload data (light, ~250kb gzipped). Geojson loaded via fetch to keep HTML small.
    payload_js = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pemetaan Prioritas MBG vs Kerawanan Pangan + Stunting</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://code.iconify.design/iconify-icon/2.1.0/iconify-icon.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&display=swap" rel="stylesheet">
<style>
  :root {{
    --navy: #003D79; --navy-deep: #002852; --navy-soft: #1A5394;
    --sky: #67B2E8; --sky-soft: #A9C4DF;
    --yellow: #FFB700; --yellow-soft: #FFE08A;
    --ink: #051C2C; --ink-soft: #2A3F52;
    --rule: #E5E8EC; --rule-strong: #D0D5DD;
    --muted: #667085; --muted-soft: #98A2B3;
    --paper: #FFFFFF; --cream: #F8F6F0; --mist: #F0F6FC;
    --positive: #00875A; --negative: #C8102E; --warning: #EA7200;
    --sp-1: 4px; --sp-2: 8px; --sp-3: 12px; --sp-4: 16px; --sp-5: 24px; --sp-6: 32px; --sp-8: 48px; --sp-10: 64px; --sp-12: 96px;
    --elev-1: 0 1px 2px rgba(5,28,44,0.04);
    --elev-2: 0 2px 8px rgba(5,28,44,0.06);
    --elev-3: 0 8px 24px rgba(5,28,44,0.10);
    --fs-xs: 11px; --fs-sm: 13px; --fs-base: 14px; --fs-md: 16px; --fs-lg: 20px;
    --fs-xl: 25px; --fs-2xl: 31px; --fs-3xl: 39px; --fs-4xl: 49px; --fs-5xl: 61px;
    --tr-fast: 0.12s ease; --tr-base: 0.2s ease; --tr-slow: 0.4s ease;
  }}
  html, body {{ background: var(--paper); color: var(--ink); }}
  body {{ font-family: 'Inter', system-ui, sans-serif; font-weight: 400; letter-spacing: -0.003em; }}
  .serif-display {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.015em; line-height: 1.08; }}
  .stat-num {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.02em; line-height: 1; font-feature-settings: 'tnum' 1, 'lnum' 1; }}
  .eyebrow {{ font-size: 11px; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; color: var(--navy); }}
  .eyebrow-roman {{ font-family: 'Source Serif 4', Georgia, serif; font-style: italic; font-size: var(--fs-md); font-weight: 500; color: var(--navy); }}
  .eyebrow-roman::before {{ content: ''; display: inline-block; width: 24px; height: 1px; background: var(--navy); vertical-align: middle; margin-right: 12px; }}
  .rule-top {{ border-top: 1px solid var(--rule); }}
  .rule-bottom {{ border-bottom: 1px solid var(--rule); }}
  .hair-accent {{ border-top: 2px solid var(--sky); }}
  .ink {{ color: var(--ink); }} .muted {{ color: var(--muted); }}
  .num {{ font-variant-numeric: tabular-nums; }}
  .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--navy); background: var(--mist); border: 1px solid var(--sky); }}
  .badge-dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--sky); display: inline-block; }}
  .callout {{ border-left: 3px solid var(--sky); background: var(--mist); padding: 18px 24px; }}
  .callout .label {{ font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--navy); }}
  .callout .text {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 18px; line-height: 1.45; color: var(--ink); margin-top: 6px; font-weight: 500; }}
  .chart-footer {{ border-top: 1px solid var(--rule); margin-top: var(--sp-5); padding-top: var(--sp-4); display: flex; flex-wrap: wrap; gap: var(--sp-5); font-size: var(--fs-xs); color: var(--muted); }}
  .chart-footer .label {{ font-weight: 600; color: var(--ink); text-transform: uppercase; letter-spacing: 0.06em; margin-right: 4px; }}
  .select-flat {{ border: 0; border-bottom: 1px solid var(--ink); background: transparent; padding: 6px 24px 6px 0; font-size: 14px; font-weight: 500; color: var(--ink); appearance: none; background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%23051C2C'%3e%3cpath fill-rule='evenodd' d='M5.23 7.21a.75.75 0 011.06.02L10 11.06l3.71-3.83a.75.75 0 111.08 1.04l-4.25 4.39a.75.75 0 01-1.08 0L5.21 8.27a.75.75 0 01.02-1.06z' clip-rule='evenodd'/%3e%3c/svg%3e"); background-repeat: no-repeat; background-position: right 0 center; background-size: 18px; }}
  .select-flat:focus {{ outline: none; border-bottom-color: var(--sky); }}

  /* TOP NAV (canon, sticky) */
  .topnav {{ background: var(--navy-deep); padding: 14px 28px; display: flex; align-items: center; gap: 24px; border-bottom: 1px solid rgba(255,255,255,0.08); position: sticky; top: 0; z-index: 60; color: white; }}
  .topnav .burger {{ font-size: 22px; cursor: pointer; opacity: 0.92; display: none; }}
  .topnav .brand {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 17px; font-weight: 600; letter-spacing: -0.01em; color: white; }}
  .topnav .brand-sub {{ font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--sky); margin-top: 2px; font-weight: 600; }}
  .topnav .menu {{ display: flex; gap: 22px; margin-left: 24px; }}
  .topnav .menu a, .topnav .menu button {{ background: none; border: 0; font-family: inherit; font-size: 13px; font-weight: 500; color: white; opacity: 0.85; padding: 6px 0; cursor: pointer; transition: opacity 0.2s; letter-spacing: -0.003em; }}
  .topnav .menu a:hover, .topnav .menu button:hover {{ opacity: 1; color: var(--sky); }}
  .topnav .right {{ margin-left: auto; display: flex; gap: 14px; align-items: center; font-size: 12px; opacity: 0.8; }}

  /* Mobile drawer */
  .nav-drawer-overlay {{ display: none; position: fixed; inset: 0; background: rgba(5,28,44,0.55); z-index: 99; opacity: 0; transition: opacity 0.3s; }}
  .nav-drawer-overlay.open {{ display: block; opacity: 1; }}
  .nav-drawer {{ position: fixed; top: 0; right: 0; bottom: 0; width: min(320px, 82vw); background: var(--navy-deep); z-index: 100; padding: 76px 28px 28px; box-shadow: -8px 0 32px rgba(0,0,0,0.3); transform: translateX(100%); transition: transform 0.3s ease; color: white; overflow-y: auto; }}
  .nav-drawer.open {{ transform: translateX(0); }}
  .nav-drawer .close-btn {{ position: absolute; top: 20px; right: 20px; background: none; border: none; cursor: pointer; color: white; padding: 6px; font-size: 26px; }}
  .nav-drawer .drawer-label {{ font-size: 10px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: rgba(255,255,255,0.55); margin: 18px 0 10px; }}
  .nav-drawer ul {{ list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 2px; }}
  .nav-drawer a, .nav-drawer button {{ display: flex; align-items: center; gap: 10px; width: 100%; text-align: left; padding: 14px 0; font-family: 'Source Serif 4', Georgia, serif; font-size: 19px; color: white; border: 0; border-bottom: 1px solid rgba(255,255,255,0.12); background: none; cursor: pointer; transition: color 0.15s; }}
  .nav-drawer a:hover, .nav-drawer button:hover {{ color: var(--sky); }}
  .nav-drawer iconify-icon {{ font-size: 18px; opacity: 0.7; }}

  /* Folio */
  .folio {{ position: sticky; top: 64px; z-index: 30; background: rgba(255,255,255,0.92); backdrop-filter: blur(8px); border-bottom: 1px solid var(--rule); padding: 8px 0; }}
  .folio-inner {{ max-width: 1280px; margin: 0 auto; padding: 0 32px; display: flex; justify-content: space-between; font-size: 10px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); }}
  .folio .left {{ color: var(--ink); }}
  .folio .right {{ color: var(--muted); }}

  /* Hero band */
  .hero-band {{ background: linear-gradient(180deg, #003D79 0%, #003D79 30%, #00498A 50%, #00407C 70%, #002852 100%); position: relative; color: white; }}
  .hero-band::before {{ content: ''; position: absolute; inset: 0; background-image:
      radial-gradient(ellipse at 20% 30%, rgba(255,255,255,0.04), transparent 50%),
      radial-gradient(ellipse at 80% 70%, rgba(103,178,232,0.06), transparent 50%);
      pointer-events: none; }}
  .hero-band::after {{ content: ''; position: absolute; bottom: -1px; left: 0; right: 0; height: 1px; background: var(--yellow); opacity: 0.4; }}
  .hero-band .eyebrow {{ color: var(--sky); }}
  .hero-band h1, .hero-band h2 {{ color: white; }}
  .hero-band p {{ color: rgba(255,255,255,0.78); }}

  /* Page nav (pill tabs under hero) */
  .page-nav {{ display: flex; gap: 4px; flex-wrap: wrap; padding: 12px 0; border-bottom: 1px solid var(--rule); margin-bottom: 8px; }}
  .page-nav button {{ padding: 8px 16px; font-size: 12px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; background: transparent; color: var(--muted); border: 1px solid transparent; cursor: pointer; transition: all 0.15s; display: flex; align-items: center; gap: 8px; }}
  .page-nav button:hover {{ color: var(--navy); background: var(--mist); }}
  .page-nav button.active {{ color: white; background: var(--navy); border-color: var(--navy); }}
  .page-nav iconify-icon {{ font-size: 14px; }}

  /* Action chips */
  .chip-action {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--navy); background: white; border: 1px solid var(--rule); cursor: pointer; transition: all 0.15s; }}
  .chip-action:hover {{ background: var(--mist); border-color: var(--navy); }}
  .chip-action.active {{ background: var(--navy); color: white; border-color: var(--navy); }}
  .chip-action iconify-icon {{ font-size: 14px; }}

  /* Tables */
  table.data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  table.data-table thead th {{ position: sticky; top: 0; background: var(--navy); color: white; padding: 10px 10px; text-align: left; font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; font-weight: 700; cursor: pointer; user-select: none; }}
  table.data-table thead th:hover {{ background: var(--navy-soft); }}
  table.data-table thead th .sort-arrow {{ opacity: 0.5; margin-left: 4px; font-size: 10px; }}
  table.data-table thead th.sorted .sort-arrow {{ opacity: 1; color: var(--yellow); }}
  table.data-table tbody td {{ padding: 8px 10px; border-bottom: 1px solid var(--rule); }}
  table.data-table tbody tr:hover {{ background: var(--mist); }}
  .tier-pill {{ display: inline-block; padding: 2px 8px; font-size: 10px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; color: white; border-radius: 2px; }}
  .quadrant-pill {{ display: inline-block; padding: 2px 8px; font-size: 10px; font-weight: 600; border-radius: 2px; background: #F0F6FC; color: var(--navy); border: 1px solid var(--rule); }}

  /* Super priority card */
  .super-card {{ display: grid; grid-template-columns: 28px 1fr 90px 90px 90px; gap: 14px; padding: 12px 0; border-bottom: 1px solid var(--rule); align-items: center; }}
  .super-card:hover {{ background: var(--mist); }}
  .super-card .rank-num {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 18px; font-weight: 600; color: var(--negative); text-align: right; }}
  .super-card .nama-kab {{ font-size: 14px; color: var(--ink); font-weight: 500; }}
  .super-card .nama-kab .sub-prov {{ display: block; font-size: 11px; color: var(--muted); font-weight: 400; }}
  .super-card .metric {{ font-variant-numeric: tabular-nums; font-size: 13px; font-weight: 600; color: var(--ink); text-align: right; }}
  .super-card .metric .lbl {{ display: block; font-size: 10px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}

  /* Bivariate legend */
  .bivariate-legend {{ display: inline-grid; grid-template-columns: auto repeat(4, 28px); gap: 2px; padding: 12px; background: white; border: 1px solid var(--rule); }}
  .bivariate-legend .lbl-x {{ grid-column: 2 / 6; display: grid; grid-template-columns: repeat(4, 1fr); gap: 2px; font-size: 9px; color: var(--muted); text-align: center; padding-bottom: 2px; }}
  .bivariate-legend .row {{ display: contents; }}
  .bivariate-legend .lbl-y {{ font-size: 9px; color: var(--muted); text-align: right; padding-right: 4px; align-self: center; }}
  .bivariate-legend .cell {{ width: 28px; height: 18px; }}
  .bivariate-legend .axis-title {{ grid-column: 1 / 6; font-size: 9px; color: var(--ink); font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; padding: 4px 0; }}

  /* Stat cards */
  .stat-card {{ padding: 4px 0; }}
  .stat-card .lbl {{ font-size: 11px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }}
  .stat-card .val {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 44px; font-weight: 500; line-height: 1; color: var(--ink); margin-top: 6px; font-variant-numeric: tabular-nums; }}
  .stat-card .val .unit {{ font-size: 18px; color: var(--muted); margin-left: 4px; }}
  .stat-card .sub {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}

  /* Provinsi card */
  .prov-row {{ display: grid; grid-template-columns: 28px 1fr 90px 90px 90px; gap: 14px; padding: 10px 0; border-bottom: 1px solid var(--rule); align-items: center; cursor: pointer; }}
  .prov-row:hover {{ background: var(--mist); }}
  .prov-row .rk {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 14px; font-weight: 600; color: var(--navy); text-align: right; }}
  .prov-row .nm {{ font-size: 14px; color: var(--ink); font-weight: 500; }}
  .prov-row .mt {{ font-size: 13px; font-variant-numeric: tabular-nums; color: var(--ink); text-align: right; font-weight: 600; }}
  .prov-row .mt .lbl {{ display: block; font-size: 10px; font-weight: 500; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}

  /* Tier bar */
  .tier-bar {{ display: flex; height: 8px; width: 100%; }}
  .tier-bar div {{ height: 100%; }}

  /* MOBILE RESPONSIVE */
  @media (max-width: 1100px) {{
    .topnav .burger {{ display: inline-flex; }}
    .topnav .menu {{ display: none; }}
    .topnav .right .nav-link {{ display: none; }}
  }}
  @media (max-width: 768px) {{
    .topnav {{ padding: 12px 18px; gap: 14px; }}
    .topnav .brand {{ font-size: 15px; }}
    .topnav .brand-sub {{ font-size: 9px; letter-spacing: 0.14em; }}
    .folio-inner {{ padding: 0 18px; font-size: 9px; letter-spacing: 0.14em; }}
    .hero-band header {{ padding-left: 18px !important; padding-right: 18px !important; padding-top: 40px !important; padding-bottom: 40px !important; }}
    .hero-band h1 {{ font-size: clamp(26px, 6.4vw, 38px) !important; }}
    .hero-band p {{ font-size: 14px; }}
    main.max-w-\\[1280px\\] {{ padding-left: 18px !important; padding-right: 18px !important; padding-bottom: 48px !important; }}
    .grid.grid-cols-1.md\\:grid-cols-4 {{ grid-template-columns: repeat(2, 1fr) !important; gap: 24px !important; }}
    .grid.grid-cols-1.md\\:grid-cols-2 {{ grid-template-columns: 1fr !important; gap: 32px !important; }}
    .stat-card .val {{ font-size: 30px !important; }}
    #chart-quadrant {{ height: 380px !important; }}
    #chart-map {{ height: 480px !important; }}
    #chart-prov-tier {{ height: 360px !important; }}
    .serif-display.text-3xl {{ font-size: 22px !important; }}
    .serif-display.text-4xl {{ font-size: 26px !important; }}
    .serif-display.text-5xl {{ font-size: 30px !important; }}
    .super-card {{ grid-template-columns: 22px 1fr 70px 70px; }}
    .super-card .col-stunt {{ display: none; }}
    .prov-row {{ grid-template-columns: 22px 1fr 70px 70px; gap: 10px; }}
    .prov-row .col-stunt {{ display: none; }}
    table.data-table {{ font-size: 11px; }}
    table.data-table thead th, table.data-table tbody td {{ padding: 6px 6px; }}
    .col-hide-sm {{ display: none !important; }}
    .chart-footer {{ font-size: 10px; gap: 14px; }}
    .select-flat {{ font-size: 14px; min-width: 100% !important; }}
  }}
  @media (max-width: 480px) {{
    .topnav .brand-sub {{ display: none; }}
    .grid.grid-cols-1.md\\:grid-cols-4 {{ grid-template-columns: 1fr !important; }}
    .col-hide-xs {{ display: none !important; }}
  }}
</style>
</head>
<body x-data="dash()" x-init="init()">

<!-- TOP NAV -->
<nav class="topnav">
  <iconify-icon class="burger" icon="mdi:menu" @click="navOpen = true" role="button" aria-label="Buka menu" tabindex="0"></iconify-icon>
  <div>
    <div class="brand">Mandiri Institute</div>
    <div class="brand-sub">Pemetaan Prioritas MBG</div>
  </div>
  <div class="menu">
    <a href="../index.html">Beranda</a>
    <a href="#" @click.prevent="gotoPage('ringkasan')">Ringkasan</a>
    <a href="#" @click.prevent="gotoPage('peta')">Peta Gap</a>
    <a href="#" @click.prevent="gotoPage('ranking')">Ranking</a>
    <a href="#" @click.prevent="gotoPage('drilldown')">Drilldown</a>
    <a href="#" @click.prevent="gotoPage('metodologi')">Metodologi</a>
  </div>
  <div class="right">
    <a class="nav-link" href="../index.html" style="color:white;opacity:0.85;font-weight:500;">Semua Dashboard</a>
    <iconify-icon class="search" icon="mdi:magnify" role="button" aria-label="Cari" tabindex="0"></iconify-icon>
  </div>
</nav>

<!-- Mobile drawer -->
<div class="nav-drawer-overlay" :class="{{ 'open': navOpen }}" @click="navOpen = false"></div>
<aside class="nav-drawer" :class="{{ 'open': navOpen }}" aria-label="Menu navigasi">
  <button class="close-btn" @click="navOpen = false" aria-label="Tutup menu">
    <iconify-icon icon="mdi:close"></iconify-icon>
  </button>
  <div class="drawer-label">Navigasi</div>
  <ul>
    <li><a href="../index.html"><iconify-icon icon="mdi:home-outline"></iconify-icon>Beranda</a></li>
  </ul>
  <div class="drawer-label">Halaman</div>
  <ul>
    <li><button @click="gotoPage('ringkasan'); navOpen = false"><iconify-icon icon="mdi:view-dashboard-outline"></iconify-icon>Ringkasan</button></li>
    <li><button @click="gotoPage('peta'); navOpen = false"><iconify-icon icon="mdi:map-outline"></iconify-icon>Peta Gap</button></li>
    <li><button @click="gotoPage('ranking'); navOpen = false"><iconify-icon icon="mdi:format-list-numbered"></iconify-icon>Ranking 514 Kabkota</button></li>
    <li><button @click="gotoPage('drilldown'); navOpen = false"><iconify-icon icon="mdi:filter-variant"></iconify-icon>Drilldown Provinsi</button></li>
    <li><button @click="gotoPage('metodologi'); navOpen = false"><iconify-icon icon="mdi:book-open-variant-outline"></iconify-icon>Metodologi</button></li>
  </ul>
  <div class="drawer-label">Cross-link</div>
  <ul>
    <li><a href="../ketahanan-pangan/ketahanan-pangan-dashboard.html"><iconify-icon icon="mdi:food-apple-outline"></iconify-icon>Ketahanan Pangan</a></li>
    <li><a href="../kelas-kabkota/dashboard.html"><iconify-icon icon="mdi:account-group-outline"></iconify-icon>Kelas Masyarakat</a></li>
  </ul>
</aside>

<div class="folio">
  <div class="folio-inner">
    <span class="left">Mandiri Institute &middot; MBG Gap Analysis</span>
    <span class="right" x-text="page.toUpperCase()"></span>
  </div>
</div>

<!-- HERO -->
<div class="hero-band">
  <header class="max-w-[1280px] mx-auto px-8 pt-16 pb-14 relative" style="z-index:1;">
    <div class="eyebrow">Riset Mandiri Institute &middot; MBG vs Kerawanan Pangan + Stunting</div>
    <h1 class="serif-display text-4xl md:text-5xl mt-5 max-w-4xl" x-text="pageTitle"></h1>
    <p class="mt-5 text-base max-w-3xl leading-relaxed" x-text="pageSubtitle"></p>
  </header>
</div>

<main class="max-w-[1280px] mx-auto px-8 pb-16">

  <!-- Page nav -->
  <nav class="page-nav rule-bottom">
    <template x-for="t in tabs" :key="t.id">
      <button :class="page === t.id ? 'active' : ''" @click="gotoPage(t.id)">
        <iconify-icon :icon="t.icon"></iconify-icon><span x-text="t.label"></span>
      </button>
    </template>
  </nav>

  <!-- ============ RINGKASAN ============ -->
  <section x-show="page === 'ringkasan'">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-10 pt-8">
      <div class="stat-card">
        <div class="lbl">Kuadran GAP</div>
        <div class="val" style="color:var(--negative);">{n_gap}<span class="unit">kabkota</span></div>
        <div class="sub">High kerawanan pangan + low SPPG</div>
      </div>
      <div class="stat-card">
        <div class="lbl">Tier 1 Prioritas Tinggi</div>
        <div class="val" style="color:var(--negative);">{n_tier1}<span class="unit">kabkota</span></div>
        <div class="sub">Quartile teratas Gap Score</div>
      </div>
      <div class="stat-card">
        <div class="lbl">Total SPPG</div>
        <div class="val">{t["n_sppg_total"]:,}<span class="unit">unit</span></div>
        <div class="sub">Sebaran 514 kabkota, 2026</div>
      </div>
      <div class="stat-card">
        <div class="lbl">Anak 6-18 Tahun</div>
        <div class="val">{pop_anak_jt:.1f}<span class="unit">juta</span></div>
        <div class="sub">Susenas KOR 2025, weighted</div>
      </div>
    </div>

    <div class="mt-12">
      <div class="callout">
        <span class="label">Headline</span>
        <div class="text">{n_gap} kabupaten/kota masuk kuadran GAP (high kerawanan pangan + low coverage SPPG). Validasi Phase 2: rata-rata stunting kuadran GAP {payload['totals']['avg_stunt_per_quadrant'].get('GAP', 0):.1f}%, di atas Over-served {payload['totals']['avg_stunt_per_quadrant'].get('Over-served', 0):.1f}% dan rata-rata nasional. Tier 1 stunting rata-rata {payload['totals']['avg_stunt_per_tier'].get('Tier 1 - Prioritas Tinggi', 0):.1f}% vs Tier 4 {payload['totals']['avg_stunt_per_tier'].get('Tier 4 - Low Priority', 0):.1f}%, monoton dengan gap_score.</div>
      </div>
    </div>

    <div class="mt-16">
      <span class="badge"><span class="badge-dot"></span>Matriks 4 Kuadran</span>
      <div class="eyebrow-roman mt-3">I. Quadrant matrix</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl">Kerawanan pangan vs coverage SPPG, 514 kabkota.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Setiap titik = 1 kabkota. Sumbu X = SPPG per 10rb anak 6-18, sumbu Y = % rumah tangga rawan pangan moderate-severe (FIES 2025). Median split membentuk 4 kuadran. Ukuran bubble = jumlah SPPG.</p>
      <div class="hair-accent mt-6 pt-2"></div>
      <div id="chart-quadrant" style="height:560px;"></div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>BGN portal scrape 2026 &middot; Susenas KOR 2025 &middot; FIES BPS</span>
        <span><span class="label">Median split</span>FIES 1.90% &middot; SPPG per 10rb anak 3.73</span>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-12 mt-16 rule-top pt-10">
      <div>
        <span class="badge" style="background:#FFF4E5;border-color:var(--warning);color:var(--warning);"><span class="badge-dot" style="background:var(--warning);"></span>Top 10 Gap Score</span>
        <h3 class="serif-display text-2xl mt-3">10 kabkota gap tertinggi (rank 1-10)</h3>
        <p class="mt-2 muted text-sm">Urutan composite gap_score = FIES_norm x (1 - SPPG_density_norm).</p>
        <div class="mt-4">
          <template x-for="(r, i) in top10Gap" :key="r.pcode">
            <div class="super-card">
              <div class="rank-num" x-text="r.rank"></div>
              <div class="nama-kab">
                <span x-text="r.nama_kab"></span>
                <span class="sub-prov" x-text="r.nama_prov"></span>
              </div>
              <div class="metric"><span class="lbl">FIES</span><span x-text="r.fies.toFixed(1)+'%'"></span></div>
              <div class="metric"><span class="lbl">SPPG</span><span x-text="r.n_sppg"></span></div>
              <div class="metric col-stunt"><span class="lbl">Stunt</span><span x-text="r.stunting != null ? r.stunting.toFixed(1)+'%' : '-'"></span></div>
            </div>
          </template>
        </div>
      </div>
      <div>
        <span class="badge" style="background:#FFE5EA;border-color:var(--negative);color:var(--negative);"><span class="badge-dot" style="background:var(--negative);"></span>Super-Priority</span>
        <h3 class="serif-display text-2xl mt-3">Top 10 super-priority (Tier 1 + GAP + Stunting tinggi)</h3>
        <p class="mt-2 muted text-sm">Triple-criteria: prioritas tinggi gap_score, kuadran GAP, dan SSGI 2021 stunting tinggi. Cluster dominan Papua/NTT/Maluku.</p>
        <div class="mt-4">
          <template x-for="(r, i) in superPriority" :key="r.pcode">
            <div class="super-card">
              <div class="rank-num" x-text="r.rank"></div>
              <div class="nama-kab">
                <span x-text="r.nama_kab"></span>
                <span class="sub-prov" x-text="r.nama_prov"></span>
              </div>
              <div class="metric"><span class="lbl">FIES</span><span x-text="r.fies.toFixed(1)+'%'"></span></div>
              <div class="metric"><span class="lbl">SPPG</span><span x-text="r.n_sppg"></span></div>
              <div class="metric col-stunt"><span class="lbl">Stunt</span><span x-text="r.stunting != null ? r.stunting.toFixed(1)+'%' : '-'"></span></div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Cross-link callout -->
    <div class="mt-16 grid grid-cols-1 md:grid-cols-2 gap-6 rule-top pt-8">
      <a href="../ketahanan-pangan/ketahanan-pangan-dashboard.html" class="block p-6 border border-[#E5E8EC] hover:border-[#003D79] hover:bg-[#F0F6FC] transition-all">
        <div class="eyebrow" style="color:var(--muted);">Cross-link &middot; Trend</div>
        <h4 class="serif-display text-xl mt-2 ink">Lihat trend kerawanan pangan FIES 2019-2025</h4>
        <p class="mt-2 muted text-sm">Dashboard Ketahanan Pangan: tren historis FIES + drilldown per kabkota.</p>
        <div class="mt-3 text-xs font-semibold" style="color:var(--navy);">Buka dashboard <iconify-icon icon="mdi:arrow-right" style="vertical-align:middle;"></iconify-icon></div>
      </a>
      <a href="../kelas-kabkota/dashboard.html" class="block p-6 border border-[#E5E8EC] hover:border-[#003D79] hover:bg-[#F0F6FC] transition-all">
        <div class="eyebrow" style="color:var(--muted);">Cross-link &middot; Demografi</div>
        <h4 class="serif-display text-xl mt-2 ink">Lihat profil kelas masyarakat per kabkota</h4>
        <p class="mt-2 muted text-sm">Dashboard Kelas Kabkota: konteks 8 kelas wb4 untuk validasi target SPPG.</p>
        <div class="mt-3 text-xs font-semibold" style="color:var(--navy);">Buka dashboard <iconify-icon icon="mdi:arrow-right" style="vertical-align:middle;"></iconify-icon></div>
      </a>
    </div>
  </section>

  <!-- ============ PETA GAP ============ -->
  <section x-show="page === 'peta'">
    <div class="rule-top pt-8 flex flex-wrap items-end gap-6">
      <div>
        <div class="eyebrow" style="color: var(--muted);">View</div>
        <div class="mt-2 flex gap-2 flex-wrap">
          <button class="chip-action" :class="mapView==='tier' ? 'active' : ''" @click="mapView='tier'; renderMap()">Tier MBG</button>
          <button class="chip-action" :class="mapView==='quadrant' ? 'active' : ''" @click="mapView='quadrant'; renderMap()">Kuadran</button>
          <button class="chip-action" :class="mapView==='bivariate' ? 'active' : ''" @click="mapView='bivariate'; renderMap()">Bivariate (Tier x Stunting)</button>
          <button class="chip-action" :class="mapView==='stunting' ? 'active' : ''" @click="mapView='stunting'; renderMap()">Stunting Tier</button>
        </div>
      </div>
    </div>
    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>514 Kabupaten/Kota</span>
      <div class="eyebrow-roman mt-3">II. Peta Gap</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl" x-text="mapHeadline()"></h2>
      <p class="mt-3 muted text-base max-w-3xl" x-text="mapSubline()"></p>
      <div class="hair-accent mt-6 pt-2"></div>
      <div id="chart-map" style="height:780px;"></div>
      <div id="legend-map" class="mt-3"></div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>BPS adm2 2020 &middot; SSGI 2021 (Kemenkes) &middot; Mandiri Institute</span>
        <span><span class="label">Catatan</span>4 kabkota tanpa data SSGI 2021 (Kep Tanimbar, Yapen, Banggai, Konawe Kepulauan)</span>
      </div>
    </div>
  </section>

  <!-- ============ RANKING ============ -->
  <section x-show="page === 'ranking'">
    <div class="rule-top pt-8 flex flex-wrap items-end gap-4">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Provinsi</div>
        <select x-model="rankFilterProv" @change="recomputeFiltered()" class="select-flat mt-2" style="min-width:200px;">
          <option value="All">Semua provinsi (38)</option>
          <template x-for="p in allProv" :key="'rp'+p.kode_prov">
            <option :value="p.kode_prov" x-text="p.nama_prov"></option>
          </template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Tier</div>
        <select x-model="rankFilterTier" @change="recomputeFiltered()" class="select-flat mt-2" style="min-width:160px;">
          <option value="All">Semua tier</option>
          <option value="Tier 1 - Prioritas Tinggi">Tier 1 Prioritas Tinggi</option>
          <option value="Tier 2 - Prioritas Sedang">Tier 2 Prioritas Sedang</option>
          <option value="Tier 3 - Cukup Tertangani">Tier 3 Cukup Tertangani</option>
          <option value="Tier 4 - Low Priority">Tier 4 Low Priority</option>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Kuadran</div>
        <select x-model="rankFilterQuad" @change="recomputeFiltered()" class="select-flat mt-2" style="min-width:160px;">
          <option value="All">Semua kuadran</option>
          <option value="GAP">GAP</option>
          <option value="Over-served">Over-served</option>
          <option value="Sudah Tertangani">Sudah Tertangani</option>
          <option value="Low Priority">Low Priority</option>
        </select>
      </div>
      <div class="flex-1 min-w-[200px]">
        <div class="eyebrow" style="color: var(--muted);">Cari kabkota</div>
        <input type="text" x-model="rankSearch" @input="recomputeFiltered()" placeholder="Ketik nama..." class="select-flat mt-2 w-full" style="border-bottom: 1px solid var(--ink);">
      </div>
      <div style="margin-left:auto">
        <button class="chip-action" @click="downloadFilteredCSV()" style="background:var(--yellow);color:var(--ink);border-color:var(--yellow);font-weight:700;">
          <iconify-icon icon="mdi:download"></iconify-icon>Unduh CSV
        </button>
      </div>
    </div>
    <div class="mt-8">
      <span class="badge"><span class="badge-dot"></span>514 Kabupaten/Kota</span>
      <div class="eyebrow-roman mt-3">III. Ranking</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl">Ranking 514 kabkota berdasarkan Gap Score.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Default sort by rank Gap Score. Klik header kolom untuk sort. <span x-text="filteredRows.length + ' kabkota terlihat'"></span>.</p>
      <div class="hair-accent mt-6 pt-2"></div>
      <div class="overflow-auto mt-4" style="max-height: 720px; border: 1px solid var(--rule);">
        <table class="data-table">
          <thead>
            <tr>
              <th @click="sortBy('rank')" :class="rankSortKey==='rank' ? 'sorted' : ''">Rank<span class="sort-arrow" x-text="rankSortKey==='rank' ? (rankSortDir>0?'▲':'▼') : '↕'"></span></th>
              <th @click="sortBy('nama_prov')" :class="rankSortKey==='nama_prov' ? 'sorted' : ''" class="col-hide-sm">Provinsi<span class="sort-arrow"></span></th>
              <th @click="sortBy('nama_kab')" :class="rankSortKey==='nama_kab' ? 'sorted' : ''">Kabupaten/Kota<span class="sort-arrow"></span></th>
              <th @click="sortBy('fies')" :class="rankSortKey==='fies' ? 'sorted' : ''" style="text-align:right;">FIES<span class="sort-arrow"></span></th>
              <th @click="sortBy('n_sppg')" :class="rankSortKey==='n_sppg' ? 'sorted' : ''" style="text-align:right;" class="col-hide-xs">SPPG<span class="sort-arrow"></span></th>
              <th @click="sortBy('sppg_10k_anak')" :class="rankSortKey==='sppg_10k_anak' ? 'sorted' : ''" style="text-align:right;" class="col-hide-sm">SPPG/10rb<span class="sort-arrow"></span></th>
              <th @click="sortBy('gap_score')" :class="rankSortKey==='gap_score' ? 'sorted' : ''" style="text-align:right;">Gap Score<span class="sort-arrow"></span></th>
              <th @click="sortBy('tier_short')" :class="rankSortKey==='tier_short' ? 'sorted' : ''">Tier<span class="sort-arrow"></span></th>
              <th @click="sortBy('quadrant')" :class="rankSortKey==='quadrant' ? 'sorted' : ''" class="col-hide-xs">Kuadran<span class="sort-arrow"></span></th>
              <th @click="sortBy('stunting')" :class="rankSortKey==='stunting' ? 'sorted' : ''" style="text-align:right;" class="col-hide-sm">Stunting<span class="sort-arrow"></span></th>
            </tr>
          </thead>
          <tbody>
            <template x-for="r in filteredRows.slice(0, rankLimit)" :key="r.pcode">
              <tr>
                <td x-text="r.rank" style="font-variant-numeric: tabular-nums; font-weight:600;"></td>
                <td x-text="r.nama_prov" class="col-hide-sm"></td>
                <td x-text="r.nama_kab" style="font-weight:500;"></td>
                <td x-text="r.fies.toFixed(1)+'%'" style="text-align:right; font-variant-numeric: tabular-nums;"></td>
                <td x-text="r.n_sppg" style="text-align:right; font-variant-numeric: tabular-nums;" class="col-hide-xs"></td>
                <td x-text="r.sppg_10k_anak.toFixed(2)" style="text-align:right; font-variant-numeric: tabular-nums;" class="col-hide-sm"></td>
                <td x-text="r.gap_score.toFixed(4)" style="text-align:right; font-variant-numeric: tabular-nums; font-weight:600;"></td>
                <td><span class="tier-pill" :style="'background: ' + tierColor(r.tier)" x-text="r.tier_short"></span></td>
                <td x-text="r.quadrant" class="col-hide-xs"></td>
                <td x-text="r.stunting != null ? r.stunting.toFixed(1)+'%' : '-'" style="text-align:right; font-variant-numeric: tabular-nums;" class="col-hide-sm"></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <div class="mt-4 flex justify-between items-center text-sm muted">
        <span x-show="filteredRows.length > rankLimit" x-text="'Menampilkan ' + Math.min(rankLimit, filteredRows.length) + ' dari ' + filteredRows.length + ' kabkota.'"></span>
        <button x-show="filteredRows.length > rankLimit" @click="rankLimit += 100" class="chip-action">Tampilkan 100 berikutnya</button>
      </div>
    </div>
  </section>

  <!-- ============ DRILLDOWN ============ -->
  <section x-show="page === 'drilldown'">
    <div class="rule-top pt-8 flex flex-wrap items-end gap-6">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Provinsi</div>
        <select x-model="drillProv" @change="renderDrilldown()" class="select-flat mt-2" style="min-width:240px;">
          <template x-for="p in allProv" :key="'dp'+p.kode_prov">
            <option :value="p.kode_prov" x-text="p.nama_prov"></option>
          </template>
        </select>
      </div>
    </div>
    <div class="mt-10">
      <span class="badge"><span class="badge-dot"></span>Profil Provinsi</span>
      <div class="eyebrow-roman mt-3">IV. Drilldown</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl">
        <span x-text="'Profil prioritas MBG: ' + (drillProvObj ? drillProvObj.nama_prov : '') + '.'"></span>
      </h2>
      <p class="mt-3 muted text-base max-w-3xl"><span x-text="(drillProvObj ? drillProvObj.n_kabkota : 0)"></span> kabkota dalam provinsi &middot; total <span x-text="(drillProvObj ? drillProvObj.total_sppg.toLocaleString() : 0)"></span> SPPG.</p>
      <div class="hair-accent mt-6 pt-2"></div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-8 mt-8">
        <div class="stat-card">
          <div class="lbl">Avg Gap Score</div>
          <div class="val" x-text="drillProvObj ? drillProvObj.avg_gap.toFixed(4) : '-'"></div>
          <div class="sub">Composite gap, mean prov</div>
        </div>
        <div class="stat-card">
          <div class="lbl">Total SPPG</div>
          <div class="val" x-text="drillProvObj ? drillProvObj.total_sppg.toLocaleString() : '-'"></div>
          <div class="sub" x-text="drillProvObj ? drillProvObj.sppg_10k_anak.toFixed(2) + ' SPPG / 10rb anak' : ''"></div>
        </div>
        <div class="stat-card">
          <div class="lbl">FIES Rata-rata</div>
          <div class="val" x-text="drillProvObj ? drillProvObj.avg_fies.toFixed(1) + '%' : '-'"></div>
          <div class="sub">Rumah tangga moderate-severe</div>
        </div>
        <div class="stat-card">
          <div class="lbl">Stunting Rata-rata</div>
          <div class="val" x-text="(drillProvObj && drillProvObj.avg_stunting != null) ? drillProvObj.avg_stunting.toFixed(1) + '%' : '-'"></div>
          <div class="sub">SSGI 2021, mean kabkota</div>
        </div>
      </div>

      <div class="mt-12 grid grid-cols-1 md:grid-cols-3 gap-10">
        <div class="md:col-span-2">
          <div class="eyebrow" style="color:var(--muted);">Kabkota dalam provinsi (sorted by gap)</div>
          <h3 class="serif-display text-2xl mt-2">Distribusi gap_score per kabkota</h3>
          <div id="chart-prov-tier" style="height:480px; margin-top: 16px;"></div>
        </div>
        <div>
          <div class="eyebrow" style="color:var(--muted);">Daftar kabkota</div>
          <h3 class="serif-display text-2xl mt-2">Ranking kabkota provinsi</h3>
          <div class="mt-4" style="max-height:520px; overflow-y:auto;">
            <template x-for="r in drillKabRows" :key="r.pcode">
              <div class="prov-row">
                <div class="rk" x-text="r.rank"></div>
                <div class="nm">
                  <span x-text="r.nama_kab"></span>
                  <span style="display:block; font-size:11px; color:var(--muted);">
                    <span class="tier-pill" :style="'background:' + tierColor(r.tier) + '; font-size:9px; padding:1px 6px;'" x-text="r.tier_short"></span>
                    <span x-text="' ' + r.quadrant"></span>
                  </span>
                </div>
                <div class="mt"><span class="lbl">Gap</span><span x-text="r.gap_score.toFixed(4)"></span></div>
                <div class="mt"><span class="lbl">SPPG</span><span x-text="r.n_sppg"></span></div>
                <div class="mt col-stunt"><span class="lbl">Stunt</span><span x-text="r.stunting != null ? r.stunting.toFixed(1)+'%' : '-'"></span></div>
              </div>
            </template>
          </div>
        </div>
      </div>

      <div class="mt-16 rule-top pt-10">
        <span class="badge"><span class="badge-dot"></span>Cross-prov Comparison</span>
        <h3 class="serif-display text-2xl mt-3">Ranking lintas provinsi (rata-rata gap_score)</h3>
        <p class="mt-2 muted text-sm">38 provinsi, urut dari rata-rata gap_score tertinggi.</p>
        <div class="mt-6 max-h-[640px] overflow-y-auto">
          <template x-for="(p, i) in allProv" :key="'pa'+p.kode_prov">
            <div class="prov-row" @click="drillProv = p.kode_prov; renderDrilldown()">
              <div class="rk" x-text="i+1"></div>
              <div class="nm">
                <span x-text="p.nama_prov" style="font-weight:600;"></span>
                <span style="display:block; font-size:11px; color:var(--muted);" x-text="p.n_kabkota + ' kabkota &middot; ' + p.total_sppg.toLocaleString() + ' SPPG'"></span>
              </div>
              <div class="mt"><span class="lbl">Avg Gap</span><span x-text="p.avg_gap.toFixed(4)"></span></div>
              <div class="mt"><span class="lbl">FIES</span><span x-text="p.avg_fies.toFixed(1)+'%'"></span></div>
              <div class="mt col-stunt"><span class="lbl">Stunt</span><span x-text="p.avg_stunting != null ? p.avg_stunting.toFixed(1)+'%' : '-'"></span></div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </section>

  <!-- ============ METODOLOGI ============ -->
  <section x-show="page === 'metodologi'">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-10 pt-10 rule-top">
      <div>
        <div class="eyebrow">Sumber data</div>
        <h3 class="serif-display text-xl mt-2">Tiga sumber utama</h3>
        <ul class="mt-4 text-sm" style="line-height:1.7;">
          <li><b>SPPG (BGN)</b>: portal scrape <code class="text-xs muted">bgn.go.id/operasional-sppg</code>, snapshot 2026-05-06, 27.427 unit kelurahan-level di-agregasi ke 514 kabkota.</li>
          <li><b>FIES 2025</b>: replikasi FAO Food Insecurity Experience Scale dari Susenas Maret 2025 (modul KOR), dengan headline metric <i>moderate-severe</i>.</li>
          <li><b>Populasi</b>: Susenas KOR Maret 2025, weighted (fwt individu), filter umur 6-18 tahun untuk denominator SPPG density.</li>
          <li><b>Stunting</b>: SSGI Kemenkes 2021, prevalensi balita stunting per kabkota (510 dari 514 kabkota).</li>
        </ul>
      </div>
      <div>
        <div class="eyebrow">Formula Gap Score</div>
        <h3 class="serif-display text-xl mt-2">Composite normalized 0-1</h3>
        <div class="mt-4 p-4 bg-[#F0F6FC] border-l-2 border-[#67B2E8]">
          <code class="text-sm" style="line-height:1.6;">gap_score = fies_norm &times; (1 - sppg_density_norm)</code>
        </div>
        <ul class="mt-3 text-sm" style="line-height:1.7;">
          <li><b>fies_norm</b>: min-max normalisasi FIES moderate-severe cross-kabkota (0=terendah, 1=tertinggi).</li>
          <li><b>sppg_density_norm</b>: min-max normalisasi SPPG per 10rb anak 6-18.</li>
          <li><b>Threshold tier</b>: quartile gap_score &middot; Q75={payload['thresholds']['q75_gap']:.4f} (Tier 1), Q50={payload['thresholds']['q50_gap']:.4f} (Tier 2), Q25={payload['thresholds']['q25_gap']:.4f} (Tier 3).</li>
          <li><b>Quadrant</b>: median split FIES (1.90%) x SPPG/10rb (3.73).</li>
        </ul>
      </div>
      <div>
        <div class="eyebrow">Cross-validation Phase 2</div>
        <h3 class="serif-display text-xl mt-2">Stunting overlay (SSGI 2021)</h3>
        <table class="text-sm mt-4 w-full" style="border-collapse: collapse;">
          <thead>
            <tr style="border-bottom: 1px solid var(--ink);">
              <th style="text-align:left; padding: 6px 0; font-weight:600;">Tier MBG</th>
              <th style="text-align:right; padding: 6px 0; font-weight:600;">Avg Stunting</th>
            </tr>
          </thead>
          <tbody>
            <tr><td style="padding: 6px 0; border-bottom: 1px solid var(--rule);">Tier 1 Prioritas Tinggi</td><td style="text-align:right; font-variant-numeric: tabular-nums; font-weight:600; color: var(--negative);">{payload['totals']['avg_stunt_per_tier'].get('Tier 1 - Prioritas Tinggi', 0):.1f}%</td></tr>
            <tr><td style="padding: 6px 0; border-bottom: 1px solid var(--rule);">Tier 2 Prioritas Sedang</td><td style="text-align:right; font-variant-numeric: tabular-nums;">{payload['totals']['avg_stunt_per_tier'].get('Tier 2 - Prioritas Sedang', 0):.1f}%</td></tr>
            <tr><td style="padding: 6px 0; border-bottom: 1px solid var(--rule);">Tier 3 Cukup Tertangani</td><td style="text-align:right; font-variant-numeric: tabular-nums;">{payload['totals']['avg_stunt_per_tier'].get('Tier 3 - Cukup Tertangani', 0):.1f}%</td></tr>
            <tr><td style="padding: 6px 0;">Tier 4 Low Priority</td><td style="text-align:right; font-variant-numeric: tabular-nums;">{payload['totals']['avg_stunt_per_tier'].get('Tier 4 - Low Priority', 0):.1f}%</td></tr>
          </tbody>
        </table>
        <p class="mt-3 muted text-xs">Trend monoton: Tier 1 stunting tertinggi, Tier 4 terendah. Validasi gap_score ranking secara independen.</p>
      </div>
    </div>

    <div class="mt-16 rule-top pt-10">
      <h3 class="serif-display text-2xl">Caveat &middot; batasan analisis</h3>
      <ul class="mt-4 text-sm grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-3" style="line-height:1.6;">
        {''.join(f'<li class="pl-4 border-l-2 border-[#FFB700]"><b>Caveat {i+1}.</b> {c}</li>' for i, c in enumerate(payload['caveats']))}
        <li class="pl-4 border-l-2 border-[#FFB700]"><b>Caveat 5.</b> Stunting SSGI 2021 (4 tahun lag dari FIES 2025). 4 kabkota tanpa stunting (Kep Tanimbar, Yapen, Banggai, Konawe Kepulauan). Asumsi struktural per kabkota.</li>
      </ul>
    </div>

    <div class="mt-16 rule-top pt-10">
      <h3 class="serif-display text-2xl">Cross-link &middot; dashboard terkait</h3>
      <div class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        <a href="../ketahanan-pangan/ketahanan-pangan-dashboard.html" class="block p-6 border border-[#E5E8EC] hover:border-[#003D79] hover:bg-[#F0F6FC] transition-all">
          <div class="eyebrow" style="color:var(--muted);">Trend FIES &middot; 2019-2025</div>
          <h4 class="serif-display text-xl mt-2 ink">Dashboard Ketahanan Pangan</h4>
          <p class="mt-2 muted text-sm">Trend historis kerawanan pangan rumah tangga, drilldown per kabkota, decomposition severity.</p>
        </a>
        <a href="../kelas-kabkota/dashboard.html" class="block p-6 border border-[#E5E8EC] hover:border-[#003D79] hover:bg-[#F0F6FC] transition-all">
          <div class="eyebrow" style="color:var(--muted);">Demografi &middot; Kelas wb4</div>
          <h4 class="serif-display text-xl mt-2 ink">Dashboard Kelas Kabkota</h4>
          <p class="mt-2 muted text-sm">Distribusi 8 kelas masyarakat (wb4 World Bank) per 514 kabkota, 2019-2025, untuk konteks demografi target SPPG.</p>
        </a>
      </div>
    </div>
  </section>

  <footer class="rule-top mt-16 pt-8 pb-4 flex items-center justify-between text-xs muted uppercase tracking-widest flex-wrap gap-2">
    <div>Mandiri Institute &middot; Dashboard Suite</div>
    <div>Generated {generated}</div>
    <div>Palette: Mandiri Official &middot; Phase 0 + Phase 2 stunting</div>
  </footer>
</main>

<script>
const PAYLOAD = {payload_js};
let GEOJSON = null; // loaded via fetch from sibling dashboard
const GEOJSON_URL = '../kelas-kabkota/kabkota_bps_simplified.geojson';
const TIER_COLORS = {json.dumps(TIER_COLORS)};
const QUADRANT_COLORS = {json.dumps(QUADRANT_COLORS)};
const STUNTING_TIER_COLORS = {json.dumps(STUNTING_TIER_COLORS)};
const BIVARIATE = {json.dumps({f"{k[0]}|{k[1]}": v for k, v in BIVARIATE_MATRIX.items()})};
const FONT = 'Inter, sans-serif';
const INK = '#051C2C';
const MUTED = '#667085';
const ROWS_BY_PCODE = Object.fromEntries(PAYLOAD.rows.map(r => [r.pcode, r]));

const PAGE_META = {{
  ringkasan:  {{ title: 'Pemetaan prioritas program MBG vs kerawanan pangan + stunting.',
                 sub: 'Composite Gap Score 514 kabkota: FIES kerawanan pangan x SPPG density, divalidasi stunting SSGI 2021. Phase 0 cross-section snapshot 2025/2026.' }},
  peta:       {{ title: 'Peta Indonesia: tier MBG, kuadran GAP, dan bivariate stunting.',
                 sub: 'Choropleth 514 kabkota dengan toggle 4 view: Tier MBG (quartile gap_score), Kuadran (median split), Bivariate (Tier x Stunting), atau Stunting tier saja.' }},
  ranking:    {{ title: 'Ranking 514 kabkota berdasarkan Gap Score.',
                 sub: 'Tabel sortable, filter provinsi/tier/kuadran/search nama kabkota, unduh CSV.' }},
  drilldown:  {{ title: 'Drilldown profil prioritas MBG per provinsi.',
                 sub: 'Pilih 1 dari 38 provinsi untuk lihat distribusi tier, list kabkota, agregat FIES dan stunting.' }},
  metodologi: {{ title: 'Metodologi Gap Score, threshold, dan caveat.',
                 sub: 'Formula composite, sumber data BGN portal + Susenas KOR + FIES + SSGI 2021 stunting, threshold quartile, dan keterbatasan analisis.' }},
}};
const TABS = [
  {{ id: 'ringkasan',  label: 'Ringkasan',          icon: 'mdi:view-dashboard-outline' }},
  {{ id: 'peta',       label: 'Peta Gap',           icon: 'mdi:map-outline' }},
  {{ id: 'ranking',    label: 'Ranking 514 Kabkota', icon: 'mdi:format-list-numbered' }},
  {{ id: 'drilldown',  label: 'Drilldown Provinsi', icon: 'mdi:filter-variant' }},
  {{ id: 'metodologi', label: 'Metodologi',         icon: 'mdi:book-open-variant-outline' }},
];

function fmtPct(v) {{ return v.toFixed(1) + '%'; }}
function fmtNum(v) {{
  if (v >= 1e6) return (v/1e6).toFixed(2) + ' jt';
  if (v >= 1e3) return (v/1e3).toFixed(0) + ' rb';
  return Math.round(v).toString();
}}

function dash() {{
  return {{
    page: 'ringkasan',
    navOpen: false,
    tabs: TABS,
    rows: PAYLOAD.rows,
    allProv: PAYLOAD.prov_list,
    superPriority: PAYLOAD.super_priority,
    top10Gap: PAYLOAD.top10_gap,
    // Map
    mapView: 'tier',
    // Ranking
    rankFilterProv: 'All',
    rankFilterTier: 'All',
    rankFilterQuad: 'All',
    rankSearch: '',
    rankSortKey: 'rank',
    rankSortDir: 1, // 1 = asc, -1 = desc
    rankLimit: 100,
    filteredRows: [],
    // Drilldown
    drillProv: PAYLOAD.prov_list[0]?.kode_prov || 11,

    init() {{
      this.recomputeFiltered();
      // hash routing
      const fromHash = (location.hash || '').replace('#', '');
      if (fromHash && TABS.find(t => t.id === fromHash)) {{
        this.page = fromHash;
      }}
      this.$nextTick(() => this.renderForPage(this.page));
      // Lazy load geojson; re-render map once loaded
      fetch(GEOJSON_URL).then(r => r.json()).then(gj => {{
        GEOJSON = gj;
        if (this.page === 'peta') this.renderMap();
      }}).catch(e => console.error('Failed to load geojson:', e));
    }},
    get pageTitle() {{ return PAGE_META[this.page].title; }},
    get pageSubtitle() {{ return PAGE_META[this.page].sub; }},
    get drillProvObj() {{
      return PAYLOAD.prov_list.find(p => p.kode_prov == this.drillProv) || null;
    }},
    get drillKabRows() {{
      return this.rows.filter(r => Math.floor(r.pcode.slice(2)/100) == this.drillProv ||
                                    String(this.drillProv).padStart(2,'0') === r.pcode.slice(2,4))
                      .sort((a,b) => a.rank - b.rank);
    }},
    tierColor(t) {{ return TIER_COLORS[t] || '#999'; }},
    gotoPage(id) {{
      this.page = id;
      this.navOpen = false;
      try {{ history.replaceState(null, '', '#' + id); }} catch(e) {{}}
      this.renderForPage(id);
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }},
    renderForPage(id) {{
      requestAnimationFrame(() => requestAnimationFrame(() => {{
        if (id === 'ringkasan')  this.renderQuadrant();
        else if (id === 'peta')  this.renderMap();
        else if (id === 'drilldown') this.renderDrilldown();
      }}));
    }},

    // ===== Ringkasan: 4-quadrant bubble matrix =====
    renderQuadrant() {{
      const fies_med = 1.90, sppg_med = 3.73;
      const traces = [];
      // 1 trace per tier (color), include all kabkota
      for (const tier of Object.keys(TIER_COLORS)) {{
        const sub = this.rows.filter(r => r.tier === tier);
        traces.push({{
          x: sub.map(r => r.sppg_10k_anak),
          y: sub.map(r => r.fies),
          mode: 'markers',
          type: 'scatter',
          name: tier.split(' - ')[0],
          marker: {{
            color: TIER_COLORS[tier],
            size: sub.map(r => Math.max(4, Math.min(40, Math.sqrt(r.n_sppg + 1) * 2.5))),
            opacity: 0.6,
            line: {{ color: 'white', width: 0.5 }},
          }},
          text: sub.map(r => `<b>${{r.nama_kab}}</b><br>${{r.nama_prov}}<br>FIES: ${{r.fies.toFixed(1)}}%<br>SPPG: ${{r.n_sppg}} (${{r.sppg_10k_anak.toFixed(2)}}/10rb anak)<br>Gap: ${{r.gap_score.toFixed(4)}}<br>${{r.quadrant}}<br>Stunt: ${{r.stunting != null ? r.stunting.toFixed(1)+'%' : '-'}}`),
          hovertemplate: '%{{text}}<extra></extra>',
        }});
      }}
      Plotly.react('chart-quadrant', traces, {{
        margin: {{ l: 70, r: 30, t: 30, b: 70 }},
        font: {{ family: FONT, size: 13, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ title: {{ text: 'SPPG per 10rb anak 6-18 (log)', font: {{ size: 13, color: MUTED }} }},
                  type: 'log', dtick: 1,
                  tickfont: {{ size: 11, color: MUTED }}, gridcolor: '#EAECF0',
                  showline: true, linecolor: INK, ticks: 'outside' }},
        yaxis: {{ title: {{ text: 'Rumah tangga rawan pangan moderate-severe (%)', font: {{ size: 13, color: MUTED }} }},
                  tickfont: {{ size: 11, color: MUTED }}, gridcolor: '#EAECF0' }},
        legend: {{ orientation: 'h', y: -0.14, x: 0, xanchor: 'left', font: {{ size: 11 }} }},
        shapes: [
          // Median split lines
          {{ type: 'line', x0: sppg_med, x1: sppg_med, y0: 0, y1: 60, xref: 'x', yref: 'y',
             line: {{ color: '#999', width: 1, dash: 'dot' }} }},
          {{ type: 'line', x0: 0.01, x1: 1000, y0: fies_med, y1: fies_med, xref: 'x', yref: 'y',
             line: {{ color: '#999', width: 1, dash: 'dot' }} }},
        ],
        annotations: [
          {{ x: 0.05, y: 30, xref: 'x', yref: 'y', text: '<b>GAP</b><br>(High FIES, Low SPPG)',
             showarrow: false, font: {{ size: 11, color: '#C8102E' }}, align: 'left' }},
          {{ x: 50, y: 30, xref: 'x', yref: 'y', text: '<b>OVER-SERVED</b><br>(High FIES, High SPPG)',
             showarrow: false, font: {{ size: 11, color: '#67B2E8' }}, align: 'left' }},
          {{ x: 0.05, y: 0.5, xref: 'x', yref: 'y', text: '<b>LOW PRIORITY</b><br>(Low FIES, Low SPPG)',
             showarrow: false, font: {{ size: 11, color: '#A9C4DF' }}, align: 'left' }},
          {{ x: 50, y: 0.5, xref: 'x', yref: 'y', text: '<b>SUDAH TERTANGANI</b><br>(Low FIES, High SPPG)',
             showarrow: false, font: {{ size: 11, color: '#003D79' }}, align: 'left' }},
        ],
      }}, {{ displaylogo: false, responsive: true }});
    }},

    // ===== Peta =====
    mapHeadline() {{
      if (this.mapView === 'tier') return 'Tier MBG: 4 prioritas berdasarkan Gap Score.';
      if (this.mapView === 'quadrant') return 'Kuadran: kombinasi FIES x SPPG density.';
      if (this.mapView === 'bivariate') return 'Bivariate: Tier MBG (warna utama) x Stunting (saturasi).';
      if (this.mapView === 'stunting') return 'Stunting tier (SSGI 2021).';
    }},
    mapSubline() {{
      if (this.mapView === 'tier') return 'Quartile gap_score: Tier 1 (Q75+, merah) sampai Tier 4 (Q25-, sky). Hover untuk detail FIES, SPPG, gap, stunting.';
      if (this.mapView === 'quadrant') return 'GAP (high FIES + low SPPG) merah, Sudah Tertangani navy, Over-served sky, Low Priority sky-soft.';
      if (this.mapView === 'bivariate') return 'Diagonal gelap = super-priority (Tier 1 + S1 stunting tinggi). 16 sel dari kombinasi 4 tier MBG x 4 tier stunting.';
      if (this.mapView === 'stunting') return 'S1 (>=30%) merah, S4 (<20.7%) sky. Validation independen MBG ranking.';
    }},
    renderMap() {{
      if (!GEOJSON) {{
        document.getElementById('chart-map').innerHTML = '<div class="empty-state" style="padding:80px 24px; text-align:center; color:var(--muted); font-size:14px;"><iconify-icon icon="mdi:map-outline" style="font-size:48px; opacity:0.4; margin-bottom:12px;"></iconify-icon><div style="font-size:16px; color:var(--ink); font-weight:600; margin-bottom:8px;">Memuat shapefile kabkota...</div><div>514 polygon BPS adm2 2020. Tunggu beberapa detik.</div></div>';
        return;
      }}
      const fids = GEOJSON.features.map(f => f.id);

      const KEY_GROUPS = {{}};
      // For each kabkota, compute color/category based on view
      this.rows.forEach(r => {{
        let cat = '-', color = '#E8E8E8';
        if (this.mapView === 'tier') {{
          cat = r.tier; color = TIER_COLORS[r.tier] || '#E8E8E8';
        }} else if (this.mapView === 'quadrant') {{
          cat = r.quadrant; color = QUADRANT_COLORS[r.quadrant] || '#E8E8E8';
        }} else if (this.mapView === 'bivariate') {{
          if (r.stunting_tier == null) {{ cat = 'No data'; color = '#E8E8E8'; }}
          else {{
            cat = r.tier + ' x ' + r.stunting_tier;
            color = BIVARIATE[r.tier + '|' + r.stunting_tier] || '#E8E8E8';
          }}
        }} else if (this.mapView === 'stunting') {{
          if (r.stunting_tier == null) {{ cat = 'No data'; color = '#E8E8E8'; }}
          else {{ cat = r.stunting_tier; color = STUNTING_TIER_COLORS[r.stunting_tier] || '#E8E8E8'; }}
        }}
        if (!KEY_GROUPS[cat]) KEY_GROUPS[cat] = {{ locs: [], color, hovertexts: [] }};
        KEY_GROUPS[cat].locs.push(r.pcode);
        KEY_GROUPS[cat].hovertexts.push(
          `<b>${{r.nama_kab}}</b><br><span style="color:#667085">${{r.nama_prov}}</span><br>` +
          `<b>Rank:</b> ${{r.rank}} / 514<br>` +
          `<b>FIES:</b> ${{r.fies.toFixed(1)}}% &middot; <b>SPPG:</b> ${{r.n_sppg}} (${{r.sppg_10k_anak.toFixed(2)}}/10rb anak)<br>` +
          `<b>Gap Score:</b> ${{r.gap_score.toFixed(4)}}<br>` +
          `<b>Tier:</b> ${{r.tier_short}} &middot; <b>Kuadran:</b> ${{r.quadrant}}<br>` +
          `<b>Stunting:</b> ${{r.stunting != null ? r.stunting.toFixed(1)+'%' : 'No data'}} ${{r.stunting_tier ? '('+r.stunting_tier+')' : ''}}`
        );
      }});

      // Build traces
      const traces = [];
      Object.entries(KEY_GROUPS).forEach(([cat, g]) => {{
        traces.push({{
          type: 'choropleth', geojson: GEOJSON, locations: g.locs,
          z: g.locs.map(_ => 1),
          featureidkey: 'properties.ADM2_PCODE',
          colorscale: [[0, g.color], [1, g.color]],
          showscale: false,
          marker: {{ line: {{ color: '#FFFFFF', width: 0.25 }} }},
          hovertext: g.hovertexts,
          hovertemplate: '%{{hovertext}}<extra></extra>',
          hoverlabel: {{ bgcolor: 'white', bordercolor: '#003D79', font: {{ family: FONT, size: 12, color: INK }}, align: 'left', namelength: -1 }},
          name: cat,
        }});
      }});

      Plotly.react('chart-map', traces, {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        font: {{ family: FONT, color: INK }},
        geo: {{ visible: false, bgcolor: '#FAFBFC', projection: {{ type: 'mercator' }},
                fitbounds: 'locations' }},
        paper_bgcolor: 'transparent',
        showlegend: false,
      }}, {{ displaylogo: false, responsive: true }});

      // Legend custom
      this.renderMapLegend();
    }},
    renderMapLegend() {{
      const el = document.getElementById('legend-map');
      if (!el) return;
      let html = '';
      const lblWrap = (children) => `<div style="display:flex; gap:24px; flex-wrap:wrap; align-items:center; padding-top:8px; border-top: 1px solid var(--rule);">${{children}}</div>`;
      const item = (color, label) => `<div style="display:flex; align-items:center; gap:6px; font-size:11px; color:var(--ink);"><span style="display:inline-block; width:14px; height:14px; background:${{color}}; border:1px solid var(--rule);"></span><span>${{label}}</span></div>`;
      if (this.mapView === 'tier') {{
        html = lblWrap(Object.entries(TIER_COLORS).map(([k, c]) => item(c, k.split(' - ')[1] ? k.split(' - ')[0] + ' ' + k.split(' - ')[1] : k)).join(''));
      }} else if (this.mapView === 'quadrant') {{
        html = lblWrap(Object.entries(QUADRANT_COLORS).map(([k, c]) => item(c, k)).join(''));
      }} else if (this.mapView === 'stunting') {{
        const lbl = {{ 'S1 High': 'S1 High (>=30.1%)', 'S2': 'S2 (25.7-30%)', 'S3': 'S3 (20.8-25.6%)', 'S4 Low': 'S4 Low (<=20.7%)' }};
        html = lblWrap(Object.entries(STUNTING_TIER_COLORS).map(([k, c]) => item(c, lbl[k])).join('') + item('#E8E8E8', 'No data (4 kabkota)'));
      }} else if (this.mapView === 'bivariate') {{
        // Build 4x4 matrix
        const tiers = ['Tier 1 - Prioritas Tinggi','Tier 2 - Prioritas Sedang','Tier 3 - Cukup Tertangani','Tier 4 - Low Priority'];
        const stunts = ['S1 High','S2','S3','S4 Low'];
        let matrix = '<div style="display:flex; gap:24px; align-items:center; padding-top:8px; border-top:1px solid var(--rule); flex-wrap: wrap;">';
        matrix += '<div style="font-size:11px; color:var(--ink); font-weight:600;">Bivariate (Tier MBG x Stunting Tier):</div>';
        matrix += '<div style="display:inline-block;">';
        matrix += '<div style="display:grid; grid-template-columns: 100px repeat(4, 24px); gap:2px;">';
        matrix += '<div></div>';
        stunts.forEach(s => matrix += `<div style="font-size:9px; color:var(--muted); text-align:center; transform: rotate(-45deg); transform-origin: bottom; height: 30px;">${{s}}</div>`);
        tiers.forEach(t => {{
          matrix += `<div style="font-size:9px; color:var(--muted); padding-right:4px; text-align:right; align-self:center;">${{t.split(' - ')[0]}}</div>`;
          stunts.forEach(s => {{
            const c = BIVARIATE[t + '|' + s] || '#E8E8E8';
            matrix += `<div style="width:24px; height:18px; background:${{c}}; border:1px solid white;"></div>`;
          }});
        }});
        matrix += '</div></div>';
        matrix += `<div style="font-size:10px; color:var(--muted); max-width:280px; line-height:1.4;">Diagonal gelap (kiri-atas) = Tier 1 + S1 = super-priority. Diagonal terang (kanan-bawah) = Tier 4 + S4 = aman.</div>`;
        matrix += '</div>';
        html = matrix;
      }}
      el.innerHTML = html;
    }},

    // ===== Ranking =====
    recomputeFiltered() {{
      let f = this.rows.slice();
      if (this.rankFilterProv !== 'All')
        f = f.filter(r => Math.floor(r.pcode.slice(2)/100) == this.rankFilterProv ||
                          String(this.rankFilterProv).padStart(2,'0') === r.pcode.slice(2,4));
      if (this.rankFilterTier !== 'All')
        f = f.filter(r => r.tier === this.rankFilterTier);
      if (this.rankFilterQuad !== 'All')
        f = f.filter(r => r.quadrant === this.rankFilterQuad);
      if (this.rankSearch.trim()) {{
        const q = this.rankSearch.toLowerCase().trim();
        f = f.filter(r => r.nama_kab.toLowerCase().includes(q) || r.nama_prov.toLowerCase().includes(q));
      }}
      // Sort
      const k = this.rankSortKey, d = this.rankSortDir;
      f.sort((a,b) => {{
        let av = a[k], bv = b[k];
        if (av == null) av = -Infinity;
        if (bv == null) bv = -Infinity;
        if (typeof av === 'string') return d * av.localeCompare(bv);
        return d * (av - bv);
      }});
      this.filteredRows = f;
      this.rankLimit = 100; // reset
    }},
    sortBy(k) {{
      if (this.rankSortKey === k) this.rankSortDir *= -1;
      else {{ this.rankSortKey = k; this.rankSortDir = (k === 'rank' || k === 'nama_kab' || k === 'nama_prov' || k === 'tier_short') ? 1 : -1; }}
      this.recomputeFiltered();
    }},
    downloadFilteredCSV() {{
      const cols = ['rank','kode_prov','nama_prov','nama_kab','n_sppg','pop_anak','fies','sppg_10k_anak','gap_score','tier','quadrant','stunting','stunting_tier'];
      const header = ['Rank','KodeProv','Provinsi','Kabkota','N_SPPG','Pop_Anak','FIES_pct','SPPG_per_10k_anak','Gap_Score','Tier','Kuadran','Stunting_pct','Stunting_Tier'];
      const lines = [header.join(',')];
      this.filteredRows.forEach(r => {{
        const cells = cols.map(c => {{
          let v = r[c];
          if (v == null) return '';
          if (c === 'kode_prov') v = String(v).padStart(2,'0');
          if (typeof v === 'string') return '"' + v.replace(/"/g, '""') + '"';
          return v;
        }});
        lines.push(cells.join(','));
      }});
      const blob = new Blob([lines.join('\\n')], {{ type: 'text/csv' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'mbg-gap-ranking-filtered.csv';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }},

    // ===== Drilldown =====
    renderDrilldown() {{
      const sub = this.drillKabRows;
      if (!sub.length) return;
      // Sorted by gap_score desc
      const sorted = sub.slice().sort((a,b) => b.gap_score - a.gap_score);
      const traces = [{{
        x: sorted.map(r => r.gap_score),
        y: sorted.map(r => r.nama_kab),
        type: 'bar',
        orientation: 'h',
        marker: {{ color: sorted.map(r => TIER_COLORS[r.tier] || '#999') }},
        text: sorted.map(r => r.gap_score.toFixed(4)),
        textposition: 'outside',
        textfont: {{ size: 11, color: INK }},
        hovertemplate: '<b>%{{y}}</b><br>Gap Score: %{{x:.4f}}<extra></extra>',
      }}];
      const h = Math.max(360, sorted.length * 22);
      Plotly.react('chart-prov-tier', traces, {{
        margin: {{ l: 180, r: 60, t: 20, b: 50 }},
        font: {{ family: FONT, size: 12, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ title: {{ text: 'Gap Score', font: {{ size: 12, color: MUTED }} }},
                  showline: true, linecolor: INK, ticks: 'outside', gridcolor: '#EAECF0' }},
        yaxis: {{ tickfont: {{ size: 11, color: INK }}, autorange: 'reversed' }},
        height: h,
        showlegend: false,
      }}, {{ displaylogo: false, responsive: true }});
    }},
  }};
}}

// Expose for onclick from topnav (anchors outside Alpine scope)
window.gotoPage = function(id) {{
  const root = document.querySelector('[x-data]')?._x_dataStack?.[0];
  if (root && typeof root.gotoPage === 'function') root.gotoPage(id);
}};
</script>
<script>document.addEventListener('alpine:init', () => {{ /* Alpine bridge ready */ }});</script>
</body>
</html>
"""


def main():
    df = load()
    print(f"Loaded {len(df)} rows from {CSV_PHASE0.name}")

    with open(META, "r", encoding="utf-8") as f:
        meta = json.load(f)
    payload = build_payload(df, meta)
    print(f"Payload rows={len(payload['rows'])}, prov={len(payload['prov_list'])}, super-priority={len(payload['super_priority'])}")

    # Verify geojson exists at sibling location (loaded at runtime via fetch)
    if not GEOJSON.exists():
        print(f"WARNING: geojson not found at {GEOJSON}")
    else:
        with open(GEOJSON, "r", encoding="utf-8") as f:
            gj = json.load(f)
        print(f"GeoJSON sibling exists, features={len(gj['features'])} (loaded via fetch at runtime)")

    html = build_html(payload, None, date.today().isoformat())
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT.name} ({OUT.stat().st_size:,} bytes / ~{OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
