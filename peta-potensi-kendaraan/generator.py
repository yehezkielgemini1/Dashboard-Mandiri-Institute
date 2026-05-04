"""
Generator dashboard "Peta Potensi Pasar Kredit Kendaraan" — Riset Kendaraan 2026 (MUF).
Input: data.csv + metadata.json + kabkota_bps_simplified.geojson + provinsi_bps_simplified.geojson.
Output: dashboard.html + heavy data .js file.
4 pages: Overview · Peta · Detail Kab · Metodologi.
"""
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
CSV = HERE / "data.csv"
META = HERE / "metadata.json"
GEOJSON_KAB = HERE / "kabkota_bps_simplified.geojson"
GEOJSON_PROV = HERE / "provinsi_bps_simplified.geojson"
OUT = HERE / "dashboard.html"
DATA_JS = HERE / "kendaraan_data.js"

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
MIDDLE_PLUS = ["Lower MC", "Middle MC", "Upper MC", "Upper Class"]


def load():
    df = pd.read_csv(CSV)
    df["nama_prov"] = df["nama_prov"].astype(str).str.replace("Sumatera", "Sumatra", regex=False)
    return df


def compute_composite(df_kab_total):
    """Compute 13 indeks + composite score per kabkot 2025."""
    # df_kab_total: kabkot × tahun, kelas_8 == 'Total'
    by_kab = {}
    for pcode, grp in df_kab_total.groupby("kabkota_4digit"):
        grp = grp.set_index("tahun")
        d = {"pcode": int(pcode), "nama_kab": grp["nama_kab"].iloc[0], "nama_prov": grp["nama_prov"].iloc[0]}

        def safe_get(yr, col):
            return float(grp.loc[yr, col]) if yr in grp.index and pd.notna(grp.loc[yr, col]) else np.nan

        def delta_pp(short_a, short_b, col):
            a, b = safe_get(short_a, col), safe_get(short_b, col)
            return (b - a) * 100 if not (np.isnan(a) or np.isnan(b)) else np.nan

        def delta_pct(short_a, short_b, col):
            a, b = safe_get(short_a, col), safe_get(short_b, col)
            if np.isnan(a) or np.isnan(b) or a <= 0:
                return np.nan
            return (b / a - 1) * 100

        # Indeks
        d["A1"] = delta_pp(2024, 2025, "pct_mobil")
        d["A2"] = delta_pp(2024, 2025, "pct_motor")
        d["A3"] = delta_pp(2019, 2025, "pct_mobil")
        d["A4"] = delta_pp(2019, 2025, "pct_motor")
        d["B1"] = delta_pct(2019, 2025, "avg_kendaraan")
        d["B2"] = delta_pct(2024, 2025, "avg_kendaraan")
        d["C1"] = safe_get(2025, "avg_tol_parkir")
        d["C2"] = safe_get(2025, "avg_pelumas")
        d["C3"] = safe_get(2025, "avg_perbaikan")
        d["C4"] = safe_get(2025, "avg_stnk")
        d["D1"] = delta_pct(2019, 2025, "avg_bensin_liter")
        d["E1"] = safe_get(2025, "pct_middle_plus") * 100 if not np.isnan(safe_get(2025, "pct_middle_plus")) else np.nan
        d["E2"] = safe_get(2025, "avg_nonfood")
        d["n_rt_middle_weighted"] = safe_get(2025, "n_rt_middle_weighted")
        d["low_confidence"] = bool(grp.loc[2025, "low_confidence"]) if 2025 in grp.index else False
        by_kab[int(pcode)] = d

    # Min-max normalize per indeks (replace NaN with 0)
    indeks = ["A1", "A2", "A3", "A4", "B1", "B2", "C1", "C2", "C3", "C4", "D1", "E1", "E2"]
    for idx in indeks:
        vals = [by_kab[k][idx] for k in by_kab if not np.isnan(by_kab[k][idx])]
        if not vals:
            for k in by_kab:
                by_kab[k][f"{idx}_norm"] = 0.0
            continue
        vmin, vmax = min(vals), max(vals)
        rng = vmax - vmin or 1
        for k in by_kab:
            v = by_kab[k][idx]
            by_kab[k][f"{idx}_norm"] = ((v - vmin) / rng * 100) if not np.isnan(v) else 0.0

    # Pillars
    pillar_weights = {
        "P1_Adoption_Velocity": 0.30,
        "P2_Purchase_Momentum": 0.25,
        "P3_Cost_Of_Ownership": 0.15,
        "P4_Intensity": 0.10,
        "P5_Capacity_Scale": 0.20,
    }
    pillar_subs = {
        "P1_Adoption_Velocity": [("A1", 0.25), ("A2", 0.25), ("A3", 0.25), ("A4", 0.25)],
        "P2_Purchase_Momentum": [("B1", 0.5), ("B2", 0.5)],
        "P3_Cost_Of_Ownership": [("C1", 0.25), ("C2", 0.25), ("C3", 0.25), ("C4", 0.25)],
        "P4_Intensity": [("D1", 1.0)],
        "P5_Capacity_Scale": [("E1", 0.5), ("E2", 0.5)],
    }

    for k, d in by_kab.items():
        composite = 0
        for pillar, sub_list in pillar_subs.items():
            pillar_score = sum(d[f"{idx}_norm"] * w for idx, w in sub_list)
            d[pillar] = round(pillar_score, 2)
            composite += pillar_score * pillar_weights[pillar]
        d["composite"] = round(composite, 2)
        d["TAM"] = round(d["composite"] * (d["n_rt_middle_weighted"] or 0) / 100, 0)

    # Tier per quartile (exclude low_conf from quartile calc)
    valid = [d for d in by_kab.values() if not d["low_confidence"]]
    valid_scores = sorted([d["composite"] for d in valid])
    n = len(valid_scores)
    if n > 0:
        q1 = valid_scores[int(n * 0.25)]
        q2 = valid_scores[int(n * 0.50)]
        q3 = valid_scores[int(n * 0.75)]
        for k, d in by_kab.items():
            if d["low_confidence"]:
                d["tier"] = "Sampel Terbatas"
            elif d["composite"] >= q3:
                d["tier"] = "Tier 1"
            elif d["composite"] >= q2:
                d["tier"] = "Tier 2"
            elif d["composite"] >= q1:
                d["tier"] = "Tier 3"
            else:
                d["tier"] = "Tier 4"
    return by_kab


