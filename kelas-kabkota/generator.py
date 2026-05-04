"""
Generator dashboard Kelas Masyarakat per Kabupaten/Kota, 2019-2025.
Input: data.csv + metadata.json + kabkota_bps_simplified.geojson (co-located).
Output: dashboard.html + kabkota_data.js (data heavy split).
McKinsey-style template, multi-page (Trend / Geografi / Detail Kabkota).
"""
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
CSV = HERE / "data.csv"
META = HERE / "metadata.json"
GEOJSON = HERE / "kabkota_bps_simplified.geojson"
OUT = HERE / "dashboard.html"
KAB_JS = HERE / "kabkota_data.js"

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
CLASSES = ["Poor", "Vulnerable", "Lower AMC", "Upper AMC",
           "Lower MC", "Middle MC", "Upper MC", "Upper Class"]
CLASS_COLORS = {
    "Poor": "#C8102E", "Vulnerable": "#EA7200", "Lower AMC": "#FFB700",
    "Upper AMC": "#FFE08A", "Lower MC": "#A9C4DF", "Middle MC": "#67B2E8",
    "Upper MC": "#2A6FB3", "Upper Class": "#003D79",
}


def load():
    df = pd.read_csv(CSV)
    df["nama_prov"] = df["nama_prov"].str.title().str.replace("Sumatera", "Sumatra", regex=False)
    df["nama_kab"] = df["nama_kab"].str.title()
    df["pcode"] = "ID" + df["kabkota_4digit"].astype(int).astype(str).str.zfill(4)
    return df


def build_payload(df):
    # Trend nasional per kelas per tahun
    nat = (df.groupby(["tahun", "kelas"])["n_individu_tertimbang"]
             .sum().reset_index())
    nat_dict = {}
    for y in YEARS:
        sub = nat[nat["tahun"] == y].set_index("kelas")["n_individu_tertimbang"]
        total = sub.sum()
        nat_dict[str(y)] = {k: round(float(sub.get(k, 0))) for k in CLASSES}
        nat_dict[str(y)]["_total"] = round(float(total))

    # Per kabkota per tahun per kelas (untuk peta + ranking)
    kab_meta = (df.groupby("pcode")
                  .agg({"nama_kab": "first", "nama_prov": "first"}).to_dict(orient="index"))

    # Build map data: {year: {kelas: {pcode: pct_kelas_dalam_kab}}}
    map_data = {}
    abs_data = {}
    for y in YEARS:
        ydf = df[df["tahun"] == y]
        map_data[str(y)] = {}
        abs_data[str(y)] = {}
        for k in CLASSES:
            sub = ydf[ydf["kelas"] == k].set_index("pcode")
            map_data[str(y)][k] = {p: round(float(sub.loc[p, "pct_kelas_dalam_kab"]), 2)
                                   for p in sub.index}
            abs_data[str(y)][k] = {p: round(float(sub.loc[p, "n_individu_tertimbang"]))
                                   for p in sub.index}

    # Untuk detail per kab: komposisi 8 kelas % per (kab, year)
    # Format: {pcode: {year: {kelas: pct}}}
    detail = {}
    for pcode, sub in df.groupby("pcode"):
        detail[pcode] = {}
        for y in YEARS:
            yr = sub[sub["tahun"] == y]
            detail[pcode][str(y)] = {row["kelas"]: round(float(row["pct_kelas_dalam_kab"]), 2)
                                     for _, row in yr.iterrows()}

    # List kabkota untuk dropdown (sorted by prov + nama)
    kab_list = sorted(
        [{"pcode": p, "nama_kab": v["nama_kab"], "nama_prov": v["nama_prov"]}
         for p, v in kab_meta.items()],
        key=lambda r: (r["nama_prov"], r["nama_kab"]),
    )

    return {
        "nat": nat_dict,
        "map": map_data,
        "abs": abs_data,
        "kab_meta": kab_meta,
        "detail": detail,
        "kab_list": kab_list,
    }


