"""
Generator Thematic Dashboard: BBM (Konsumsi BBM per Kelas Masyarakat).
Template terbaru: sticky sidebar + hero band + McKinsey style.
Pages: Trend / Per Kelas / Geografi.
"""
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
CSV = HERE / "bbm_provinsi_kelas_stata.csv"
GEOJSON = HERE / "provinsi_bps_simplified.geojson"
OUT = HERE / "dashboard.html"

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
CLASSES = ["Poor", "Vulnerable", "Lower AMC", "Upper AMC",
           "Lower MC", "Middle MC", "Upper MC", "Upper Class"]
FUELS = ["Tidak beli", "Premium", "Pertalite", "Pertamax", "Pertamax Turbo"]
FUEL_COLORS = {
    "Tidak beli": "#B6B8BA",
    "Premium": "#EA7200",
    "Pertalite": "#FFB700",
    "Pertamax": "#67B2E8",
    "Pertamax Turbo": "#003D79",
}
PEMEKARAN_MAP = {92: 94, 95: 91, 96: 91, 97: 91}


def load():
    df = pd.read_csv(CSV)
    df["nama_prov"] = df["nama_prov"].str.title().str.replace("Sumatera", "Sumatra", regex=False)
    return df


def build_payload(df):
    # 38 prov asli untuk ranking; 34 prov merged untuk peta
    df["pcode38"] = "ID" + df["kode_prov"].astype(int).astype(str).str.zfill(2)
    df_34 = df.copy()
    df_34["kode_prov"] = df_34["kode_prov"].replace(PEMEKARAN_MAP)
    df_34["pcode"] = "ID" + df_34["kode_prov"].astype(int).astype(str).str.zfill(2)

    # ========== Trend nasional per (tahun, jenis BBM) ==========
    nat = (df.groupby(["tahun", "jenis_bbm"])["n_tertimbang"].sum().reset_index())
    trend_data = {}
    for y in YEARS:
        sub = nat[nat["tahun"] == y].set_index("jenis_bbm")["n_tertimbang"]
        total = sub.sum()
        trend_data[str(y)] = {f: round(float(sub.get(f, 0))) for f in FUELS}
        trend_data[str(y)]["_total"] = round(float(total))

    # ========== Per kelas per (tahun, kelas, jenis BBM) ==========
    klas = (df.groupby(["tahun", "kelas", "jenis_bbm"])["n_tertimbang"].sum().reset_index())
    klas_data = {}
    for y in YEARS:
        klas_data[str(y)] = {}
        for k in CLASSES:
            sub = klas[(klas["tahun"] == y) & (klas["kelas"] == k)].set_index("jenis_bbm")["n_tertimbang"]
            klas_data[str(y)][k] = {f: round(float(sub.get(f, 0))) for f in FUELS}

    # ========== Per provinsi (peta 34 + ranking 38) ==========
    # Map data: per (tahun, kelas/All, fuel, pcode) → share buyers-only %
    map_data = {}
    rank_data = {}
    for y in YEARS:
        map_data[str(y)] = {}
        rank_data[str(y)] = {}
        ydf34 = df_34[df_34["tahun"] == y]
        ydf38 = df[df["tahun"] == y]

        for k in CLASSES + ["All"]:
            map_data[str(y)][k] = {}
            rank_data[str(y)][k] = {}

            for f in FUELS[1:]:  # buyers only
                if k == "All":
                    sub34 = ydf34.groupby(["pcode", "jenis_bbm"])["n_tertimbang"].sum().reset_index()
                    sub38 = ydf38.groupby(["pcode38", "jenis_bbm"])["n_tertimbang"].sum().reset_index()
                else:
                    sub34 = ydf34[ydf34["kelas"] == k].groupby(["pcode", "jenis_bbm"])["n_tertimbang"].sum().reset_index()
                    sub38 = ydf38[ydf38["kelas"] == k].groupby(["pcode38", "jenis_bbm"])["n_tertimbang"].sum().reset_index()

                # share buyers only per pcode
                buyers34 = sub34[sub34["jenis_bbm"] != "Tidak beli"]
                tot34 = buyers34.groupby("pcode")["n_tertimbang"].sum()
                f34 = buyers34[buyers34["jenis_bbm"] == f].set_index("pcode")["n_tertimbang"]
                map_data[str(y)][k][f] = {p: round(float(f34.get(p, 0)) / tot34[p] * 100, 2)
                                          for p in tot34.index if tot34[p] > 0}

                buyers38 = sub38[sub38["jenis_bbm"] != "Tidak beli"]
                tot38 = buyers38.groupby("pcode38")["n_tertimbang"].sum()
                f38 = buyers38[buyers38["jenis_bbm"] == f].set_index("pcode38")["n_tertimbang"]
                rank_data[str(y)][k][f] = {p: round(float(f38.get(p, 0)) / tot38[p] * 100, 2)
                                           for p in tot38.index if tot38[p] > 0}

    prov_meta = df_34.groupby("pcode")["nama_prov"].first().to_dict()
    prov_meta_38 = df.groupby("pcode38")["nama_prov"].first().to_dict()

    # Centroids
    try:
        import geopandas as gpd
        SHP = r"C:\Users\LENOVO\OneDrive - PT Bank Mandiri (Persero) Tbk\Desktop\Mandiri\Software\IDN_shp\idn_admbnda_adm1_bps_20200401.shp"
        gdf = gpd.read_file(SHP)
        centroids = {r["ADM1_PCODE"]: [round(r.geometry.centroid.x, 3), round(r.geometry.centroid.y, 3)] for _, r in gdf.iterrows()}
    except Exception:
        centroids = {}

    return {
        "trend": trend_data,
        "klas": klas_data,
        "map": map_data,
        "rank38": rank_data,
        "prov_meta": prov_meta,
        "prov_meta_38": prov_meta_38,
        "centroids": centroids,
    }


