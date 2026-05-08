"""
Generator dashboard Profil Demografi & Kesehatan Indonesia 2025.
Input  : data/demografi-kesehatan.csv + metadata.json + (reused) kabkota_bps_simplified.geojson
Output : dashboard.html (single file, data embedded inline)

Mirrors editorial style of `kelas-kabkota/dashboard.html` (canonical):
  sidebar (drawer di mobile), folio header, hero band, chart-card, ranking, footer.

Pages: Ringkasan / Demografi / Asuransi / Spending / Metodologi.
"""
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
CSV = HERE / "data" / "demografi-kesehatan.csv"
META = HERE / "metadata.json"
GEOJSON = HERE.parent / "kelas-kabkota" / "kabkota_bps_simplified.geojson"
OUT = HERE / "dashboard.html"


# ---------- Profile ordering & color palette (Mandiri brand) ----------
AGING_ORDER = [
    "Young (<7%)",
    "Aging-Early (7-10%)",
    "Aging-Onset (10-15%)",
    "Aging-Mature (>=15%)",
]
AGING_COLORS = {
    "Young (<7%)":         "#67B2E8",
    "Aging-Early (7-10%)": "#A9C4DF",
    "Aging-Onset (10-15%)": "#FFB700",
    "Aging-Mature (>=15%)": "#C8102E",
}
INSURANCE_ORDER = [
    "Very Low (<50%)",
    "Low Coverage (50-75%)",
    "Medium Coverage (75-90%)",
    "High Coverage (>=90%)",
]
INSURANCE_COLORS = {
    "Very Low (<50%)":          "#C8102E",
    "Low Coverage (50-75%)":    "#EA7200",
    "Medium Coverage (75-90%)": "#67B2E8",
    "High Coverage (>=90%)":    "#003D79",
}


def _normalize_profile(s, mapping):
    """Map CSV labels (which use unicode '>=' as '≥') to ASCII keys."""
    return s.astype(str).str.replace("≥", ">=", regex=False).map(lambda v: v if v in mapping else v.replace("≥", ">="))


def load():
    df = pd.read_csv(CSV)
    df["nama_prov"] = (
        df["nama_prov"].str.title()
        .str.replace("Sumatera", "Sumatra", regex=False)
    )
    df["nama_kab"] = df["nama_kab"].str.title()
    df["pcode"] = "ID" + df["kode_kabkota"].astype(int).astype(str).str.zfill(4)
    # Normalize profile labels to ASCII (CSV uses '≥' for >=)
    df["aging_profile"] = df["aging_profile"].astype(str).str.replace("≥", ">=", regex=False)
    df["insurance_profile"] = df["insurance_profile"].astype(str).str.replace("≥", ">=", regex=False)
    return df


def build_payload(df: pd.DataFrame, meta: dict) -> dict:
    pop_total = float(df["pop_total_2025"].sum())

    # Weighted national averages (better than raw means for kabkota cross-section)
    def wmean(col):
        return float((df[col] * df["pop_total_2025"]).sum() / pop_total)

    pct_lansia_avg   = wmean("pct_lansia_60") * 100
    pct_jkn_avg      = wmean("pct_jkn_total") * 100
    pct_jkn_pbi_avg  = wmean("pct_jkn_pbi") * 100
    pct_jkn_npbi_avg = wmean("pct_jkn_non_pbi") * 100
    pct_swasta_avg   = wmean("pct_asuransi_swasta") * 100
    pct_no_ins_avg   = wmean("pct_no_insurance") * 100
    avg_oop_rp       = wmean("avg_oop_health_total")
    oop_burden_avg   = wmean("oop_pct_total_nonfood") * 100
    avg_inap         = wmean("avg_rawat_inap")
    avg_jalan        = wmean("avg_rawat_jalan")
    avg_obat         = wmean("avg_obat")
    avg_premi        = wmean("avg_premi_asuransi_kesehatan")
    dep_ratio_avg    = wmean("dependency_ratio")
    aging_idx_avg    = float(df["aging_index"].median())

    pop_balita = int(df["pop_balita_0_4"].sum())
    pop_anak = int(df["pop_anak_5_14"].sum())
    pop_remaja = int(df["pop_remaja_15_24"].sum())
    pop_dewasa = int(df["pop_dewasa_25_59"].sum())
    pop_lansia = int(df["pop_lansia_60_plus"].sum())

    # Profile distribution counts
    aging_dist = df["aging_profile"].value_counts().to_dict()
    insurance_dist = df["insurance_profile"].value_counts().to_dict()
    aging_dist = {k: int(aging_dist.get(k, 0)) for k in AGING_ORDER}
    insurance_dist = {k: int(insurance_dist.get(k, 0)) for k in INSURANCE_ORDER}

    # Per-province aggregation for stacked-bar (asuransi page)
    prov_agg = (
        df.assign(
            jkn_pbi_w=df["pct_jkn_pbi"] * df["pop_total_2025"],
            jkn_npbi_w=df["pct_jkn_non_pbi"] * df["pop_total_2025"],
            swasta_w=df["pct_asuransi_swasta"] * df["pop_total_2025"],
            none_w=df["pct_no_insurance"] * df["pop_total_2025"],
            jkn_total_w=df["pct_jkn_total"] * df["pop_total_2025"],
            lansia_w=df["pct_lansia_60"] * df["pop_total_2025"],
            oop_w=df["oop_pct_total_nonfood"] * df["pop_total_2025"],
        )
        .groupby("nama_prov")
        .agg(
            pop=("pop_total_2025", "sum"),
            jkn_pbi=("jkn_pbi_w", "sum"),
            jkn_npbi=("jkn_npbi_w", "sum"),
            swasta=("swasta_w", "sum"),
            none=("none_w", "sum"),
            jkn_total=("jkn_total_w", "sum"),
            lansia=("lansia_w", "sum"),
            oop=("oop_w", "sum"),
            avg_oop_rp=("avg_oop_health_total", "mean"),
            n=("nama_kab", "count"),
        )
        .reset_index()
    )
    for col in ["jkn_pbi", "jkn_npbi", "swasta", "none", "jkn_total", "lansia", "oop"]:
        prov_agg[col] = (prov_agg[col] / prov_agg["pop"]) * 100
    prov_agg = prov_agg.sort_values("jkn_total", ascending=True)

    prov_list = []
    for _, r in prov_agg.iterrows():
        prov_list.append({
            "nama_prov": r["nama_prov"],
            "pop": int(r["pop"]),
            "n_kabkota": int(r["n"]),
            "jkn_pbi": round(float(r["jkn_pbi"]), 2),
            "jkn_npbi": round(float(r["jkn_npbi"]), 2),
            "swasta": round(float(r["swasta"]), 2),
            "none": round(float(r["none"]), 2),
            "jkn_total": round(float(r["jkn_total"]), 2),
            "lansia": round(float(r["lansia"]), 2),
            "oop": round(float(r["oop"]), 2),
            "avg_oop_rp": int(r["avg_oop_rp"]),
        })

    # Per-kabkota records (stripped to what JS needs)
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "pcode":     r["pcode"],
            "nama_kab":  r["nama_kab"],
            "nama_prov": r["nama_prov"],
            "pop":       int(r["pop_total_2025"]),
            "pop_balita":  int(r["pop_balita_0_4"]),
            "pop_anak":    int(r["pop_anak_5_14"]),
            "pop_remaja":  int(r["pop_remaja_15_24"]),
            "pop_dewasa":  int(r["pop_dewasa_25_59"]),
            "pop_lansia":  int(r["pop_lansia_60_plus"]),
            "dep_ratio":   round(float(r["dependency_ratio"]), 2),
            "sex_ratio":   round(float(r["sex_ratio"]), 2),
            "aging_idx":   round(float(r["aging_index"]), 2),
            "pct_lansia":  round(float(r["pct_lansia_60"]) * 100, 2),
            "pct_balita":  round(float(r["pct_balita_0_4"]) * 100, 2),
            "pct_anak":    round(float(r["pct_anak_5_14"]) * 100, 2),
            "pct_dewasa":  round(float(r["pct_dewasa_produktif"]) * 100, 2),
            "pct_jkn_pbi":   round(float(r["pct_jkn_pbi"]) * 100, 2),
            "pct_jkn_npbi":  round(float(r["pct_jkn_non_pbi"]) * 100, 2),
            "pct_swasta":    round(float(r["pct_asuransi_swasta"]) * 100, 2),
            "pct_jkn":       round(float(r["pct_jkn_total"]) * 100, 2),
            "pct_no_ins":    round(float(r["pct_no_insurance"]) * 100, 2),
            "oop_rp":        int(r["avg_oop_health_total"]),
            "oop_inap":      int(r["avg_rawat_inap"]),
            "oop_jalan":     int(r["avg_rawat_jalan"]),
            "oop_obat":      int(r["avg_obat"]),
            "oop_premi":     int(r["avg_premi_asuransi_kesehatan"]),
            "oop_burden":    round(float(r["oop_pct_total_nonfood"]) * 100, 2),
            "aging_profile": r["aging_profile"],
            "ins_profile":   r["insurance_profile"],
            "n_sample":      int(r["n_sample_total"]) if not pd.isna(r["n_sample_total"]) else 0,
        })

    return {
        "summary": {
            "pop_total": pop_total,
            "pop_balita": pop_balita,
            "pop_anak": pop_anak,
            "pop_remaja": pop_remaja,
            "pop_dewasa": pop_dewasa,
            "pop_lansia": pop_lansia,
            "pct_lansia_avg": round(pct_lansia_avg, 2),
            "pct_jkn_avg": round(pct_jkn_avg, 2),
            "pct_jkn_pbi_avg": round(pct_jkn_pbi_avg, 2),
            "pct_jkn_npbi_avg": round(pct_jkn_npbi_avg, 2),
            "pct_swasta_avg": round(pct_swasta_avg, 2),
            "pct_no_ins_avg": round(pct_no_ins_avg, 2),
            "avg_oop_rp": int(round(avg_oop_rp)),
            "oop_burden_avg": round(oop_burden_avg, 2),
            "avg_inap": int(round(avg_inap)),
            "avg_jalan": int(round(avg_jalan)),
            "avg_obat": int(round(avg_obat)),
            "avg_premi": int(round(avg_premi)),
            "dep_ratio_avg": round(dep_ratio_avg, 2),
            "aging_idx_med": round(aging_idx_avg, 2),
            "n_kabkota": int(len(df)),
        },
        "aging_dist": aging_dist,
        "insurance_dist": insurance_dist,
        "prov": prov_list,
        "kab": rows,
        "meta": {
            "title": meta.get("title", "Profil Demografi & Kesehatan Indonesia 2025"),
            "subtitle": meta.get("subtitle", ""),
            "last_updated": meta.get("last_updated", date.today().isoformat()),
            "caveats": meta.get("caveats", []),
        },
    }