def build_payload(df, meta):
    # Filter Total rows untuk kabkot (composite calc)
    df_kab_total = df[(df["geo_level"] == "kabkot") & (df["kelas_8"] == "Total")].copy()
    composite = compute_composite(df_kab_total)

    # Trend nasional middle+ per tahun (key metrics)
    nat = df[(df["geo_level"] == "nasional") & (df["kelas_8"] == "Total")].set_index("tahun")
    nat_trend = {}
    for col in ["pct_mobil", "pct_motor", "avg_kendaraan", "avg_bensin_liter", "avg_nonfood", "pct_middle_plus"]:
        nat_trend[col] = [float(nat.loc[y, col]) if y in nat.index and pd.notna(nat.loc[y, col]) else None for y in YEARS]

    # Scorecard table — key metric per tahun + Δ 19-25
    scorecard_rows = [
        {"label": "Kepemilikan mobil per rumah tangga (%)", "col": "pct_mobil", "fmt": "pct", "delta_fmt": "pp"},
        {"label": "Kepemilikan motor per rumah tangga (%)", "col": "pct_motor", "fmt": "pct", "delta_fmt": "pp"},
        {"label": "Belanja kendaraan per rumah tangga (Rp/tahun)", "col": "avg_kendaraan", "fmt": "rp", "delta_fmt": "rp_pct"},
        {"label": "Konsumsi bensin per rumah tangga (liter/tahun)", "col": "avg_bensin_liter", "fmt": "num", "delta_fmt": "num_pct"},
        {"label": "Belanja non-makanan per rumah tangga (Rp/bulan)", "col": "avg_nonfood", "fmt": "rp", "delta_fmt": "rp_pct"},
        {"label": "Rumah tangga kelas Middle+ nasional (%)", "col": "pct_middle_plus", "fmt": "pct", "delta_fmt": "pp"},
    ]
    scorecard = []
    for r in scorecard_rows:
        vals = nat_trend[r["col"]]
        v19, v25 = vals[0], vals[-1]
        delta = None
        if v19 is not None and v25 is not None:
            if r["delta_fmt"] in ("pp",):
                delta = (v25 - v19) * 100  # convert ratio to pp
            else:
                delta = (v25 / v19 - 1) * 100 if v19 > 0 else None
        scorecard.append({
            "label": r["label"], "fmt": r["fmt"], "delta_fmt": r["delta_fmt"],
            "vals": vals, "delta": delta,
        })

    # Per kab time series untuk drilldown
    kab_ts = {}
    for pcode, grp in df_kab_total.groupby("kabkota_4digit"):
        g = grp.set_index("tahun")
        kab_ts[int(pcode)] = {
            col: [float(g.loc[y, col]) if y in g.index and pd.notna(g.loc[y, col]) else None for y in YEARS]
            for col in ["pct_mobil", "pct_motor", "avg_kendaraan", "avg_bensin_liter", "avg_nonfood"]
        }

    # Kab list sorted by composite desc
    kab_list = sorted(
        [{"pcode": d["pcode"], "nama_kab": d["nama_kab"], "nama_prov": d["nama_prov"],
          "composite": d["composite"], "TAM": d["TAM"], "tier": d["tier"], "low_conf": d["low_confidence"],
          "n_rt": d["n_rt_middle_weighted"]}
         for d in composite.values()],
        key=lambda r: -r["composite"]
    )

    # Tier counts
    tier_counts = {}
    for d in composite.values():
        tier_counts[d["tier"]] = tier_counts.get(d["tier"], 0) + 1

    # Peta Indikator: per (tahun, indikator, pcode_kab) → value
    INDIKATORS = ["pct_mobil", "pct_motor", "avg_kendaraan", "avg_bensin_liter",
                  "avg_nonfood", "avg_tol_parkir", "avg_pelumas", "avg_perbaikan",
                  "avg_stnk", "pct_middle_plus"]
    map_indikator = {}
    for y in YEARS:
        map_indikator[str(y)] = {}
        sub = df_kab_total[df_kab_total["tahun"] == y]
        for ind in INDIKATORS:
            map_indikator[str(y)][ind] = {
                f"ID{int(row['kabkota_4digit']):04d}": round(float(row[ind]), 4)
                for _, row in sub.iterrows() if pd.notna(row[ind])
            }

    # Provinsi rollup ranking: aggregate kab → prov (avg composite, sum TAM)
    prov_rollup = {}
    for d in composite.values():
        # kabkota_4digit format: PPKK (2 digit prov + 2 digit kab)
        pcode_prov = f"ID{str(d['pcode']).zfill(4)[:2]}"
        if pcode_prov not in prov_rollup:
            prov_rollup[pcode_prov] = {
                "pcode": pcode_prov,
                "nama_prov": d["nama_prov"],
                "n_kab": 0, "n_low_conf": 0,
                "sum_composite": 0, "sum_tam": 0,
                "tier_counts": {"Tier 1": 0, "Tier 2": 0, "Tier 3": 0, "Tier 4": 0, "Sampel Terbatas": 0},
            }
        p = prov_rollup[pcode_prov]
        p["n_kab"] += 1
        if d["low_confidence"]:
            p["n_low_conf"] += 1
        p["sum_composite"] += d["composite"]
        p["sum_tam"] += d["TAM"]
        p["tier_counts"][d["tier"]] = p["tier_counts"].get(d["tier"], 0) + 1
    for p in prov_rollup.values():
        p["avg_composite"] = round(p["sum_composite"] / p["n_kab"], 2) if p["n_kab"] else 0
        p["TAM"] = round(p["sum_tam"], 0)
        del p["sum_composite"], p["sum_tam"]
    prov_list = sorted(prov_rollup.values(), key=lambda r: -r["avg_composite"])

    return {
        "composite": composite,
        "nat_trend": nat_trend,
        "kab_ts": kab_ts,
        "kab_list": kab_list,
        "tier_counts": tier_counts,
        "indeks_meta": meta["composite_indeks"],
        "pillar_weights": meta["pillar_weights"],
        "caveat": meta["caveat"],
        "scorecard": scorecard,
        "years": YEARS,
        "map_indikator": map_indikator,
        "prov_rollup": prov_rollup,
        "prov_list": prov_list,
    }