def build_html(payload, geojson, generated):
    pop_2025 = payload["trend"]["2025"]["_total"]
    nonbuy_2025 = payload["trend"]["2025"]["Tidak beli"]
    nonbuy_share_2025 = nonbuy_2025 / pop_2025 * 100
    pertalite_2025 = payload["trend"]["2025"]["Pertalite"]
    pertamax_2025 = payload["trend"]["2025"]["Pertamax"]
    buyer_total = pop_2025 - nonbuy_2025
    pert_share = pertalite_2025 / buyer_total * 100 if buyer_total > 0 else 0
    pmax_share = pertamax_2025 / buyer_total * 100 if buyer_total > 0 else 0

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Thematic Issue: Konsumsi BBM per Kelas Masyarakat</title>
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

  .sidebar {{ position: fixed; top: 0; left: 0; bottom: 0; width: 220px; background: var(--navy); color: white; padding: 24px 0; z-index: 40; display: flex; flex-direction: column; overflow-y: auto; }}
  .sidebar .brand {{ padding: 0 24px 20px 24px; border-bottom: 1px solid rgba(255,255,255,0.12); }}
  .sidebar .brand-title {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 18px; font-weight: 600; line-height: 1.15; color: white; }}
  .sidebar .brand-sub {{ font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--yellow); margin-top: 4px; font-weight: 600; }}
  .sidebar .yellow-accent {{ display: inline-block; width: 10px; height: 10px; background: var(--yellow); margin-bottom: 8px; }}
  .sidebar .nav-section {{ padding: 16px 0; }}
  .sidebar .nav-label {{ padding: 0 24px; font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(255,255,255,0.4); margin-bottom: 8px; }}
  .sidebar .nav-item {{ display: flex; align-items: center; gap: 10px; padding: 10px 24px; font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.7); border-left: 3px solid transparent; cursor: pointer; transition: all 0.15s; background: none; border-top: none; border-right: none; border-bottom: none; width: 100%; text-align: left; }}
  .sidebar .nav-item:hover {{ color: white; background: rgba(255,255,255,0.05); }}
  .sidebar .nav-item.active {{ color: white; border-left-color: var(--yellow); background: rgba(255,183,0,0.1); }}
  .sidebar .nav-item iconify-icon {{ font-size: 18px; }}
  .sidebar .topic-switch {{ padding: 12px 24px; border-bottom: 1px solid rgba(255,255,255,0.12); }}
  .sidebar .topic-switch label {{ font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(255,255,255,0.4); display: block; margin-bottom: 6px; }}
  .sidebar .topic-switch select {{ width: 100%; background: rgba(255,255,255,0.08); color: white; border: 1px solid rgba(255,255,255,0.2); padding: 6px 10px; font-size: 13px; font-family: 'Inter', sans-serif; }}
  .sidebar .footer {{ margin-top: auto; padding: 16px 24px; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(255,255,255,0.4); border-top: 1px solid rgba(255,255,255,0.12); }}
  .with-sidebar {{ margin-left: 220px; }}
  .hero-band {{ background: var(--navy); color: white; }}
  .hero-band .eyebrow {{ color: var(--yellow); }}
  .hero-band h1, .hero-band h2 {{ color: white; }}
  .hero-band p {{ color: rgba(255,255,255,0.78); }}
  .thematic-tag {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--navy); background: var(--yellow); border-radius: 0; margin-bottom: 16px; }}

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
    <a href="../../index.html" style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--yellow);text-transform:uppercase;letter-spacing:0.1em;font-weight:600;text-decoration:none;margin-bottom:10px;">
      <iconify-icon icon="mdi:arrow-left"></iconify-icon><span>Beranda</span>
    </a>
    <span class="yellow-accent"></span>
    <div class="brand-title">Mandiri Institute</div>
    <div class="brand-sub">Isu Tematik</div>
  </div>
  <!-- Thematic topic switcher (extensible) -->
  <div class="topic-switch">
    <label>Topik tematik</label>
    <select onchange="if(this.value) window.location.href = this.value">
      <option value="">Konsumsi BBM</option>
      <option value="" disabled>Subsidi (soon)</option>
      <option value="" disabled>Inflasi Pangan (soon)</option>
      <option value="" disabled>Pemilu & Pasar (soon)</option>
    </select>
  </div>
  <div class="nav-section">
    <div class="nav-label">Konsumsi BBM</div>
    <template x-for="t in tabs" :key="t.id">
      <button @click="setPage(t.id)" :class="page === t.id ? 'nav-item active' : 'nav-item'">
        <iconify-icon :icon="t.icon"></iconify-icon>
        <span x-text="t.label"></span>
      </button>
    </template>
  </div>
  <div class="footer">
    <div>Susenas BPS · 2019-2025</div>
  </div>