def build_html(payload: dict, geojson: dict, generated: str) -> str:
    s = payload["summary"]
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Profil Demografi & Kesehatan Indonesia 2025 - Mandiri Institute</title>
<meta name="description" content="514 Kab/Kota - Aging, JKN Coverage, Out-of-Pocket Health Spending. Susenas KOR + KP 2025.">
<meta name="theme-color" content="#003D79">
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
    --sp-1: 4px; --sp-2: 8px; --sp-3: 12px; --sp-4: 16px;
    --sp-5: 24px; --sp-6: 32px; --sp-8: 48px; --sp-10: 64px; --sp-12: 96px;
    --elev-1: 0 1px 2px rgba(5,28,44,0.04);
    --elev-2: 0 2px 8px rgba(5,28,44,0.06);
    --elev-3: 0 8px 24px rgba(5,28,44,0.10);
    --elev-4: 0 16px 48px rgba(5,28,44,0.14);
    --fs-xs: 11px; --fs-sm: 13px; --fs-base: 14px; --fs-md: 16px;
    --fs-lg: 20px; --fs-xl: 25px; --fs-2xl: 31px; --fs-3xl: 39px;
    --fs-4xl: 49px; --fs-5xl: 61px;
    --tr-fast: 0.12s ease; --tr-base: 0.2s ease; --tr-slow: 0.4s ease;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ background: var(--paper); color: var(--ink); }}
  body {{ font-family: 'Inter', system-ui, sans-serif; font-weight: 400; letter-spacing: -0.003em; margin: 0; }}
  .serif-display {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.015em; line-height: 1.08; }}
  .stat-num {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.02em; line-height: 1; font-feature-settings: 'tnum' 1, 'lnum' 1; }}
  .eyebrow {{ font-size: 11px; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; color: var(--navy); }}
  .rule-top {{ border-top: 1px solid var(--rule); }}
  .rule-bottom {{ border-bottom: 1px solid var(--rule); }}
  .hair-accent {{ border-top: 2px solid var(--sky); }}
  .ink {{ color: var(--ink); }}
  .muted {{ color: var(--muted); }}
  .num {{ font-variant-numeric: tabular-nums; }}
  .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--navy); background: var(--mist); border: 1px solid var(--sky); }}
  .badge-dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--sky); display: inline-block; }}
  .callout {{ border-left: 3px solid var(--sky); background: var(--mist); padding: 18px 24px; }}
  .callout .label {{ font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--navy); }}
  .callout .text {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 16px; line-height: 1.5; color: var(--ink); margin-top: 6px; font-weight: 500; }}
  .chart-footer {{ border-top: 1px solid var(--rule); margin-top: var(--sp-5); padding-top: var(--sp-4); display: flex; flex-wrap: wrap; gap: var(--sp-5); font-size: var(--fs-xs); color: var(--muted); }}
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
  .sidebar .crosslink {{ padding: 12px 24px; border-top: 1px solid rgba(255,255,255,0.12); }}
  .sidebar .crosslink a {{ display: flex; align-items: center; gap: 8px; font-size: 11px; color: rgba(255,255,255,0.7); text-decoration: none; padding: 6px 0; transition: color 0.15s; }}
  .sidebar .crosslink a:hover {{ color: var(--sky); }}
  .sidebar .crosslink iconify-icon {{ font-size: 14px; }}
  .with-sidebar {{ margin-left: 220px; }}

  /* Mobile drawer */
  .topbar-mobile {{ display: none; position: sticky; top: 0; z-index: 45; background: var(--navy); color: white; padding: 12px 16px; align-items: center; gap: 12px; }}
  .topbar-mobile button {{ background: none; border: none; color: white; cursor: pointer; padding: 4px; display: flex; align-items: center; }}
  .topbar-mobile .topbar-title {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 15px; font-weight: 600; }}
  .topbar-mobile .topbar-sub {{ font-size: 9px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--sky); }}
  .sidebar-overlay {{ display: none; position: fixed; inset: 0; background: rgba(5,28,44,0.5); z-index: 39; }}
  @media (max-width: 1100px) {{
    .sidebar {{ transform: translateX(-100%); transition: transform 0.25s ease; box-shadow: var(--elev-3); }}
    .sidebar.open {{ transform: translateX(0); }}
    .with-sidebar {{ margin-left: 0; }}
    .topbar-mobile {{ display: flex; }}
    .sidebar-overlay.open {{ display: block; }}
    main.dash-main {{ padding-left: 16px !important; padding-right: 16px !important; }}
  }}

  .hero-band {{ background: linear-gradient(180deg, var(--navy) 0%, #002852 100%); position: relative; color: white; }}
  .hero-band::before {{ content: ''; position: absolute; inset: 0; background-image:
    radial-gradient(ellipse at 20% 30%, rgba(255,255,255,0.04), transparent 50%),
    radial-gradient(ellipse at 80% 70%, rgba(103,178,232,0.06), transparent 50%);
    pointer-events: none; }}
  .hero-band::after {{ content: ''; position: absolute; bottom: -1px; left: 0; right: 0; height: 1px; background: var(--yellow); opacity: 0.4; }}
  .hero-band .eyebrow {{ color: var(--sky); }}
  .hero-band h1, .hero-band h2 {{ color: white; }}
  .hero-band p {{ color: rgba(255,255,255,0.78); }}

  .chip-action {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: var(--fs-xs); font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--navy); background: white; border: 1px solid var(--rule); cursor: pointer; transition: all 0.12s; }}
  .chip-action:hover {{ background: var(--mist); border-color: var(--navy); }}
  .chip-action.active {{ background: var(--navy); color: white; border-color: var(--navy); }}
  .chip-action iconify-icon {{ font-size: 14px; }}

  .callout-card {{ border: 1px solid var(--rule); padding: 24px; background: white; border-top: 3px solid var(--sky); height: 100%; }}
  .callout-card .label {{ font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); }}
  .callout-card .num {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; font-size: 44px; line-height: 1.05; color: var(--navy); margin-top: 12px; letter-spacing: -0.02em; }}
  .callout-card .num-sub {{ font-size: 18px; font-weight: 500; color: var(--muted); margin-left: 4px; }}
  .callout-card .desc {{ font-size: 13px; color: var(--muted); margin-top: 10px; line-height: 1.5; }}
  .callout-card.is-warn {{ border-top-color: var(--warning); }}
  .callout-card.is-warn .num {{ color: var(--warning); }}
  .callout-card.is-bad {{ border-top-color: var(--negative); }}
  .callout-card.is-bad .num {{ color: var(--negative); }}
  .callout-card.is-pos {{ border-top-color: var(--positive); }}
  .callout-card.is-pos .num {{ color: var(--positive); }}

  .map-legend {{ display: flex; align-items: center; gap: var(--sp-5); padding-top: var(--sp-4); margin-top: var(--sp-4); border-top: 1px solid var(--rule); flex-wrap: wrap; }}
  .map-legend-label {{ font-size: 11px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }}
  .map-legend-bins {{ display: flex; align-items: center; gap: 0; flex: 1; min-width: 280px; }}
  .map-legend-bin {{ flex: 1; display: flex; flex-direction: column; gap: 4px; }}
  .map-legend-bin .swatch {{ height: 8px; }}
  .map-legend-bin .range {{ font-size: 10px; color: var(--muted); font-variant-numeric: tabular-nums; padding-top: 2px; }}

  .rank-card h4 {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 17px; font-weight: 600; color: var(--ink); margin-bottom: 4px; }}
  .rank-card .sub {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }}
  .rank-list {{ margin-top: 14px; }}
  .rank-row {{ display: grid; grid-template-columns: 28px 1fr 130px; align-items: center; gap: 16px; padding: 10px 0; border-bottom: 1px solid var(--rule); }}
  .rank-row:hover {{ background: var(--mist); }}
  .rank-row:nth-child(even) {{ background: rgba(245,247,250,0.4); }}
  .rank-row .rank-num {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 16px; font-weight: 600; color: var(--sky); text-align: right; }}
  .rank-row.is-bottom .rank-num {{ color: #C8102E; }}
  .rank-row .rank-name {{ font-size: 14px; color: var(--ink); font-weight: 500; }}
  .rank-row .rank-name .sub-prov {{ display: block; font-size: 11px; color: var(--muted); font-weight: 400; }}
  .rank-row .rank-bar-wrap {{ position: relative; height: 6px; background: var(--mist); overflow: hidden; }}
  .rank-row .rank-bar {{ position: absolute; left: 0; top: 0; height: 100%; max-width: 100%; background: var(--navy); }}
  .rank-row.is-bottom .rank-bar {{ background: #C8102E; opacity: 0.7; }}
  .rank-row .rank-val {{ font-variant-numeric: tabular-nums; font-size: 13px; font-weight: 600; color: var(--ink); margin-top: 4px; }}
  .rank-cell-right {{ display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }}

  /* Folio header */
  .folio {{ position: sticky; top: 0; z-index: 30; background: rgba(255,255,255,0.92); backdrop-filter: blur(8px); border-bottom: 1px solid var(--rule); padding: 8px 0; }}
  .folio-inner {{ max-width: 1280px; margin: 0 auto; padding: 0 32px; display: flex; justify-content: space-between; font-size: 10px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); }}
  .folio .left {{ color: var(--ink); }}
  .folio .right {{ color: var(--muted); }}
  @media (max-width: 1100px) {{ .folio {{ display: none; }} }}

  /* Eyebrow roman */
  .eyebrow-roman {{ font-family: 'Source Serif 4', Georgia, serif; font-style: italic; font-size: var(--fs-md); font-weight: 500; letter-spacing: 0.02em; text-transform: none; color: var(--navy); }}
  .eyebrow-roman::before {{ content: ''; display: inline-block; width: 24px; height: 1px; background: var(--navy); vertical-align: middle; margin-right: 12px; }}

  /* Profile pill (aging / insurance) */
  .pill {{ display: inline-block; padding: 3px 8px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }}

  /* Definition card (metodologi page) */
  .def-card {{ border: 1px solid var(--rule); padding: 20px; background: white; }}
  .def-card .term {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 18px; font-weight: 600; color: var(--navy); }}
  .def-card .formula {{ font-family: 'Courier New', monospace; font-size: 12px; color: var(--ink-soft); background: var(--mist); padding: 6px 10px; margin-top: 10px; border-left: 2px solid var(--sky); }}
  .def-card .desc {{ font-size: 13px; color: var(--muted); margin-top: 10px; line-height: 1.55; }}

  *:focus-visible {{ outline: 2px solid var(--sky); outline-offset: 3px; border-radius: 1px; }}
  button {{ transition: all var(--tr-base); }}
</style>
</head>
<body>

<div x-data="dashboard()" x-init="init()">

<!-- Mobile topbar -->
<div class="topbar-mobile">
  <button @click="navOpen = true" aria-label="Buka menu"><iconify-icon icon="mdi:menu" style="font-size:24px;"></iconify-icon></button>
  <div>
    <div class="topbar-title">Demografi & Kesehatan</div>
    <div class="topbar-sub">Mandiri Institute</div>
  </div>
</div>

<div class="sidebar-overlay" :class="navOpen ? 'open' : ''" @click="navOpen = false"></div>

<aside class="sidebar" :class="navOpen ? 'open' : ''">
  <div class="brand">
    <a href="../index.html" style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--sky);text-transform:uppercase;letter-spacing:0.1em;font-weight:600;text-decoration:none;margin-bottom:10px;">
      <iconify-icon icon="mdi:arrow-left"></iconify-icon><span>Beranda</span>
    </a>
    <span class="yellow-accent"></span>
    <div class="brand-title">Mandiri Institute</div>
    <div class="brand-sub">Demografi &amp; Kesehatan</div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Halaman</div>
    <template x-for="t in tabs" :key="t.id">
      <button @click="setPage(t.id)" :class="page === t.id ? 'nav-item active' : 'nav-item'">
        <iconify-icon :icon="t.icon"></iconify-icon>
        <span x-text="t.label"></span>
      </button>
    </template>
  </div>
  <div class="crosslink">
    <div class="nav-label" style="padding:0 0 6px 0;">Cross-link</div>
    <a href="../mbg-gap-analysis/dashboard.html"><iconify-icon icon="mdi:food-apple"></iconify-icon><span>MBG Gap Analysis</span></a>
    <a href="../kelas-kabkota/dashboard.html"><iconify-icon icon="mdi:account-group"></iconify-icon><span>Kelas Masyarakat</span></a>
    <a href="../konsumsi-susenas/dashboard.html"><iconify-icon icon="mdi:cart-outline"></iconify-icon><span>Konsumsi Susenas</span></a>
  </div>
  <div class="footer">
    <div>{s['n_kabkota']} kab/kota &middot; Susenas 2025</div>
  </div>
</aside>

<div class="with-sidebar">

<div class="folio">
  <div class="folio-inner">
    <span class="left">Mandiri Institute &middot; Demografi & Kesehatan</span>
    <span class="right" x-text="page.toUpperCase()"></span>
  </div>
</div>

<div class="hero-band">
  <header class="max-w-[1280px] mx-auto px-8 pt-12 pb-12 md:pt-16 md:pb-16" style="position:relative;z-index:1;">
    <div class="eyebrow">Riset Mandiri Institute &middot; Demografi & Kesehatan</div>
    <h1 class="serif-display text-3xl md:text-5xl mt-5 max-w-4xl" x-text="pageTitle"></h1>
    <p class="mt-5 text-base max-w-3xl leading-relaxed" x-text="pageSubtitle"></p>
  </header>
</div>

<main class="dash-main max-w-[1280px] mx-auto px-8 pb-16">

  <!-- ============ PAGE 1: RINGKASAN ============ -->
  <section x-show="page === 'ringkasan'">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 rule-top pt-8">
      <div class="callout-card">
        <div class="label">Populasi 2025</div>
        <div class="num">{s['pop_total']/1e6:.1f}<span class="num-sub">jt</span></div>
        <div class="desc">{s['n_kabkota']} kab/kota Indonesia, weighted Susenas KOR.</div>
      </div>
      <div class="callout-card is-warn">
        <div class="label">Lansia 60+</div>
        <div class="num">{s['pct_lansia_avg']:.1f}<span class="num-sub">%</span></div>
        <div class="desc">{s['pop_lansia']/1e6:.1f} juta jiwa. Indonesia di fase aging-onset.</div>
      </div>
      <div class="callout-card is-pos">
        <div class="label">JKN Coverage</div>
        <div class="num">{s['pct_jkn_avg']:.1f}<span class="num-sub">%</span></div>
        <div class="desc">PBI {s['pct_jkn_pbi_avg']:.1f}% + non-PBI {s['pct_jkn_npbi_avg']:.1f}%. {s['pct_no_ins_avg']:.1f}% no insurance.</div>
      </div>
      <div class="callout-card is-bad">
        <div class="label">OOP Kesehatan</div>
        <div class="num">Rp {s['avg_oop_rp']/1000:.0f}<span class="num-sub">rb</span></div>
        <div class="desc">Per RT/bulan. {s['oop_burden_avg']:.1f}% dari konsumsi non-pangan.</div>
      </div>
    </div>

    <div class="mt-12 md:mt-16">
      <span class="badge"><span class="badge-dot"></span>Bubble Matrix</span>
      <div class="eyebrow-roman mt-3">I. Aging x Insurance Gap</div>
      <h2 class="serif-display text-2xl md:text-3xl mt-2 max-w-3xl">514 kab/kota dipetakan menurut beban demografi & gap proteksi.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Sumbu X: % lansia 60+. Sumbu Y: % populasi tanpa asuransi. Ukuran bubble: populasi total. Warna: profil aging.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div id="chart-bubble" style="height:560px;"></div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas KOR Maret 2025 (BPS)</span>
        <span><span class="label">Catatan</span>Kuadran kanan-atas = aging tinggi + gap proteksi besar (prioritas policy)</span>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-12 mt-12 md:mt-16 rule-top pt-10">
      <div class="rank-card">
        <div class="sub">Top 5 Aging</div>
        <h4>% Lansia 60+ tertinggi</h4>
        <div class="rank-list" id="topRingAging"></div>
      </div>
      <div class="rank-card">
        <div class="sub">Bottom 5 JKN</div>
        <h4>Coverage terendah</h4>
        <div class="rank-list" id="topRingJkn"></div>
      </div>
      <div class="rank-card">
        <div class="sub">Top 5 OOP Burden</div>
        <h4>Rasio OOP / non-pangan</h4>
        <div class="rank-list" id="topRingOop"></div>
      </div>
    </div>
  </section>

  <!-- ============ PAGE 2: DEMOGRAFI ============ -->
  <section x-show="page === 'demografi'">
    <div class="rule-top pt-8 flex flex-wrap items-end gap-6">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Wilayah</div>
        <select x-model="wilayah" @change="renderDemografiMap()" class="select-flat mt-2" style="min-width:170px;">
          <template x-for="w in wilayahList" :key="'wd'+w"><option :value="w" x-text="w"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Provinsi</div>
        <select x-model="provFilter" @change="renderDemografiMap()" class="select-flat mt-2" style="min-width:170px;">
          <option value="All">Semua provinsi</option>
          <template x-for="p in provOptions" :key="'pod'+p.pcode"><option :value="p.pcode" x-text="p.nama"></option></template>
        </select>
      </div>
    </div>

    <div class="mt-10 md:mt-12">
      <span class="badge"><span class="badge-dot"></span>{s['n_kabkota']} Kabupaten/Kota</span>
      <div class="eyebrow-roman mt-3">II. Demografi</div>
      <h2 class="serif-display text-2xl md:text-3xl mt-2 max-w-3xl">Aging onset menyebar tidak merata: Jateng, Jatim, DIY hotspot.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Choropleth % lansia 60+ per kabupaten/kota (BPS 2020 boundary). Klik bin di legenda untuk drill-down rangking.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div id="chart-demografi-map" style="height:680px;"></div>
      <div class="map-legend">
        <div class="map-legend-label">Share lansia 60+ (%)</div>
        <div class="map-legend-bins" id="legend-demografi"></div>
      </div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas KOR 2025 &middot; Shapefile BPS adm2 2020</span>
        <span><span class="label">Threshold</span>Aging-Mature ditetapkan pada >= 15% (UN classification)</span>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-10 mt-12 md:mt-16 rule-top pt-10">
      <div>
        <div class="sub" style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">Aging Profile Distribution</div>
        <h4 style="font-family:'Source Serif 4',serif;font-size:17px;font-weight:600;margin-bottom:4px;margin-top:4px;">Klasifikasi 514 kab/kota (UN/WHO threshold)</h4>
        <div id="chart-aging-bar" style="height:340px;"></div>
        <div class="chart-footer">
          <span><span class="label">Klasifikasi</span>Young &lt; 7% &middot; Aging-Early 7-10% &middot; Onset 10-15% &middot; Mature &gt;= 15%</span>
        </div>
      </div>
      <div>
        <div class="sub" style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">Komposisi Populasi Nasional</div>
        <h4 style="font-family:'Source Serif 4',serif;font-size:17px;font-weight:600;margin-bottom:4px;margin-top:4px;">Distribusi 5 cohort umur</h4>
        <div id="chart-pop-cohort" style="height:340px;"></div>
        <div class="chart-footer">
          <span><span class="label">Cohort</span>Balita 0-4 &middot; Anak 5-14 &middot; Remaja 15-24 &middot; Dewasa 25-59 &middot; Lansia 60+</span>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-10 mt-12 md:mt-16 rule-top pt-10">
      <div class="rank-card">
        <div class="sub">Top 10 Lansia</div>
        <h4>% lansia 60+ tertinggi</h4>
        <div class="rank-list" id="rank-lansia-top"></div>
      </div>
      <div class="rank-card">
        <div class="sub">Bottom 10 Lansia</div>
        <h4>Komposisi lansia terendah</h4>
        <div class="rank-list" id="rank-lansia-bottom"></div>
      </div>
    </div>
  </section>

  <!-- ============ PAGE 3: ASURANSI ============ -->
  <section x-show="page === 'asuransi'">
    <div class="rule-top pt-8 flex flex-wrap items-end gap-6">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Wilayah</div>
        <select x-model="wilayah" @change="renderAsuransiMap()" class="select-flat mt-2" style="min-width:170px;">
          <template x-for="w in wilayahList" :key="'wa'+w"><option :value="w" x-text="w"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Provinsi</div>
        <select x-model="provFilter" @change="renderAsuransiMap()" class="select-flat mt-2" style="min-width:170px;">
          <option value="All">Semua provinsi</option>
          <template x-for="p in provOptions" :key="'poa'+p.pcode"><option :value="p.pcode" x-text="p.nama"></option></template>
        </select>
      </div>
    </div>

    <div class="mt-10 md:mt-12">
      <span class="badge"><span class="badge-dot"></span>JKN Coverage</span>
      <div class="eyebrow-roman mt-3">III. Asuransi Kesehatan</div>
      <h2 class="serif-display text-2xl md:text-3xl mt-2 max-w-3xl">Coverage gap geografis: Indonesia Timur tertinggal jauh.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Choropleth % JKN total (PBI + non-PBI). Papua Tengah, Pegunungan, dan Maluku Utara di bin terendah; Jawa-Sumatra-Kalimantan didominasi >= 75%.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div id="chart-asuransi-map" style="height:680px;"></div>
      <div class="map-legend">
        <div class="map-legend-label">Share JKN total (%)</div>
        <div class="map-legend-bins" id="legend-asuransi"></div>
      </div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas KOR 2025 (PBI + non-PBI)</span>
        <span><span class="label">Catatan</span>Coverage survey 75.8% lebih rendah dari admin BPJS 85-90% (RT respondent effect)</span>
      </div>
    </div>

    <div class="mt-12 md:mt-16 rule-top pt-10">
      <span class="badge"><span class="badge-dot"></span>38 Provinsi</span>
      <div class="eyebrow-roman mt-3">III.B. Komposisi Asuransi per Provinsi</div>
      <h2 class="serif-display text-2xl md:text-3xl mt-2 max-w-3xl">PBI vs non-PBI vs Swasta vs No-Insurance.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Stacked bar 100% per provinsi, di-rank dari coverage terendah ke tertinggi.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div id="chart-prov-stack" style="height:780px;"></div>
      <div class="chart-footer">
        <span><span class="label">Bobot</span>Populasi 2025 per kab</span>
      </div>
    </div>

    <div class="mt-12 md:mt-16 rule-top pt-10">
      <div class="rank-card">
        <div class="sub">Bottom 15 Coverage</div>
        <h4>Kab/kota dengan gap proteksi terbesar (target intervensi)</h4>
        <div class="rank-list" id="rank-jkn-bottom"></div>
      </div>
    </div>
  </section>

  <!-- ============ PAGE 4: SPENDING ============ -->
  <section x-show="page === 'spending'">
    <div class="rule-top pt-8 flex flex-wrap items-end gap-6">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Wilayah</div>
        <select x-model="wilayah" @change="renderSpendingMap()" class="select-flat mt-2" style="min-width:170px;">
          <template x-for="w in wilayahList" :key="'ws'+w"><option :value="w" x-text="w"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Provinsi</div>
        <select x-model="provFilter" @change="renderSpendingMap()" class="select-flat mt-2" style="min-width:170px;">
          <option value="All">Semua provinsi</option>
          <template x-for="p in provOptions" :key="'pos'+p.pcode"><option :value="p.pcode" x-text="p.nama"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Tampilan</div>
        <div class="mt-2 flex gap-2">
          <button class="chip-action" :class="spendingMode === 'burden' ? 'active' : ''" @click="spendingMode = 'burden'; renderSpendingMap()">Burden (%)</button>
          <button class="chip-action" :class="spendingMode === 'rp' ? 'active' : ''" @click="spendingMode = 'rp'; renderSpendingMap()">Rupiah/bulan</button>
        </div>
      </div>
    </div>

    <div class="mt-10 md:mt-12">
      <span class="badge"><span class="badge-dot"></span>OOP Burden</span>
      <div class="eyebrow-roman mt-3">IV. Spending Kesehatan</div>
      <h2 class="serif-display text-2xl md:text-3xl mt-2 max-w-3xl">Beban OOP kesehatan per RT, % total konsumsi non-pangan.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Choropleth burden ratio. Burden tinggi tidak selalu match daerah miskin: Dairi, Majalengka, Kota Batu, Sampang masuk top.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div id="chart-spending-map" style="height:680px;"></div>
      <div class="map-legend">
        <div class="map-legend-label" x-text="spendingMode === 'burden' ? 'OOP / non-pangan (%)' : 'OOP nominal Rp/bulan'"></div>
        <div class="map-legend-bins" id="legend-spending"></div>
      </div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas KP Blok 4.2 2025</span>
        <span><span class="label">Komponen OOP</span>Rawat inap + jalan + obat + premi (premi ~60%)</span>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-10 mt-12 md:mt-16 rule-top pt-10">
      <div>
        <div class="sub" style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">Komposisi OOP Nasional</div>
        <h4 style="font-family:'Source Serif 4',serif;font-size:17px;font-weight:600;margin-bottom:4px;margin-top:4px;">Rata-rata Rp/RT/bulan</h4>
        <div id="chart-oop-donut" style="height:380px;"></div>
        <div class="chart-footer">
          <span><span class="label">Catatan</span>Premi asuransi dominan; "true" OOP (inap + jalan + obat) hanya 40%</span>
        </div>
      </div>
      <div>
        <div class="sub" style="font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">Scatter OOP x Coverage</div>
        <h4 style="font-family:'Source Serif 4',serif;font-size:17px;font-weight:600;margin-bottom:4px;margin-top:4px;">Apakah JKN tinggi mengurangi OOP?</h4>
        <div id="chart-oop-scatter" style="height:380px;"></div>
        <div class="chart-footer">
          <span><span class="label">X axis</span>% JKN coverage &middot; <span class="label">Y axis</span>OOP nominal</span>
        </div>
      </div>
    </div>

    <div class="mt-12 md:mt-16 rule-top pt-10">
      <div class="rank-card">
        <div class="sub">Top 10 OOP Burden</div>
        <h4>Rasio OOP terhadap non-pangan tertinggi</h4>
        <div class="rank-list" id="rank-oop-top"></div>
      </div>
    </div>
  </section>

  <!-- ============ PAGE 5: METODOLOGI ============ -->
  <section x-show="page === 'metodologi'">
    <div class="rule-top pt-8">
      <span class="badge"><span class="badge-dot"></span>Methodology</span>
      <div class="eyebrow-roman mt-3">V. Metodologi & Definisi</div>
      <h2 class="serif-display text-2xl md:text-3xl mt-2 max-w-3xl">Susenas Maret 2025 KOR + KP, weighted estimation per kab/kota.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Dokumentasi sumber data, formula derived metric, threshold klasifikasi, dan caveats interpretasi.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-10">
      <div class="def-card">
        <div class="term">Sumber Data</div>
        <div class="desc">
          <strong>Susenas KOR Maret 2025 (BPS)</strong> &mdash; Individu &amp; Rumah Tangga, weighted via <code>weind</code> (individu) dan <code>wert</code> (RT). Cakupan 514 kab/kota di 38 provinsi, populasi tertimbang 281,62 juta jiwa.<br><br>
          <strong>Susenas KP Maret 2025 (BPS)</strong> &mdash; Modul Konsumsi/Pengeluaran, Blok 4.2 komoditi kesehatan. Output: avg Rp/RT/bulan untuk 4 komponen: rawat inap, rawat jalan, obat, premi asuransi kesehatan.
        </div>
      </div>

      <div class="def-card">
        <div class="term">% Lansia 60+</div>
        <div class="formula">pct_lansia_60 = pop_lansia_60_plus / pop_total_2025</div>
        <div class="desc">Rasio populasi 60 tahun ke atas terhadap populasi total. Threshold UN: Young &lt; 7%, Aging-Early 7-10%, Aging-Onset 10-15%, Aging-Mature &gt;= 15%. Indonesia secara nasional di {s['pct_lansia_avg']:.1f}% (Aging-Onset).</div>
      </div>

      <div class="def-card">
        <div class="term">Aging Index</div>
        <div class="formula">aging_index = (lansia_60+ / anak_0-14) * 100</div>
        <div class="desc">Rasio lansia terhadap anak. Nilai &gt; 100 = jumlah lansia melampaui anak. Median nasional: {s['aging_idx_med']:.1f}.</div>
      </div>

      <div class="def-card">
        <div class="term">Dependency Ratio</div>
        <div class="formula">dep_ratio = (anak 0-14 + lansia 60+) / dewasa 25-59 * 100</div>
        <div class="desc">Setiap 100 penduduk usia produktif menanggung X penduduk non-produktif. Rata-rata nasional weighted: {s['dep_ratio_avg']:.1f}.</div>
      </div>

      <div class="def-card">
        <div class="term">JKN Total Coverage</div>
        <div class="formula">pct_jkn_total = pct_jkn_pbi + pct_jkn_non_pbi</div>
        <div class="desc">Pengakuan respondent RT bahwa anggota memiliki kartu JKN (PBI dari pemerintah atau non-PBI mandiri). Klasifikasi: Very Low &lt; 50%, Low 50-75%, Medium 75-90%, High &gt;= 90%.</div>
      </div>

      <div class="def-card">
        <div class="term">OOP Burden Ratio</div>
        <div class="formula">oop_pct_total_nonfood = avg_oop_health / avg_total_nonfood</div>
        <div class="desc">Pangsa pengeluaran kesehatan dalam total pengeluaran non-pangan rumah tangga. Burden &gt;= 10% sering dikategorikan financial hardship (WHO catastrophic health expenditure proxy).</div>
      </div>
    </div>

    <div class="mt-12 md:mt-16 rule-top pt-10">
      <span class="badge"><span class="badge-dot"></span>Caveats</span>
      <h2 class="serif-display text-xl md:text-2xl mt-3 max-w-3xl">Hal yang perlu hati-hati saat membaca angka.</h2>
      <ul class="mt-6 space-y-3 text-sm" style="color:var(--ink-soft);line-height:1.6;max-width:780px;">
        <li><strong style="color:var(--ink);">Survey vs admin gap.</strong> JKN coverage Susenas 75.8% lebih rendah dari admin BPJS 85-90%. Survey effect normal: respondent RT belum tentu tahu detail status JKN setiap anggota.</li>
        <li><strong style="color:var(--ink);">OOP termasuk premi.</strong> Komponen premi (Rp {s['avg_premi']/1000:.0f}rb) dominan ~60% dari total OOP Rp {s['avg_oop_rp']/1000:.0f}rb. "True" OOP (inap + jalan + obat) hanya ~40%.</li>
        <li><strong style="color:var(--ink);">Dependency ratio interpretasi.</strong> Indonesia masih demographic dividend window, namun dependency naik karena aging onset. Bukan hanya beban anak (dropping fertility) tapi juga beban lansia (rising longevity).</li>
        <li><strong style="color:var(--ink);">Sample size kabkota kecil.</strong> Beberapa kabkota pemekaran punya sample sangat kecil (n &lt; 100). Validate dengan kolom <code>n_sample_total</code> sebelum cross-tab.</li>
        <li><strong style="color:var(--ink);">pct_no_insurance edge cases.</strong> Bisa = 100% di kabkota dengan sample sangat tipis. Jangan generalisasi ke seluruh penduduk kabkota tanpa cek confidence.</li>
      </ul>
    </div>

    <div class="mt-12 md:mt-16 rule-top pt-10">
      <span class="badge"><span class="badge-dot"></span>Cross-link</span>
      <h2 class="serif-display text-xl md:text-2xl mt-3 max-w-3xl">Dashboard Mandiri Institute terkait.</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <a href="../mbg-gap-analysis/dashboard.html" class="def-card" style="text-decoration:none;display:block;">
          <div class="term" style="display:flex;align-items:center;gap:8px;"><iconify-icon icon="mdi:food-apple"></iconify-icon>MBG Gap Analysis</div>
          <div class="desc">Sasaran balita 0-4 tahun (program MBG). Cross-overlay dengan demografi balita per kab/kota di dashboard ini.</div>
        </a>
        <a href="../kelas-kabkota/dashboard.html" class="def-card" style="text-decoration:none;display:block;">
          <div class="term" style="display:flex;align-items:center;gap:8px;"><iconify-icon icon="mdi:account-group"></iconify-icon>Kelas Masyarakat</div>
          <div class="desc">8 kelas wb4 per kab/kota 2019-2025. Overlay kelas dengan profil kesehatan untuk segmentasi target intervensi.</div>
        </a>
        <a href="../konsumsi-susenas/dashboard.html" class="def-card" style="text-decoration:none;display:block;">
          <div class="term" style="display:flex;align-items:center;gap:8px;"><iconify-icon icon="mdi:cart-outline"></iconify-icon>Konsumsi Susenas</div>
          <div class="desc">Pola konsumsi RT lintas kelas dan wilayah. Kontekstualisasi OOP kesehatan dalam total konsumsi.</div>
        </a>
      </div>
    </div>
  </section>

  <footer class="rule-top mt-16 pt-8 pb-4 flex flex-wrap items-center justify-between gap-4 text-xs muted uppercase tracking-widest">
    <div>Mandiri Institute &middot; Demografi & Kesehatan</div>
    <div>Generated {generated}</div>
    <div>Susenas KOR + KP Maret 2025 (BPS)</div>
  </footer>
</main>
</div>
</div>

<script>
const SUMMARY = {json.dumps(payload['summary'])};
const KAB     = {json.dumps(payload['kab'], separators=(',',':'))};
const PROV    = {json.dumps(payload['prov'], separators=(',',':'))};
const AGING_DIST     = {json.dumps(payload['aging_dist'])};
const INSURANCE_DIST = {json.dumps(payload['insurance_dist'])};
const GEOJSON = {json.dumps(geojson, separators=(',',':'))};

const AGING_ORDER = {json.dumps(AGING_ORDER)};
const AGING_COLORS = {json.dumps(AGING_COLORS)};
const INSURANCE_ORDER = {json.dumps(INSURANCE_ORDER)};
const INSURANCE_COLORS = {json.dumps(INSURANCE_COLORS)};

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
const MAP_OUTLIER_KABS = new Set(['ID3101']); // Kep Seribu

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
  const minLon = pct(lons, 0.025), maxLon = pct(lons, 0.975);
  const minLat = pct(lats, 0.025), maxLat = pct(lats, 0.975);
  const dLon = Math.max((maxLon-minLon) * 0.08, 0.05);
  const dLat = Math.max((maxLat-minLat) * 0.08, 0.05);
  return {{ lon: [minLon-dLon, maxLon+dLon], lat: [minLat-dLat, maxLat+dLat] }};
}}