def build_html(payload, geojson, generated):
    # Hero stats
    pop_2025 = payload["nat"]["2025"]["_total"]
    pop_2019 = payload["nat"]["2019"]["_total"]
    poor_2025 = payload["nat"]["2025"]["Poor"]
    poor_2019 = payload["nat"]["2019"]["Poor"]
    poor_share_2025 = poor_2025 / pop_2025 * 100
    poor_share_2019 = poor_2019 / pop_2019 * 100
    middle_up_2025 = sum(payload["nat"]["2025"][k] for k in ["Lower MC","Middle MC","Upper MC","Upper Class"])
    middle_up_2019 = sum(payload["nat"]["2019"][k] for k in ["Lower MC","Middle MC","Upper MC","Upper Class"])
    middle_share_2025 = middle_up_2025 / pop_2025 * 100
    middle_share_2019 = middle_up_2019 / pop_2019 * 100

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kelas Masyarakat per Kabupaten/Kota, 2019-2025</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://code.iconify.design/iconify-icon/2.1.0/iconify-icon.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&display=swap" rel="stylesheet">
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
    --rule: #E5E8EC;          /* lighter than before, more refined */
    --rule-strong: #D0D5DD;
    --muted: #667085;
    --muted-soft: #98A2B3;
    --paper: #FFFFFF;
    --cream: #F8F6F0;         /* warmer cream */
    --mist: #F0F6FC;          /* lighter mist */
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
  .serif-display {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.015em; line-height: 1.08; }}
  .stat-num {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.02em; line-height: 1; }}
  .eyebrow {{ font-size: 11px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--navy); }}
  .rule-top {{ border-top: 1px solid var(--rule); }}
  .rule-bottom {{ border-bottom: 1px solid var(--rule); }}
  .hair-accent {{ border-top: 3px solid var(--sky); }}
  .ink {{ color: var(--ink); }}
  .muted {{ color: var(--muted); }}
  .num {{ font-variant-numeric: tabular-nums; }}
  .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--navy); background: var(--mist); border: 1px solid var(--sky); }}
  .badge-dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--sky); display: inline-block; }}
  .callout {{ border-left: 3px solid var(--sky); background: var(--mist); padding: 18px 24px; }}
  .callout .label {{ font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--navy); }}
  .callout .text {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 18px; line-height: 1.45; color: var(--ink); margin-top: 6px; font-weight: 500; }}
  .chart-footer {{ border-top: 1px solid var(--rule); margin-top: 16px; padding-top: 12px; display: flex; flex-wrap: wrap; gap: 24px; font-size: 11px; color: var(--muted); }}
  .chart-footer .label {{ font-weight: 600; color: var(--ink); text-transform: uppercase; letter-spacing: 0.06em; margin-right: 4px; }}
  .select-flat {{ border: 0; border-bottom: 1px solid var(--ink); background: transparent; padding: 6px 24px 6px 0; font-size: 15px; font-weight: 500; color: var(--ink); appearance: none; background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%23051C2C'%3e%3cpath fill-rule='evenodd' d='M5.23 7.21a.75.75 0 011.06.02L10 11.06l3.71-3.83a.75.75 0 111.08 1.04l-4.25 4.39a.75.75 0 01-1.08 0L5.21 8.27a.75.75 0 01.02-1.06z' clip-rule='evenodd'/%3e%3c/svg%3e"); background-repeat: no-repeat; background-position: right 0 center; background-size: 18px; }}
  .select-flat:focus {{ outline: none; border-bottom-color: var(--sky); }}

  /* Sidebar */
  .sidebar {{ position: fixed; top: 0; left: 0; bottom: 0; width: 220px; background: var(--navy); color: white; padding: 24px 0; z-index: 40; display: flex; flex-direction: column; overflow-y: auto; }}
  .sidebar .brand {{ padding: 0 24px 20px 24px; border-bottom: 1px solid rgba(255,255,255,0.12); }}
  .sidebar .brand-title {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 18px; font-weight: 600; line-height: 1.15; color: white; }}
  .sidebar .brand-sub {{ font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--sky); margin-top: 4px; font-weight: 600; }}
  .sidebar .yellow-accent {{ display: inline-block; width: 10px; height: 10px; background: var(--yellow); margin-bottom: 8px; }}
  .sidebar .nav-section {{ padding: 16px 0; }}
  .sidebar .nav-label {{ padding: 0 24px; font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(255,255,255,0.4); margin-bottom: 8px; }}
  .sidebar .nav-item {{ display: flex; align-items: center; gap: 10px; padding: 10px 24px; font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.7); border-left: 3px solid transparent; cursor: pointer; transition: all 0.15s; background: none; border-top: none; border-right: none; border-bottom: none; width: 100%; text-align: left; }}
  .sidebar .nav-item:hover {{ color: white; background: rgba(255,255,255,0.05); }}
  .sidebar .nav-item.active {{ color: white; border-left-color: var(--sky); background: rgba(103,178,232,0.1); }}
  .sidebar .nav-item iconify-icon {{ font-size: 18px; }}
  .sidebar .footer {{ margin-top: auto; padding: 16px 24px; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(255,255,255,0.4); border-top: 1px solid rgba(255,255,255,0.12); }}
  .with-sidebar {{ margin-left: 220px; }}
  .hero-band {{ background: var(--navy); color: white; }}
  .hero-band .eyebrow {{ color: var(--sky); }}
  .hero-band h1, .hero-band h2 {{ color: white; }}
  .hero-band p {{ color: rgba(255,255,255,0.78); }}

  /* Action chips */
  .chip-action {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--navy); background: white; border: 1px solid var(--rule); cursor: pointer; transition: all 0.12s; }}
  .chip-action:hover {{ background: var(--mist); border-color: var(--navy); }}
  .chip-action.active {{ background: var(--navy); color: white; border-color: var(--navy); }}
  .chip-action iconify-icon {{ font-size: 14px; }}

  .map-legend {{ display: flex; align-items: center; gap: 16px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--rule); }}
  .map-legend-label {{ font-size: 11px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }}
  .map-legend-bins {{ display: flex; align-items: center; gap: 0; flex: 1; }}
  .map-legend-bin {{ flex: 1; display: flex; flex-direction: column; gap: 4px; }}
  .map-legend-bin .swatch {{ height: 10px; }}
  .map-legend-bin .range {{ font-size: 10px; color: var(--muted); font-variant-numeric: tabular-nums; padding-top: 2px; }}

  .rank-card h4 {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 17px; font-weight: 600; color: var(--ink); margin-bottom: 4px; }}
  .rank-card .sub {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }}
  .rank-list {{ margin-top: 14px; }}
  .rank-row {{ display: grid; grid-template-columns: 28px 1fr 130px; align-items: center; gap: 16px; padding: 10px 0; border-bottom: 1px solid var(--rule); }}
  .rank-row:hover {{ background: var(--mist); }}
  .rank-row .rank-num {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 16px; font-weight: 600; color: var(--sky); text-align: right; }}
  .rank-row.is-bottom .rank-num {{ color: #C8102E; }}
  .rank-row .rank-name {{ font-size: 14px; color: var(--ink); font-weight: 500; }}
  .rank-row .rank-name .sub-prov {{ display: block; font-size: 11px; color: var(--muted); font-weight: 400; }}
  .rank-row .rank-bar-wrap {{ position: relative; height: 6px; background: var(--mist); overflow: hidden; }}
  .rank-row .rank-bar {{ position: absolute; left: 0; top: 0; height: 100%; max-width: 100%; background: var(--navy); }}
  .rank-row.is-bottom .rank-bar {{ background: #C8102E; opacity: 0.7; }}
  .rank-row .rank-val {{ font-variant-numeric: tabular-nums; font-size: 13px; font-weight: 600; color: var(--ink); margin-top: 4px; }}
  .rank-cell-right {{ display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }}
/* === DESIGN POLISH PASS === */
  /* Smooth all transitions */
  button, .chip-action, .pick-chip, .nav-item, .card, a, select, input {{ transition: all var(--tr-base); }}

  /* Card lift on hover (subtle elevation) */
  .compare-card {{ transition: all var(--tr-base); }}
  .compare-card:hover {{ box-shadow: var(--elev-3); transform: translateY(-2px); }}

  /* Refined chip */
  .chip-action {{ border-radius: 0; padding: 6px 12px; font-size: var(--fs-xs); }}
  .chip-action:active {{ transform: translateY(1px); }}

  /* Refined badge */
  .badge {{ padding: 4px 10px; }}

  /* Refined sidebar nav transition */
  .sidebar .nav-item {{ position: relative; overflow: hidden; }}
  .sidebar .nav-item::before {{ content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 0; background: var(--sky); transition: width var(--tr-base); }}
  .sidebar .nav-item:hover::before {{ width: 3px; }}
  .sidebar .nav-item.active::before {{ width: 3px; }}

  /* Better focus state — accent ring */
  *:focus-visible {{ outline: 2px solid var(--sky); outline-offset: 3px; border-radius: 1px; }}

  /* Hero band: subtle gradient depth */
  .hero-band {{ background: linear-gradient(180deg, var(--navy) 0%, #002852 100%); position: relative; }}
  .hero-band::after {{ content: ''; position: absolute; bottom: -1px; left: 0; right: 0; height: 1px; background: var(--yellow); opacity: 0.4; }}

  /* Refined eyebrow */
  .eyebrow {{ letter-spacing: 0.16em; }}

  /* Refined stat-num — more dramatic */
  .stat-num {{ font-feature-settings: 'tnum' 1, 'lnum' 1; }}

  /* Better serif rendering */
  .serif-display {{ font-feature-settings: 'liga' 1, 'kern' 1; text-rendering: optimizeLegibility; }}

  /* Rank rows — subtle alternating bg */
  .rank-row:nth-child(even) {{ background: rgba(245,247,250,0.4); }}

  /* Empty state */
  .empty-state {{ display: flex; flex-direction: column; align-items: center; justify-content: center; padding: var(--sp-8); text-align: center; color: var(--muted); }}
  .empty-state iconify-icon {{ font-size: 48px; opacity: 0.4; margin-bottom: var(--sp-3); }}
  .empty-state .title {{ font-size: var(--fs-md); color: var(--ink); font-weight: 600; margin-bottom: var(--sp-2); }}
  .empty-state .desc {{ font-size: var(--fs-sm); max-width: 280px; }}

  /* Section dividers — more refined */
  .rule-top, .rule-bottom {{ border-color: var(--rule); }}

  /* Hair accent — slimmer */
  .hair-accent {{ border-top-width: 2px; }}

  /* Footer chart — more breathing */
  .chart-footer {{ padding-top: var(--sp-4); margin-top: var(--sp-5); gap: var(--sp-5); font-size: var(--fs-xs); }}

  /* Callout — refined */
  .callout {{ border-radius: 0; padding: var(--sp-4) var(--sp-5); }}
  .callout .text {{ font-size: var(--fs-md); }}

  /* Map legend chip — more polished */
  .map-legend {{ gap: var(--sp-5); padding-top: var(--sp-4); margin-top: var(--sp-4); }}
  .map-legend-bin .swatch {{ height: 8px; border-radius: 0; }}

  /* Tab indicator smoother */
  .tab-active::after {{ transition: transform var(--tr-base); }}

  
/* === EDITORIAL CRAFT LAYER === */

  /* Folio header — running small caps (Mandiri Institute · Susenas 2025) */
  .folio {{ position: sticky; top: 0; z-index: 30; background: rgba(255,255,255,0.92); backdrop-filter: blur(8px); border-bottom: 1px solid var(--rule); padding: 8px 0; }}
  .folio-inner {{ max-width: 1280px; margin: 0 auto; padding: 0 32px; display: flex; justify-content: space-between; font-size: 10px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); }}
  .folio .left {{ color: var(--ink); }}
  .folio .right {{ color: var(--muted); }}

  /* Drop cap — 3-line initial letter */
  .drop-cap::first-letter {{ float: left; font-family: 'Source Serif 4', Georgia, serif; font-size: 64px; font-weight: 600; line-height: 0.85; padding: 4px 10px 0 0; color: var(--navy); }}

  /* Italic caption — under chart, magazine style */
  .fig-caption {{ font-family: 'Source Serif 4', Georgia, serif; font-style: italic; font-size: var(--fs-sm); color: var(--muted); margin-top: var(--sp-3); padding-top: var(--sp-3); border-top: 1px solid var(--rule); max-width: 720px; line-height: 1.5; }}
  .fig-caption .figno {{ font-style: normal; font-weight: 600; color: var(--ink); margin-right: var(--sp-2); }}

  /* Pull quote — section break dengan kutipan besar */
  .pull-quote {{ margin: var(--sp-10) auto; max-width: 800px; text-align: center; padding: var(--sp-5) 0; border-top: 2px solid var(--ink); border-bottom: 2px solid var(--ink); }}
  .pull-quote blockquote {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 28px; font-weight: 500; line-height: 1.35; color: var(--ink); letter-spacing: -0.01em; }}
  .pull-quote cite {{ display: block; font-style: normal; font-size: var(--fs-xs); font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin-top: var(--sp-3); }}

  /* Mega Mendung gradient hero — 7-layer subtle cloud */
  .hero-band-craft {{ background:
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

  /* Songket palette validation tagline */
  .heritage-tag {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; font-size: 10px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--yellow); background: rgba(255,183,0,0.08); border: 1px solid rgba(255,183,0,0.3); border-radius: 0; }}

  /* Roman numeral eyebrow */
  .eyebrow-roman {{ font-family: 'Source Serif 4', Georgia, serif; font-style: italic; font-size: var(--fs-md); font-weight: 500; letter-spacing: 0.02em; text-transform: none; color: var(--navy); }}
  .eyebrow-roman::before {{ content: ''; display: inline-block; width: 24px; height: 1px; background: var(--navy); vertical-align: middle; margin-right: 12px; }}

  /* Neurath pictogram array */
  .pictogram-array {{ display: grid; grid-template-columns: repeat(20, 1fr); gap: 2px; max-width: 400px; margin-top: var(--sp-3); }}
  .pictogram-array .person {{ aspect-ratio: 1; background: var(--navy); mask: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='black'><path d='M12 12a4 4 0 100-8 4 4 0 000 8zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z'/></svg>") center/contain no-repeat; -webkit-mask: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='black'><path d='M12 12a4 4 0 100-8 4 4 0 000 8zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z'/></svg>") center/contain no-repeat; }}
  .pictogram-array .person.muted {{ background: var(--rule-strong); }}
  .pictogram-legend {{ font-size: var(--fs-xs); color: var(--muted); margin-top: var(--sp-2); }}

  /* Tufte data-ink — chart container minimal chrome */
  .chart-tufte {{ background: white; }}

  
</style>
</head>
<body>

<div x-data="dashboard()" x-init="init()">
<aside class="sidebar">
  <div class="brand">
    <a href="../index.html" style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--sky);text-transform:uppercase;letter-spacing:0.1em;font-weight:600;text-decoration:none;margin-bottom:10px;">
      <iconify-icon icon="mdi:arrow-left"></iconify-icon><span>Beranda</span>
    </a>
    <span class="yellow-accent"></span>
    <div class="brand-title">Mandiri Institute</div>
    <div class="brand-sub">Dashboard</div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Kelas Masyarakat</div>
    <template x-for="t in tabs" :key="t.id">
      <button @click="setPage(t.id)" :class="page === t.id ? 'nav-item active' : 'nav-item'">
        <iconify-icon :icon="t.icon"></iconify-icon>
        <span x-text="t.label"></span>
      </button>
    </template>
  </div>
  <div class="footer">
    <div>514 kab/kota · 8 kelas wb4 · 2019-2025</div>
  </div>
</aside>

<div class="with-sidebar">
<div class="folio">
  <div class="folio-inner">
    <span class="left">Mandiri Institute · Kelas Kabkota</span>
    <span class="right" x-text="page.toUpperCase()"></span>
  </div>
</div>
<div class="hero-band hero-band-craft">
  <header class="max-w-[1280px] mx-auto px-8 pt-16 pb-16">
    <div class="eyebrow">Riset Mandiri Institute · Demografi Kelas</div>
    <h1 class="serif-display text-4xl md:text-5xl mt-5 max-w-4xl" x-text="pageTitle"></h1>
    <p class="mt-5 text-base max-w-3xl leading-relaxed" x-text="pageSubtitle"></p>
  </header>
</div>

<main class="max-w-[1280px] mx-auto px-8 pb-16">

  <!-- TREND -->
  <section x-show="page === 'trend'">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-10 rule-top pt-8">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Populasi 2025</div>
        <div class="stat-num text-5xl mt-3 ink">{pop_2025/1e6:.1f}<span class="text-2xl muted ml-1">jt</span></div>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Kelas Poor 2025</div>
        <div class="stat-num text-5xl mt-3" style="color:#C8102E">{poor_share_2025:.1f}<span class="text-2xl muted ml-1">%</span></div>
        <div class="text-sm muted mt-1">vs {poor_share_2019:.1f}% pada 2019</div>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Middle Up & Above 2025</div>
        <div class="stat-num text-5xl mt-3 ink" style="color:#003D79">{middle_share_2025:.1f}<span class="text-2xl muted ml-1">%</span></div>
        <div class="text-sm muted mt-1">vs {middle_share_2019:.1f}% pada 2019</div>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Cakupan</div>
        <div class="stat-num text-5xl mt-3 ink">514<span class="text-2xl muted ml-1">kab</span></div>
        <div class="text-sm muted mt-1">+ 38 prov · 8 kelas</div>
      </div>
    </div>
    <div class="mt-16">
      <span class="badge"><span class="badge-dot"></span>Populasi Tertimbang Nasional</span>
      <div class="eyebrow-roman mt-3">I. Trend</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl">Pergeseran kelas: Poor turun, Middle Class naik.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Distribusi 8 kelas masyarakat (wb4) Indonesia, populasi tertimbang Susenas 2019-2025.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div class="mb-3 mt-2 flex gap-2">
        <button class="chip-action" :class="trendMode==='abs' ? 'active' : ''" @click="trendMode='abs'; renderTrend()">Absolut (juta)</button>
        <button class="chip-action" :class="trendMode==='share' ? 'active' : ''" @click="trendMode='share'; renderTrend()">Share (%)</button>
      </div>
      <div id="chart-trend" style="height:520px;"></div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas Maret BPS · klasifikasi wb4 Mandiri Institute</span>
        <span><span class="label">Bobot</span>fwt (individu)</span>
      </div>
    </div>
  </section>

  <!-- GEOGRAFI -->
  <section x-show="page === 'geografi'">
    <!-- Unified filter row -->
    <div class="rule-top pt-8 flex flex-wrap items-end gap-6">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Tahun</div>
        <select x-model="year" @change="renderMap()" class="select-flat mt-2" style="min-width:90px;">
          <template x-for="y in years" :key="'gy'+y"><option :value="y" x-text="y"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Kelas</div>
        <select x-model="mapKelas" @change="renderMap()" class="select-flat mt-2" style="min-width:140px;">
          <template x-for="k in classes" :key="'mk'+k"><option :value="k" x-text="k"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Wilayah</div>
        <select x-model="wilayah" @change="onWilayahChange()" class="select-flat mt-2" style="min-width:170px;">
          <template x-for="w in wilayahList" :key="'w'+w"><option :value="w" x-text="w"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Provinsi</div>
        <select x-model="provFilter" @change="renderMap()" class="select-flat mt-2" style="min-width:170px;">
          <option value="All">Semua provinsi</option>
          <template x-for="p in provOptions" :key="'po'+p.pcode"><option :value="p.pcode" x-text="p.nama"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Tampilan</div>
        <div class="mt-2 flex gap-2">
          <button class="chip-action" :class="mapMode==='pct' ? 'active' : ''" @click="mapMode='pct'; renderMap()">Share (%)</button>
          <button class="chip-action" :class="mapMode==='abs' ? 'active' : ''" @click="mapMode='abs'; renderMap()">Jumlah</button>
        </div>
      </div>
      <div style="margin-left:auto">
        <button class="chip-action" @click="exportPPT('chart-map', 'Konsentrasi kelas ' + mapKelas + ' per kabupaten/kota', 'Tahun ' + year + ' · Susenas BPS')" style="background:var(--yellow);color:var(--ink);border-color:var(--yellow);font-weight:700;">
          <iconify-icon icon="mdi:presentation"></iconify-icon>Export PPT
        </button>
      </div>
    </div>
    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>514 Kabupaten/Kota</span>
      <div class="eyebrow-roman mt-3">II. Geografi</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl" x-text="'Konsentrasi kelas ' + mapKelas + ' per kabupaten/kota.'"></h2>
      <p class="mt-3 muted text-base max-w-3xl">Peta 514 kab/kota (BPS 2020). Kabkot pemekaran ditampilkan berdasarkan kode terdekat.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div id="chart-map" style="height:780px;"></div>
      <div class="map-legend">
        <div class="map-legend-label" x-text="mapMode==='pct' ? 'Share kelas dalam kab (%)' : 'Jumlah individu tertimbang'"></div>
        <div class="map-legend-bins" id="legend-geografi"></div>
      </div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas BPS · Shapefile BPS adm2 2020</span>
        <span><span class="label">Catatan</span>540 kab di data, 522 di shapefile (perbedaan pemekaran 2020+)</span>
      </div>

      <!-- Top/Bottom 10 kabkota per kelas -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-16 mt-12 rule-top pt-10">
        <div class="rank-card">
          <div class="sub">Top 10 Kab/Kota</div>
          <h4 x-text="'Konsentrasi tertinggi: ' + mapKelas"></h4>
          <div class="rank-list">
            <template x-for="(r, i) in rankTop" :key="'t'+r.pcode">
              <div class="rank-row">
                <div class="rank-num" x-text="i+1"></div>
                <div class="rank-name">
                  <span x-text="r.nama_kab"></span>
                  <span class="sub-prov" x-text="r.nama_prov"></span>
                </div>
                <div class="rank-cell-right">
                  <div class="rank-bar-wrap" style="width: 110px;">
                    <div class="rank-bar" :style="'width: '+(r.value/rankMax*100)+'%'"></div>
                  </div>
                  <div class="rank-val" x-text="formatVal(r.value)"></div>
                </div>
              </div>
            </template>
          </div>
        </div>
        <div class="rank-card">
          <div class="sub">Bottom 10 Kab/Kota</div>
          <h4 x-text="'Konsentrasi terendah: ' + mapKelas"></h4>
          <div class="rank-list">
            <template x-for="(r, i) in rankBottom" :key="'b'+r.pcode">
              <div class="rank-row is-bottom">
                <div class="rank-num" x-text="i+1"></div>
                <div class="rank-name">
                  <span x-text="r.nama_kab"></span>
                  <span class="sub-prov" x-text="r.nama_prov"></span>
                </div>
                <div class="rank-cell-right">
                  <div class="rank-bar-wrap" style="width: 110px;">
                    <div class="rank-bar" :style="'width: '+(r.value/rankMax*100)+'%'"></div>
                  </div>
                  <div class="rank-val" x-text="formatVal(r.value)"></div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- DETAIL KABKOTA -->
  <section x-show="page === 'detail'">
    <!-- Cascading filter: provinsi dulu → kab/kota -->
    <div class="rule-top pt-8 flex flex-wrap items-end gap-6">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Provinsi</div>
        <select x-model="detailProv" @change="onDetailProvChange()" class="select-flat mt-2" style="min-width:200px;">
          <template x-for="p in detailProvList" :key="'dpl'+p.pcode">
            <option :value="p.pcode" x-text="p.nama"></option>
          </template>
        </select>
      </div>
      <div class="flex-1 min-w-[260px]">
        <div class="eyebrow" style="color: var(--muted);">Kabupaten/Kota</div>
        <select x-model="detailPcode" @change="renderDetail()" class="select-flat mt-2 w-full">
          <template x-for="k in detailKabOptions" :key="'dkl'+k.pcode">
            <option :value="k.pcode" x-text="k.nama_kab"></option>
          </template>
        </select>
      </div>
    </div>
    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>Profil Kabupaten/Kota</span>
      <div class="eyebrow-roman mt-3">III. Detail Kab</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl">
        <span x-text="'Komposisi kelas masyarakat: ' + (kabMeta(detailPcode).nama_kab || detailPcode) + '.'"></span>
      </h2>
      <p class="mt-3 muted text-base max-w-3xl"><span x-text="kabMeta(detailPcode).nama_prov"></span> · tren 2019-2025</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div id="chart-detail" style="height:560px;"></div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas BPS, weighted</span>
        <span><span class="label">Total</span>tiap tahun = 100% per kab</span>
      </div>
    </div>
  </section>

  <!-- INEQUALITY -->
  <section x-show="page === 'inequality'">
    <div class="rule-top pt-8 flex flex-wrap items-end gap-6">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Tahun</div>
        <select x-model="year" @change="renderInequality()" class="select-flat mt-2" style="min-width:90px;">
          <template x-for="y in years" :key="'iy'+y"><option :value="y" x-text="y"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Cakupan</div>
        <select x-model="ineqScope" @change="renderInequality()" class="select-flat mt-2" style="min-width:200px;">
          <option value="nasional">Nasional</option>
          <template x-for="p in ineqProvList" :key="'ip'+p.pcode"><option :value="p.pcode" x-text="p.nama"></option></template>
        </select>
      </div>
    </div>
    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>Inequality Visualization</span>
      <div class="eyebrow-roman mt-3">IV. Inequality</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl">Kurva Lorenz & koefisien Gini.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Distribusi kumulatif populasi (X) terhadap kumulatif "wealth proxy" (Y, kelas-weighted). Kurva diagonal = perfect equality. Semakin jauh kurva turun ke kanan-bawah, semakin tinggi inequality (Gini ↑).</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-12 mt-2">
        <div class="md:col-span-2">
          <div id="chart-lorenz" style="height:540px;"></div>
        </div>
        <div>
          <div class="eyebrow" style="color: var(--muted);">Gini Coefficient</div>
          <div class="stat-num" style="font-size:96px;color:var(--navy);line-height:1;margin-top:8px;" x-text="ineqGini"></div>
          <div class="text-sm muted mt-3" x-text="ineqGiniLabel"></div>
          <div class="mt-8">
            <div class="eyebrow" style="color: var(--muted);">Interpretasi</div>
            <ul class="mt-3 text-sm" style="line-height:1.6;color:var(--ink)">
              <li>0.0 - 0.3: Setara relatif</li>
              <li>0.3 - 0.4: Inequality moderat</li>
              <li>0.4 - 0.5: Inequality tinggi</li>
              <li>&gt; 0.5: Inequality ekstrim</li>
            </ul>
          </div>
          <div class="mt-8">
            <div class="eyebrow" style="color: var(--muted);">Cakupan</div>
            <div class="text-sm mt-2 ink" x-text="ineqScopeLabel"></div>
          </div>
        </div>
      </div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas BPS · pop tertimbang</span>
        <span><span class="label">Proksi kekayaan</span>bobot kelas (1-8) sebagai urutan pendapatan</span>
        <span><span class="label">Method</span>Trapezoid Gini = 1 - 2 × area di bawah Lorenz</span>
      </div>
    </div>
  </section>

  <footer class="rule-top mt-16 pt-8 pb-4 flex items-center justify-between text-xs muted uppercase tracking-widest">
    <div>Mandiri Institute · Dashboard</div>
    <div>Generated {generated}</div>
    <div>Palette: Mandiri Official</div>
  </footer>
</main>
</div>
</div>

<script>
const PAYLOAD_LIGHT = {{
  nat: {json.dumps(payload['nat'])},
  kab_meta: {json.dumps(payload['kab_meta'])},
  kab_list: {json.dumps(payload['kab_list'])},
}};
const GEOJSON = {json.dumps(geojson)};
const CLASSES = {json.dumps(CLASSES)};
const CLASS_COLORS = {json.dumps(CLASS_COLORS)};
const YEARS = {json.dumps([str(y) for y in YEARS])};
const FONT = 'Inter, sans-serif';
const INK = '#051C2C';
const MUTED = '#667085';

const REGION_PROVS = {{
  'Indonesia':          null,
  'Sumatra':            ['11','12','13','14','15','16','17','18','19','21'],
  'Jawa':               ['31','32','33','34','35','36'],
  'Bali-Nusa Tenggara': ['51','52','53'],
  'Kalimantan':         ['61','62','63','64','65'],
  'Sulawesi':           ['71','72','73','74','75','76'],
  'Maluku-Papua':       ['81','82','91','92','94','95','96','97'],
}};
// Kabkota pcode format: ID1101 (4 digit). Prov code = char 2-4 (ID + 2 digit).
function pcodeProvCode(pcode) {{ return pcode.slice(2, 4); }}
function inRegion(pcode, wilayah, prov) {{
  const pc = pcodeProvCode(pcode);
  if (prov && prov !== 'All') return pc === prov;
  if (!wilayah || wilayah === 'Indonesia') return true;
  return REGION_PROVS[wilayah].includes(pc);
}}
// Kab outlier (kepulauan / island districts) yang bikin bbox melebar
// Di-exclude dari PETA, tetap dipertahankan di RANKING
const MAP_OUTLIER_KABS = new Set(['ID3101']); // Kep Seribu DKI Jakarta
function filteredGeojson(allowedSet) {{
  return {{ type: 'FeatureCollection',
    features: GEOJSON.features.filter(f => allowedSet.has(f.id) && !MAP_OUTLIER_KABS.has(f.id)) }};
}}
// Compute bbox from polygon dominant area (exclude outlier seperti Kep Seribu)
// Tight bbox via percentile clipping (trim 2.5% outlier coords; handle Kep Seribu jenis kasus)
function tightBbox(features) {{
  if (!features.length) return null;
  const lons = [], lats = [];
  features.forEach(f => {{
    function walk(c) {{
      if (typeof c[0] === 'number') {{ lons.push(c[0]); lats.push(c[1]); }}
      else c.forEach(walk);
    }}
    walk(f.geometry.coordinates);
  }});
  if (!lons.length) return null;
  lons.sort((a,b) => a-b);
  lats.sort((a,b) => a-b);
  const pct = (arr, p) => arr[Math.min(Math.max(Math.floor(arr.length * p), 0), arr.length-1)];
  // 2.5% / 97.5% percentile clip — points outlier (Kep Seribu) terpotong
  const minLon = pct(lons, 0.025), maxLon = pct(lons, 0.975);
  const minLat = pct(lats, 0.025), maxLat = pct(lats, 0.975);
  const dLon = Math.max((maxLon-minLon) * 0.08, 0.05);
  const dLat = Math.max((maxLat-minLat) * 0.08, 0.05);
  return {{ lon: [minLon-dLon, maxLon+dLon], lat: [minLat-dLat, maxLat+dLat] }};
}}

const TABS = [
  {{ id: 'trend',    label: 'Trend',    icon: 'mdi:trending-up' }},
  {{ id: 'geografi', label: 'Geografi', icon: 'mdi:map-outline' }},
  {{ id: 'detail',   label: 'Detail Kab', icon: 'mdi:city-variant-outline' }},
  {{ id: 'inequality', label: 'Inequality', icon: 'mdi:chart-bell-curve' }},
];
const PAGE_META = {{
  trend:    {{ title: 'Distribusi 8 kelas masyarakat Indonesia, 2019-2025.',
              sub: 'Pergeseran populasi tertimbang antar kelas wb4: dari Poor sampai Upper Class.' }},
  geografi: {{ title: 'Konsentrasi kelas masyarakat per kabupaten/kota.',
              sub: 'Choropleth 514 kab/kota (BPS 2020). Filter kelas + tahun untuk lihat sebaran geografis.' }},
  detail:   {{ title: 'Profil komposisi kelas per kabupaten/kota.',
              sub: 'Pilih kab/kota untuk lihat tren komposisi 8 kelas dari tahun ke tahun.' }},
  inequality: {{ title: 'Ketimpangan: kurva Lorenz & koefisien Gini.',
              sub: 'Distribusi kelas divisualisasi via kurva Lorenz. Gini = ukuran ketimpangan (0 = setara, 1 = ekstrim).' }},
}};

function computeBins(values) {{
  const sorted = values.filter(v => v != null && !isNaN(v)).slice().sort((a, b) => a - b);
  if (sorted.length === 0) return {{ edges: [0,0,0,0,0,1] }};
  const q = (p) => sorted[Math.min(Math.floor(p * (sorted.length - 1)), sorted.length - 1)];
  return {{ edges: [sorted[0], q(0.2), q(0.4), q(0.6), q(0.8), sorted[sorted.length - 1]] }};
}}
function fmtPct(v) {{ return v.toFixed(1) + '%'; }}
function fmtNum(v) {{
  if (v >= 1000000) return (v/1000000).toFixed(2) + ' jt';
  if (v >= 1000) return (v/1000).toFixed(0) + ' rb';
  return Math.round(v).toString();
}}

function dashboard() {{
  return {{
    tabs: TABS, page: 'trend',
    years: YEARS, year: '2025', classes: CLASSES,
    trendMode: 'share',
    mapKelas: 'Poor', mapMode: 'pct',
    wilayah: 'Indonesia', wilayahList: Object.keys(REGION_PROVS), provFilter: 'All',
    rankTop: [], rankBottom: [],
    detailPcode: PAYLOAD_LIGHT.kab_list[0]?.pcode || '',
    detailProv: pcodeProvCode(PAYLOAD_LIGHT.kab_list[0]?.pcode || 'ID11'),
    kabList: PAYLOAD_LIGHT.kab_list,
    get detailProvList() {{
      // Semua prov unik dari kab_meta, sorted by name
      const provMap = {{}};
      Object.entries(PAYLOAD_LIGHT.kab_meta).forEach(([p, m]) => {{
        const pc = pcodeProvCode(p);
        if (!provMap[pc]) provMap[pc] = m.nama_prov;
      }});
      return Object.entries(provMap).sort((a,b) => a[1].localeCompare(b[1])).map(([pc, n]) => ({{ pcode: pc, nama: n }}));
    }},
    get detailKabOptions() {{
      // Filter kab_list ke prov terpilih
      return PAYLOAD_LIGHT.kab_list.filter(k => pcodeProvCode(k.pcode) === this.detailProv);
    }},
    onDetailProvChange() {{
      const opts = this.detailKabOptions;
      if (opts.length) this.detailPcode = opts[0].pcode;
      this.renderDetail();
    }},
    // ----- Inequality (Lorenz + Gini) -----
    ineqScope: 'nasional',
    ineqGini: '-',
    ineqGiniLabel: '',
    ineqScopeLabel: 'Indonesia (semua kab/kota)',
    get ineqProvList() {{
      const provMap = {{}};
      Object.entries(PAYLOAD_LIGHT.kab_meta).forEach(([p, m]) => {{
        const pc = pcodeProvCode(p);
        if (!provMap[pc]) provMap[pc] = m.nama_prov;
      }});
      return Object.entries(provMap).sort((a,b) => a[1].localeCompare(b[1])).map(([pc, n]) => ({{ pcode: pc, nama: n }}));
    }},
    renderInequality() {{
      // Compute Lorenz curve + Gini dari distribusi 8 kelas
      // Wealth proxy: kelas index (1=Poor → 8=Upper Class)
      // Per scope: aggregate populasi per kelas, urutkan ascending kelas, build cum dist
      const yearKey = String(this.year);
      const natData = PAYLOAD_LIGHT.nat[yearKey] || {{}};

      let popPerKelas = {{}};
      if (this.ineqScope === 'nasional') {{
        CLASSES.forEach(k => {{ popPerKelas[k] = natData[k] || 0; }});
        this.ineqScopeLabel = 'Indonesia (semua kab/kota)';
      }} else {{
        // Aggregate kabs in scope prov
        const data = window.KABKOTA_DATA;
        const absSlice = (data?.abs?.[yearKey] || {{}});
        CLASSES.forEach(k => {{
          const kSlice = absSlice[k] || {{}};
          let sum = 0;
          Object.entries(kSlice).forEach(([p, v]) => {{
            if (pcodeProvCode(p) === this.ineqScope) sum += v;
          }});
          popPerKelas[k] = sum;
        }});
        const provName = (this.ineqProvList.find(p => p.pcode === this.ineqScope) || {{}}).nama || this.ineqScope;
        this.ineqScopeLabel = provName + ' (semua kab di prov)';
      }}

      // Build cumulative pop & cum wealth
      // Treat kelas index as wealth weight: Poor=1, Vulnerable=2, ..., Upper Class=8
      const sorted = CLASSES.map((k, i) => ({{ kelas: k, weight: i+1, pop: popPerKelas[k] }}));
      const totalPop = sorted.reduce((s, x) => s + x.pop, 0) || 1;
      const totalWealth = sorted.reduce((s, x) => s + x.pop * x.weight, 0) || 1;
      let cumPop = 0, cumWealth = 0;
      const points = [{{ x: 0, y: 0 }}];
      sorted.forEach(x => {{
        cumPop += x.pop;
        cumWealth += x.pop * x.weight;
        points.push({{ x: cumPop / totalPop, y: cumWealth / totalWealth }});
      }});

      // Gini = 1 - 2 × trapezoidal area di bawah Lorenz
      let area = 0;
      for (let i = 1; i < points.length; i++) {{
        area += (points[i].x - points[i-1].x) * (points[i].y + points[i-1].y) / 2;
      }}
      const gini = 1 - 2 * area;
      this.ineqGini = gini.toFixed(3);
      this.ineqGiniLabel = gini < 0.3 ? 'Setara relatif' : gini < 0.4 ? 'Inequality moderat' : gini < 0.5 ? 'Inequality tinggi' : 'Inequality ekstrim';

      Plotly.react('chart-lorenz', [
        // Equality line
        {{ x: [0, 1], y: [0, 1], type: 'scatter', mode: 'lines',
           line: {{ color: '#B6B8BA', width: 1.5, dash: 'dash' }}, name: 'Garis kesetaraan sempurna' }},
        // Lorenz curve
        {{ x: points.map(p => p.x), y: points.map(p => p.y), type: 'scatter', mode: 'lines+markers',
           line: {{ color: '#003D79', width: 3 }}, marker: {{ size: 6, color: '#003D79' }},
           fill: 'tonexty', fillcolor: 'rgba(0,61,121,0.08)',
           name: 'Kurva Lorenz',
           hovertemplate: 'Cum pop: %{{x:.1%}}<br>Cum wealth: %{{y:.1%}}<extra></extra>' }},
      ], {{
        margin: {{ l: 60, r: 30, t: 30, b: 60 }},
        font: {{ family: FONT, size: 13, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ title: 'Kumulatif populasi (%)', range: [0, 1], tickformat: '.0%', showline: true, linecolor: INK, ticks: 'outside' }},
        yaxis: {{ title: 'Kumulatif kekayaan (%)', range: [0, 1], tickformat: '.0%', gridcolor: '#EAECF0' }},
        legend: {{ orientation: 'h', y: -0.18, x: 0, xanchor: 'left' }},
      }}, {{ displaylogo: false, responsive: true }});
    }},
    get pageTitle() {{ return PAGE_META[this.page].title; }},
    get pageSubtitle() {{ return PAGE_META[this.page].sub; }},
    get rankMax() {{ return this.rankTop.length ? this.rankTop[0].value : 1; }},
    get provOptions() {{
      // Dedup prov dari kab_meta. pcode kab = ID + 4 digit, prov code = digit 1-2.
      const codes = REGION_PROVS[this.wilayah];
      const provMap = {{}};
      Object.entries(PAYLOAD_LIGHT.kab_meta).forEach(([p, m]) => {{
        const pc = pcodeProvCode(p);
        if (!provMap[pc] && (!codes || codes.includes(pc))) provMap[pc] = m.nama_prov;
      }});
      return Object.entries(provMap).sort((a,b) => a[1].localeCompare(b[1])).map(([pc, n]) => ({{ pcode: pc, nama: n }}));
    }},
    onWilayahChange() {{ this.provFilter = 'All'; this.renderMap(); }},
    kabMeta(p) {{ return PAYLOAD_LIGHT.kab_meta[p] || {{}}; }},
    formatVal(v) {{ return this.mapMode === 'pct' ? fmtPct(v) : fmtNum(v); }},
    // ----- PPT-ready PNG export with Mandiri branding -----
    exportPPT(divId, title, subtitle) {{
      const W = 1920, H = 1080;
      const canvas = document.createElement('canvas');
      canvas.width = W; canvas.height = H;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = '#003D79';
      ctx.fillRect(0, 0, W, 6);
      ctx.fillStyle = '#051C2C';
      ctx.font = "600 36px 'Source Serif 4', Georgia, serif";
      ctx.fillText(title || 'Mandiri Institute Dashboard', 60, 90);
      ctx.font = "400 18px 'Inter', sans-serif";
      ctx.fillStyle = '#667085';
      ctx.fillText(subtitle || '', 60, 125);
      Plotly.toImage(divId, {{ format: 'png', width: 1700, height: 800, scale: 2 }})
        .then(url => {{
          const img = new Image();
          img.onload = () => {{
            ctx.drawImage(img, 110, 160, 1700, 800);
            ctx.fillStyle = '#667085';
            ctx.font = "400 14px 'Inter', sans-serif";
            const src = 'Sumber: Susenas Maret BPS · Mandiri Institute · ' + new Date().toISOString().slice(0,10);
            ctx.fillText(src, 60, H - 30);
            const logo = new Image();
            const self = this;
            logo.onload = () => {{
              const lh = 60, lw = logo.width * (lh / logo.height);
              ctx.drawImage(logo, W - lw - 60, H - lh - 20, lw, lh);
              self._downloadCanvas(canvas, self.page + '-Mandiri-Institute.png');
            }};
            logo.onerror = () => self._downloadCanvas(canvas, self.page + '.png');
            const depth = window.location.pathname.includes('/thematic/') ? '../../_assets' : '../_assets';
            logo.src = depth + '/logo/mandiri-institute-color.jpg';
          }};
          img.src = url;
        }});
    }},
    _downloadCanvas(canvas, filename) {{
      canvas.toBlob(blob => {{
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = filename;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }}, 'image/png');
    }},
    init() {{
      this.$nextTick(() => this.renderForPage(this.page));
    }},
    setPage(id) {{
      this.page = id;
      this.renderForPage(id);
    }},
    renderForPage(id) {{
      requestAnimationFrame(() => requestAnimationFrame(() => {{
        if (id === 'trend') this.renderTrend();
        else if (id === 'geografi') this.renderMap();
        else if (id === 'detail') this.renderDetail();
        else if (id === 'inequality') this.renderInequality();
      }}));
    }},
    renderTrend() {{
      const traces = CLASSES.map(k => ({{
        x: YEARS.map(y => +y),
        y: YEARS.map(y => {{
          const v = PAYLOAD_LIGHT.nat[y][k];
          if (this.trendMode === 'share') return v / PAYLOAD_LIGHT.nat[y]._total * 100;
          return v / 1e6;
        }}),
        name: k, type: this.trendMode === 'share' ? 'bar' : 'scatter',
        mode: 'lines+markers',
        marker: {{ color: CLASS_COLORS[k], size: 8 }},
        line: {{ color: CLASS_COLORS[k], width: 2.5 }},
        hovertemplate: this.trendMode === 'share'
          ? '%{{x}}<br>' + k + ': %{{y:.1f}}%<extra></extra>'
          : '%{{x}}<br>' + k + ': %{{y:.2f}} juta<extra></extra>',
      }}));
      Plotly.react('chart-trend', traces, {{
        barmode: this.trendMode === 'share' ? 'stack' : undefined,
        bargap: 0.45,
        margin: {{ l: 70, r: 30, t: 20, b: 80 }},
        font: {{ family: FONT, size: 13, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ tickfont: {{ size: 14, color: INK }}, showline: true, linecolor: INK, ticks: 'outside', tickcolor: INK, ticklen: 4 }},
        yaxis: {{ title: {{ text: this.trendMode === 'share' ? 'Share (%)' : 'Populasi (juta)', font: {{ size: 12, color: MUTED }} }},
                 tickfont: {{ size: 12, color: MUTED }}, gridcolor: '#EAECF0' }},
        legend: {{ orientation: 'h', y: -0.18, x: 0, xanchor: 'left', font: {{ size: 12 }} }},
      }}, {{ displaylogo: false, responsive: true }});
    }},
    renderMap() {{
      const data = window.KABKOTA_DATA;
      if (!data) return;
      const sliceFull = (data[this.mapMode][this.year] || {{}})[this.mapKelas] || {{}};
      const slice = {{}};
      // Exclude outlier kabs (Kep Seribu) dari peta — tetap di ranking
      Object.keys(sliceFull).forEach(p => {{
        if (inRegion(p, this.wilayah, this.provFilter) && !MAP_OUTLIER_KABS.has(p)) slice[p] = sliceFull[p];
      }});
      const locs = Object.keys(slice);
      const vals = locs.map(p => slice[p]);
      const allowedSet = new Set(locs);
      const filteredGJ = filteredGeojson(allowedSet);

      // BASE layer: SEMUA kab di scope (termasuk yang tidak punya data) → render abu-abu
      const baseFeatures = GEOJSON.features.filter(f =>
        inRegion(f.id, this.wilayah, this.provFilter) && !MAP_OUTLIER_KABS.has(f.id));
      const baseGJ = {{ type: 'FeatureCollection', features: baseFeatures }};
      const baseLocs = baseFeatures.map(f => f.id);
      const noDataLocs = baseLocs.filter(p => !(p in slice));
      const bins = computeBins(vals);
      const palette = this.mapKelas === 'Poor'
        ? ['#FFEEEE','#FFCCCC','#FF8888','#E63950','#C8102E']
        : ['#E8EFF6','#A9C4DF','#67B2E8','#2A6FB3','#003D79'];
      const colorscale = [
        [0.0, palette[0]], [0.2-1e-9, palette[0]],
        [0.2, palette[1]], [0.4-1e-9, palette[1]],
        [0.4, palette[2]], [0.6-1e-9, palette[2]],
        [0.6, palette[3]], [0.8-1e-9, palette[3]],
        [0.8, palette[4]], [1.0, palette[4]],
      ];
      const hovertext = locs.map(p => {{
        const m = PAYLOAD_LIGHT.kab_meta[p] || {{}};
        const v = slice[p];
        return `<b>${{m.nama_kab || p}}</b><br><span style="color:#667085">${{m.nama_prov || ''}}</span><br>` +
               `<span style="color:#003D79;font-size:18px;font-weight:600">${{this.formatVal(v)}}</span><br>` +
               `<span style="color:#667085">Kelas ${{this.mapKelas}} · ${{this.year}}</span>`;
      }});
      // Border tipis & adaptive: makin sedikit polygon (zoom-in), makin tipis biar gak dominan
      const borderWidth = locs.length < 50 ? 0.4 : (locs.length < 200 ? 0.3 : 0.2);
      // No-data hover text
      const noDataHover = noDataLocs.map(p => {{
        const m = PAYLOAD_LIGHT.kab_meta[p] || {{}};
        return `<b>${{m.nama_kab || p}}</b><br><span style="color:#667085">${{m.nama_prov || ''}}</span><br>` +
               `<span style="color:#667085">No data untuk Kelas ${{this.mapKelas}} · ${{this.year}}</span>`;
      }});

      Plotly.react('chart-map', [
        // BASE layer: kab tanpa data → fill abu-abu muda
        noDataLocs.length ? {{
          type: 'choropleth', geojson: baseGJ, locations: noDataLocs, z: noDataLocs.map(_ => 0),
          featureidkey: 'properties.ADM2_PCODE',
          colorscale: [[0, '#E8E8E8'], [1, '#E8E8E8']],
          showscale: false,
          marker: {{ line: {{ color: '#FFFFFF', width: borderWidth }} }},
          hovertext: noDataHover, hovertemplate: '%{{hovertext}}<extra></extra>',
          hoverlabel: {{ bgcolor: 'white', bordercolor: '#999', font: {{ family: FONT, size: 13, color: INK }}, align: 'left', namelength: -1 }},
        }} : null,
        // DATA layer: kab dengan data → warna quintile
        {{
          type: 'choropleth', geojson: filteredGJ, locations: locs, z: vals,
          featureidkey: 'properties.ADM2_PCODE',
          zmin: bins.edges[0], zmax: bins.edges[5],
          colorscale, showscale: false,
          marker: {{ line: {{ color: '#FFFFFF', width: borderWidth }} }},
          hovertext, hovertemplate: '%{{hovertext}}<extra></extra>',
          hoverlabel: {{ bgcolor: 'white', bordercolor: '#003D79', font: {{ family: FONT, size: 13, color: INK }}, align: 'left', namelength: -1 }},
        }}
      ].filter(t => t), {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        font: {{ family: FONT, color: INK }},
        geo: (() => {{
          const bbox = tightBbox(baseGJ.features);
          return {{ visible: false, bgcolor: '#FAFBFC', projection: {{ type: 'mercator' }},
                   ...(bbox ? {{ lonaxis: {{ range: bbox.lon, autorange: false }},
                                 lataxis: {{ range: bbox.lat, autorange: false }} }}
                            : {{ fitbounds: 'locations' }}),
                   uirevision: this.wilayah + '|' + this.provFilter + '|' + this.mapMode }};
        }})(),
        paper_bgcolor: 'transparent',
      }}, {{ displaylogo: false, responsive: true }});

      // Legend
      const el = document.getElementById('legend-geografi');
      if (el) {{
        el.innerHTML = palette.map((c, i) => {{
          const lo = bins.edges[i];
          return `<div class="map-legend-bin"><div class="swatch" style="background:${{c}}"></div><div class="range">${{this.formatVal(lo)}}${{i===4?'+':''}}</div></div>`;
        }}).join('');
      }}

      // Ranking — filter null/undefined dulu biar sort tidak NaN
      const ranked = locs.map(p => {{
        const m = PAYLOAD_LIGHT.kab_meta[p] || {{}};
        const raw = slice[p];
        const v = (raw == null || isNaN(raw)) ? null : Number(raw);
        return {{ pcode: p, nama_kab: m.nama_kab || p, nama_prov: m.nama_prov || '', value: v }};
      }}).filter(r => r.value !== null)
         .sort((a,b) => b.value - a.value);
      this.rankTop = ranked.slice(0, 10);
      this.rankBottom = ranked.slice().sort((a,b) => a.value - b.value).slice(0, 10);
    }},
    renderDetail() {{
      const data = window.KABKOTA_DETAIL || {{}};
      const d = data[this.detailPcode] || {{}};
      const traces = CLASSES.map(k => ({{
        x: YEARS.map(y => +y),
        y: YEARS.map(y => (d[y] && d[y][k]) || 0),
        name: k, type: 'bar',
        marker: {{ color: CLASS_COLORS[k] }},
        hovertemplate: '%{{x}}<br>' + k + ': %{{y:.1f}}%<extra></extra>',
      }}));
      Plotly.react('chart-detail', traces, {{
        barmode: 'stack', bargap: 0.45,
        margin: {{ l: 60, r: 30, t: 20, b: 80 }},
        font: {{ family: FONT, size: 13, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ tickfont: {{ size: 14, color: INK }}, showline: true, linecolor: INK, ticks: 'outside', tickcolor: INK, ticklen: 4 }},
        yaxis: {{ title: {{ text: 'Share (%)', font: {{ size: 12, color: MUTED }} }},
                 tickfont: {{ size: 12, color: MUTED }}, gridcolor: '#EAECF0', range: [0, 100] }},
        legend: {{ orientation: 'h', y: -0.18, x: 0, xanchor: 'left', font: {{ size: 12 }} }},
      }}, {{ displaylogo: false, responsive: true }});
    }},
  }};
}}
</script>
<script src="kabkota_data.js"></script>
</body>
</html>
"""


def main():
    df = load()
    payload = build_payload(df)

    # Heavy data ke file JS terpisah
    heavy = (
        f"window.KABKOTA_DATA = {{ pct: {json.dumps(payload['map'], separators=(',',':'))}, "
        f"abs: {json.dumps(payload['abs'], separators=(',',':'))} }};\n"
        f"window.KABKOTA_DETAIL = {json.dumps(payload['detail'], separators=(',',':'))};\n"
    )
    KAB_JS.write_text(heavy, encoding="utf-8")
    print(f"Wrote {KAB_JS.name} ({KAB_JS.stat().st_size:,} bytes)")

    with open(GEOJSON, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    html = build_html(payload, geojson, date.today().isoformat())
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT.name} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