</aside>

<div class="with-sidebar">
<div class="folio">
  <div class="folio-inner">
    <span class="left">Mandiri Institute · BBM</span>
    <span class="right" x-text="page.toUpperCase()"></span>
  </div>
</div>
<div class="hero-band hero-band-craft">
  <header class="max-w-[1280px] mx-auto px-8 pt-16 pb-16">
    <div class="thematic-tag"><iconify-icon icon="mdi:fire"></iconify-icon>Isu Tematik</div>
    <div class="eyebrow">Riset Mandiri Institute · Energi & Konsumen</div>
    <h1 class="serif-display text-4xl md:text-5xl mt-5 max-w-4xl" x-text="pageTitle"></h1>
    <p class="mt-5 text-base max-w-3xl leading-relaxed" x-text="pageSubtitle"></p>
  </header>
</div>

<main class="max-w-[1280px] mx-auto px-8 pb-16">

  <!-- TREND -->
  <section x-show="page === 'trend'">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-10 rule-top pt-8">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Konsumen 2025</div>
        <div class="stat-num text-5xl mt-3 ink">{pop_2025/1e6:.1f}<span class="text-2xl muted ml-1">jt</span></div>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Tidak beli BBM 2025</div>
        <div class="stat-num text-5xl mt-3" style="color:#B6B8BA">{nonbuy_share_2025:.1f}<span class="text-2xl muted ml-1">%</span></div>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Pertalite (buyers) 2025</div>
        <div class="stat-num text-5xl mt-3" style="color:#FFB700">{pert_share:.1f}<span class="text-2xl muted ml-1">%</span></div>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Pertamax (buyers) 2025</div>
        <div class="stat-num text-5xl mt-3" style="color:#67B2E8">{pmax_share:.1f}<span class="text-2xl muted ml-1">%</span></div>
      </div>
    </div>
    <div class="mt-16">
      <span class="badge"><span class="badge-dot"></span>Populasi Tertimbang Nasional</span>
      <div class="eyebrow-roman mt-3">I. Trend</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl">Pergeseran konsumsi BBM nasional, 2019-2025.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Komposisi 5 jenis BBM. Premium di phase-out pasca 2022, Pertalite jadi default massal.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div class="mb-3 mt-2 flex gap-2">
        <button class="chip-action" :class="trendMode==='abs' ? 'active' : ''" @click="trendMode='abs'; renderTrend()">Absolut (juta)</button>
        <button class="chip-action" :class="trendMode==='share' ? 'active' : ''" @click="trendMode='share'; renderTrend()">Share (%)</button>
      </div>
      <div id="chart-trend" style="height:520px;"></div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas BPS Blok 42</span>
        <span><span class="label">Bobot</span>weind (individu)</span>
        <span><span class="label">Versi kode BPS</span>206/207 (2019-21), 215/216 (2022-24), 243/244 (2025)</span>
      </div>
    </div>
  </section>

  <!-- PER KELAS -->
  <section x-show="page === 'kelas'">
    <div class="rule-top pt-8 flex flex-wrap items-end gap-10">
      <div class="flex-1">
        <div class="eyebrow mb-2" style="color: var(--muted);">Tahun</div>
        <div class="flex items-center gap-3">
          <div class="stat-num text-3xl text-navy" style="color:var(--navy);min-width:80px" x-text="year"></div>
          <input type="range" min="0" :max="years.length-1" step="1" :value="years.indexOf(year)"
            @input="year = years[$event.target.value]; renderKelas()"
            style="flex:1;max-width:400px">
        </div>
      </div>
      <div>
        <div class="eyebrow mb-2" style="color: var(--muted);">Tampilan</div>
        <div class="flex gap-2">
          <button class="chip-action" :class="kelasMode==='share' ? 'active' : ''" @click="kelasMode='share'; renderKelas()">Share buyers (%)</button>
          <button class="chip-action" :class="kelasMode==='raw' ? 'active' : ''" @click="kelasMode='raw'; renderKelas()">Jumlah konsumen</button>
        </div>
      </div>
    </div>
    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>8 Kelas wb4</span>
      <div class="eyebrow-roman mt-3">II. Per Kelas</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl" x-text="'Komposisi BBM per kelas masyarakat, ' + year + '.'"></h2>
      <p class="mt-3 muted text-base max-w-3xl">Stacked bar: tiap kelas menunjukkan share jenis BBM yang dipilih.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div id="chart-kelas" style="height:560px;"></div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas BPS · klasifikasi wb4</span>
        <span><span class="label">Total</span>= 100% per kelas (mode share)</span>
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
          <option value="All">Semua kelas</option>
          <template x-for="k in classes" :key="'mk'+k"><option :value="k" x-text="k"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Jenis BBM</div>
        <select x-model="mapFuel" @change="renderMap()" class="select-flat mt-2" style="min-width:160px;">
          <template x-for="f in mapFuels" :key="'mf'+f"><option :value="f" x-text="f"></option></template>
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
      <div style="margin-left:auto">
        <button class="chip-action" @click="exportPPT('chart-map', 'Sebaran ' + mapFuel + ' per provinsi', 'Tahun ' + year + ' · Kelas ' + mapKelas + ' · Susenas BPS')" style="background:var(--yellow);color:var(--ink);border-color:var(--yellow);font-weight:700;">
          <iconify-icon icon="mdi:presentation"></iconify-icon>Export PPT
        </button>
      </div>
    </div>
    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>34 Provinsi (38 ranking)</span>
      <div class="eyebrow-roman mt-3">III. Geografi</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl" x-text="'Sebaran ' + mapFuel + ' per provinsi, ' + mapKelas + '.'"></h2>
      <p class="mt-3 muted text-base max-w-3xl">Peta share <em>hanya</em> untuk RT yang membeli BBM. Pemekaran Papua diagregasi ke induk.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div id="chart-map" style="height:780px;"></div>
      <div class="map-legend">
        <div class="map-legend-label">Share RT pembeli (%)</div>
        <div class="map-legend-bins" id="legend-geografi"></div>
      </div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas BPS · Shapefile BPS adm1 2020</span>
        <span><span class="label">Catatan</span>Pemekaran Papua 2022+ diagregasi</span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-16 mt-12 rule-top pt-10">
        <div class="rank-card">
          <div class="sub">Top 10 Provinsi</div>
          <h4 x-text="'Share tertinggi: ' + mapFuel"></h4>
          <div class="rank-list">
            <template x-for="(r, i) in rankTop" :key="'t'+r.pcode">
              <div class="rank-row">
                <div class="rank-num" x-text="i+1"></div>
                <div class="rank-name" x-text="r.nama"></div>
                <div class="rank-cell-right">
                  <div class="rank-bar-wrap" style="width: 110px;">
                    <div class="rank-bar" :style="'width: '+(r.value/rankMax*100)+'%'"></div>
                  </div>
                  <div class="rank-val" x-text="r.value.toFixed(1)+'%'"></div>
                </div>
              </div>
            </template>
          </div>
        </div>
        <div class="rank-card">
          <div class="sub">Bottom 10 Provinsi</div>
          <h4 x-text="'Share terendah: ' + mapFuel"></h4>
          <div class="rank-list">
            <template x-for="(r, i) in rankBottom" :key="'b'+r.pcode">
              <div class="rank-row is-bottom">
                <div class="rank-num" x-text="i+1"></div>
                <div class="rank-name" x-text="r.nama"></div>
                <div class="rank-cell-right">
                  <div class="rank-bar-wrap" style="width: 110px;">
                    <div class="rank-bar" :style="'width: '+(r.value/rankMax*100)+'%'"></div>
                  </div>
                  <div class="rank-val" x-text="r.value.toFixed(1)+'%'"></div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </section>

  <footer class="rule-top mt-16 pt-8 pb-4 flex items-center justify-between text-xs muted uppercase tracking-widest">
    <div>Mandiri Institute · Isu Tematik · BBM</div>
    <div>Generated {generated}</div>
    <div>Palette: Mandiri Official</div>
  </footer>