function computeBins(values) {{
  const sorted = values.filter(v => v != null && !isNaN(v)).slice().sort((a, b) => a - b);
  if (sorted.length === 0) return {{ edges: [0,0,0,0,0,1] }};
  const q = (p) => sorted[Math.min(Math.floor(p * (sorted.length - 1)), sorted.length - 1)];
  return {{ edges: [sorted[0], q(0.2), q(0.4), q(0.6), q(0.8), sorted[sorted.length - 1]] }};
}}
function fmtPct(v) {{ return (v == null || isNaN(v)) ? '-' : v.toFixed(1) + '%'; }}
function fmtNum(v) {{
  if (v == null || isNaN(v)) return '-';
  if (v >= 1000000) return (v/1000000).toFixed(2) + ' jt';
  if (v >= 1000) return (v/1000).toFixed(0) + ' rb';
  return Math.round(v).toString();
}}
function fmtRp(v) {{ if (v == null || isNaN(v)) return '-'; return 'Rp ' + Math.round(v/1000).toLocaleString('id-ID') + ' rb'; }}

const TABS = [
  {{ id: 'ringkasan',  label: 'Ringkasan',   icon: 'mdi:view-dashboard-outline' }},
  {{ id: 'demografi',  label: 'Demografi',   icon: 'mdi:account-group-outline' }},
  {{ id: 'asuransi',   label: 'Asuransi',    icon: 'mdi:shield-check-outline' }},
  {{ id: 'spending',   label: 'Spending',    icon: 'mdi:cash-multiple' }},
  {{ id: 'metodologi', label: 'Metodologi',  icon: 'mdi:book-open-page-variant' }},
];
const PAGE_META = {{
  ringkasan: {{ title: '281,6 juta jiwa, lansia 12,3% (aging-onset), JKN 75,8%, OOP Rp 242 rb/bulan.',
               sub: 'Snapshot demografi & kesehatan 514 kab/kota Indonesia, Susenas Maret 2025 (KOR + KP).' }},
  demografi: {{ title: 'Profil demografi: Indonesia di fase aging-onset.',
               sub: 'Sebaran lansia, balita, dependency ratio, dan profil aging per kabupaten/kota.' }},
  asuransi:  {{ title: 'JKN coverage: gap geografis tajam ke Indonesia Timur.',
               sub: 'PBI + non-PBI + asuransi swasta. Bottom 10 dominasi Papua Tengah, Pegunungan, Maluku Utara.' }},
  spending:  {{ title: 'Beban out-of-pocket kesehatan rumah tangga.',
               sub: 'Komponen OOP, burden ratio terhadap konsumsi non-pangan, relasi dengan JKN coverage.' }},
  metodologi: {{ title: 'Sumber data, definisi metric, dan caveats interpretasi.',
                 sub: 'Susenas KOR + KP 2025, klasifikasi UN aging, threshold WHO catastrophic health.' }},
}};