def build_html(payload, geojson_kab, generated):
    n_kab = len(payload["kab_list"])
    n_low_conf = sum(1 for k in payload["kab_list"] if k["low_conf"])
    tier1_n = payload["tier_counts"].get("Tier 1", 0)
    tier2_n = payload["tier_counts"].get("Tier 2", 0)

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Peta Potensi Pasar Kredit Kendaraan, Riset Kendaraan 2026</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://code.iconify.design/iconify-icon/2.1.0/iconify-icon.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&display=swap" rel="stylesheet">
<style>
  :root {{
    --navy: #003D79; --navy-deep: #002852; --sky: #67B2E8; --yellow: #FFB700;
    --ink: #051C2C; --rule: #E5E8EC; --rule-strong: #D0D5DD; --muted: #667085;
    --paper: #FFFFFF; --cream: #F8F6F0; --mist: #F0F6FC;
    --tier1: #003D79; --tier2: #67B2E8; --tier3: #FFE08A; --tier4: #E5E8EC; --lowconf: #C8102E;
  }}
  html, body {{ background: var(--paper); color: var(--ink); }}
  body {{ font-family: 'Inter', system-ui, sans-serif; font-weight: 400; letter-spacing: -0.003em; }}
  .serif-display {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.015em; line-height: 1.08; }}
  .stat-num {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.02em; line-height: 1; }}
  .eyebrow {{ font-size: 11px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--navy); }}
  .eyebrow-roman {{ font-family: 'Source Serif 4', Georgia, serif; font-style: italic; font-size: 16px; font-weight: 500; color: var(--navy); }}
  .eyebrow-roman::before {{ content: ''; display: inline-block; width: 24px; height: 1px; background: var(--navy); vertical-align: middle; margin-right: 12px; }}
  .rule-top {{ border-top: 1px solid var(--rule); }}
  .hair-accent {{ border-top: 2px solid var(--sky); }}
  .ink {{ color: var(--ink); }} .muted {{ color: var(--muted); }}
  .num {{ font-variant-numeric: tabular-nums; }}
  .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--navy); background: var(--mist); border: 1px solid var(--sky); }}
  .badge-dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--sky); display: inline-block; }}
  .chip-action {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--navy); background: white; border: 1px solid var(--rule); cursor: pointer; transition: all 0.12s; }}
  .chip-action:hover {{ background: var(--mist); border-color: var(--navy); }}
  .chip-action.active {{ background: var(--navy); color: white; border-color: var(--navy); }}
  .select-flat {{ border: 0; border-bottom: 1px solid var(--ink); background: transparent; padding: 6px 24px 6px 0; font-size: 15px; font-weight: 500; color: var(--ink); appearance: none; }}
  .chart-footer {{ border-top: 1px solid var(--rule); margin-top: 16px; padding-top: 12px; display: flex; flex-wrap: wrap; gap: 24px; font-size: 11px; color: var(--muted); }}
  .chart-footer .label {{ font-weight: 600; color: var(--ink); text-transform: uppercase; letter-spacing: 0.06em; margin-right: 4px; }}

  /* Sidebar (sama dengan dashboard lain) */
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
  .sidebar .footer {{ margin-top: auto; padding: 16px 24px; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(255,255,255,0.4); border-top: 1px solid rgba(255,255,255,0.12); }}
  .with-sidebar {{ margin-left: 220px; }}

  /* Hero band */
  .hero-band {{ background: linear-gradient(180deg, #003D79 0%, #003D79 30%, #00498A 50%, #00407C 70%, #002852 100%); color: white; position: relative; }}
  .hero-band::after {{ content: ''; position: absolute; bottom: -1px; left: 0; right: 0; height: 1px; background: var(--yellow); opacity: 0.4; }}
  .hero-band .eyebrow {{ color: var(--yellow); }}
  .hero-band h1, .hero-band h2 {{ color: white; }}
  .hero-band p {{ color: rgba(255,255,255,0.78); }}
  .thematic-tag {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--navy); background: var(--yellow); border-radius: 0; margin-bottom: 16px; }}

  /* Tier chip */
  .tier-chip {{ display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; font-size: 10px; font-weight: 700; letter-spacing: 0.06em; }}
  .tier-1 {{ background: var(--tier1); color: white; }}
  .tier-2 {{ background: var(--tier2); color: white; }}
  .tier-3 {{ background: var(--tier3); color: var(--ink); }}
  .tier-4 {{ background: var(--tier4); color: var(--muted); }}
  .tier-low {{ background: rgba(200,16,46,0.1); color: var(--lowconf); border: 1px solid var(--lowconf); }}

  /* Top-50 table */
  .rank-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .rank-table thead th {{ text-align: left; font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); padding: 10px 8px; border-bottom: 2px solid var(--ink); position: sticky; top: 0; background: white; }}
  .rank-table thead th.sortable {{ cursor: pointer; }}
  .rank-table thead th.sortable:hover {{ color: var(--navy); }}
  .rank-table tbody td {{ padding: 10px 8px; border-bottom: 1px solid var(--rule); vertical-align: middle; }}
  .rank-table tbody tr:hover {{ background: var(--mist); }}
  .rank-table .rank-no {{ font-family: 'Source Serif 4', serif; font-weight: 600; color: var(--sky); width: 36px; }}
  .rank-table .nama-kab {{ font-weight: 600; color: var(--ink); }}
  .rank-table .sub-prov {{ display: block; font-size: 11px; color: var(--muted); font-weight: 400; margin-top: 2px; }}

  /* Drilldown drawer */
  .drilldown {{ position: fixed; top: 0; right: 0; bottom: 0; width: 540px; background: white; border-left: 1px solid var(--rule); box-shadow: -8px 0 32px rgba(5,28,44,0.12); transform: translateX(100%); transition: transform 0.25s; z-index: 60; overflow-y: auto; }}
  .drilldown.is-open {{ transform: translateX(0); }}
  .drilldown .head {{ background: var(--navy); color: white; padding: 24px; position: relative; }}
  .drilldown .head .close {{ position: absolute; top: 16px; right: 16px; background: transparent; border: none; color: rgba(255,255,255,0.7); cursor: pointer; font-size: 22px; }}
  .drilldown .head h3 {{ font-family: 'Source Serif 4', serif; font-size: 24px; font-weight: 600; line-height: 1.1; }}
  .drilldown .head .sub {{ font-size: 12px; color: rgba(255,255,255,0.7); margin-top: 4px; }}
  .drilldown .body {{ padding: 24px; }}
  .pillar-row {{ display: flex; align-items: center; gap: 12px; padding: 8px 0; }}
  .pillar-row .lbl {{ flex: 1; font-size: 12px; color: var(--ink); }}
  .pillar-row .bar-wrap {{ width: 200px; height: 8px; background: var(--mist); position: relative; }}
  .pillar-row .bar {{ position: absolute; left: 0; top: 0; height: 100%; background: var(--navy); }}
  .pillar-row .val {{ font-family: 'Source Serif 4', serif; font-weight: 600; font-size: 14px; color: var(--ink); width: 50px; text-align: right; }}

  /* Caveat banner */
  .caveat-banner {{ background: rgba(234,114,0,0.08); border-left: 3px solid #EA7200; padding: 14px 18px; margin: 16px 0; }}
  .caveat-banner .label {{ font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #EA7200; }}
  .caveat-banner .text {{ font-size: 13px; color: var(--ink); margin-top: 4px; line-height: 1.5; }}

  *:focus-visible {{ outline: 2px solid var(--sky); outline-offset: 2px; }}
</style>
</head>
<body>

<div x-data="dashboard()" x-init="init()">

<aside class="sidebar">
  <div class="brand">
    <a href="../index.html" style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--yellow);text-transform:uppercase;letter-spacing:0.1em;font-weight:600;text-decoration:none;margin-bottom:10px;">
      <iconify-icon icon="mdi:arrow-left"></iconify-icon><span>Beranda</span>
    </a>
    <span class="yellow-accent"></span>
    <div class="brand-title">Mandiri Institute</div>
    <div class="brand-sub">Research Initiatives</div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Riset Kendaraan 2026</div>
    <template x-for="t in tabs" :key="t.id">
      <button @click="setPage(t.id)" :class="page === t.id ? 'nav-item active' : 'nav-item'">
        <iconify-icon :icon="t.icon"></iconify-icon><span x-text="t.label"></span>
      </button>
    </template>
  </div>
  <div class="footer">
    <div>Riset 2026</div>
  </div>
</aside>

<div class="with-sidebar">
<div class="hero-band">
  <header class="max-w-[1280px] mx-auto px-8 pt-16 pb-16">
    <div class="thematic-tag"><iconify-icon icon="mdi:car-multiple"></iconify-icon>Research Initiative</div>
    <div class="eyebrow">Riset Mandiri Institute &middot; Kredit Kendaraan</div>
    <h1 class="serif-display text-4xl md:text-5xl mt-5 max-w-4xl" x-text="pageTitle"></h1>
    <p class="mt-5 text-base max-w-3xl leading-relaxed" x-text="pageSubtitle"></p>
  </header>
</div>

<main class="max-w-[1280px] mx-auto px-8 pb-16">

  <!-- ==================== OVERVIEW ==================== -->
  <section x-show="page === 'overview'">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-10 rule-top pt-8">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Kab/Kota dianalisis</div>
        <div class="stat-num text-5xl mt-3 ink">{n_kab}</div>
        <div class="text-sm muted mt-1">Cakupan nasional 2025</div>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Tier 1 (Top 25%)</div>
        <div class="stat-num text-5xl mt-3" style="color:var(--navy);">{tier1_n}</div>
        <div class="text-sm muted mt-1">Prioritas utama targeting</div>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Tier 2 (50-75%)</div>
        <div class="stat-num text-5xl mt-3" style="color:var(--sky);">{tier2_n}</div>
        <div class="text-sm muted mt-1">Prioritas sekunder</div>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Sampel Terbatas</div>
        <div class="stat-num text-5xl mt-3" style="color:var(--lowconf);">{n_low_conf}</div>
        <div class="text-sm muted mt-1">Sampel &lt; 30 RT Middle+</div>
      </div>
    </div>

    <div class="caveat-banner">
      <div class="label">Catatan penting</div>
      <div class="text">
        D1 (bensin liter): aproksimasi via harga Pertalite (BPS Susenas tidak mengumpulkan kuantitas).
        Kabkot pemekaran Papua (kode 92/95/96/97) pasca-2022 tidak punya baseline 2019 untuk delta A3/A4/B1/D1.
        Ambang sampel: kabkot dengan jumlah RT Middle+ &lt; 30 ditandai sampel terbatas.
      </div>
    </div>

    <!-- Scorecard table — key metric snapshot 2019-2025 -->
    <div class="mt-12">
      <div class="eyebrow-roman">I. Skor Nasional Middle+</div>
      <h2 class="serif-display text-3xl mt-3 max-w-3xl">Indikator utama, 2019-2025.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Indikator pasar kendaraan Middle Class+ nasional, 2019-2025 dengan perubahan total.</p>
      <div class="hair-accent mt-6 pt-2"></div>
      <div class="overflow-x-auto mt-2">
        <table class="rank-table" style="min-width:800px;">
          <thead>
            <tr>
              <th style="text-align:left;min-width:240px;">Indikator</th>
              <template x-for="y in [2019,2020,2021,2022,2023,2024,2025]" :key="'sy'+y">
                <th class="text-right" x-text="y"></th>
              </template>
              <th class="text-right" style="border-left:2px solid var(--ink);">Δ 19-25</th>
            </tr>
          </thead>
          <tbody>
            <template x-for="(r, i) in scorecard" :key="'sc'+i">
              <tr>
                <td><strong x-text="r.label"></strong></td>
                <template x-for="(v, j) in r.vals" :key="'sv'+j">
                  <td class="text-right num" x-text="formatScVal(v, r.fmt)"></td>
                </template>
                <td class="text-right num" style="border-left:2px solid var(--ink);font-weight:600;"
                    :style="r.delta !== null ? 'color:' + (r.delta >= 0 ? 'var(--positive,#00875A)' : 'var(--negative,#C8102E)') : 'color:var(--muted)'"
                    x-text="formatScDelta(r.delta, r.delta_fmt)"></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas KOR-RT + KP Blok 4.2</span>
        <span><span class="label">Filter</span>middle+ ∈ {{Lower MC, Middle MC, Upper MC, Upper Class}}</span>
      </div>
    </div>

    <div class="mt-12">
      <div class="eyebrow-roman">II. Tren Visual</div>
      <h2 class="serif-display text-3xl mt-3 max-w-3xl">Adopsi kendaraan dan intensitas pemakaian.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Tren 2019-2025 untuk Middle Class+ (Lower MC, Middle MC, Upper MC, Upper Class). Basis: Susenas BPS, level RT.</p>
      <div class="hair-accent mt-6 pt-2"></div>
      <div id="chart-trend" style="height:480px;"></div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas KOR-RT + KP Blok 4.2, BPS</span>
        <span><span class="label">Filter</span>middle+ ∈ {{Lower MC, Middle MC, Upper MC, Upper Class}}</span>
      </div>
    </div>
  </section>

  <!-- ==================== PETA ==================== -->
  <section x-show="page === 'peta'">
    <div class="rule-top pt-8 flex flex-wrap items-end gap-6">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Tampilan</div>
        <div class="mt-2 flex gap-2">
          <button class="chip-action" :class="mapMode==='composite' ? 'active' : ''" @click="mapMode='composite'; renderMap()">Skor Komposit</button>
          <button class="chip-action" :class="mapMode==='TAM' ? 'active' : ''" @click="mapMode='TAM'; renderMap()">Pasar Potensial</button>
        </div>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Filter Tier</div>
        <div class="mt-2 flex gap-2 flex-wrap">
          <template x-for="t in ['Tier 1','Tier 2','Tier 3','Tier 4','Sampel Terbatas']" :key="'tf'+t">
            <button class="chip-action" :class="tierFilter.includes(t) ? 'active' : ''" @click="toggleTier(t)" x-text="t"></button>
          </template>
        </div>
      </div>
      <div style="margin-left:auto">
        <button class="chip-action" @click="exportPPT()" style="background:var(--yellow);color:var(--ink);border-color:var(--yellow);font-weight:700;">
          <iconify-icon icon="mdi:presentation"></iconify-icon>Export PPT
        </button>
      </div>
    </div>
    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>{n_kab} Kab/Kota · 13 Indeks</span>
      <div class="eyebrow-roman mt-3">II. Peta Skor Komposit</div>
      <h2 class="serif-display text-3xl mt-3 max-w-3xl">Kepadatan pasar kredit kendaraan per kab/kota.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Choropleth kab/kota dengan skor komposit 5 dimensi (Adopsi, Pembelian, Biaya, Intensitas, Kapasitas). Klik kab/kota untuk lihat profil detail.</p>
      <div class="hair-accent mt-6 pt-2"></div>
      <div id="chart-map" style="height:780px;"></div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas BPS · Shapefile BPS adm2 2020</span>
        <span><span class="label">Skor Komposit</span>rata-rata tertimbang 5 dimensi (lihat Metodologi)</span>
        <span><span class="label">Tier</span>kuartil skor (Tier 1 = 25% teratas)</span>
      </div>
    </div>

    <!-- Top-50 ranking table -->
    <div class="mt-16 rule-top pt-10">
      <div class="eyebrow-roman">III. Top 50 Ranking</div>
      <h3 class="serif-display text-2xl mt-3 max-w-3xl">Ranking <span x-text="rankView==='kab' ? 'kab/kota' : 'provinsi'"></span> berdasarkan <span x-text="rankSortBy==='composite' ? 'Skor Komposit' : 'Pasar Potensial'"></span>.</h3>
      <div class="mt-4 flex gap-3 flex-wrap items-end">
        <div>
          <div class="eyebrow" style="color:var(--muted)">View</div>
          <div class="mt-2 flex gap-2">
            <button class="chip-action" :class="rankView==='kab' ? 'active' : ''" @click="rankView='kab'">Per Kab/Kota</button>
            <button class="chip-action" :class="rankView==='prov' ? 'active' : ''" @click="rankView='prov'">Per Provinsi</button>
          </div>
        </div>
        <div>
          <div class="eyebrow" style="color:var(--muted)">Sort</div>
          <div class="mt-2 flex gap-2">
            <button class="chip-action" :class="rankSortBy==='composite' ? 'active' : ''" @click="rankSortBy='composite'">Skor</button>
            <button class="chip-action" :class="rankSortBy==='TAM' ? 'active' : ''" @click="rankSortBy='TAM'">Pasar Potensial</button>
          </div>
        </div>
        <div x-show="rankView==='kab'">
          <div class="eyebrow" style="color:var(--muted)">Wilayah</div>
          <select x-model="rankWilayah" @change="rankProv='All'" class="select-flat mt-2" style="min-width:160px;">
            <template x-for="w in Object.keys(REGION_PROVS_JS)" :key="'rw'+w"><option :value="w" x-text="w"></option></template>
          </select>
        </div>
        <div x-show="rankView==='kab'">
          <div class="eyebrow" style="color:var(--muted)">Provinsi</div>
          <select x-model="rankProv" class="select-flat mt-2" style="min-width:160px;">
            <option value="All">Semua provinsi</option>
            <template x-for="p in rankProvOptions" :key="'rp'+p.pcode"><option :value="p.pcode" x-text="p.nama"></option></template>
          </select>
        </div>
      </div>
      <!-- Per Kab/Kota view -->
      <div x-show="rankView==='kab'" class="mt-6" style="max-height:600px;overflow-y:auto;border:1px solid var(--rule);">
        <table class="rank-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Kab/Kota</th>
              <th class="text-right">Skor</th>
              <th class="text-right">Pasar Potensial (RT)</th>
              <th>Tier</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <template x-for="(r, i) in topKabs" :key="'tk'+r.pcode">
              <tr>
                <td class="rank-no num" x-text="i+1"></td>
                <td>
                  <div class="nama-kab" x-text="r.nama_kab"></div>
                  <div class="sub-prov" x-text="r.nama_prov"></div>
                </td>
                <td class="text-right num" x-text="r.composite.toFixed(1)"></td>
                <td class="text-right num" x-text="(r.TAM/1000).toFixed(0)+' rb'"></td>
                <td><span class="tier-chip" :class="tierClass(r.tier)" x-text="r.tier"></span></td>
                <td><button class="chip-action" @click="openDrilldown(r.pcode)" style="font-size:10px;padding:3px 8px;">Detail</button></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Per Provinsi view -->
      <div x-show="rankView==='prov'" class="mt-6" style="max-height:600px;overflow-y:auto;border:1px solid var(--rule);">
        <table class="rank-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Provinsi</th>
              <th class="text-right">Rata-rata Skor</th>
              <th class="text-right">Total Pasar Potensial (RT)</th>
              <th class="text-right">N Kab</th>
              <th>Distribusi Tier</th>
            </tr>
          </thead>
          <tbody>
            <template x-for="(r, i) in topProvs" :key="'tp'+r.pcode">
              <tr>
                <td class="rank-no num" x-text="i+1"></td>
                <td><div class="nama-kab" x-text="r.nama_prov"></div></td>
                <td class="text-right num" x-text="r.avg_composite.toFixed(1)"></td>
                <td class="text-right num" x-text="(r.TAM/1e6).toFixed(2)+' jt'"></td>
                <td class="text-right num" x-text="r.n_kab + (r.n_low_conf > 0 ? ' (' + r.n_low_conf + ' terbatas)' : '')"></td>
                <td>
                  <div style="display:flex;height:8px;border:1px solid var(--rule);max-width:140px">
                    <template x-for="t in ['Tier 1','Tier 2','Tier 3','Tier 4','Sampel Terbatas']" :key="'tb'+r.pcode+t">
                      <div :style="'background:' + tierColor(t) + ';flex:' + (r.tier_counts[t] || 0)" :title="t + ': ' + (r.tier_counts[t] || 0)"></div>
                    </template>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <!-- ==================== INDIKATOR ==================== -->
  <section x-show="page === 'indikator'">
    <div class="rule-top pt-8 flex flex-wrap items-end gap-6">
      <div class="flex-1 min-w-[260px]">
        <div class="eyebrow" style="color:var(--muted)">Indikator</div>
        <select x-model="indMetric" @change="renderIndikator()" class="select-flat mt-2 w-full">
          <template x-for="m in indMetrics" :key="'im'+m">
            <option :value="m" x-text="indLabels[m].label"></option>
          </template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color:var(--muted)">Tahun</div>
        <select x-model="indYear" @change="renderIndikator()" class="select-flat mt-2" style="min-width:90px">
          <template x-for="y in [2019,2020,2021,2022,2023,2024,2025]" :key="'iy'+y">
            <option :value="String(y)" x-text="y"></option>
          </template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color:var(--muted)">Wilayah</div>
        <select x-model="indWilayah" @change="indProv='All'; renderIndikator()" class="select-flat mt-2" style="min-width:160px">
          <template x-for="w in Object.keys(REGION_PROVS_JS)" :key="'iw'+w">
            <option :value="w" x-text="w"></option>
          </template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color:var(--muted)">Provinsi</div>
        <select x-model="indProv" @change="renderIndikator()" class="select-flat mt-2" style="min-width:160px">
          <option value="All">Semua provinsi</option>
          <template x-for="p in indProvOptions" :key="'ip'+p.pcode">
            <option :value="p.pcode" x-text="p.nama"></option>
          </template>
        </select>
      </div>
    </div>

    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>514 Kab/Kota · Indikator</span>
      <div class="eyebrow-roman mt-3">III. Detail Indikator</div>
      <h2 class="serif-display text-3xl mt-3 max-w-3xl" x-text="indLabels[indMetric].label + ' per kab/kota.'"></h2>
      <p class="mt-3 muted text-base max-w-3xl">Indikator mentah (sebelum normalisasi). Filter wilayah dan provinsi untuk fokus regional.</p>
      <div class="hair-accent mt-6 pt-2"></div>
      <div id="chart-indikator" style="height:780px;"></div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas BPS · middle+ filter</span>
        <span><span class="label">Tahun</span><span x-text="indYear"></span></span>
      </div>

      <!-- Top/Bottom 10 -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-12 mt-12 rule-top pt-10">
        <div>
          <div class="eyebrow" style="color:var(--muted)">Top 10</div>
          <h4 class="serif-display text-lg mt-2" x-text="'Tertinggi: ' + indLabels[indMetric].label"></h4>
          <div class="mt-4">
            <template x-for="(r, i) in indRankTop" :key="'irt'+r.pcode">
              <div style="display:flex;justify-content:space-between;align-items:baseline;padding:8px 0;border-bottom:1px solid var(--rule);font-size:13px">
                <span><strong style="color:var(--sky);font-family:'Source Serif 4',serif" x-text="i+1"></strong>&nbsp;&nbsp;<span x-text="r.nama"></span><span class="muted" style="font-size:11px;display:block;margin-left:24px" x-text="r.prov"></span></span>
                <span class="num" style="font-weight:600" x-text="formatIndVal(r.value, indLabels[indMetric].fmt)"></span>
              </div>
            </template>
          </div>
        </div>
        <div>
          <div class="eyebrow" style="color:var(--muted)">Bottom 10</div>
          <h4 class="serif-display text-lg mt-2" x-text="'Terendah: ' + indLabels[indMetric].label"></h4>
          <div class="mt-4">
            <template x-for="(r, i) in indRankBottom" :key="'irb'+r.pcode">
              <div style="display:flex;justify-content:space-between;align-items:baseline;padding:8px 0;border-bottom:1px solid var(--rule);font-size:13px">
                <span><strong style="color:#C8102E;font-family:'Source Serif 4',serif" x-text="i+1"></strong>&nbsp;&nbsp;<span x-text="r.nama"></span><span class="muted" style="font-size:11px;display:block;margin-left:24px" x-text="r.prov"></span></span>
                <span class="num" style="font-weight:600" x-text="formatIndVal(r.value, indLabels[indMetric].fmt)"></span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ==================== METODOLOGI ==================== -->
  <section x-show="page === 'metodologi'">
    <div class="rule-top pt-8">

      <!-- Layer A: Hero ringkas + pillar weight bar visual -->
      <div class="eyebrow-roman">III. Arsitektur</div>
      <h2 class="serif-display text-4xl mt-3 max-w-3xl">5 dimensi · 13 indeks · 1 skor komposit (0-100).</h2>
      <p class="mt-4 muted text-base max-w-3xl">Setiap kab/kota dinilai dengan agregasi tertimbang 13 indeks yang dikelompokkan ke 5 dimensi. Bobot dimensi (kiri ke kanan):</p>

      <!-- Pillar weight stacked bar -->
      <div class="mt-6">
        <div style="display:flex;height:36px;border:1px solid var(--ink);">
          <div style="background:var(--navy);width:30%;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase">P1 · 30%</div>
          <div style="background:#1A5394;width:25%;display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase">P2 · 25%</div>
          <div style="background:#67B2E8;width:15%;display:flex;align-items:center;justify-content:center;color:var(--ink);font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase">P3 · 15%</div>
          <div style="background:#A9C4DF;width:10%;display:flex;align-items:center;justify-content:center;color:var(--ink);font-size:11px;font-weight:700;letter-spacing:0.06em">P4 · 10%</div>
          <div style="background:var(--yellow);width:20%;display:flex;align-items:center;justify-content:center;color:var(--ink);font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase">P5 · 20%</div>
        </div>
        <div style="display:flex;margin-top:6px;font-size:10px;color:var(--muted);font-weight:600;letter-spacing:0.08em;text-transform:uppercase;">
          <div style="width:30%">Adopsi</div>
          <div style="width:25%">Pembelian</div>
          <div style="width:15%">Biaya</div>
          <div style="width:10%">Intensitas</div>
          <div style="width:20%">Kapasitas</div>
        </div>
      </div>

      <!-- Layer B: 13 indeks tabel lengkap -->
      <div class="mt-12">
        <div class="eyebrow-roman">IV. 13 Indeks</div>
        <h3 class="serif-display text-2xl mt-3 max-w-3xl">Definisi setiap indeks, formula, dan bobot.</h3>
        <div class="overflow-x-auto mt-6">
          <table class="rank-table" style="min-width:900px;">
            <thead>
              <tr>
                <th style="width:60px">Kode</th>
                <th style="min-width:180px">Dimensi</th>
                <th style="min-width:300px">Label</th>
                <th>Formula</th>
                <th class="text-right">Bobot Sub</th>
                <th class="text-right">Bobot Dimensi</th>
              </tr>
            </thead>
            <tbody>
              <template x-for="ix in indeksMeta" :key="ix.id">
                <tr>
                  <td><strong x-text="ix.id" style="color:var(--navy);font-family:'Source Serif 4',serif"></strong></td>
                  <td x-text="pillarLabel(ix.pillar)"></td>
                  <td x-text="ix.label"></td>
                  <td><code x-text="ix.formula_calc" style="font-size:11px;background:var(--mist);padding:2px 6px"></code></td>
                  <td class="text-right num" x-text="(ix.sub_w * 100).toFixed(0) + '%'"></td>
                  <td class="text-right num muted" x-text="(pillarWeights[ix.pillar] * 100).toFixed(0) + '%'"></td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Layer C: 4-step method walkthrough -->
      <div class="mt-12">
        <div class="eyebrow-roman">V. Langkah Hitung</div>
        <h3 class="serif-display text-2xl mt-3 max-w-3xl">Empat tahap dari data mentah ke tier skor.</h3>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mt-6">
          <div style="border-top:3px solid var(--navy);padding-top:16px;">
            <div class="stat-num" style="font-size:48px;color:var(--navy);line-height:1;">1</div>
            <div class="eyebrow mt-3" style="color:var(--ink);">Hitung</div>
            <p class="text-sm muted mt-2 leading-relaxed">Hitung 13 indeks per kabkot 2025: <code>delta_pp</code> (perubahan poin persentase), <code>delta_pct</code> (% perubahan), atau <code>level</code> (nilai absolut tahun terbaru).</p>
          </div>
          <div style="border-top:3px solid var(--navy);padding-top:16px;">
            <div class="stat-num" style="font-size:48px;color:var(--navy);line-height:1;">2</div>
            <div class="eyebrow mt-3" style="color:var(--ink);">Normalisasi</div>
            <p class="text-sm muted mt-2 leading-relaxed">Skala min-max tiap indeks ke 0-100 lintas kabkot. Indeks dengan NaN diset ke 0 (penalti).</p>
          </div>
          <div style="border-top:3px solid var(--navy);padding-top:16px;">
            <div class="stat-num" style="font-size:48px;color:var(--navy);line-height:1;">3</div>
            <div class="eyebrow mt-3" style="color:var(--ink);">Agregasi</div>
            <p class="text-sm muted mt-2 leading-relaxed">Rata-rata tertimbang subindeks → skor dimensi (0-100). Rata-rata tertimbang dimensi (P1 30%, P2 25%, P3 15%, P4 10%, P5 20%) → <strong>skor komposit</strong> 0-100.</p>
          </div>
          <div style="border-top:3px solid var(--yellow);padding-top:16px;">
            <div class="stat-num" style="font-size:48px;color:var(--navy);line-height:1;">4</div>
            <div class="eyebrow mt-3" style="color:var(--ink);">Tier</div>
            <p class="text-sm muted mt-2 leading-relaxed">Kuartil skor (sampel terbatas dikecualikan): <strong>Tier 1</strong> 25% teratas, Tier 2-T4 strata bawah. <strong>Pasar Potensial</strong> = skor × jumlah RT Middle+ / 100.</p>
          </div>
        </div>
      </div>

      <!-- Layer D: Caveat formal numbered -->
      <div class="rule-top pt-8 mt-12">
        <div class="eyebrow-roman">VI. Catatan &amp; Batasan</div>
        <h3 class="serif-display text-2xl mt-3 max-w-3xl">Hal-hal yang perlu diperhatikan saat membaca skor komposit.</h3>
        <ol class="mt-6 space-y-4 text-sm" style="list-style:none;padding:0;counter-reset:cv;">
          <template x-for="(c, i) in caveat" :key="'cv'+i">
            <li style="counter-increment:cv;display:flex;gap:16px;padding:14px 18px;background:rgba(234,114,0,0.06);border-left:3px solid #EA7200;">
              <span style="font-family:'Source Serif 4',serif;font-size:24px;font-weight:600;color:#EA7200;line-height:1;min-width:32px" x-text="(i+1).toString().padStart(2,'0')"></span>
              <span style="line-height:1.6" x-text="c"></span>
            </li>
          </template>
        </ol>
      </div>

      <!-- Data source footer -->
      <div class="rule-top pt-8 mt-12">
        <div class="eyebrow">Sumber Data &amp; Reproduksibilitas</div>
        <p class="text-sm mt-3 leading-relaxed">
          <strong>Sumber:</strong> Susenas Maret BPS 2019-2025, KOR-RT + Konsumsi Pengeluaran (KP) Blok 4.2.<br>
          <strong>Filter universal:</strong> Middle+ (Lower MC, Middle MC, Upper MC, Upper Class). Pengecualian: <code>pct_middle_plus</code> memakai seluruh RT sebagai denominator.<br>
          <strong>Bobot:</strong> <code>wert</code> (penimbang RT, ekuivalen <code>fwt</code> KOR-RT).<br>
          <strong>Ambang sampel:</strong> jumlah RT Middle+ 2025 &lt; 30 → ditandai <em>sampel terbatas</em> (tidak dikeluarkan dari data).
        </p>
      </div>
    </div>
  </section>

  <footer class="rule-top mt-16 pt-8 pb-4 flex items-center justify-between text-xs muted uppercase tracking-widest">
    <div>Mandiri Institute · Riset Kendaraan 2026</div>
    <div>Generated {generated}</div>
    <div>Susenas BPS · weighted</div>
  </footer>
</main>
</div>

<!-- Drilldown drawer -->
<aside class="drilldown" :class="drilldown.open ? 'is-open' : ''" role="dialog">
  <div class="head">
    <button class="close" @click="drilldown.open = false">×</button>
    <div class="badge" style="background:rgba(255,255,255,0.1);border-color:rgba(255,255,255,0.3);color:white">
      <span x-text="drilldown.tier"></span>
    </div>
    <h3 x-text="drilldown.nama_kab" class="mt-2"></h3>
    <div class="sub" x-text="drilldown.nama_prov"></div>
  </div>
  <div class="body">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <div>
        <div class="eyebrow" style="color:var(--muted)">Skor Komposit</div>
        <div class="stat-num text-3xl mt-2" style="color:var(--navy)" x-text="drilldown.composite"></div>
      </div>
      <div>
        <div class="eyebrow" style="color:var(--muted)">Pasar Potensial (RT Middle+)</div>
        <div class="stat-num text-3xl mt-2" style="color:var(--navy)" x-text="drilldown.tam_display"></div>
      </div>
    </div>

    <div class="mt-6">
      <div class="eyebrow">Skor 5 Dimensi</div>
      <div class="mt-3">
        <template x-for="p in drilldown.pillars" :key="p.lbl">
          <div class="pillar-row">
            <span class="lbl" x-text="p.lbl"></span>
            <div class="bar-wrap">
              <div class="bar" :style="'width:' + p.val + '%'"></div>
            </div>
            <span class="val" x-text="p.val.toFixed(1)"></span>
          </div>
        </template>
      </div>
    </div>

    <div class="mt-6">
      <div class="eyebrow">Trend 2019-2025</div>
      <div id="chart-detail" style="height:280px;margin-top:12px"></div>
    </div>

    <template x-if="drilldown.low_conf">
      <div class="caveat-banner mt-6">
        <div class="label">Sampel Terbatas</div>
        <div class="text">Jumlah RT Middle+ &lt; 30 di 2025. Skor tetap dihitung tapi presisi rendah.</div>
      </div>
    </template>
  </div>
</aside>

</div>

<script src="kendaraan_data.js"></script>
<script>
const TABS = [
  {{ id: 'overview',   label: 'Overview',   icon: 'mdi:view-dashboard-outline' }},
  {{ id: 'peta',       label: 'Peta Potensi', icon: 'mdi:map-outline' }},
  {{ id: 'indikator',  label: 'Detail Indikator', icon: 'mdi:layers-outline' }},
  {{ id: 'metodologi', label: 'Metodologi', icon: 'mdi:book-open-variant' }},
];
const PAGE_META = {{
  overview:   {{ title: 'Potensi Pasar Kredit Kendaraan, Indonesia 2025.',
                sub: 'Skor komposit 13 indeks dari Susenas 2019-2025, fokus segmen Middle Class+.' }},
  peta:       {{ title: 'Sebaran skor komposit per kabupaten/kota.',
                sub: 'Choropleth 514 kab/kota dengan skor 5 dimensi. Top 50 ranking + profil detail per kab/kota.' }},
  indikator:  {{ title: 'Detail indikator per kab/kota.',
                sub: 'Jelajahi tiap indikator (% mobil, % motor, rata-rata belanja, dll) lintas tahun, wilayah, dan provinsi.' }},
  metodologi: {{ title: 'Metodologi skor komposit.',
                sub: '5 dimensi, 13 indeks, agregasi tertimbang. Tabel definisi + langkah hitung + catatan.' }},
}};
const FONT = 'Inter, sans-serif';
const INK = '#051C2C';
const MUTED = '#667085';
const TIER_COLORS = {{ 'Tier 1': '#003D79', 'Tier 2': '#67B2E8', 'Tier 3': '#FFE08A', 'Tier 4': '#E5E8EC', 'Sampel Terbatas': '#C8102E' }};

const REGION_PROVS = {{
  'Indonesia':          null,
  'Sumatra':            ['11','12','13','14','15','16','17','18','19','21'],
  'Jawa':               ['31','32','33','34','35','36'],
  'Bali-Nusa Tenggara': ['51','52','53'],
  'Kalimantan':         ['61','62','63','64','65'],
  'Sulawesi':           ['71','72','73','74','75','76'],
  'Maluku-Papua':       ['81','82','91','92','94','95','96','97'],
}};
const INDIKATOR_LABELS = {{
  pct_mobil:        {{ label: 'Kepemilikan mobil per rumah tangga (%)', fmt: 'pct', palette: ['#E8EFF6','#A9C4DF','#67B2E8','#2A6FB3','#003D79'] }},
  pct_motor:        {{ label: 'Kepemilikan motor per rumah tangga (%)', fmt: 'pct', palette: ['#E8EFF6','#A9C4DF','#67B2E8','#2A6FB3','#003D79'] }},
  avg_kendaraan:    {{ label: 'Belanja kendaraan per rumah tangga (Rp/tahun)', fmt: 'rp', palette: ['#FFF8E5','#FFE08A','#FFB700','#D67900','#003D79'] }},
  avg_bensin_liter: {{ label: 'Konsumsi bensin per rumah tangga (liter/tahun)', fmt: 'num', palette: ['#FFF8E5','#FFE08A','#FFB700','#D67900','#003D79'] }},
  avg_nonfood:      {{ label: 'Belanja non-makanan per rumah tangga (Rp/bulan)', fmt: 'rp', palette: ['#E8EFF6','#A9C4DF','#67B2E8','#2A6FB3','#003D79'] }},
  avg_tol_parkir:   {{ label: 'Belanja tol + parkir per rumah tangga (Rp/tahun)', fmt: 'rp', palette: ['#E8EFF6','#A9C4DF','#67B2E8','#2A6FB3','#003D79'] }},
  avg_pelumas:      {{ label: 'Belanja pelumas per rumah tangga (Rp/tahun)', fmt: 'rp', palette: ['#E8EFF6','#A9C4DF','#67B2E8','#2A6FB3','#003D79'] }},
  avg_perbaikan:    {{ label: 'Belanja perbaikan kendaraan per rumah tangga (Rp/tahun)', fmt: 'rp', palette: ['#E8EFF6','#A9C4DF','#67B2E8','#2A6FB3','#003D79'] }},
  avg_stnk:         {{ label: 'Pajak STNK per rumah tangga (Rp/tahun)', fmt: 'rp', palette: ['#E8EFF6','#A9C4DF','#67B2E8','#2A6FB3','#003D79'] }},
  pct_middle_plus:  {{ label: 'Rumah tangga kelas Middle+ (%)', fmt: 'pct', palette: ['#FFF8E5','#FFE08A','#FFB700','#D67900','#003D79'] }},
}};
function pcodeProvCode(pcode) {{ return pcode.slice(2, 4); }}
function inRegion(pcode, wilayah, prov) {{
  const pc = pcodeProvCode(pcode);
  if (prov && prov !== 'All') return pc === prov;
  if (!wilayah || wilayah === 'Indonesia') return true;
  return REGION_PROVS[wilayah].includes(pc);
}}

const PAYLOAD = window.PAYLOAD;
const GEOJSON = window.GEOJSON_KAB;

function dashboard() {{
  return {{
    tabs: TABS, page: 'overview',
    mapMode: 'composite',  // 'composite' | 'TAM'
    tierFilter: ['Tier 1', 'Tier 2'],
    rankSortBy: 'composite',
    rankView: 'kab',           // 'kab' | 'prov'
    rankWilayah: 'Indonesia',
    rankProv: 'All',
    REGION_PROVS_JS: REGION_PROVS,
    // Indikator page state
    indYear: '2025',
    indMetric: 'pct_mobil',
    indWilayah: 'Indonesia',
    indProv: 'All',
    indMetrics: Object.keys(INDIKATOR_LABELS),
    indLabels: INDIKATOR_LABELS,
    drilldown: {{ open: false, pcode: null, nama_kab: '', nama_prov: '', tier: '', composite: 0, tam_display: '', pillars: [], low_conf: false }},
    caveat: PAYLOAD.caveat,
    scorecard: PAYLOAD.scorecard,
    indeksMeta: PAYLOAD.indeks_meta,
    pillarWeights: PAYLOAD.pillar_weights,
    formatScVal(v, fmt) {{
      if (v == null) return '-';
      if (fmt === 'pct') return (v * 100).toFixed(1) + '%';
      if (fmt === 'rp') {{
        if (v >= 1e6) return 'Rp ' + (v/1e6).toFixed(1) + ' jt';
        if (v >= 1e3) return 'Rp ' + (v/1e3).toFixed(0) + ' rb';
        return 'Rp ' + Math.round(v);
      }}
      if (fmt === 'num') return v.toFixed(0);
      return String(v);
    }},
    formatScDelta(v, fmt) {{
      if (v == null) return '-';
      const sign = v >= 0 ? '+' : '';
      if (fmt === 'pp') return sign + v.toFixed(1) + ' pp';
      return sign + v.toFixed(1) + '%';
    }},
    indeksByPillar(pid) {{
      return this.indeksMeta.filter(x => x.pillar === pid);
    }},
    pillarLabel(pid) {{
      const m = {{ 'P1_Adoption_Velocity': 'P1 · Adopsi',
                  'P2_Purchase_Momentum': 'P2 · Pembelian',
                  'P3_Cost_Of_Ownership': 'P3 · Biaya',
                  'P4_Intensity': 'P4 · Intensitas',
                  'P5_Capacity_Scale': 'P5 · Kapasitas' }};
      return m[pid] || pid;
    }},
    get pageTitle() {{ return PAGE_META[this.page].title; }},
    get pageSubtitle() {{ return PAGE_META[this.page].sub; }},
    get topKabs() {{
      // Per-kab view: filter wilayah/prov + tier
      let list = [...PAYLOAD.kab_list];
      list = list.filter(k => {{
        const pcode = 'ID' + String(k.pcode).padStart(4, '0');
        return inRegion(pcode, this.rankWilayah, this.rankProv);
      }});
      list = list.filter(k => this.tierFilter.length === 0 || this.tierFilter.includes(k.tier));
      list.sort((a,b) => (b[this.rankSortBy] || 0) - (a[this.rankSortBy] || 0));
      return list.slice(0, 50);
    }},
    get topProvs() {{
      // Per-prov rollup: sort by avg_composite or TAM
      const sortKey = this.rankSortBy === 'composite' ? 'avg_composite' : 'TAM';
      return [...PAYLOAD.prov_list].sort((a,b) => (b[sortKey] || 0) - (a[sortKey] || 0));
    }},
    get rankProvOptions() {{
      // Prov options di filter, dependent on wilayah
      const codes = REGION_PROVS[this.rankWilayah];
      const all = Object.values(PAYLOAD.prov_rollup);
      const filtered = codes ? all.filter(p => codes.includes(pcodeProvCode(p.pcode))) : all;
      return filtered.sort((a,b) => a.nama_prov.localeCompare(b.nama_prov))
        .map(p => ({{ pcode: pcodeProvCode(p.pcode), nama: p.nama_prov }}));
    }},
    get indProvOptions() {{
      const codes = REGION_PROVS[this.indWilayah];
      const all = Object.values(PAYLOAD.prov_rollup);
      const filtered = codes ? all.filter(p => codes.includes(pcodeProvCode(p.pcode))) : all;
      return filtered.sort((a,b) => a.nama_prov.localeCompare(b.nama_prov))
        .map(p => ({{ pcode: pcodeProvCode(p.pcode), nama: p.nama_prov }}));
    }},
    tierClass(t) {{
      return {{ 'Tier 1': 'tier-1', 'Tier 2': 'tier-2', 'Tier 3': 'tier-3', 'Tier 4': 'tier-4', 'Sampel Terbatas': 'tier-low' }}[t] || '';
    }},
    tierColor(t) {{ return TIER_COLORS[t] || '#999'; }},
    toggleTier(t) {{
      const i = this.tierFilter.indexOf(t);
      if (i >= 0) this.tierFilter.splice(i, 1);
      else this.tierFilter.push(t);
      this.renderMap();
    }},
    init() {{
      this.$nextTick(() => this.renderForPage(this.page));
    }},
    setPage(id) {{ this.page = id; this.renderForPage(id); }},
    renderForPage(id) {{
      requestAnimationFrame(() => requestAnimationFrame(() => {{
        if (id === 'overview') this.renderTrend();
        else if (id === 'peta') this.renderMap();
        else if (id === 'indikator') this.renderIndikator();
      }}));
    }},
    formatIndVal(v, fmt) {{
      if (v == null) return '-';
      if (fmt === 'pct') return (v * 100).toFixed(1) + '%';
      if (fmt === 'rp') {{
        if (v >= 1e6) return 'Rp ' + (v/1e6).toFixed(2) + ' jt';
        if (v >= 1e3) return 'Rp ' + (v/1e3).toFixed(0) + ' rb';
        return 'Rp ' + Math.round(v);
      }}
      if (fmt === 'num') return v.toFixed(0);
      return String(v);
    }},
    get indSliceFiltered() {{
      const slice = (PAYLOAD.map_indikator[this.indYear] || {{}})[this.indMetric] || {{}};
      const out = {{}};
      Object.entries(slice).forEach(([p, v]) => {{
        if (inRegion(p, this.indWilayah, this.indProv)) out[p] = v;
      }});
      return out;
    }},
    get indRankTop() {{
      const slice = this.indSliceFiltered;
      const list = Object.entries(slice).map(([p, v]) => {{
        const pcode = parseInt(p.slice(2));
        const d = PAYLOAD.composite[pcode];
        return {{ pcode, nama: d ? d.nama_kab : p, prov: d ? d.nama_prov : '', value: v }};
      }}).sort((a,b) => b.value - a.value).slice(0, 10);
      return list;
    }},
    get indRankBottom() {{
      const slice = this.indSliceFiltered;
      const list = Object.entries(slice).map(([p, v]) => {{
        const pcode = parseInt(p.slice(2));
        const d = PAYLOAD.composite[pcode];
        return {{ pcode, nama: d ? d.nama_kab : p, prov: d ? d.nama_prov : '', value: v }};
      }}).sort((a,b) => a.value - b.value).slice(0, 10);
      return list;
    }},
    renderIndikator() {{
      const slice = this.indSliceFiltered;
      const meta = INDIKATOR_LABELS[this.indMetric];
      const locs = Object.keys(slice);
      const vals = locs.map(p => slice[p]);
      const palette = meta.palette;
      const fmt = meta.fmt;

      // Quintile bins
      const sorted = vals.slice().sort((a,b) => a-b);
      const q = (p) => sorted.length ? sorted[Math.min(Math.floor(p * (sorted.length - 1)), sorted.length - 1)] : 0;
      const bins = [sorted[0] || 0, q(0.2), q(0.4), q(0.6), q(0.8), sorted[sorted.length-1] || 1];
      const colorscale = [
        [0.0, palette[0]], [0.2-1e-9, palette[0]],
        [0.2, palette[1]], [0.4-1e-9, palette[1]],
        [0.4, palette[2]], [0.6-1e-9, palette[2]],
        [0.6, palette[3]], [0.8-1e-9, palette[3]],
        [0.8, palette[4]], [1.0, palette[4]],
      ];

      // Hovertext
      const hovertext = locs.map(p => {{
        const pcode = parseInt(p.slice(2));
        const d = PAYLOAD.composite[pcode];
        const nama = d ? d.nama_kab : p;
        const prov = d ? d.nama_prov : '';
        const v = slice[p];
        return `<b>${{nama}}</b><br><span style="color:#667085">${{prov}}</span><br>` +
               `<span style="color:#003D79;font-size:18px;font-weight:600">${{this.formatIndVal(v, fmt)}}</span><br>` +
               `<span style="color:#667085">${{meta.label}} · ${{this.indYear}}</span>`;
      }});

      // Filter geojson to displayed kabs + base layer for non-data
      const allowedSet = new Set(locs);
      const dataFeatures = GEOJSON.features.filter(f => allowedSet.has(f.id) && (this.indWilayah === 'Indonesia' && this.indProv === 'All' || inRegion(f.id, this.indWilayah, this.indProv)));
      const dataGJ = {{ type: 'FeatureCollection', features: dataFeatures }};
      // Base: kab di scope wilayah/prov tapi tidak punya data
      const baseFeatures = GEOJSON.features.filter(f => inRegion(f.id, this.indWilayah, this.indProv) && !allowedSet.has(f.id));
      const baseGJ = {{ type: 'FeatureCollection', features: baseFeatures }};
      const baseLocs = baseFeatures.map(f => f.id);

      Plotly.react('chart-indikator', [
        baseLocs.length ? {{
          type: 'choropleth', geojson: baseGJ, locations: baseLocs, z: baseLocs.map(_=>0),
          featureidkey: 'properties.ADM2_PCODE',
          colorscale: [[0,'#E8E8E8'],[1,'#E8E8E8']], showscale: false,
          marker: {{ line: {{ color: 'white', width: 0.3 }} }},
          hoverinfo: 'skip', showlegend: false,
        }} : null,
        {{
          type: 'choropleth', geojson: dataGJ, locations: locs, z: vals,
          featureidkey: 'properties.ADM2_PCODE',
          zmin: bins[0], zmax: bins[5],
          colorscale, showscale: true,
          colorbar: {{ thickness: 10, len: 0.7, tickfont: {{ size: 11, color: MUTED }} }},
          marker: {{ line: {{ color: 'white', width: 0.3 }} }},
          hovertext, hovertemplate: '%{{hovertext}}<extra></extra>',
          hoverlabel: {{ bgcolor: 'white', bordercolor: '#003D79', font: {{ family: FONT, size: 13, color: INK }}, align: 'left', namelength: -1 }},
        }}
      ].filter(t => t), {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        font: {{ family: FONT, color: INK }},
        geo: {{ visible: false, bgcolor: '#FAFBFC', projection: {{ type: 'mercator' }}, fitbounds: 'locations' }},
        paper_bgcolor: 'transparent',
      }}, {{ displaylogo: false, responsive: true }});
    }},
    renderTrend() {{
      const t = PAYLOAD.nat_trend;
      const yrs = [2019,2020,2021,2022,2023,2024,2025];
      const traces = [
        {{ x: yrs, y: t.pct_mobil.map(v => v ? v*100 : null), name: 'Kepemilikan mobil', mode: 'lines+markers', type: 'scatter', yaxis: 'y',
           line: {{ color: '#003D79', width: 2.5 }}, marker: {{ size: 8, color: '#003D79' }} }},
        {{ x: yrs, y: t.pct_motor.map(v => v ? v*100 : null), name: 'Kepemilikan motor', mode: 'lines+markers', type: 'scatter', yaxis: 'y',
           line: {{ color: '#67B2E8', width: 2.5 }}, marker: {{ size: 8, color: '#67B2E8' }} }},
        {{ x: yrs, y: t.avg_kendaraan.map(v => v ? v/1e6 : null), name: 'Belanja kendaraan per RT (Rp jt/tahun)', mode: 'lines+markers', type: 'scatter', yaxis: 'y2',
           line: {{ color: '#FFB700', width: 2.5, dash: 'dot' }}, marker: {{ size: 8, color: '#FFB700' }} }},
      ];
      Plotly.react('chart-trend', traces, {{
        margin: {{ l: 60, r: 60, t: 30, b: 60 }},
        font: {{ family: FONT, size: 13, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ tickfont: {{ size: 14, color: INK }}, showline: true, linecolor: INK, ticks: 'outside', tickcolor: INK, ticklen: 4 }},
        yaxis: {{ title: {{ text: 'Kepemilikan per RT (%)', font: {{ size: 12, color: MUTED }} }},
                 tickfont: {{ size: 12, color: MUTED }}, gridcolor: '#F0F2F5', range: [0, 100] }},
        yaxis2: {{ title: {{ text: 'Belanja kendaraan (Rp jt/RT/tahun)', font: {{ size: 12, color: '#FFB700' }} }},
                  overlaying: 'y', side: 'right', tickfont: {{ size: 12, color: '#FFB700' }} }},
        legend: {{ orientation: 'h', y: -0.18, x: 0, xanchor: 'left' }},
      }}, {{ displaylogo: false, responsive: true }});
    }},
    renderMap() {{
      const isComposite = this.mapMode === 'composite';
      // Build slice keyed by pcode
      const slice = {{}};
      const tierByP = {{}};
      Object.values(PAYLOAD.composite).forEach(d => {{
        if (this.tierFilter.length > 0 && !this.tierFilter.includes(d.tier)) return;
        const v = isComposite ? d.composite : d.TAM;
        slice['ID' + String(d.pcode).padStart(4, '0')] = v;
        tierByP['ID' + String(d.pcode).padStart(4, '0')] = d.tier;
      }});
      const locs = Object.keys(slice);
      const vals = locs.map(p => slice[p]);

      // Hovertext rich
      const hovertext = locs.map(p => {{
        const pcode = parseInt(p.slice(2));
        const d = PAYLOAD.composite[pcode];
        if (!d) return p;
        const tamRb = (d.TAM / 1000).toFixed(0);
        const lc = d.low_confidence ? '<br><span style="color:#C8102E">⚠ Low confidence (n &lt; 30)</span>' : '';
        return `<b>${{d.nama_kab}}</b><br><span style="color:#667085">${{d.nama_prov}}</span><br>` +
               `<span style="color:#003D79;font-size:18px;font-weight:600">${{d.composite.toFixed(1)}}</span> Composite<br>` +
               `<span style="color:#667085">TAM: ${{tamRb}} rb RT · ${{d.tier}}</span>${{lc}}`;
      }});

      // No-data layer (kabs in geojson but not in slice)
      const allowedSet = new Set(locs);
      const noDataFeatures = GEOJSON.features.filter(f => !allowedSet.has(f.id));
      const noDataLocs = noDataFeatures.map(f => f.id);
      const dataFeatures = GEOJSON.features.filter(f => allowedSet.has(f.id));
      const dataGJ = {{ type: 'FeatureCollection', features: dataFeatures }};
      const baseGJ = {{ type: 'FeatureCollection', features: noDataFeatures }};

      Plotly.react('chart-map', [
        // Base layer: kab tidak match tier filter → grey
        noDataLocs.length ? {{
          type: 'choropleth', geojson: baseGJ, locations: noDataLocs, z: noDataLocs.map(_=>0),
          featureidkey: 'properties.ADM2_PCODE',
          colorscale: [[0,'#E8E8E8'],[1,'#E8E8E8']], showscale: false,
          marker: {{ line: {{ color: 'white', width: 0.3 }} }},
          hoverinfo: 'skip', showlegend: false,
        }} : null,
        {{
          type: 'choropleth', geojson: dataGJ, locations: locs, z: vals,
          featureidkey: 'properties.ADM2_PCODE',
          zmin: 0, zmax: isComposite ? 100 : Math.max(...vals, 1),
          colorscale: isComposite
            ? [[0,'#E8EFF6'],[0.25,'#A9C4DF'],[0.5,'#67B2E8'],[0.75,'#2A6FB3'],[1,'#003D79']]
            : [[0,'#FFF8E5'],[0.25,'#FFE08A'],[0.5,'#FFB700'],[0.75,'#D67900'],[1,'#003D79']],
          showscale: true,
          colorbar: {{ title: {{ text: isComposite ? 'Composite' : 'TAM (RT)', font: {{ size: 11, color: MUTED }} }},
                      thickness: 10, len: 0.7, tickfont: {{ size: 11, color: MUTED }} }},
          marker: {{ line: {{ color: 'white', width: 0.3 }} }},
          hovertext, hovertemplate: '%{{hovertext}}<extra></extra>',
          hoverlabel: {{ bgcolor: 'white', bordercolor: '#003D79', font: {{ family: FONT, size: 13, color: INK }}, align: 'left', namelength: -1 }},
        }}
      ].filter(t => t), {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        font: {{ family: FONT, color: INK }},
        geo: {{ visible: false, bgcolor: '#FAFBFC', projection: {{ type: 'mercator' }},
                lonaxis: {{ range: [94, 141.5] }}, lataxis: {{ range: [-11.5, 6.5] }} }},
        paper_bgcolor: 'transparent',
      }}, {{ displaylogo: false, responsive: true }});

      // Click event for drilldown
      const mapEl = document.getElementById('chart-map');
      const self = this;
      if (mapEl.removeAllListeners) mapEl.removeAllListeners('plotly_click');
      mapEl.on('plotly_click', d => {{
        if (d.points && d.points[0] && d.points[0].location) {{
          self.openDrilldown(parseInt(d.points[0].location.slice(2)));
        }}
      }});
    }},
    openDrilldown(pcode) {{
      const d = PAYLOAD.composite[pcode];
      if (!d) return;
      this.drilldown.open = true;
      this.drilldown.pcode = pcode;
      this.drilldown.nama_kab = d.nama_kab;
      this.drilldown.nama_prov = d.nama_prov;
      this.drilldown.tier = d.tier;
      this.drilldown.composite = d.composite.toFixed(1);
      this.drilldown.tam_display = (d.TAM / 1000).toFixed(0) + ' rb';
      this.drilldown.low_conf = d.low_confidence;
      this.drilldown.pillars = [
        {{ lbl: 'P1 Adoption Velocity', val: d.P1_Adoption_Velocity }},
        {{ lbl: 'P2 Purchase Momentum', val: d.P2_Purchase_Momentum }},
        {{ lbl: 'P3 Cost of Ownership', val: d.P3_Cost_Of_Ownership }},
        {{ lbl: 'P4 Intensity',         val: d.P4_Intensity }},
        {{ lbl: 'P5 Capacity Scale',    val: d.P5_Capacity_Scale }},
      ];
      // Render trend chart in drawer
      this.$nextTick(() => {{
        const ts = PAYLOAD.kab_ts[pcode];
        if (!ts) return;
        const yrs = [2019,2020,2021,2022,2023,2024,2025];
        Plotly.newPlot('chart-detail', [
          {{ x: yrs, y: ts.pct_mobil.map(v => v ? v*100 : null), name: 'Kepemilikan mobil', mode: 'lines+markers', line: {{color:'#003D79', width:2}} }},
          {{ x: yrs, y: ts.pct_motor.map(v => v ? v*100 : null), name: 'Kepemilikan motor', mode: 'lines+markers', line: {{color:'#67B2E8', width:2}} }},
        ], {{
          margin: {{ l: 40, r: 20, t: 20, b: 40 }},
          font: {{ family: FONT, size: 11, color: INK }},
          plot_bgcolor: 'white', paper_bgcolor: 'white',
          xaxis: {{ tickfont: {{ size: 11 }} }},
          yaxis: {{ tickfont: {{ size: 11, color: MUTED }}, gridcolor: '#F0F2F5', range: [0, 100], title: {{text:'%',font:{{size:10}}}} }},
          legend: {{ orientation: 'h', y: -0.15, x: 0, xanchor: 'left', font: {{ size: 10 }} }},
        }}, {{ displaylogo: false, responsive: true }});
      }});
    }},
    exportPPT() {{
      const W = 1920, H = 1080;
      const canvas = document.createElement('canvas');
      canvas.width = W; canvas.height = H;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#FFFFFF'; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = '#003D79'; ctx.fillRect(0, 0, W, 6);
      ctx.fillStyle = '#051C2C';
      ctx.font = "600 36px 'Source Serif 4', Georgia, serif";
      ctx.fillText('Peta Potensi Pasar Kredit Kendaraan per Kab/Kota', 60, 90);
      ctx.font = "400 18px 'Inter', sans-serif"; ctx.fillStyle = '#667085';
      ctx.fillText((this.mapMode==='composite'?'Skor Komposit':'Pasar Potensial') + ' · 2025 · Riset Mandiri Institute', 60, 125);
      Plotly.toImage('chart-map', {{ format: 'png', width: 1700, height: 800, scale: 2 }})
        .then(url => {{
          const img = new Image();
          img.onload = () => {{
            ctx.drawImage(img, 110, 160, 1700, 800);
            ctx.fillStyle = '#667085'; ctx.font = "400 14px 'Inter', sans-serif";
            ctx.fillText('Sumber: Susenas BPS · Mandiri Institute · ' + new Date().toISOString().slice(0,10), 60, H - 30);
            const logo = new Image();
            logo.onload = () => {{
              const lh = 60, lw = logo.width * (lh / logo.height);
              ctx.drawImage(logo, W - lw - 60, H - lh - 20, lw, lh);
              canvas.toBlob(blob => {{
                const u = URL.createObjectURL(blob);
                const a = document.createElement('a'); a.href = u; a.download = 'peta-kendaraan-2025-Mandiri-Institute.png';
                document.body.appendChild(a); a.click(); document.body.removeChild(a);
                URL.revokeObjectURL(u);
              }}, 'image/png');
            }};
            logo.src = '../_assets/logo/mandiri-institute-color.jpg';
          }};
          img.src = url;
        }});
    }},
  }};
}}
</script>
</body>
</html>
"""


def main():
    df = load()
    with open(META, "r", encoding="utf-8") as f:
        meta = json.load(f)
    payload = build_payload(df, meta)

    with open(GEOJSON_KAB, "r", encoding="utf-8") as f:
        geojson_kab = json.load(f)

    # Heavy data ke .js file
    js = (
        f"window.PAYLOAD = {json.dumps(payload, separators=(',', ':'))};\n"
        f"window.GEOJSON_KAB = {json.dumps(geojson_kab, separators=(',', ':'))};\n"
    )
    DATA_JS.write_text(js, encoding="utf-8")
    print(f"Wrote {DATA_JS.name} ({DATA_JS.stat().st_size:,} bytes)")

    html = build_html(payload, geojson_kab, date.today().isoformat())
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT.name} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