</main>
</div>
</div>

<script>
const PAYLOAD = {json.dumps(payload)};
const GEOJSON = {json.dumps(geojson)};
const CLASSES = {json.dumps(CLASSES)};
const FUELS = {json.dumps(FUELS)};
const FUEL_COLORS = {json.dumps(FUEL_COLORS)};
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
function pcodeProvCode(pcode) {{ return pcode.slice(2, 4); }}
function inRegion(pcode, wilayah, prov) {{
  const pc = pcodeProvCode(pcode);
  if (prov && prov !== 'All') return pc === prov;
  if (!wilayah || wilayah === 'Indonesia') return true;
  return REGION_PROVS[wilayah].includes(pc);
}}
function filteredGeojson(allowedSet) {{
  return {{ type: 'FeatureCollection', features: GEOJSON.features.filter(f => allowedSet.has(f.id)) }};
}}
function tightBbox(features) {{
  if (!features.length) return null;
  const lons = [], lats = [];
  features.forEach(f => {{
    function walk(c) {{ if (typeof c[0] === 'number') {{ lons.push(c[0]); lats.push(c[1]); }} else c.forEach(walk); }}
    walk(f.geometry.coordinates);
  }});
  if (!lons.length) return null;
  lons.sort((a,b) => a-b); lats.sort((a,b) => a-b);
  const pct = (arr, p) => arr[Math.min(Math.max(Math.floor(arr.length * p), 0), arr.length-1)];
  const minLon = pct(lons, 0.025), maxLon = pct(lons, 0.975);
  const minLat = pct(lats, 0.025), maxLat = pct(lats, 0.975);
  const dLon = Math.max((maxLon-minLon) * 0.08, 0.05);
  const dLat = Math.max((maxLat-minLat) * 0.08, 0.05);
  return {{ lon: [minLon-dLon, maxLon+dLon], lat: [minLat-dLat, maxLat+dLat] }};
}}