function dashboard() {{
  const kabByPcode = Object.fromEntries(KAB.map(r => [r.pcode, r]));
  return {{
    tabs: TABS, page: 'ringkasan',
    pageRendered: {{}},
    navOpen: false,
    wilayah: 'Indonesia', wilayahList: Object.keys(REGION_PROVS), provFilter: 'All',
    spendingMode: 'burden',
    get provOptions() {{
      const codes = REGION_PROVS[this.wilayah];
      const provMap = {{}};
      KAB.forEach(r => {{
        const pc = pcodeProvCode(r.pcode);
        if (!provMap[pc] && (!codes || codes.includes(pc))) provMap[pc] = r.nama_prov;
      }});
      return Object.entries(provMap).sort((a,b) => a[1].localeCompare(b[1])).map(([pc, n]) => ({{ pcode: pc, nama: n }}));
    }},
    get pageTitle() {{ return PAGE_META[this.page].title; }},
    get pageSubtitle() {{ return PAGE_META[this.page].sub; }},
    init() {{
      this.$nextTick(() => this.renderForPage(this.page));
    }},
    setPage(id) {{
      this.page = id;
      this.navOpen = false;
      this.renderForPage(id);
    }},
    renderForPage(id) {{
      requestAnimationFrame(() => requestAnimationFrame(() => {{
        if (id === 'ringkasan') this.renderRingkasan();
        else if (id === 'demografi') this.renderDemografi();
        else if (id === 'asuransi') this.renderAsuransi();
        else if (id === 'spending') this.renderSpending();
        // metodologi has no charts
      }}));
    }},

    /* ========== RANK HELPERS ========== */
    renderRankList(elId, rows, valFmt, isBottom) {{
      const el = document.getElementById(elId);
      if (!el || !rows.length) return;
      const max = Math.max(...rows.map(r => r.value));
      el.innerHTML = rows.map((r, i) => `
        <div class="rank-row${{isBottom ? ' is-bottom' : ''}}">
          <div class="rank-num">${{i+1}}</div>
          <div class="rank-name">
            <span>${{r.nama_kab}}</span>
            <span class="sub-prov">${{r.nama_prov}}</span>
          </div>
          <div class="rank-cell-right">
            <div class="rank-bar-wrap" style="width: 110px;">
              <div class="rank-bar" style="width: ${{(r.value/max*100).toFixed(1)}}%"></div>
            </div>
            <div class="rank-val">${{valFmt(r.value)}}</div>
          </div>
        </div>`).join('');
    }},

    /* ========== PAGE 1: RINGKASAN ========== */
    renderRingkasan() {{
      // Bubble matrix: x = pct_lansia, y = pct_no_ins, size = pop, color = aging_profile
      const traces = AGING_ORDER.map(prof => {{
        const subset = KAB.filter(r => r.aging_profile === prof);
        return {{
          x: subset.map(r => r.pct_lansia),
          y: subset.map(r => r.pct_no_ins),
          mode: 'markers',
          type: 'scatter',
          name: prof,
          marker: {{
            color: AGING_COLORS[prof] || '#999',
            size: subset.map(r => Math.sqrt(r.pop) / 80),
            sizemode: 'diameter',
            sizemin: 4,
            opacity: 0.65,
            line: {{ width: 0.5, color: 'white' }},
          }},
          text: subset.map(r => r.nama_kab + '<br>' + r.nama_prov),
          customdata: subset.map(r => [r.pop, r.pct_jkn, r.oop_burden]),
          hovertemplate: '<b>%{{text}}</b><br>' +
                         'Lansia: %{{x:.1f}}%<br>' +
                         'No-insurance: %{{y:.1f}}%<br>' +
                         'JKN: %{{customdata[1]:.1f}}%<br>' +
                         'OOP burden: %{{customdata[2]:.1f}}%<br>' +
                         'Pop: %{{customdata[0]:,.0f}}<extra></extra>',
        }};
      }});
      Plotly.react('chart-bubble', traces, {{
        margin: {{ l: 60, r: 30, t: 20, b: 80 }},
        font: {{ family: FONT, size: 13, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ title: {{ text: '% Lansia 60+ (aging burden)', font: {{ size: 12, color: MUTED }} }},
                 tickfont: {{ size: 11, color: MUTED }}, gridcolor: '#EAECF0', showline: true, linecolor: INK }},
        yaxis: {{ title: {{ text: '% Tanpa asuransi (insurance gap)', font: {{ size: 12, color: MUTED }} }},
                 tickfont: {{ size: 11, color: MUTED }}, gridcolor: '#EAECF0' }},
        legend: {{ orientation: 'h', y: -0.18, x: 0, xanchor: 'left', font: {{ size: 11 }} }},
        shapes: [
          {{ type: 'line', x0: SUMMARY.pct_lansia_avg, x1: SUMMARY.pct_lansia_avg, y0: 0, y1: 1, yref: 'paper', line: {{ color: '#999', width: 1, dash: 'dot' }} }},
          {{ type: 'line', x0: 0, x1: 1, y0: SUMMARY.pct_no_ins_avg, y1: SUMMARY.pct_no_ins_avg, xref: 'paper', line: {{ color: '#999', width: 1, dash: 'dot' }} }},
        ],
        annotations: [
          {{ x: SUMMARY.pct_lansia_avg, y: 1, yref: 'paper', text: ' avg lansia ' + SUMMARY.pct_lansia_avg.toFixed(1) + '%', showarrow: false, font: {{ size: 10, color: MUTED }}, xanchor: 'left', yanchor: 'top' }},
          {{ x: 1, y: SUMMARY.pct_no_ins_avg, xref: 'paper', text: 'avg no-ins ' + SUMMARY.pct_no_ins_avg.toFixed(1) + '% ', showarrow: false, font: {{ size: 10, color: MUTED }}, xanchor: 'right', yanchor: 'bottom' }},
        ],
      }}, {{ displaylogo: false, responsive: true }});

      // Top 5 ranking lists
      const topAging = [...KAB].sort((a,b) => b.pct_lansia - a.pct_lansia).slice(0,5)
        .map(r => ({{ nama_kab: r.nama_kab, nama_prov: r.nama_prov, value: r.pct_lansia }}));
      const bottomJkn = [...KAB].sort((a,b) => a.pct_jkn - b.pct_jkn).slice(0,5)
        .map(r => ({{ nama_kab: r.nama_kab, nama_prov: r.nama_prov, value: r.pct_jkn }}));
      const topOop = [...KAB].sort((a,b) => b.oop_burden - a.oop_burden).slice(0,5)
        .map(r => ({{ nama_kab: r.nama_kab, nama_prov: r.nama_prov, value: r.oop_burden }}));
      this.renderRankList('topRingAging', topAging, fmtPct, false);
      this.renderRankList('topRingJkn', bottomJkn, fmtPct, true);
      this.renderRankList('topRingOop', topOop, fmtPct, true);
    }},

    /* ========== PAGE 2: DEMOGRAFI ========== */
    renderDemografi() {{
      this.renderDemografiMap();
      this.renderAgingBar();
      this.renderPopCohort();

      const top = [...KAB].sort((a,b) => b.pct_lansia - a.pct_lansia).slice(0,10)
        .map(r => ({{ nama_kab: r.nama_kab, nama_prov: r.nama_prov, value: r.pct_lansia }}));
      const bot = [...KAB].sort((a,b) => a.pct_lansia - b.pct_lansia).slice(0,10)
        .map(r => ({{ nama_kab: r.nama_kab, nama_prov: r.nama_prov, value: r.pct_lansia }}));
      this.renderRankList('rank-lansia-top', top, fmtPct, false);
      this.renderRankList('rank-lansia-bottom', bot, fmtPct, true);
    }},
    renderDemografiMap() {{
      const filtered = KAB.filter(r => inRegion(r.pcode, this.wilayah, this.provFilter) && !MAP_OUTLIER_KABS.has(r.pcode));
      const locs = filtered.map(r => r.pcode);
      const vals = filtered.map(r => r.pct_lansia);
      const allowedSet = new Set(locs);
      const filteredGJ = {{ type: 'FeatureCollection', features: GEOJSON.features.filter(f => allowedSet.has(f.id)) }};
      const bins = computeBins(vals);
      const palette = ['#E8EFF6','#A9C4DF','#67B2E8','#FFB700','#C8102E'];
      const colorscale = [
        [0.0, palette[0]], [0.2-1e-9, palette[0]],
        [0.2, palette[1]], [0.4-1e-9, palette[1]],
        [0.4, palette[2]], [0.6-1e-9, palette[2]],
        [0.6, palette[3]], [0.8-1e-9, palette[3]],
        [0.8, palette[4]], [1.0, palette[4]],
      ];
      const hovertext = filtered.map(r =>
        `<b>${{r.nama_kab}}</b><br><span style="color:#667085">${{r.nama_prov}}</span><br>` +
        `<span style="color:#003D79;font-size:18px;font-weight:600">${{r.pct_lansia.toFixed(1)}}%</span> lansia 60+<br>` +
        `<span style="color:#667085">Pop ${{(r.pop/1000).toFixed(0)}}rb &middot; Profil: ${{r.aging_profile}}</span><br>` +
        `<span style="color:#667085">Dep ratio ${{r.dep_ratio.toFixed(0)}} &middot; Aging idx ${{r.aging_idx.toFixed(0)}}</span>`);
      const borderWidth = locs.length < 50 ? 0.4 : (locs.length < 200 ? 0.3 : 0.2);
      Plotly.react('chart-demografi-map', [{{
        type: 'choropleth', geojson: filteredGJ, locations: locs, z: vals,
        featureidkey: 'properties.ADM2_PCODE',
        zmin: bins.edges[0], zmax: bins.edges[5],
        colorscale, showscale: false,
        marker: {{ line: {{ color: '#FFFFFF', width: borderWidth }} }},
        hovertext, hovertemplate: '%{{hovertext}}<extra></extra>',
        hoverlabel: {{ bgcolor: 'white', bordercolor: '#003D79', font: {{ family: FONT, size: 13, color: INK }}, align: 'left', namelength: -1 }},
      }}], {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        font: {{ family: FONT, color: INK }},
        geo: (() => {{
          const bbox = tightBbox(filteredGJ.features);
          return {{ visible: false, bgcolor: '#FAFBFC', projection: {{ type: 'mercator' }},
                   ...(bbox ? {{ lonaxis: {{ range: bbox.lon, autorange: false }},
                                 lataxis: {{ range: bbox.lat, autorange: false }} }}
                            : {{ fitbounds: 'locations' }}),
                   uirevision: this.wilayah + '|' + this.provFilter }};
        }})(),
        paper_bgcolor: 'transparent',
      }}, {{ displaylogo: false, responsive: true }});

      const el = document.getElementById('legend-demografi');
      if (el) el.innerHTML = palette.map((c, i) => {{
        const lo = bins.edges[i];
        return `<div class="map-legend-bin"><div class="swatch" style="background:${{c}}"></div><div class="range">${{lo.toFixed(1)}}%${{i===4?'+':''}}</div></div>`;
      }}).join('');
    }},
    renderAgingBar() {{
      const labels = AGING_ORDER;
      const counts = labels.map(k => AGING_DIST[k] || 0);
      const colors = labels.map(k => AGING_COLORS[k]);
      Plotly.react('chart-aging-bar', [{{
        x: counts, y: labels, type: 'bar', orientation: 'h',
        marker: {{ color: colors }},
        text: counts.map(c => c.toString()),
        textposition: 'outside',
        textfont: {{ size: 12, color: INK }},
        hovertemplate: '%{{y}}<br>%{{x}} kab/kota<extra></extra>',
      }}], {{
        margin: {{ l: 170, r: 50, t: 20, b: 40 }},
        font: {{ family: FONT, size: 12, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ title: {{ text: 'Jumlah kab/kota', font: {{ size: 11, color: MUTED }} }}, gridcolor: '#EAECF0' }},
        yaxis: {{ tickfont: {{ size: 12, color: INK }} }},
        showlegend: false,
      }}, {{ displaylogo: false, responsive: true }});
    }},
    renderPopCohort() {{
      const cohorts = [
        {{ name: 'Balita 0-4',  value: SUMMARY.pop_balita, color: '#67B2E8' }},
        {{ name: 'Anak 5-14',   value: SUMMARY.pop_anak,   color: '#A9C4DF' }},
        {{ name: 'Remaja 15-24',value: SUMMARY.pop_remaja, color: '#1A5394' }},
        {{ name: 'Dewasa 25-59',value: SUMMARY.pop_dewasa, color: '#003D79' }},
        {{ name: 'Lansia 60+',  value: SUMMARY.pop_lansia, color: '#FFB700' }},
      ];
      const total = cohorts.reduce((s,c) => s + c.value, 0);
      Plotly.react('chart-pop-cohort', [{{
        x: cohorts.map(c => c.name),
        y: cohorts.map(c => c.value/1e6),
        type: 'bar',
        marker: {{ color: cohorts.map(c => c.color) }},
        text: cohorts.map(c => (c.value/total*100).toFixed(1) + '%'),
        textposition: 'outside',
        textfont: {{ size: 12, color: INK }},
        hovertemplate: '%{{x}}<br>%{{y:.1f}} jt jiwa<extra></extra>',
      }}], {{
        margin: {{ l: 60, r: 30, t: 30, b: 60 }},
        font: {{ family: FONT, size: 12, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ tickfont: {{ size: 11, color: INK }} }},
        yaxis: {{ title: {{ text: 'Populasi (juta)', font: {{ size: 11, color: MUTED }} }}, gridcolor: '#EAECF0' }},
        showlegend: false,
      }}, {{ displaylogo: false, responsive: true }});
    }},

    /* ========== PAGE 3: ASURANSI ========== */
    renderAsuransi() {{
      this.renderAsuransiMap();
      this.renderProvStack();
      const bot = [...KAB].sort((a,b) => a.pct_jkn - b.pct_jkn).slice(0,15)
        .map(r => ({{ nama_kab: r.nama_kab, nama_prov: r.nama_prov, value: r.pct_jkn }}));
      this.renderRankList('rank-jkn-bottom', bot, fmtPct, true);
    }},
    renderAsuransiMap() {{
      const filtered = KAB.filter(r => inRegion(r.pcode, this.wilayah, this.provFilter) && !MAP_OUTLIER_KABS.has(r.pcode));
      const locs = filtered.map(r => r.pcode);
      const vals = filtered.map(r => r.pct_jkn);
      const allowedSet = new Set(locs);
      const filteredGJ = {{ type: 'FeatureCollection', features: GEOJSON.features.filter(f => allowedSet.has(f.id)) }};
      const bins = computeBins(vals);
      // Inverted scale: low coverage = red (bad), high = navy (good)
      const palette = ['#C8102E','#EA7200','#FFB700','#67B2E8','#003D79'];
      const colorscale = [
        [0.0, palette[0]], [0.2-1e-9, palette[0]],
        [0.2, palette[1]], [0.4-1e-9, palette[1]],
        [0.4, palette[2]], [0.6-1e-9, palette[2]],
        [0.6, palette[3]], [0.8-1e-9, palette[3]],
        [0.8, palette[4]], [1.0, palette[4]],
      ];
      const hovertext = filtered.map(r =>
        `<b>${{r.nama_kab}}</b><br><span style="color:#667085">${{r.nama_prov}}</span><br>` +
        `<span style="color:#003D79;font-size:18px;font-weight:600">${{r.pct_jkn.toFixed(1)}}%</span> JKN<br>` +
        `<span style="color:#667085">PBI ${{r.pct_jkn_pbi.toFixed(1)}}% &middot; non-PBI ${{r.pct_jkn_npbi.toFixed(1)}}% &middot; Swasta ${{r.pct_swasta.toFixed(1)}}%</span><br>` +
        `<span style="color:#C8102E">No-ins ${{r.pct_no_ins.toFixed(1)}}%</span> &middot; Profil: ${{r.ins_profile}}`);
      const borderWidth = locs.length < 50 ? 0.4 : (locs.length < 200 ? 0.3 : 0.2);
      Plotly.react('chart-asuransi-map', [{{
        type: 'choropleth', geojson: filteredGJ, locations: locs, z: vals,
        featureidkey: 'properties.ADM2_PCODE',
        zmin: bins.edges[0], zmax: bins.edges[5],
        colorscale, showscale: false,
        marker: {{ line: {{ color: '#FFFFFF', width: borderWidth }} }},
        hovertext, hovertemplate: '%{{hovertext}}<extra></extra>',
        hoverlabel: {{ bgcolor: 'white', bordercolor: '#003D79', font: {{ family: FONT, size: 13, color: INK }}, align: 'left', namelength: -1 }},
      }}], {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        font: {{ family: FONT, color: INK }},
        geo: (() => {{
          const bbox = tightBbox(filteredGJ.features);
          return {{ visible: false, bgcolor: '#FAFBFC', projection: {{ type: 'mercator' }},
                   ...(bbox ? {{ lonaxis: {{ range: bbox.lon, autorange: false }},
                                 lataxis: {{ range: bbox.lat, autorange: false }} }}
                            : {{ fitbounds: 'locations' }}),
                   uirevision: this.wilayah + '|' + this.provFilter }};
        }})(),
        paper_bgcolor: 'transparent',
      }}, {{ displaylogo: false, responsive: true }});

      const el = document.getElementById('legend-asuransi');
      if (el) el.innerHTML = palette.map((c, i) => {{
        const lo = bins.edges[i];
        return `<div class="map-legend-bin"><div class="swatch" style="background:${{c}}"></div><div class="range">${{lo.toFixed(0)}}%${{i===4?'+':''}}</div></div>`;
      }}).join('');
    }},
    renderProvStack() {{
      const provs = PROV.slice();  // already sorted by jkn_total ascending
      const traces = [
        {{ x: provs.map(p => p.jkn_pbi),  y: provs.map(p => p.nama_prov), name: 'JKN PBI',
           type: 'bar', orientation: 'h', marker: {{ color: '#003D79' }},
           hovertemplate: '<b>%{{y}}</b><br>JKN PBI: %{{x:.1f}}%<extra></extra>' }},
        {{ x: provs.map(p => p.jkn_npbi), y: provs.map(p => p.nama_prov), name: 'JKN non-PBI',
           type: 'bar', orientation: 'h', marker: {{ color: '#67B2E8' }},
           hovertemplate: '<b>%{{y}}</b><br>JKN non-PBI: %{{x:.1f}}%<extra></extra>' }},
        {{ x: provs.map(p => p.swasta),   y: provs.map(p => p.nama_prov), name: 'Asuransi Swasta',
           type: 'bar', orientation: 'h', marker: {{ color: '#FFB700' }},
           hovertemplate: '<b>%{{y}}</b><br>Swasta: %{{x:.1f}}%<extra></extra>' }},
        {{ x: provs.map(p => p.none),     y: provs.map(p => p.nama_prov), name: 'Tanpa asuransi',
           type: 'bar', orientation: 'h', marker: {{ color: '#C8102E' }},
           hovertemplate: '<b>%{{y}}</b><br>No insurance: %{{x:.1f}}%<extra></extra>' }},
      ];
      Plotly.react('chart-prov-stack', traces, {{
        barmode: 'stack',
        margin: {{ l: 180, r: 30, t: 20, b: 60 }},
        font: {{ family: FONT, size: 11, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ title: {{ text: 'Share (%)', font: {{ size: 11, color: MUTED }} }}, gridcolor: '#EAECF0', range: [0, 110] }},
        yaxis: {{ tickfont: {{ size: 11, color: INK }} }},
        legend: {{ orientation: 'h', y: -0.06, x: 0, xanchor: 'left', font: {{ size: 11 }} }},
      }}, {{ displaylogo: false, responsive: true }});
    }},

    /* ========== PAGE 4: SPENDING ========== */
    renderSpending() {{
      this.renderSpendingMap();
      this.renderOopDonut();
      this.renderOopScatter();
      const top = [...KAB].sort((a,b) => b.oop_burden - a.oop_burden).slice(0,10)
        .map(r => ({{ nama_kab: r.nama_kab, nama_prov: r.nama_prov, value: r.oop_burden }}));
      this.renderRankList('rank-oop-top', top, fmtPct, false);
    }},
    renderSpendingMap() {{
      const filtered = KAB.filter(r => inRegion(r.pcode, this.wilayah, this.provFilter) && !MAP_OUTLIER_KABS.has(r.pcode));
      const locs = filtered.map(r => r.pcode);
      const useBurden = this.spendingMode === 'burden';
      const vals = filtered.map(r => useBurden ? r.oop_burden : r.oop_rp);
      const allowedSet = new Set(locs);
      const filteredGJ = {{ type: 'FeatureCollection', features: GEOJSON.features.filter(f => allowedSet.has(f.id)) }};
      const bins = computeBins(vals);
      const palette = ['#FFEEEE','#FFCCCC','#FF8888','#E63950','#C8102E'];
      const colorscale = [
        [0.0, palette[0]], [0.2-1e-9, palette[0]],
        [0.2, palette[1]], [0.4-1e-9, palette[1]],
        [0.4, palette[2]], [0.6-1e-9, palette[2]],
        [0.6, palette[3]], [0.8-1e-9, palette[3]],
        [0.8, palette[4]], [1.0, palette[4]],
      ];
      const fmt = useBurden ? (v) => v.toFixed(1) + '%' : (v) => 'Rp ' + (v/1000).toFixed(0) + 'rb';
      const hovertext = filtered.map(r =>
        `<b>${{r.nama_kab}}</b><br><span style="color:#667085">${{r.nama_prov}}</span><br>` +
        `<span style="color:#C8102E;font-size:18px;font-weight:600">${{useBurden ? r.oop_burden.toFixed(1)+'%' : 'Rp '+(r.oop_rp/1000).toFixed(0)+'rb'}}</span><br>` +
        `<span style="color:#667085">OOP nominal Rp ${{(r.oop_rp/1000).toFixed(0)}}rb &middot; Burden ${{r.oop_burden.toFixed(1)}}%</span><br>` +
        `<span style="color:#667085">Premi ${{(r.oop_premi/1000).toFixed(0)}}rb &middot; JKN ${{r.pct_jkn.toFixed(1)}}%</span>`);
      const borderWidth = locs.length < 50 ? 0.4 : (locs.length < 200 ? 0.3 : 0.2);
      Plotly.react('chart-spending-map', [{{
        type: 'choropleth', geojson: filteredGJ, locations: locs, z: vals,
        featureidkey: 'properties.ADM2_PCODE',
        zmin: bins.edges[0], zmax: bins.edges[5],
        colorscale, showscale: false,
        marker: {{ line: {{ color: '#FFFFFF', width: borderWidth }} }},
        hovertext, hovertemplate: '%{{hovertext}}<extra></extra>',
        hoverlabel: {{ bgcolor: 'white', bordercolor: '#C8102E', font: {{ family: FONT, size: 13, color: INK }}, align: 'left', namelength: -1 }},
      }}], {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        font: {{ family: FONT, color: INK }},
        geo: (() => {{
          const bbox = tightBbox(filteredGJ.features);
          return {{ visible: false, bgcolor: '#FAFBFC', projection: {{ type: 'mercator' }},
                   ...(bbox ? {{ lonaxis: {{ range: bbox.lon, autorange: false }},
                                 lataxis: {{ range: bbox.lat, autorange: false }} }}
                            : {{ fitbounds: 'locations' }}),
                   uirevision: this.wilayah + '|' + this.provFilter + '|' + this.spendingMode }};
        }})(),
        paper_bgcolor: 'transparent',
      }}, {{ displaylogo: false, responsive: true }});

      const el = document.getElementById('legend-spending');
      if (el) el.innerHTML = palette.map((c, i) => {{
        const lo = bins.edges[i];
        return `<div class="map-legend-bin"><div class="swatch" style="background:${{c}}"></div><div class="range">${{fmt(lo)}}${{i===4?'+':''}}</div></div>`;
      }}).join('');
    }},
    renderOopDonut() {{
      const items = [
        {{ name: 'Rawat inap',  value: SUMMARY.avg_inap,   color: '#C8102E' }},
        {{ name: 'Rawat jalan', value: SUMMARY.avg_jalan,  color: '#EA7200' }},
        {{ name: 'Obat',        value: SUMMARY.avg_obat,   color: '#FFB700' }},
        {{ name: 'Premi',       value: SUMMARY.avg_premi,  color: '#003D79' }},
      ];
      Plotly.react('chart-oop-donut', [{{
        labels: items.map(i => i.name),
        values: items.map(i => i.value),
        type: 'pie',
        hole: 0.55,
        marker: {{ colors: items.map(i => i.color) }},
        textinfo: 'label+percent',
        textfont: {{ size: 12 }},
        hovertemplate: '%{{label}}<br>Rp %{{value:,.0f}}/bulan<br>%{{percent}}<extra></extra>',
      }}], {{
        margin: {{ l: 20, r: 20, t: 20, b: 20 }},
        font: {{ family: FONT, size: 12, color: INK }},
        showlegend: false,
        annotations: [{{
          text: 'Rp ' + (SUMMARY.avg_oop_rp/1000).toFixed(0) + 'rb<br><span style="font-size:11px;color:#667085">total/RT/bln</span>',
          showarrow: false, font: {{ size: 16, family: 'Source Serif 4', color: '#003D79' }},
        }}],
      }}, {{ displaylogo: false, responsive: true }});
    }},
    renderOopScatter() {{
      const traces = INSURANCE_ORDER.map(prof => {{
        const subset = KAB.filter(r => r.ins_profile === prof);
        return {{
          x: subset.map(r => r.pct_jkn),
          y: subset.map(r => r.oop_rp/1000),
          mode: 'markers',
          type: 'scatter',
          name: prof,
          marker: {{
            color: INSURANCE_COLORS[prof] || '#999',
            size: subset.map(r => Math.sqrt(r.pop) / 120),
            sizemode: 'diameter',
            sizemin: 3,
            opacity: 0.65,
            line: {{ width: 0.4, color: 'white' }},
          }},
          text: subset.map(r => r.nama_kab + '<br>' + r.nama_prov),
          hovertemplate: '<b>%{{text}}</b><br>JKN: %{{x:.1f}}%<br>OOP: Rp %{{y:.0f}}rb<extra></extra>',
        }};
      }});
      Plotly.react('chart-oop-scatter', traces, {{
        margin: {{ l: 60, r: 30, t: 20, b: 70 }},
        font: {{ family: FONT, size: 12, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ title: {{ text: '% JKN coverage', font: {{ size: 11, color: MUTED }} }}, gridcolor: '#EAECF0', range: [0, 105] }},
        yaxis: {{ title: {{ text: 'OOP (Rp ribu / RT / bulan)', font: {{ size: 11, color: MUTED }} }}, gridcolor: '#EAECF0' }},
        legend: {{ orientation: 'h', y: -0.18, x: 0, xanchor: 'left', font: {{ size: 10 }} }},
      }}, {{ displaylogo: false, responsive: true }});
    }},
  }};
}}
</script>

</body>
</html>
"""


def main():
    df = load()
    print(f"Loaded {len(df)} kabkota rows.")
    meta = json.loads(META.read_text(encoding="utf-8"))
    payload = build_payload(df, meta)
    geojson = json.loads(GEOJSON.read_text(encoding="utf-8"))
    print(f"Loaded geojson: {len(geojson['features'])} features.")
    html = build_html(payload, geojson, date.today().isoformat())
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT.name} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