const TABS = [
  {{ id: 'trend',    label: 'Trend Nasional', icon: 'mdi:trending-up' }},
  {{ id: 'kelas',    label: 'Per Kelas',     icon: 'mdi:chart-bar-stacked' }},
  {{ id: 'geografi', label: 'Geografi',      icon: 'mdi:map-outline' }},
];
const PAGE_META = {{
  trend:    {{ title: 'Konsumen BBM Indonesia, 2019-2025.',
              sub: 'Komposisi 5 jenis bensin (Premium phase-out, Pertalite-Pertamax dominasi). Basis: konsumen tertimbang Susenas.' }},
  kelas:    {{ title: 'Distribusi BBM per kelas masyarakat.',
              sub: 'Stacked bar share jenis BBM di tiap kelas wb4. Pilih tahun untuk lihat pergeseran.' }},
  geografi: {{ title: 'Sebaran konsumen BBM per provinsi.',
              sub: 'Peta share RT pembeli BBM. Filter kelas + jenis untuk eksplorasi.' }},
}};

function computeBins(values) {{
  const sorted = values.filter(v => v != null && !isNaN(v)).slice().sort((a, b) => a - b);
  if (sorted.length === 0) return {{ edges: [0,0,0,0,0,1] }};
  const q = (p) => sorted[Math.min(Math.floor(p * (sorted.length - 1)), sorted.length - 1)];
  return {{ edges: [sorted[0], q(0.2), q(0.4), q(0.6), q(0.8), sorted[sorted.length - 1]] }};
}}

function dashboard() {{
  return {{
    tabs: TABS, page: 'trend',
    years: YEARS, year: '2025', classes: CLASSES,
    trendMode: 'share',
    kelasMode: 'share',
    mapKelas: 'All', mapFuel: 'Pertalite', mapFuels: FUELS.slice(1),
    wilayah: 'Indonesia', wilayahList: Object.keys(REGION_PROVS), provFilter: 'All',
    rankTop: [], rankBottom: [],
    get pageTitle() {{ return PAGE_META[this.page].title; }},
    get pageSubtitle() {{ return PAGE_META[this.page].sub; }},
    get rankMax() {{ return this.rankTop.length ? this.rankTop[0].value : 1; }},
    get provOptions() {{
      const codes = REGION_PROVS[this.wilayah];
      const all = Object.entries(PAYLOAD.prov_meta_38);
      const filtered = codes ? all.filter(([p, _]) => codes.includes(pcodeProvCode(p))) : all;
      return filtered.sort((a, b) => a[1].localeCompare(b[1])).map(([p, n]) => ({{ pcode: pcodeProvCode(p), nama: n }}));
    }},
    onWilayahChange() {{ this.provFilter = 'All'; this.renderForPage(this.page); }},
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
    init() {{ this.$nextTick(() => this.renderForPage(this.page)); }},
    setPage(id) {{ this.page = id; this.renderForPage(id); }},
    renderForPage(id) {{
      requestAnimationFrame(() => requestAnimationFrame(() => {{
        if (id === 'trend') this.renderTrend();
        else if (id === 'kelas') this.renderKelas();
        else if (id === 'geografi') this.renderMap();
      }}));
    }},
    renderTrend() {{
      const traces = FUELS.map(f => ({{
        x: YEARS.map(y => +y),
        y: YEARS.map(y => {{
          const v = PAYLOAD.trend[y][f];
          if (this.trendMode === 'share') return v / PAYLOAD.trend[y]._total * 100;
          return v / 1e6;
        }}),
        name: f, type: 'bar',
        marker: {{ color: FUEL_COLORS[f] }},
        hovertemplate: this.trendMode === 'share'
          ? '%{{x}}<br>' + f + ': %{{y:.1f}}%<extra></extra>'
          : '%{{x}}<br>' + f + ': %{{y:.2f}} jt<extra></extra>',
      }}));
      Plotly.react('chart-trend', traces, {{
        barmode: 'stack', bargap: 0.45,
        margin: {{ l: 70, r: 30, t: 20, b: 80 }},
        font: {{ family: FONT, size: 13, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ tickfont: {{ size: 14, color: INK }}, showline: true, linecolor: INK, ticks: 'outside', tickcolor: INK, ticklen: 4 }},
        yaxis: {{ title: {{ text: this.trendMode === 'share' ? 'Share (%)' : 'Konsumen (juta)', font: {{ size: 12, color: MUTED }} }},
                 tickfont: {{ size: 12, color: MUTED }}, gridcolor: '#EAECF0' }},
        legend: {{ orientation: 'h', y: -0.18, x: 0, xanchor: 'left', font: {{ size: 12 }} }},
      }}, {{ displaylogo: false, responsive: true }});
    }},
    renderKelas() {{
      const k = PAYLOAD.klas[this.year];
      const traces = FUELS.map(f => {{
        if (this.kelasMode === 'share' && f === 'Tidak beli') return null;
        const y = CLASSES.map(c => {{
          const v = (k[c] && k[c][f]) || 0;
          if (this.kelasMode === 'share') {{
            const buyersTotal = FUELS.filter(ff => ff !== 'Tidak beli')
              .reduce((s, ff) => s + ((k[c] && k[c][ff]) || 0), 0);
            return buyersTotal > 0 ? v / buyersTotal * 100 : 0;
          }}
          return v / 1e6;
        }});
        return {{
          x: CLASSES, y, name: f, type: 'bar',
          marker: {{ color: FUEL_COLORS[f] }},
          hovertemplate: this.kelasMode === 'share'
            ? '%{{x}}<br>' + f + ': %{{y:.1f}}%<extra></extra>'
            : '%{{x}}<br>' + f + ': %{{y:.2f}} jt<extra></extra>',
        }};
      }}).filter(t => t);
      Plotly.react('chart-kelas', traces, {{
        barmode: 'stack', bargap: 0.45,
        margin: {{ l: 60, r: 30, t: 20, b: 80 }},
        font: {{ family: FONT, size: 13, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ tickfont: {{ size: 14, color: INK }}, showline: true, linecolor: INK, ticks: 'outside', tickcolor: INK, ticklen: 4, automargin: true }},
        yaxis: {{ title: {{ text: this.kelasMode === 'share' ? 'Share (%)' : 'Konsumen (juta)', font: {{ size: 12, color: MUTED }} }},
                 tickfont: {{ size: 12, color: MUTED }}, gridcolor: '#EAECF0' }},
        legend: {{ orientation: 'h', y: -0.20, x: 0, xanchor: 'left', font: {{ size: 12 }} }},
      }}, {{ displaylogo: false, responsive: true }});
    }},
    renderMap() {{
      const sliceFull = ((PAYLOAD.map[this.year] || {{}})[this.mapKelas] || {{}})[this.mapFuel] || {{}};
      const slice = {{}};
      Object.keys(sliceFull).forEach(p => {{ if (inRegion(p, this.wilayah, this.provFilter)) slice[p] = sliceFull[p]; }});
      const locs = Object.keys(slice);
      const vals = locs.map(p => slice[p]);
      const allowedSet = new Set(locs);
      const filteredGJ = filteredGeojson(allowedSet);
      const baseFeatures = GEOJSON.features.filter(f => inRegion(f.id, this.wilayah, this.provFilter));
      const baseGJ = {{ type: 'FeatureCollection', features: baseFeatures }};
      const noDataLocs = baseFeatures.map(f => f.id).filter(p => !(p in slice));
      const bins = computeBins(vals);
      const palette = ['#E8EFF6','#A9C4DF','#67B2E8','#2A6FB3','#003D79'];
      const colorscale = [
        [0.0, palette[0]], [0.2-1e-9, palette[0]],
        [0.2, palette[1]], [0.4-1e-9, palette[1]],
        [0.4, palette[2]], [0.6-1e-9, palette[2]],
        [0.6, palette[3]], [0.8-1e-9, palette[3]],
        [0.8, palette[4]], [1.0, palette[4]],
      ];
      const rankSlice38 = ((PAYLOAD.rank38[this.year] || {{}})[this.mapKelas] || {{}})[this.mapFuel] || {{}};
      const ranked38 = Object.keys(rankSlice38).map(p => ({{ pcode: p, value: rankSlice38[p] }}))
        .sort((a,b) => b.value - a.value);
      const rankByPcode38 = {{}}; ranked38.forEach((r, i) => {{ rankByPcode38[r.pcode] = i + 1; }});
      const hovertext = locs.map(p => {{
        const nama = PAYLOAD.prov_meta[p] || p;
        const v = slice[p];
        const rank = rankByPcode38[p] || '-';
        return `<b>${{nama}}</b><br>` +
               `<span style="color:#003D79;font-size:18px;font-weight:600">${{v.toFixed(1)}}%</span><br>` +
               `<span style="color:#667085">Share ${{this.mapFuel}} di kelas ${{this.mapKelas}}</span><br>` +
               `<span style="color:#667085">Rank #${{rank}} dari 38</span>`;
      }});
      const top3 = ranked38.filter(t => inRegion(t.pcode, this.wilayah, this.provFilter)).slice(0, 3);
      const labelLons = [], labelLats = [], labelText = [];
      top3.forEach(t => {{
        const c = PAYLOAD.centroids[t.pcode];
        if (c) {{
          labelLons.push(c[0]); labelLats.push(c[1]);
          labelText.push('<b>' + (PAYLOAD.prov_meta_38[t.pcode] || t.pcode) + '</b>');
        }}
      }});
      Plotly.react('chart-map', [
        noDataLocs.length ? {{
          type: 'choropleth', geojson: baseGJ, locations: noDataLocs, z: noDataLocs.map(_=>0),
          featureidkey: 'properties.ADM1_PCODE',
          colorscale: [[0,'#E8E8E8'],[1,'#E8E8E8']], showscale: false,
          marker: {{ line: {{ color: 'white', width: 0.8 }} }},
          hoverinfo: 'skip', showlegend: false,
        }} : null,
        {{
          type: 'choropleth', geojson: filteredGJ, locations: locs, z: vals,
          featureidkey: 'properties.ADM1_PCODE',
          zmin: bins.edges[0], zmax: bins.edges[5],
          colorscale, showscale: false,
          marker: {{ line: {{ color: 'white', width: 0.8 }} }},
          hovertext, hovertemplate: '%{{hovertext}}<extra></extra>',
          hoverlabel: {{ bgcolor: 'white', bordercolor: '#003D79', font: {{ family: FONT, size: 13, color: INK }}, align: 'left', namelength: -1 }},
        }},
        {{
          type: 'scattergeo', mode: 'text',
          lon: labelLons, lat: labelLats, text: labelText,
          textfont: {{ family: 'Source Serif 4, serif', size: 12, color: '#051C2C' }},
          hoverinfo: 'skip', showlegend: false,
        }},
      ].filter(t => t), {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        font: {{ family: FONT, color: INK }},
        geo: (() => {{ const bbox = tightBbox(baseGJ.features); return {{ visible: false, bgcolor: 'transparent', projection: {{ type: 'mercator' }}, ...(bbox ? {{ lonaxis: {{ range: bbox.lon, autorange: false }}, lataxis: {{ range: bbox.lat, autorange: false }} }} : {{ fitbounds: 'locations' }}), uirevision: this.wilayah + '|' + this.provFilter }}; }})(),
        paper_bgcolor: 'transparent',
      }}, {{ displaylogo: false, responsive: true }});

      const el = document.getElementById('legend-geografi');
      if (el) {{
        el.innerHTML = palette.map((c, i) => {{
          const lo = bins.edges[i];
          return `<div class="map-legend-bin"><div class="swatch" style="background:${{c}}"></div><div class="range">${{lo.toFixed(1)}}%${{i===4?'+':''}}</div></div>`;
        }}).join('');
      }}

      const ranked = Object.keys(rankSlice38).map(p => ({{ pcode: p, nama: PAYLOAD.prov_meta_38[p] || p, value: rankSlice38[p] }})).sort((a,b) => b.value - a.value);
      this.rankTop = ranked.slice(0, 10);
      this.rankBottom = ranked.slice().sort((a,b) => a.value - b.value).slice(0, 10);
    }},
  }};
}}
</script>
</body>
</html>
"""


def main():
    df = load()
    payload = build_payload(df)
    with open(GEOJSON, "r", encoding="utf-8") as f:
        geojson = json.load(f)
    html = build_html(payload, geojson, date.today().isoformat())
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT.name} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
