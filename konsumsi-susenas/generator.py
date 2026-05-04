"""
Generator dashboard Konsumsi per Kapita per Bulan, 2019-2025 (Susenas).
Input: data.csv + metadata.json (co-located, dari data_processing).
Output: dashboard.html (single file, data embed).
Stack: Plotly.js + Tailwind CSS (CDN), Alpine.js untuk filter, McKinsey-style template.
"""
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
CSV = HERE / "data.csv"
if not CSV.exists():
    CSV = HERE / "Old" / "data.csv"  # data_processing pindahkan ke Old/
# Raw source data: di luar dashboard folder (publish-only).
# Konvensi Mandiri Institute: dashboard folder = HANYA file yang siap di-publish.
# Raw data tinggal di Data\Dashboard-Sources\<topik>\
DATA_SOURCES = HERE.parent.parent.parent / "Data" / "Dashboard-Sources" / "konsumsi-susenas"
CSV_KOMODITI = DATA_SOURCES / "data_komoditi.csv"
if not CSV_KOMODITI.exists():
    # Fallback: kalau user pindah-pindah, cek lokasi lama
    CSV_KOMODITI_LEGACY = HERE / "data_komoditi.csv"
    if CSV_KOMODITI_LEGACY.exists():
        CSV_KOMODITI = CSV_KOMODITI_LEGACY
    else:
        raise FileNotFoundError(
            f"data_komoditi.csv tidak ditemukan di {CSV_KOMODITI} maupun {CSV_KOMODITI_LEGACY}"
        )
META = HERE / "metadata.json"
if not META.exists():
    META = HERE / "Old" / "metadata.json"
GEOJSON = HERE / "provinsi_bps_simplified.geojson"
OUT = HERE / "dashboard.html"
KOMODITI_JS = HERE / "komoditi_data.js"

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
CLASSES = ["Poor", "Vulnerable", "Lower AMC", "Upper AMC",
           "Lower MC", "Middle MC", "Upper MC", "Upper Class"]

# Pemekaran Papua 2022+ -> induk (kompatibel dgn shapefile BPS 2020, 34 prov)
PEMEKARAN_MAP = {92: 94, 95: 91, 96: 91, 97: 91}


def normalize_prov_name(s):
    """Title case + spelling override (Sumatera → Sumatra) per style guide."""
    s = str(s).strip().title()
    s = s.replace("Sumatera", "Sumatra")
    return s


def load():
    """
    Return 2 versi df:
      - df_38: original 38 prov (untuk ranking & non-map analytics)
      - df_34: pemekaran Papua diagregasi ke induk (untuk peta choropleth)
    """
    raw = pd.read_csv(CSV)
    raw["nama_prov"] = raw["nama_prov"].apply(normalize_prov_name)
    raw["pcode38"] = "ID" + raw["kode_prov"].astype(int).astype(str).str.zfill(2)

    df_34 = raw.copy()
    df_34["kode_prov"] = df_34["kode_prov"].replace(PEMEKARAN_MAP)
    df_34["pcode"] = "ID" + df_34["kode_prov"].astype(int).astype(str).str.zfill(2)

    df_38 = raw.copy()
    df_38["pcode"] = df_38["pcode38"]
    return df_38, df_34


def build_komoditi_js():
    """
    Aggregate komoditi data per (tahun, kelas, komoditi, prov) → rp_per_kapita_bulan.
    Save as JS file (window.KOMODITI_DATA) untuk loaded via <script src> di HTML.
    File terpisah karena ~5MB; script src works untuk file://.
    """
    print("Loading komoditi CSV...")
    df = pd.read_csv(CSV_KOMODITI)
    # Pakai 38 prov originalnya (untuk ranking & data); peta akan match by pcode (34 dipakai render, 38 untuk ranking).
    df["pcode"] = "ID" + df["kode_prov"].astype(int).astype(str).str.zfill(2)

    # Re-aggregate after pemekaran merge: weighted by population is approximate
    # since we don't have pop here; use sum of rp × prov-share approach.
    # Simplest: groupby (tahun, kelas, nama_komoditi, pcode) → mean rp.
    print("Aggregating...")
    # Schema terbaru: rp_per_kapita_bulan (post-fix factor 30/7)
    agg = (df.groupby(["tahun", "kelas", "nama_komoditi", "pcode"])
             ["rp_per_kapita_bulan"].mean().reset_index())
    agg["rp"] = agg["rp_per_kapita_bulan"].round().astype(int)

    # Build nested dict: {year: {kelas: {komoditi: {pcode: rp}}}}
    print("Building dict...")
    out = {}
    for year in YEARS:
        out[str(year)] = {}
        ydf = agg[agg["tahun"] == year]
        for kelas in CLASSES:
            kdf = ydf[ydf["kelas"] == kelas]
            out[str(year)][kelas] = {}
            for kom, sub in kdf.groupby("nama_komoditi"):
                out[str(year)][kelas][kom] = dict(zip(sub["pcode"], sub["rp"]))

    # Komoditi list grouped by kelompok for dropdown.
    # Parse nama jadi short label + description: "Beras (beras lokal, kualitas unggul, impor)"
    # → short="Beras", desc="beras lokal, kualitas unggul, impor"
    def parse_name(full):
        s = full.strip()
        if "(" in s and s.endswith(")"):
            i = s.rindex("(")
            short = s[:i].strip().rstrip(",;")
            desc = s[i + 1:-1].strip()
            return short, desc
        if "/" in s:
            parts = [p.strip() for p in s.split("/")]
            return parts[0], "atau " + ", ".join(parts[1:])
        return s, None

    dim = pd.read_csv(HERE / "komoditi_dim.csv")
    dim_sorted = dim.sort_values(["is_makanan", "kelompok", "nama_komoditi"], ascending=[False, True, True])
    valid = set(agg["nama_komoditi"].unique())
    komoditi_list = []
    for _, r in dim_sorted.iterrows():
        if r["nama_komoditi"] in valid:
            short, desc = parse_name(r["nama_komoditi"])
            komoditi_list.append({
                "key": r["nama_komoditi"],   # match KOMODITI_DATA keys
                "short": short,
                "desc": desc,
                "kelompok": r["kelompok"],
                "is_makanan": bool(r["is_makanan"]),
            })

    js = (
        f"window.KOMODITI_DATA = {json.dumps(out, separators=(',', ':'))};\n"
        f"window.KOMODITI_LIST = {json.dumps(komoditi_list, separators=(',', ':'))};\n"
    )
    KOMODITI_JS.write_text(js, encoding="utf-8")
    print(f"Wrote {KOMODITI_JS.name} ({KOMODITI_JS.stat().st_size:,} bytes)")


def build_aggregates(df):
    tot = df[df["kelompok"] == "__TOTAL__"].copy()  # has rp_per_kapita_bulan etc.
    klp = df[df["kelompok"] != "__TOTAL__"].copy()  # has share_pct only

    # ---- A. Nasional per tahun: weighted mean of per-kapita rp, per tahun
    nat = (
        tot.groupby("tahun")
        .apply(lambda g: pd.Series({
            "rp_total": np.average(g["rp_per_kapita_bulan"], weights=g["pop_tertimbang"]),
            "rp_median": np.average(g["rp_per_kapita_median"], weights=g["pop_tertimbang"]),
            "share_makanan": np.average(g["share_makanan_pct"], weights=g["pop_tertimbang"]),
            "share_nonmakanan": np.average(g["share_nonmakanan_pct"], weights=g["pop_tertimbang"]),
            "pop": g["pop_tertimbang"].sum(),
        }))
        .reset_index()
    )
    nat["rp_makanan"] = nat["rp_total"] * nat["share_makanan"] / 100
    nat["rp_nonmakanan"] = nat["rp_total"] * nat["share_nonmakanan"] / 100

    # ---- B. Nasional per (tahun, kelas): weighted mean
    nat_kelas = (
        tot.groupby(["tahun", "kelas"])
        .apply(lambda g: pd.Series({
            "rp_total": np.average(g["rp_per_kapita_bulan"], weights=g["pop_tertimbang"]),
            "share_makanan": np.average(g["share_makanan_pct"], weights=g["pop_tertimbang"]),
            "share_nonmakanan": np.average(g["share_nonmakanan_pct"], weights=g["pop_tertimbang"]),
        }))
        .reset_index()
    )

    # ---- C. Nasional per (tahun, kelas, kelompok): weighted mean of share_pct
    # Need pop weights from tot, joined by (tahun, prov, kelas).
    # Drop existing (NaN) pop_tertimbang in klp first to avoid suffix collision.
    klp = klp.drop(columns=["pop_tertimbang"]).merge(
        tot[["tahun", "kode_prov", "kelas", "pop_tertimbang"]],
        on=["tahun", "kode_prov", "kelas"], how="left",
    )
    nat_klp = (
        klp.groupby(["tahun", "kelas", "kelompok"])
        .apply(lambda g: pd.Series({
            "share_pct": np.average(g["share_pct"], weights=g["pop_tertimbang"]),
        }))
        .reset_index()
    )

    # ---- D. Per (tahun, prov, kelas): rp_per_kapita (already in tot)
    prov = tot[["tahun", "pcode", "nama_prov", "kelas", "rp_per_kapita_bulan", "share_makanan_pct"]].copy()

    # ---- E. Per (tahun, prov): weighted across kelas
    prov_all = (
        tot.groupby(["tahun", "pcode"])
        .apply(lambda g: pd.Series({
            "nama_prov": g["nama_prov"].iloc[0],
            "rp_per_kapita_bulan": np.average(g["rp_per_kapita_bulan"], weights=g["pop_tertimbang"]),
            "share_makanan_pct": np.average(g["share_makanan_pct"], weights=g["pop_tertimbang"]),
        }))
        .reset_index()
    )

    return nat, nat_kelas, nat_klp, prov, prov_all


def build_prov_38(df_38):
    """Untuk ranking: per (tahun, kelas/All, prov38) → rp_per_kapita_bulan."""
    tot = df_38[df_38["kelompok"] == "__TOTAL__"].copy()
    rank_data = {}
    rank_meta = {}
    for y in YEARS:
        rank_data[str(y)] = {}
        for k in CLASSES:
            sub = tot[(tot["tahun"] == y) & (tot["kelas"] == k)]
            rank_data[str(y)][k] = {
                row["pcode"]: round(float(row["rp_per_kapita_bulan"]))
                for _, row in sub.iterrows()
            }
        # All kelas: weighted across 8 kelas per prov
        ydf = tot[tot["tahun"] == y]
        agg = (ydf.groupby(["pcode"])
                  .apply(lambda g: np.average(g["rp_per_kapita_bulan"], weights=g["pop_tertimbang"]))
              )
        rank_data[str(y)]["All"] = {p: round(float(v)) for p, v in agg.items()}
    rank_meta = tot.groupby("pcode")["nama_prov"].first().to_dict()
    return rank_data, rank_meta


def to_js(nat, nat_kelas, nat_klp, prov, prov_all, kelompok_order, klp_makanan):
    # Trend nasional
    trend = {
        "tahun": nat["tahun"].astype(int).tolist(),
        "rp_total": [round(x) for x in nat["rp_total"]],
        "rp_makanan": [round(x) for x in nat["rp_makanan"]],
        "rp_nonmakanan": [round(x) for x in nat["rp_nonmakanan"]],
        "share_makanan": [round(x, 2) for x in nat["share_makanan"]],
    }

    # Per kelas per tahun
    nat_kelas_dict = {}
    for y in YEARS:
        sub = nat_kelas[nat_kelas["tahun"] == y].set_index("kelas")
        nat_kelas_dict[str(y)] = {
            k: {
                "rp_total": round(float(sub.loc[k, "rp_total"])),
                "share_makanan": round(float(sub.loc[k, "share_makanan"]), 2),
                "share_nonmakanan": round(float(sub.loc[k, "share_nonmakanan"]), 2),
            }
            for k in CLASSES if k in sub.index
        }

    # Heatmap kelompok × kelas per tahun
    heatmap = {}
    for y in YEARS:
        sub = nat_klp[nat_klp["tahun"] == y]
        heatmap[str(y)] = {
            kl: {kp: round(float(v), 2) for kp, v in sub[sub["kelas"] == kl].set_index("kelompok")["share_pct"].to_dict().items()}
            for kl in CLASSES
        }

    # Peta: per (tahun, kelas/All, prov) -> rp
    map_data = {}
    for y in YEARS:
        map_data[str(y)] = {}
        for k in CLASSES:
            sub = prov[(prov["tahun"] == y) & (prov["kelas"] == k)]
            map_data[str(y)][k] = {
                row["pcode"]: round(float(row["rp_per_kapita_bulan"]))
                for _, row in sub.iterrows()
            }
        # All kelas
        sub = prov_all[prov_all["tahun"] == y]
        map_data[str(y)]["All"] = {
            row["pcode"]: round(float(row["rp_per_kapita_bulan"]))
            for _, row in sub.iterrows()
        }

    prov_meta = (prov_all.groupby("pcode")["nama_prov"].first().to_dict())

    return {
        "trend": trend,
        "nat_kelas": nat_kelas_dict,
        "heatmap": heatmap,
        "map": map_data,
        "prov_meta": prov_meta,    # 34 prov (pemekaran merged)
        "kelompok_order": kelompok_order,
        "klp_makanan": klp_makanan,
    }


def build_html(payload, geojson, generated):
    rp_2019 = payload["trend"]["rp_total"][0]
    rp_2025 = payload["trend"]["rp_total"][-1]
    growth = (rp_2025 / rp_2019 - 1) * 100
    cagr = ((rp_2025 / rp_2019) ** (1 / 6) - 1) * 100
    share_makanan_2025 = payload["trend"]["share_makanan"][-1]
    share_makanan_2019 = payload["trend"]["share_makanan"][0]

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Konsumsi per Kapita per Bulan, 2019-2025</title>
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
  .eyebrow-on-dark {{ font-size: 11px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--sky); }}
  .rule-top {{ border-top: 1px solid var(--rule); }}
  .rule-bottom {{ border-bottom: 1px solid var(--rule); }}
  .hair-accent {{ border-top: 3px solid var(--sky); }}
  .ink {{ color: var(--ink); }}
  .muted {{ color: var(--muted); }}
  .num {{ font-variant-numeric: tabular-nums; }}
  .navy-bg {{ background-color: var(--navy); }}
  .cream-bg {{ background-color: var(--cream); }}
  .mist-bg {{ background-color: var(--mist); }}
  .select-flat {{ border: 0; border-bottom: 1px solid var(--ink); background: transparent; padding: 6px 24px 6px 0; font-size: 15px; font-weight: 500; color: var(--ink); appearance: none; background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%23051C2C'%3e%3cpath fill-rule='evenodd' d='M5.23 7.21a.75.75 0 011.06.02L10 11.06l3.71-3.83a.75.75 0 111.08 1.04l-4.25 4.39a.75.75 0 01-1.08 0L5.21 8.27a.75.75 0 01.02-1.06z' clip-rule='evenodd'/%3e%3c/svg%3e"); background-repeat: no-repeat; background-position: right 0 center; background-size: 18px; }}
  .select-flat:focus {{ outline: none; border-bottom-color: var(--sky); }}

  /* Top nav (dark navy band) */
  .topnav {{ background: var(--navy); color: white; }}
  .topnav .brand {{ color: white; }}
  .topnav .brand .yellow-accent {{ color: var(--yellow); margin-right: 6px; }}
  .tab {{ position: relative; padding: 8px 4px; font-size: 11px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: rgba(255,255,255,0.7); background: transparent; border: none; transition: color 0.15s; }}
  .tab:hover {{ color: white; }}
  .tab-active {{ position: relative; padding: 8px 4px; font-size: 11px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: white; background: transparent; border: none; }}
  .tab-active::after {{ content: ''; position: absolute; left: 0; right: 0; bottom: -16px; height: 3px; background: var(--sky); }}

  /* Hero band (dark navy bg, white text) */
  .hero-band {{ background: var(--navy); color: white; }}
  .hero-band .eyebrow {{ color: var(--sky); }}
  .hero-band h1, .hero-band h2 {{ color: white; }}
  .hero-band p {{ color: rgba(255,255,255,0.78); }}
  .hero-band .ink {{ color: white; }}
  .hero-band .muted {{ color: rgba(255,255,255,0.6); }}
  .hero-band .stat-num {{ color: white; }}
  .hero-band .border-rule {{ border-color: rgba(255,255,255,0.15) !important; }}

  /* Data badge (FT-style chip above chart title) */
  .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--navy); background: var(--mist); border: 1px solid var(--sky); border-radius: 2px; }}
  .badge-dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--sky); display: inline-block; }}

  /* Key insight callout (Economist/Bloomberg style) */
  .callout {{ border-left: 3px solid var(--sky); background: var(--mist); padding: 18px 24px; }}
  .callout .label {{ font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--navy); }}
  .callout .text {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 18px; line-height: 1.45; color: var(--ink); margin-top: 6px; font-weight: 500; }}

  /* Chart footer (Brookings-style source/methodology) */
  .chart-footer {{ border-top: 1px solid var(--rule); margin-top: 16px; padding-top: 12px; display: flex; flex-wrap: wrap; gap: 24px; font-size: 11px; color: var(--muted); }}
  .chart-footer .label {{ font-weight: 600; color: var(--ink); text-transform: uppercase; letter-spacing: 0.06em; margin-right: 4px; }}

  /* Section background variants (alt rhythm) */
  .section-cream {{ background: var(--cream); }}

  /* Insight panel (Pew / OWID 2-col text+chart) */
  .insight-grid {{ display: grid; grid-template-columns: 1fr; gap: 32px; }}
  @media (min-width: 1024px) {{ .insight-grid {{ grid-template-columns: 320px 1fr; gap: 56px; }} }}
  .insight-panel h3 {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 22px; line-height: 1.25; font-weight: 500; color: var(--ink); margin-bottom: 12px; }}
  .insight-panel p {{ font-size: 14px; line-height: 1.6; color: var(--muted); margin-bottom: 12px; }}
  .insight-panel .takeaways {{ margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--rule); }}
  .insight-panel .takeaways li {{ font-size: 13px; line-height: 1.5; color: var(--ink); padding-left: 14px; position: relative; margin-bottom: 8px; }}
  .insight-panel .takeaways li::before {{ content: '▪'; position: absolute; left: 0; color: var(--sky); font-size: 14px; line-height: 1; top: 4px; }}

  /* Ranking table: editorial */
  .rank-card h4 {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 17px; font-weight: 600; color: var(--ink); margin-bottom: 4px; }}
  .rank-card .sub {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }}
  .rank-list {{ margin-top: 14px; }}
  .rank-row {{ display: grid; grid-template-columns: 28px 1fr 110px; align-items: center; gap: 16px; padding: 10px 0; border-bottom: 1px solid var(--rule); transition: background 0.12s; }}
  .rank-row:hover {{ background: var(--mist); padding-left: 8px; padding-right: 8px; margin-left: -8px; margin-right: -8px; }}
  .rank-row .rank-num {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 16px; font-weight: 600; color: var(--sky); text-align: right; }}
  .rank-row.is-bottom .rank-num {{ color: #C8102E; }}
  .rank-row .rank-name {{ font-size: 14px; color: var(--ink); font-weight: 500; }}
  .rank-row .rank-bar-wrap {{ position: relative; height: 6px; background: var(--mist); border-radius: 0; overflow: hidden; }}
  .rank-row .rank-bar {{ position: absolute; left: 0; top: 0; height: 100%; max-width: 100%; background: var(--navy); }}
  .rank-row.is-bottom .rank-bar {{ background: #C8102E; opacity: 0.7; }}
  .rank-row .rank-val {{ font-variant-numeric: tabular-nums; font-size: 13px; font-weight: 600; color: var(--ink); margin-top: 4px; }}
  .rank-cell-right {{ display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }}

  /* Floating hover info card (untuk peta) */
  .hover-card {{ position: absolute; pointer-events: none; z-index: 50; background: white; border: 1px solid var(--rule); box-shadow: 0 8px 24px rgba(5,28,44,0.12); padding: 0; min-width: 260px; max-width: 300px; opacity: 0; transition: opacity 0.12s; transform: translate(-50%, -100%); margin-top: -16px; }}
  .hover-card.is-visible {{ opacity: 1; }}
  .hover-card .icon-box {{ background: var(--mist); border-bottom: 3px solid var(--sky); padding: 24px; display: flex; align-items: center; justify-content: center; }}
  .hover-card .icon-box iconify-icon {{ font-size: 56px; color: var(--navy); }}
  .hover-card .body {{ padding: 16px 20px; }}
  .hover-card .item-label {{ font-size: 11px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }}
  .hover-card .item-name {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 16px; font-weight: 600; color: var(--ink); margin-top: 2px; line-height: 1.2; }}
  .hover-card .prov-name {{ font-size: 14px; font-weight: 600; color: var(--ink); margin-top: 12px; }}
  .hover-card .value {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 28px; font-weight: 600; color: var(--navy); margin-top: 2px; letter-spacing: -0.01em; line-height: 1; }}
  .hover-card .meta {{ font-size: 11px; color: var(--muted); margin-top: 6px; }}

  /* Icon di samping title komoditi */
  .title-icon {{ display: inline-flex; align-items: center; justify-content: center; width: 48px; height: 48px; background: var(--mist); border-left: 3px solid var(--sky); margin-right: 14px; vertical-align: middle; }}
  .title-icon iconify-icon {{ font-size: 28px; color: var(--navy); }}

  /* Map legend (FT/Bloomberg-style chip strip) */
  .map-legend {{ display: flex; align-items: center; gap: 16px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--rule); }}
  .map-legend-label {{ font-size: 11px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }}
  .map-legend-bins {{ display: flex; align-items: center; gap: 0; flex: 1; }}
  .map-legend-bin {{ flex: 1; display: flex; flex-direction: column; gap: 4px; }}
  .map-legend-bin .swatch {{ height: 10px; }}
  .map-legend-bin .range {{ font-size: 10px; color: var(--muted); font-variant-numeric: tabular-nums; padding-top: 2px; }}

  /* Action chips di chart footer (download, compare, dll) */
  .chip-action {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--navy); background: white; border: 1px solid var(--rule); cursor: pointer; transition: all 0.12s; }}
  .chip-action:hover {{ background: var(--mist); border-color: var(--navy); }}
  .chip-action.active {{ background: var(--navy); color: white; border-color: var(--navy); }}
  .chip-action iconify-icon {{ font-size: 14px; }}

  /* Cmd+K command palette */
  .cmdk-backdrop {{ position: fixed; inset: 0; background: rgba(5,28,44,0.45); z-index: 100; display: flex; align-items: flex-start; justify-content: center; padding-top: 12vh; }}
  .cmdk-modal {{ width: 640px; max-width: 90vw; background: white; box-shadow: 0 20px 60px rgba(5,28,44,0.3); display: flex; flex-direction: column; max-height: 70vh; }}
  .cmdk-search {{ display: flex; align-items: center; gap: 12px; padding: 16px 20px; border-bottom: 1px solid var(--rule); }}
  .cmdk-search iconify-icon {{ font-size: 20px; color: var(--muted); }}
  .cmdk-search input {{ flex: 1; border: none; outline: none; font-size: 16px; color: var(--ink); font-family: 'Inter', sans-serif; background: transparent; }}
  .cmdk-search kbd {{ padding: 2px 6px; font-size: 11px; background: var(--mist); border: 1px solid var(--rule); border-radius: 3px; color: var(--muted); font-family: 'Inter', monospace; }}
  .cmdk-results {{ overflow-y: auto; padding: 8px 0; }}
  .cmdk-section {{ padding: 8px 20px 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }}
  .cmdk-item {{ display: flex; align-items: center; gap: 12px; padding: 10px 20px; cursor: pointer; font-size: 14px; color: var(--ink); }}
  .cmdk-item:hover, .cmdk-item.active {{ background: var(--mist); }}
  .cmdk-item iconify-icon {{ font-size: 18px; color: var(--navy); }}
  .cmdk-item .meta {{ margin-left: auto; font-size: 11px; color: var(--muted); }}

  /* Dark mode */
  body.dark {{ --paper: #051C2C; --ink: #E5EAF0; --rule: #1E3A55; --muted: #8A9BAE; --mist: #0E2940; --cream: #0E2940; --navy: #67B2E8; --sky: #003D79; }}
  body.dark .hero-band {{ background: #0A2240; }}
  body.dark .sidebar {{ background: #0A2240; }}
  body.dark .navy-bg {{ background: #0A2240; }}

  /* Sparkline mini chart di hero stat */
  .hero-stat {{ position: relative; }}
  .hero-stat .sparkline {{ height: 32px; margin-top: 8px; opacity: 0.85; }}

  /* Freshness badge */
  .freshness {{ display: inline-flex; align-items: center; gap: 6px; padding: 2px 8px; font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--sky); background: rgba(103,178,232,0.08); border: 1px solid rgba(103,178,232,0.3); border-radius: 0; }}
  .freshness .dot {{ width: 6px; height: 6px; border-radius: 50%; background: var(--sky); animation: pulse 2.5s infinite; }}
  @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}

  /* Loading skeleton */
  .skeleton {{ background: linear-gradient(90deg, var(--mist) 25%, #F4F4F4 50%, var(--mist) 75%); background-size: 200% 100%; animation: shimmer 1.4s infinite; }}
  @keyframes shimmer {{ 0% {{ background-position: -200% 0; }} 100% {{ background-position: 200% 0; }} }}

  /* Auto-narrated insight box */
  .narrative {{ background: var(--cream); border-left: 3px solid var(--yellow); padding: 16px 20px; margin-top: 16px; }}
  .narrative .label {{ font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink); }}
  .narrative .text {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 15px; line-height: 1.5; color: var(--ink); margin-top: 6px; }}

  /* Saved views pinned */
  .pin-btn {{ background: transparent; border: 1px solid var(--rule); padding: 4px 8px; font-size: 10px; color: var(--muted); cursor: pointer; }}
  .pin-btn:hover {{ background: var(--mist); color: var(--navy); border-color: var(--navy); }}
  .pin-btn.is-pinned {{ background: var(--yellow); color: var(--ink); border-color: var(--yellow); }}

  /* Tour onboarding */
  .tour-spot {{ position: fixed; z-index: 90; background: white; padding: 16px 20px; box-shadow: 0 12px 40px rgba(5,28,44,0.25); max-width: 320px; border-left: 3px solid var(--yellow); }}
  .tour-spot .step {{ font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--navy); }}
  .tour-spot .text {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 15px; line-height: 1.4; margin-top: 6px; color: var(--ink); }}
  .tour-spot .actions {{ display: flex; gap: 8px; margin-top: 12px; justify-content: space-between; align-items: center; }}
  .tour-spot button {{ font-size: 11px; padding: 5px 12px; border: 1px solid var(--ink); background: white; cursor: pointer; }}
  .tour-spot button.primary {{ background: var(--ink); color: white; }}

  /* Mobile responsive */
  .mobile-toggle {{ display: none; position: fixed; top: 12px; left: 12px; z-index: 50; background: var(--navy); color: white; border: none; padding: 8px; cursor: pointer; }}
  @media (max-width: 768px) {{
    .sidebar {{ transform: translateX(-100%); transition: transform 0.25s; }}
    .sidebar.is-open {{ transform: translateX(0); }}
    .with-sidebar {{ margin-left: 0; }}
    .mobile-toggle {{ display: block; }}
    .insight-grid {{ grid-template-columns: 1fr !important; }}
    .max-w-\\[1280px\\] {{ padding-left: 16px; padding-right: 16px; }}
    h1.serif-display {{ font-size: 32px !important; }}
    h2.serif-display {{ font-size: 22px !important; }}
    .stat-num {{ font-size: 32px !important; }}
  }}

  /* Color blind safe palette toggle */
  body.cb-mode {{
    --navy: #0072B2; --sky: #56B4E9; --yellow: #E69F00;
  }}
  body.cb-mode .map-legend-bin .swatch[data-cb] {{ background-image: none; }}

  /* Hover sync: row highlighted dari peta hover */
  .rank-row.is-hovered {{ background: var(--yellow) !important; transition: background 0.1s; }}
  .rank-row.is-hovered .rank-name {{ font-weight: 700; }}

  /* Provinsi profile sticky side panel (click drill-down) */
  .prov-panel {{ position: fixed; top: 0; right: 0; bottom: 0; width: 380px; background: white; border-left: 1px solid var(--rule); box-shadow: -8px 0 32px rgba(5,28,44,0.12); transform: translateX(100%); transition: transform 0.25s; z-index: 60; overflow-y: auto; }}
  .prov-panel.is-open {{ transform: translateX(0); }}
  .prov-panel .head {{ background: var(--navy); color: white; padding: 24px; }}
  .prov-panel .head .close {{ position: absolute; top: 16px; right: 16px; background: transparent; border: none; color: rgba(255,255,255,0.7); cursor: pointer; font-size: 22px; }}
  .prov-panel .head .close:hover {{ color: white; }}
  .prov-panel .head .label {{ font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--sky); }}
  .prov-panel .head h3 {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 28px; font-weight: 600; line-height: 1.1; margin-top: 6px; color: white; }}
  .prov-panel .body {{ padding: 24px; }}
  .prov-panel .metric {{ padding: 16px 0; border-bottom: 1px solid var(--rule); }}
  .prov-panel .metric:last-child {{ border-bottom: none; }}
  .prov-panel .metric .lbl {{ font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }}
  .prov-panel .metric .val {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 32px; font-weight: 600; color: var(--navy); margin-top: 4px; line-height: 1; }}
  .prov-panel .metric .sub {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}

  /* Editorial display typography upgrade (Stripe Annual Letter) */
  .stat-num.huge {{ font-size: 96px; line-height: 0.95; letter-spacing: -0.03em; }}
  .stat-num.giant {{ font-size: 128px; line-height: 0.95; letter-spacing: -0.04em; }}

  /* A11y: focus ring + skip link */
  *:focus-visible {{ outline: 2px solid var(--sky); outline-offset: 2px; }}
  .skip-link {{ position: absolute; top: -100px; left: 8px; background: var(--ink); color: white; padding: 8px 16px; z-index: 200; font-size: 14px; font-weight: 600; transition: top 0.15s; }}
  .skip-link:focus {{ top: 8px; }}

  /* Outlier badge */
  .outlier-badge {{ display: inline-flex; align-items: center; gap: 4px; padding: 2px 6px; font-size: 9px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #C8102E; background: rgba(200,16,46,0.1); border: 1px solid #C8102E; }}

  /* Sparkline kolom — opt-in via .has-spark */
  .rank-row.has-spark {{ grid-template-columns: 28px 1fr 60px 130px !important; gap: 10px !important; }}
  .rank-spark {{ width: 60px; height: 22px; }}
  /* Default rank-row: tetap 3-col, lebar value cell cukup untuk "Rp X.XXX.XXX" inline */
  .rank-row .rank-cell-right {{ min-width: 130px; }}
  .rank-row .rank-val {{ white-space: nowrap; }}

  /* Comparison picker */
  .compare-card {{ border: 1px solid var(--rule); padding: 24px; background: white; }}
  .compare-card .head {{ border-bottom: 1px solid var(--rule); padding-bottom: 12px; margin-bottom: 16px; position: relative; }}
  .compare-card .head .label {{ font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); }}
  .compare-card .head .nama {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 22px; font-weight: 600; color: var(--ink); margin-top: 2px; }}
  .compare-card .head .remove {{ position: absolute; top: 0; right: 0; background: transparent; border: none; cursor: pointer; color: var(--muted); font-size: 18px; }}
  .compare-card .head .remove:hover {{ color: #C8102E; }}
  .compare-card .metric-row {{ display: flex; justify-content: space-between; align-items: baseline; padding: 10px 0; border-bottom: 1px dashed var(--rule); }}
  .compare-card .metric-row:last-child {{ border-bottom: none; }}
  .compare-card .metric-row .lbl {{ font-size: 12px; color: var(--muted); }}
  .compare-card .metric-row .val {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 20px; font-weight: 600; color: var(--navy); font-variant-numeric: tabular-nums; }}
  .compare-card .metric-row .sub {{ font-size: 11px; color: var(--muted); margin-left: 4px; }}
  .pick-chip {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: 12px; font-weight: 600; color: var(--ink); background: white; border: 1px solid var(--rule); cursor: pointer; transition: all 0.12s; }}
  .pick-chip:hover {{ border-color: var(--navy); }}
  .pick-chip.active {{ background: var(--navy); color: white; border-color: var(--navy); }}

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

  /* Print stylesheet */
  @media print {{
    .sidebar, .with-sidebar > .hero-band > header > p, .year-slider-wrap, .chip-action, .cmdk-backdrop {{ display: none !important; }}
    .with-sidebar {{ margin-left: 0 !important; }}
    body {{ background: white !important; color: black !important; }}
    .hero-band {{ background: white !important; color: black !important; border-bottom: 2px solid black; padding: 16px 0 !important; }}
    .hero-band h1 {{ color: black !important; font-size: 22pt !important; }}
    .hero-band .eyebrow {{ color: black !important; }}
    main {{ max-width: none !important; padding: 16px !important; }}
    section {{ display: block !important; page-break-after: always; }}
    .insight-grid {{ grid-template-columns: 1fr !important; gap: 12px !important; }}
    .callout {{ background: white !important; border: 1px solid black !important; }}
    .rank-row:hover {{ background: transparent !important; }}
  }}

  /* Sticky sidebar TOC (gov.uk / Notion style) */
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

  /* Year slider + play button (Flourish/OWID style) */
  .year-slider-wrap {{ display: flex; align-items: center; gap: 16px; }}
  .year-slider {{ flex: 1; min-width: 280px; max-width: 480px; }}
  .year-slider input[type=range] {{ -webkit-appearance: none; appearance: none; width: 100%; height: 4px; background: var(--rule); outline: none; border-radius: 0; }}
  .year-slider input[type=range]::-webkit-slider-thumb {{ -webkit-appearance: none; appearance: none; width: 18px; height: 18px; background: var(--navy); cursor: pointer; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 0 1px var(--navy); }}
  .year-slider input[type=range]::-moz-range-thumb {{ width: 18px; height: 18px; background: var(--navy); cursor: pointer; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 0 1px var(--navy); }}
  .year-ticks {{ display: flex; justify-content: space-between; margin-top: 8px; font-size: 11px; color: var(--muted); font-variant-numeric: tabular-nums; }}
  .year-tick {{ cursor: pointer; padding: 0 4px; transition: color 0.12s; }}
  .year-tick:hover {{ color: var(--navy); }}
  .year-tick.active {{ color: var(--navy); font-weight: 700; }}
  .play-btn {{ width: 38px; height: 38px; background: var(--navy); color: white; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.15s; }}
  .play-btn:hover {{ background: var(--navy-deep); }}
  .play-btn iconify-icon {{ font-size: 18px; }}
  .year-current {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 24px; font-weight: 600; color: var(--navy); min-width: 64px; }}
</style>
<script src="komoditi_data.js"></script>
</head>
<body>

<div x-data="dashboard()" x-init="init()">

<!-- A11y skip link -->
<a href="#main-content" class="skip-link">Lewati ke konten utama</a>

<!-- Provinsi profile sticky side panel -->
<aside class="prov-panel" :class="provPanel.open ? 'is-open' : ''" role="dialog" aria-label="Profil provinsi">
  <div class="head">
    <button class="close" @click="provPanel.open = false" aria-label="Tutup panel">×</button>
    <div class="label">Profil Provinsi</div>
    <h3 x-text="provPanel.nama"></h3>
  </div>
  <div class="body">
    <div class="metric">
      <div class="lbl">Pengeluaran per kapita / bulan</div>
      <div class="val" x-text="provPanel.rpTotal"></div>
      <div class="sub">Tahun <span x-text="year"></span> · Kelas <span x-text="mapKelas"></span></div>
    </div>
    <div class="metric">
      <div class="lbl">Rank Nasional</div>
      <div class="val" x-text="'#' + provPanel.rank + ' / 38'"></div>
    </div>
    <div class="metric">
      <div class="lbl">Pemekaran note</div>
      <div class="sub" x-text="provPanel.note"></div>
    </div>
  </div>
</aside>

<!-- Mobile toggle -->
<button class="mobile-toggle" @click="sidebarOpen = !sidebarOpen" aria-label="Toggle sidebar">
  <iconify-icon :icon="sidebarOpen ? 'mdi:close' : 'mdi:menu'" style="font-size:20px;"></iconify-icon>
</button>

<!-- Tour onboarding (first visit) -->
<div x-show="tour.active" x-cloak class="tour-spot" :style="'top:80px; left:240px;'">
  <div class="step" x-text="TOUR_STEPS[tour.step].step"></div>
  <div class="text" x-text="TOUR_STEPS[tour.step].text"></div>
  <div class="actions">
    <button @click="tour.active = false; localStorage.setItem('tour_done', '1')">Skip</button>
    <button class="primary" @click="tour.step++; if (tour.step >= TOUR_STEPS.length) {{ tour.active = false; localStorage.setItem('tour_done', '1'); }}">
      <span x-text="tour.step === TOUR_STEPS.length - 1 ? 'Selesai' : 'Berikutnya →'"></span>
    </button>
  </div>
</div>

<!-- Sticky sidebar -->
<aside class="sidebar" :class="sidebarOpen ? 'is-open' : ''">
  <div class="brand">
    <a href="../index.html" style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--sky);text-transform:uppercase;letter-spacing:0.1em;font-weight:600;text-decoration:none;margin-bottom:10px;">
      <iconify-icon icon="mdi:arrow-left"></iconify-icon><span>Beranda</span>
    </a>
    <span class="yellow-accent"></span>
    <div class="brand-title">Mandiri Institute</div>
    <div class="brand-sub">Dashboard</div>
  </div>
  <div class="nav-section">
    <div class="nav-label">Konsumsi Susenas</div>
    <template x-for="t in tabs" :key="t.id">
      <button @click="setPage(t.id)" :class="page === t.id ? 'nav-item active' : 'nav-item'">
        <iconify-icon :icon="t.icon"></iconify-icon>
        <span x-text="t.label"></span>
      </button>
    </template>
  </div>
  <div class="footer" style="display:flex;flex-direction:column;gap:8px;">
    <button @click="toggleDark()" class="nav-item" style="border:none;text-transform:none;letter-spacing:0;font-size:11px;padding:6px 0;">
      <iconify-icon :icon="dark ? 'mdi:weather-sunny' : 'mdi:weather-night'"></iconify-icon>
      <span x-text="dark ? 'Light mode' : 'Dark mode'"></span>
    </button>
    <button @click="cmdk.open = true" class="nav-item" style="border:none;text-transform:none;letter-spacing:0;font-size:11px;padding:6px 0;">
      <iconify-icon icon="mdi:magnify"></iconify-icon>
      <span>Cari</span>
      <kbd style="margin-left:auto;padding:1px 5px;background:rgba(255,255,255,0.1);border-radius:3px;font-size:10px;">⌘K</kbd>
    </button>
    <button @click="toggleColorBlind()" class="nav-item" style="border:none;text-transform:none;letter-spacing:0;font-size:11px;padding:6px 0;">
      <iconify-icon icon="mdi:eye-outline"></iconify-icon>
      <span x-text="cbMode ? 'Default colors' : 'Color blind safe'"></span>
    </button>
    <div class="freshness mt-2" style="background:rgba(103,178,232,0.15);">
      <span class="dot"></span><span>Data updated <span x-text="dataUpdated"></span></span>
    </div>
    <div class="heritage-tag mt-3" title="Palette navy + gold = Songket Sumatera (gold thread on indigo base)">
      Palette · Songket
    </div>
    <div style="opacity:0.6;font-size:10px;margin-top:8px;">2019-2025</div>
  </div>
</aside>

<!-- Command palette (Cmd+K) -->
<div class="cmdk-backdrop" x-show="cmdk.open" x-cloak @click.self="cmdk.open = false" @keydown.escape.window="cmdk.open = false">
  <div class="cmdk-modal" @click.stop>
    <div class="cmdk-search">
      <iconify-icon icon="mdi:magnify"></iconify-icon>
      <input type="text" placeholder="Cari halaman, komoditi, atau provinsi..."
        x-model="cmdk.query" @keydown.enter="cmdkExecute(0)" x-ref="cmdkInput">
      <kbd>ESC</kbd>
    </div>
    <div class="cmdk-results">
      <template x-if="cmdkResults.length === 0">
        <div class="cmdk-item" style="color:var(--muted);">Tidak ada hasil.</div>
      </template>
      <template x-for="(r, i) in cmdkResults" :key="r.kind+r.value+i">
        <div class="cmdk-item" @click="cmdkExecute(i)">
          <iconify-icon :icon="r.icon"></iconify-icon>
          <span x-text="r.label"></span>
          <span class="meta" x-text="r.kind"></span>
        </div>
      </template>
    </div>
  </div>
</div>

<div class="with-sidebar">
<!-- Hero band -->
<div class="folio">
  <div class="folio-inner">
    <span class="left">Mandiri Institute · Susenas 2025</span>
    <span class="right" x-text="page.toUpperCase()"></span>
  </div>
</div>
<div class="hero-band hero-band-craft">
  <header class="max-w-[1280px] mx-auto px-8 pt-16 pb-16">
    <div class="eyebrow">Riset Mandiri Institute · Pengeluaran Rumah Tangga</div>
    <h1 class="serif-display text-4xl md:text-5xl mt-5 max-w-4xl" x-text="pageTitle"></h1>
    <p class="mt-5 text-base max-w-3xl leading-relaxed" x-text="pageSubtitle"></p>
  </header>
</div>

<main id="main-content" class="max-w-[1280px] mx-auto px-8 pb-16" role="main">

  <!-- ==================== PAGE: TREND ==================== -->
  <section x-show="page === 'trend'">
    <!-- Hero stats with sparkline -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-10 rule-top pt-8">
      <div class="hero-stat">
        <div class="eyebrow" style="color: var(--muted);">Per kapita 2025</div>
        <div class="stat-num text-5xl mt-3 ink">Rp {rp_2025/1000:.0f}<span class="text-2xl muted ml-1">rb/bln</span></div>
        <div class="sparkline" id="spark-1"></div>
      </div>
      <div class="hero-stat">
        <div class="eyebrow" style="color: var(--muted);">Pertumbuhan 2019-2025</div>
        <div class="stat-num text-5xl mt-3 ink">+{growth:.1f}<span class="text-2xl muted ml-1">%</span></div>
        <div class="text-sm muted mt-1">CAGR {cagr:.1f}%</div>
      </div>
      <div class="hero-stat">
        <div class="eyebrow" style="color: var(--muted);">Share makanan 2025</div>
        <div class="stat-num text-5xl mt-3 ink">{share_makanan_2025:.1f}<span class="text-2xl muted ml-1">%</span></div>
        <div class="text-sm muted mt-1">vs {share_makanan_2019:.1f}% pada 2019</div>
        <div class="sparkline" id="spark-3"></div>
      </div>
      <div class="hero-stat">
        <div class="eyebrow" style="color: var(--muted);">Cakupan</div>
        <div class="stat-num text-5xl mt-3 ink">38<span class="text-2xl muted ml-1">prov</span></div>
        <div class="text-sm muted mt-1">8 kelas wb4 · 20 kelompok</div>
      </div>
    </div>
    <!-- Auto-narrated insight -->
    <div class="narrative mt-8">
      <div class="label"><iconify-icon icon="mdi:lightbulb-outline" style="vertical-align:-2px"></iconify-icon> Insight Otomatis</div>
      <div class="text drop-cap" x-text="autoNarrative('trend')"></div>
    </div>
    <div class="mt-16">
      <span class="badge"><span class="badge-dot"></span>Weighted Mean Nasional</span>
      <div class="eyebrow-roman mt-3">I. Trend</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl">Pengeluaran per kapita tumbuh, share makanan turun.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Total per kapita per bulan dan kontribusi makanan/non-makanan, rata-rata tertimbang nasional, 2019 sampai 2025.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div class="insight-grid mt-2">
        <aside class="insight-panel">
          <div class="callout">
            <div class="label">Key Insight</div>
            <div class="text">Pengeluaran nominal naik {growth:.0f}%, namun bobot makanan turun dari {share_makanan_2019:.0f}% ke {share_makanan_2025:.0f}%, ciri klasik kelas yang lebih sejahtera.</div>
          </div>
          <div class="takeaways">
            <ul>
              <li>CAGR nominal {cagr:.1f}% per tahun (belum disesuaikan inflasi).</li>
              <li>Pertumbuhan paling cepat pada non-makanan, bukan makanan.</li>
              <li>Pola konsisten dengan Hukum Engel (lihat Exhibit 2).</li>
            </ul>
          </div>
        </aside>
        <div>
          <div class="flex items-center gap-2 mb-3">
            <button class="chip-action" :class="compareBaseline ? 'active' : ''" @click="compareBaseline = !compareBaseline; renderTrend()">
              <iconify-icon icon="mdi:compare-horizontal"></iconify-icon>vs 2019
            </button>
            <button class="chip-action" @click="exportPPT('chart-trend', 'Pengeluaran per kapita Indonesia, 2019-2025', 'Trend nasional · Susenas Maret BPS')" style="background:var(--yellow);color:var(--ink);border-color:var(--yellow);font-weight:700;">
              <iconify-icon icon="mdi:presentation"></iconify-icon>Export PPT
            </button>
            <button class="chip-action" @click="downloadCSV('trend')">
              <iconify-icon icon="mdi:download"></iconify-icon>CSV
            </button>
          </div>
          <div id="chart-trend" style="height:480px;"></div>
          <div class="chart-footer">
            <span><span class="label">Sumber</span>Susenas Maret BPS, Blok 41 & 42</span>
            <span><span class="label">Bobot</span>weind × r301 (per kapita tertimbang)</span>
            <span><span class="label">Catatan</span>nilai nominal, belum disesuaikan inflasi</span>
          </div>
          <p class="fig-caption">
            <span class="figno">Figure I.</span>Pengeluaran per kapita Indonesia tumbuh dari Rp 1,17 juta (2019) menjadi Rp 1,58 juta (2025), CAGR 5,1% nominal. Komposisi tetap didominasi makanan, tapi share-nya turun ringan dari 56,5% ke 56,3%.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- ==================== PAGE: ENGEL ==================== -->
  <section x-show="page === 'engel'">
    <!-- Pull quote — Engel's law origin -->
    <div class="pull-quote">
      <blockquote>
        "The proportion of income spent on food decreases as income rises."
      </blockquote>
      <cite>Ernst Engel, 1857</cite>
    </div>
    <div class="rule-top pt-8 flex flex-wrap items-end gap-10">
      <div class="flex-1">
        <div class="eyebrow mb-2" style="color: var(--muted);">Tahun fokus</div>
        <div class="year-slider-wrap">
          <button class="play-btn" @click="togglePlay('renderEngel')">
            <iconify-icon :icon="playing ? 'mdi:pause' : 'mdi:play'"></iconify-icon>
          </button>
          <div class="year-current num" x-text="year"></div>
          <div class="year-slider">
            <input type="range" min="0" :max="years.length - 1" step="1"
              :value="years.indexOf(year)"
              @input="year = years[$event.target.value]; renderEngel()">
            <div class="year-ticks">
              <template x-for="y in years" :key="'ets'+y">
                <span class="year-tick" :class="y === year ? 'active' : ''" @click="year = y; renderEngel()" x-text="y"></span>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>Buyers + Non-buyers · 8 Kelas wb4</span>
      <div class="eyebrow-roman mt-3">II. Engel</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl">Hukum Engel: share makanan turun seiring naiknya kelas.</h2>
      <p class="mt-3 muted text-base max-w-3xl" x-text="'Komposisi pengeluaran makanan vs non-makanan per kelas masyarakat, ' + year + '.'"></p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div class="insight-grid mt-2">
        <aside class="insight-panel">
          <div class="callout">
            <div class="label">Key Insight</div>
            <div class="text">Rumah tangga kelas Poor mengalokasikan mayoritas pengeluaran ke makanan; semakin tinggi kelas, semakin besar share non-makanan (perumahan, pendidikan, jasa).</div>
          </div>
          <div class="takeaways">
            <ul>
              <li>Rasio Engel = ukuran tidak langsung kesejahteraan rumah tangga.</li>
              <li>Indonesia konsisten dengan pola lintas negara: kelas atas alokasikan &lt;40% ke makanan.</li>
              <li>Implikasi: kelompok pengeluaran non-makanan jadi growth driver belanja konsumen.</li>
            </ul>
          </div>
        </aside>
        <div>
          <div class="mb-3">
            <button class="chip-action" @click="exportPPT('chart-engel', 'Hukum Engel: share makanan vs non-makanan per kelas', 'Tahun ' + year + ' · Susenas Maret BPS')" style="background:var(--yellow);color:var(--ink);border-color:var(--yellow);font-weight:700;">
              <iconify-icon icon="mdi:presentation"></iconify-icon>Export PPT
            </button>
            <button class="chip-action" @click="downloadCSV('engel')">
              <iconify-icon icon="mdi:download"></iconify-icon>CSV
            </button>
          </div>
          <div id="chart-engel" style="height:520px;"></div>
          <div class="chart-footer">
            <span><span class="label">Sumber</span>Susenas Maret BPS, Blok 41 & 42</span>
            <span><span class="label">Klasifikasi</span>kelas wb4 Mandiri Institute</span>
            <span><span class="label">Total</span>= 100% per kelas</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ==================== PAGE: KOMPOSISI ==================== -->
  <section x-show="page === 'komposisi'">
    <div class="rule-top pt-8 flex flex-wrap items-end gap-10">
      <div class="flex-1">
        <div class="eyebrow mb-2" style="color: var(--muted);">Tahun fokus</div>
        <div class="year-slider-wrap">
          <button class="play-btn" @click="togglePlay('renderHeatmap')">
            <iconify-icon :icon="playing ? 'mdi:pause' : 'mdi:play'"></iconify-icon>
          </button>
          <div class="year-current num" x-text="year"></div>
          <div class="year-slider">
            <input type="range" min="0" :max="years.length - 1" step="1"
              :value="years.indexOf(year)"
              @input="year = years[$event.target.value]; renderHeatmap()">
            <div class="year-ticks">
              <template x-for="y in years" :key="'hts'+y">
                <span class="year-tick" :class="y === year ? 'active' : ''" @click="year = y; renderHeatmap()" x-text="y"></span>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>Share % · 20 Kelompok × 8 Kelas</span>
      <div class="eyebrow-roman mt-3">III. Komposisi</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl">Distribusi share pengeluaran: 20 kelompok × 8 kelas.</h2>
      <p class="mt-3 muted text-base max-w-3xl" x-text="'Heatmap share pengeluaran (%) per kelompok per kelas, ' + year + '. Warna lebih pekat = share lebih tinggi di kelas itu.'"></p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div class="insight-grid mt-2">
        <aside class="insight-panel">
          <div class="callout">
            <div class="label">Cara Membaca</div>
            <div class="text">Setiap baris adalah satu kelompok pengeluaran; setiap kolom adalah satu kelas. Warna pekat menandakan share tinggi di kelas tersebut.</div>
          </div>
          <div class="takeaways">
            <ul>
              <li>"Padi-padian" dan "Rokok dan Tembakau" pekat di kelas bawah.</li>
              <li>"Perumahan dan Fasilitas RT" dan "Aneka Barang & Jasa" pekat di kelas atas.</li>
              <li>Heatmap ini gambaran portofolio belanja per segmen.</li>
            </ul>
          </div>
        </aside>
        <div>
          <div class="mb-3 flex gap-2 flex-wrap">
            <button class="chip-action" :class="kompMode==='heatmap' ? 'active' : ''" @click="kompMode='heatmap'; renderHeatmap()">Heatmap</button>
            <button class="chip-action" :class="kompMode==='treemap' ? 'active' : ''" @click="kompMode='treemap'; renderHeatmap()">Treemap</button>
            <div style="margin-left:auto;display:flex;gap:8px;">
              <button class="chip-action" @click="downloadCSV('komposisi')"><iconify-icon icon="mdi:download"></iconify-icon>CSV</button>
              <button class="chip-action" @click="exportPPT('chart-heatmap', 'Komposisi share pengeluaran per kelompok dan kelas', 'Tahun ' + year + ' · Susenas Maret BPS')" style="background:var(--yellow);color:var(--ink);border-color:var(--yellow);font-weight:700;">
                <iconify-icon icon="mdi:presentation"></iconify-icon>Export PPT
              </button>
              <button class="chip-action" @click="downloadImage('chart-heatmap', 'png')"><iconify-icon icon="mdi:image-outline"></iconify-icon>PNG raw</button>
              <button class="chip-action" @click="downloadImage('chart-heatmap', 'svg')"><iconify-icon icon="mdi:vector-square"></iconify-icon>SVG</button>
            </div>
          </div>
          <div id="chart-heatmap" style="height:760px;"></div>
          <div class="chart-footer">
            <span><span class="label">Sumber</span>Susenas Maret BPS, Blok 41 & 42</span>
            <span><span class="label">Total</span>tiap kolom = 100%</span>
            <span><span class="label">Bobot</span>weind × r301</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ==================== PAGE: GEOGRAFI ==================== -->
  <section x-show="page === 'geografi'">
    <!-- Unified filter row: tahun, kelas, wilayah, provinsi + actions -->
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
        <div class="eyebrow" style="color: var(--muted);">Wilayah</div>
        <select x-model="wilayah" @change="onWilayahChange()" class="select-flat mt-2" style="min-width:170px;">
          <template x-for="w in wilayahList" :key="'w'+w"><option :value="w" x-text="w"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Provinsi</div>
        <select x-model="provFilter" @change="renderForPage(page)" class="select-flat mt-2" style="min-width:170px;">
          <option value="All">Semua provinsi</option>
          <template x-for="p in provOptions" :key="'po'+p.pcode"><option :value="p.pcode" x-text="p.nama"></option></template>
        </select>
      </div>
      <div style="margin-left:auto;display:flex;gap:8px;align-items:center;">
        <button class="play-btn" @click="togglePlay('renderMap')" title="Play tahun">
          <iconify-icon :icon="playing ? 'mdi:pause' : 'mdi:play'"></iconify-icon>
        </button>
        <button class="chip-action" @click="exportPPT('chart-map', 'Disparitas geografis pengeluaran per kapita', 'Tahun ' + year + ' · Kelas ' + mapKelas + ' · Susenas BPS')" style="background:var(--yellow);color:var(--ink);border-color:var(--yellow);font-weight:700;">
          <iconify-icon icon="mdi:presentation"></iconify-icon>PPT
        </button>
        <button class="chip-action" @click="downloadCSV('geografi')">
          <iconify-icon icon="mdi:download"></iconify-icon>CSV
        </button>
        <button class="chip-action" @click="copyShareLink()">
          <iconify-icon icon="mdi:link-variant"></iconify-icon>Tautan
        </button>
      </div>
    </div>
    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>Per Kapita / Bulan · 34 Provinsi</span>
      <div class="eyebrow-roman mt-3">IV. Geografi</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl">Disparitas geografis pengeluaran per kapita.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Peta 34 provinsi (BPS 2020). Pemekaran Papua pasca-2022 diagregasi ke induk.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div id="chart-map" style="height:780px;"></div>
      <!-- Custom HTML legend (FT/Bloomberg style) -->
      <div class="map-legend">
        <div class="map-legend-label">Pengeluaran per kapita / bulan</div>
        <div class="map-legend-bins" id="legend-geografi"></div>
      </div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas BPS · Shapefile BPS 2020</span>
        <span><span class="label">Catatan</span>Papua Selatan/Tengah/Pegunungan/Barat Daya merge ke induk</span>
      </div>
      <!-- Ranking 38 prov di bawah peta, 2 kolom -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-16 mt-12 rule-top pt-10">
        <div class="rank-card">
          <div class="sub">Top 10 Provinsi</div>
          <h4>Pengeluaran tertinggi per kapita per bulan</h4>
          <div class="rank-list">
            <template x-for="(r, i) in rankTop" :key="'t'+r.pcode">
              <div class="rank-row has-spark" :class="hoveredPcode && pcodeProvMatch(hoveredPcode, r.pcode) ? 'is-hovered' : ''">
                <div class="rank-num" x-text="i+1"></div>
                <div class="rank-name" x-text="r.nama"></div>
                <svg class="rank-spark" :data-pcode="r.pcode" viewBox="0 0 60 22"></svg>
                <div class="rank-cell-right">
                  <div class="rank-bar-wrap" style="width: 100px;">
                    <div class="rank-bar" :style="'width: '+(r.value/rankMax*100)+'%'"></div>
                  </div>
                  <div class="rank-val" x-text="'Rp '+r.value.toLocaleString('id-ID')"></div>
                </div>
              </div>
            </template>
          </div>
        </div>
        <div class="rank-card">
          <div class="sub">Bottom 10 Provinsi</div>
          <h4>Pengeluaran terendah per kapita per bulan</h4>
          <div class="rank-list">
            <template x-for="(r, i) in rankBottom" :key="'b'+r.pcode">
              <div class="rank-row has-spark is-bottom" :class="hoveredPcode && pcodeProvMatch(hoveredPcode, r.pcode) ? 'is-hovered' : ''">
                <div class="rank-num" x-text="i+1"></div>
                <div class="rank-name" x-text="r.nama"></div>
                <svg class="rank-spark" :data-pcode="r.pcode" viewBox="0 0 60 22"></svg>
                <div class="rank-cell-right">
                  <div class="rank-bar-wrap" style="width: 100px;">
                    <div class="rank-bar" :style="'width: '+(r.value/rankMax*100)+'%'"></div>
                  </div>
                  <div class="rank-val" x-text="'Rp '+r.value.toLocaleString('id-ID')"></div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
      <p class="text-xs muted mt-4">Ranking menampilkan 38 provinsi (termasuk pemekaran Papua 2022+: Papua Selatan, Papua Tengah, Papua Pegunungan, Papua Barat Daya). Peta di atas tetap 34 provinsi karena keterbatasan shapefile BPS 2020.</p>
    </div>
  </section>

  <!-- ==================== PAGE: KOMODITI ==================== -->
  <section x-show="page === 'komoditi'">
    <!-- Unified filter row -->
    <div class="rule-top pt-8 flex flex-wrap items-end gap-6">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Tahun</div>
        <select x-model="year" @change="renderKomoditi()" class="select-flat mt-2" style="min-width:90px;">
          <template x-for="y in years" :key="'ky'+y"><option :value="y" x-text="y"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Kelas</div>
        <select x-model="komKelas" @change="renderKomoditi()" class="select-flat mt-2" style="min-width:140px;">
          <template x-for="k in classes" :key="'kk'+k"><option :value="k" x-text="k"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Kelompok</div>
        <select x-model="komKelompok" @change="onKelompokChange()" class="select-flat mt-2" style="min-width:220px;">
          <template x-for="g in kelompokList" :key="'g'+g"><option :value="g" x-text="g"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Komoditi</div>
        <select x-model="komSelected" @change="renderKomoditi()" class="select-flat mt-2" style="min-width:260px;">
          <template x-for="k in komoditiInKelompok" :key="k.key"><option :value="k.key" x-text="k.short"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Wilayah</div>
        <select x-model="wilayah" @change="onWilayahChange()" class="select-flat mt-2" style="min-width:170px;">
          <template x-for="w in wilayahList" :key="'wk'+w"><option :value="w" x-text="w"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Provinsi</div>
        <select x-model="provFilter" @change="renderForPage(page)" class="select-flat mt-2" style="min-width:170px;">
          <option value="All">Semua provinsi</option>
          <template x-for="p in provOptions" :key="'pok'+p.pcode"><option :value="p.pcode" x-text="p.nama"></option></template>
        </select>
      </div>
      <div style="margin-left:auto;display:flex;gap:8px;align-items:center;">
        <button class="play-btn" @click="togglePlay('renderKomoditi')" title="Play tahun">
          <iconify-icon :icon="playing ? 'mdi:pause' : 'mdi:play'"></iconify-icon>
        </button>
        <button class="chip-action" @click="exportPPT('chart-komoditi-map', 'Konsumsi ' + komShort + ' per provinsi', 'Tahun ' + year + ' · Kelas ' + komKelas + ' · Susenas BPS')" style="background:var(--yellow);color:var(--ink);border-color:var(--yellow);font-weight:700;">
          <iconify-icon icon="mdi:presentation"></iconify-icon>PPT
        </button>
        <button class="chip-action" @click="downloadCSV('komoditi')">
          <iconify-icon icon="mdi:download"></iconify-icon>CSV
        </button>
        <button class="chip-action" @click="copyShareLink()">
          <iconify-icon icon="mdi:link-variant"></iconify-icon>Tautan
        </button>
      </div>
    </div>
    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>Drill-down Komoditi · 316 Item</span>
      <div class="eyebrow-roman mt-3">V. Komoditi</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl flex items-center">
        <span class="title-icon"><iconify-icon :icon="komIcon"></iconify-icon></span>
        <span x-text="'Konsumsi ' + komShort + '.'"></span>
      </h2>
      <!-- Definisi komoditi (kalau ada deskripsi dari kurung) -->
      <div class="mt-4 max-w-3xl" x-show="komDesc">
        <div class="callout">
          <div class="label">Definisi</div>
          <div class="text"><span x-text="komShort"></span><span class="muted text-base font-normal" style="font-family:Inter,sans-serif"> mencakup: </span><span x-text="komDesc"></span>.</div>
        </div>
      </div>
      <p class="mt-4 muted text-base max-w-3xl">Pengeluaran per kapita per bulan untuk komoditi terpilih, dipecah per provinsi pada kelas yang dipilih.</p>
      <div class="hair-accent mt-8 pt-2"></div>
      <div class="relative">
        <div id="chart-komoditi-map" style="height:780px;"></div>
        <!-- Custom HTML legend -->
        <div class="map-legend">
          <div class="map-legend-label">Pengeluaran per kapita / bulan</div>
          <div class="map-legend-bins" id="legend-komoditi"></div>
        </div>
        <!-- Floating hover card -->
        <div class="hover-card" :class="hover.visible ? 'is-visible' : ''" :style="'left:'+hover.x+'px; top:'+hover.y+'px'">
          <div class="icon-box"><iconify-icon :icon="komIcon"></iconify-icon></div>
          <div class="body">
            <div class="item-label">Komoditi</div>
            <div class="item-name" x-text="komShort"></div>
            <div class="prov-name" x-text="hover.prov"></div>
            <div class="value" x-text="hover.value"></div>
            <div class="meta" x-text="'per kapita / bulan · Kelas ' + komKelas + ' · Rank #' + hover.rank + ' dari 38'"></div>
          </div>
        </div>
      </div>
      <div class="chart-footer">
        <span><span class="label">Sumber</span>Susenas BPS, item-level (b41k4 / b42k4)</span>
        <span><span class="label">Metric</span>rp_per_kapita per bulan, mean per (tahun, kelas, prov)</span>
        <span><span class="label">Catatan</span>termasuk non-buyer (zero spending)</span>
      </div>
      <!-- Ranking 38 prov, 2 kolom -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-16 mt-12 rule-top pt-10">
        <div class="rank-card">
          <div class="sub">Top 10 Provinsi</div>
          <h4 x-text="'Konsumsi tertinggi: ' + komShort"></h4>
          <div class="rank-list">
            <template x-for="(r, i) in komRankTop" :key="'kt'+r.pcode">
              <div class="rank-row">
                <div class="rank-num" x-text="i+1"></div>
                <div class="rank-name" x-text="r.nama"></div>
                <div class="rank-cell-right">
                  <div class="rank-bar-wrap" style="width: 100px;">
                    <div class="rank-bar" :style="'width: '+(r.value/komRankMax*100)+'%'"></div>
                  </div>
                  <div class="rank-val" x-text="'Rp '+r.value.toLocaleString('id-ID')"></div>
                </div>
              </div>
            </template>
          </div>
        </div>
        <div class="rank-card">
          <div class="sub">Bottom 10 Provinsi</div>
          <h4 x-text="'Konsumsi terendah: ' + komShort"></h4>
          <div class="rank-list">
            <template x-for="(r, i) in komRankBottom" :key="'kb'+r.pcode">
              <div class="rank-row is-bottom">
                <div class="rank-num" x-text="i+1"></div>
                <div class="rank-name" x-text="r.nama"></div>
                <div class="rank-cell-right">
                  <div class="rank-bar-wrap" style="width: 100px;">
                    <div class="rank-bar" :style="'width: '+(r.value/komRankMax*100)+'%'"></div>
                  </div>
                  <div class="rank-val" x-text="'Rp '+r.value.toLocaleString('id-ID')"></div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
      <p class="text-xs muted mt-4">Ranking 38 provinsi (termasuk pemekaran Papua 2022+). Peta di atas: 34 provinsi (4 pemekaran Papua diagregasi ke induk).</p>
    </div>
  </section>

  <!-- COMPARE PROVINSI -->
  <section x-show="page === 'compare'">
    <div class="rule-top pt-8 flex flex-wrap items-end gap-6">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Tahun</div>
        <select x-model="year" @change="renderCompare()" class="select-flat mt-2" style="min-width:90px;">
          <template x-for="y in years" :key="'cy'+y"><option :value="y" x-text="y"></option></template>
        </select>
      </div>
      <div class="flex-1 min-w-[280px]">
        <div class="eyebrow" style="color: var(--muted);">Tambah provinsi (max 4)</div>
        <select @change="addCompareProv($event)" class="select-flat mt-2 w-full">
          <option value="">+ Pilih provinsi...</option>
          <template x-for="p in compareAvailable" :key="'cap'+p.pcode"><option :value="p.pcode" x-text="p.nama"></option></template>
        </select>
      </div>
      <div class="flex flex-wrap gap-2">
        <template x-for="(p, i) in comparePicked" :key="'cpx'+p">
          <span class="pick-chip active">
            <span x-text="comparePcodeName(p)"></span>
            <button @click="removeCompare(i)" style="background:transparent;border:none;color:white;cursor:pointer;padding:0 2px;" aria-label="Remove">×</button>
          </span>
        </template>
      </div>
    </div>
    <div class="mt-12">
      <span class="badge"><span class="badge-dot"></span>Comparison Picker · 2-4 Provinsi</span>
      <div class="eyebrow-roman mt-3">VI. Compare</div>
      <h2 class="serif-display text-3xl mt-2 max-w-3xl">Side-by-side metric, radar profile.</h2>
      <p class="mt-3 muted text-base max-w-3xl">Pilih 2-4 provinsi untuk dibandingkan, atau klik provinsi di peta Geografi.</p>
      <div class="hair-accent mt-8 pt-2"></div>

      <!-- Radar chart -->
      <div class="mt-6">
        <div class="eyebrow" style="color: var(--muted);">Profile multi-dimensi (radar)</div>
        <div id="chart-radar" style="height:480px;"></div>
      </div>

      <!-- Side-by-side metric strip -->
      <div class="grid mt-8" :style="'grid-template-columns: repeat(' + Math.max(comparePicked.length, 1) + ', 1fr); gap: 16px;'">
        <template x-for="(pcode, idx) in comparePicked" :key="'cc'+pcode">
          <div class="compare-card">
            <div class="head">
              <button class="remove" @click="removeCompare(idx)" aria-label="Tutup">×</button>
              <div class="label">Provinsi</div>
              <div class="nama" x-text="comparePcodeName(pcode)"></div>
            </div>
            <template x-for="m in compareMetrics(pcode)" :key="m.lbl + pcode">
              <div class="metric-row">
                <span class="lbl" x-text="m.lbl"></span>
                <div><span class="val" x-text="m.val"></span><span class="sub" x-text="m.sub"></span></div>
              </div>
            </template>
          </div>
        </template>
      </div>

      <div class="chart-footer mt-12">
        <span><span class="label">Sumber</span>Susenas BPS · weighted</span>
        <span><span class="label">Catatan</span>Pemekaran Papua: pilih induk (ID91 / ID94) untuk include sub-prov</span>
      </div>
    </div>
  </section>

  <!-- METODOLOGI -->
  <section x-show="page === 'metodologi'">
    <div class="rule-top pt-8">
      <div class="freshness mb-4"><span class="dot"></span><span>Data updated <span x-text="dataUpdated"></span></span></div>
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-12">
        <div>
          <div class="eyebrow">Sumber Data</div>
          <h3 class="serif-display text-2xl mt-3">Susenas BPS, 2019-2025.</h3>
          <p class="mt-3 muted text-sm leading-relaxed">Survei Sosial Ekonomi Nasional bulan Maret. Modul Konsumsi (Blok 41 & 42) dengan ~315.000-343.000 RT sampel per tahun. Pop tertimbang nasional 2025 = 281,622,304 (verified vs Stata baseline).</p>
        </div>
        <div>
          <div class="eyebrow">Bobot</div>
          <h3 class="serif-display text-2xl mt-3">weind × r301</h3>
          <p class="mt-3 muted text-sm leading-relaxed"><code>weind</code> = bobot individu RT-level. <code>r301</code> = jumlah anggota RT. Dipakai untuk per-kapita weighted (estimator nasional). Confirmed match Stata <code>[iw=weind]</code>.</p>
        </div>
        <div>
          <div class="eyebrow">Klasifikasi Kelas (wb4)</div>
          <h3 class="serif-display text-2xl mt-3">8 kelas masyarakat.</h3>
          <p class="mt-3 muted text-sm leading-relaxed">Klasifikasi internal Mandiri Institute berdasarkan pengeluaran per kapita: Poor, Vulnerable, Lower AMC, Upper AMC, Lower MC, Middle MC, Upper MC, Upper Class.</p>
        </div>
      </div>

      <div class="rule-top pt-12 mt-12 grid grid-cols-1 lg:grid-cols-2 gap-12">
        <div>
          <div class="eyebrow">Formula Per Kapita</div>
          <table class="editorial mt-4">
            <thead><tr><th>Variable</th><th>Formula</th></tr></thead>
            <tbody>
              <tr><td class="font-semibold">Makanan / bulan / RT</td><td><code>sum(b41k10) × 30/7</code></td></tr>
              <tr><td class="font-semibold">Non-makanan / bulan / RT</td><td><code>sum(b42k4) + sum(b42k5)/12</code></td></tr>
              <tr><td class="font-semibold">Per kapita</td><td><code>total RT / r301</code></td></tr>
              <tr><td class="font-semibold">Weight per kapita</td><td><code>weind × r301</code></td></tr>
            </tbody>
          </table>
          <p class="text-xs muted mt-3">Konversi seminggu→sebulan = ×30/7 (BPS standard). Bukan 365.25/(12×7).</p>
        </div>
        <div>
          <div class="eyebrow">Caveat & Catatan</div>
          <ul class="mt-4 space-y-3 text-sm">
            <li class="flex gap-2"><iconify-icon icon="mdi:alert-circle-outline" style="color:#EA7200;font-size:18px;flex-shrink:0;"></iconify-icon><span>Pemekaran Papua 2022+ (4 prov baru: ID92, 95, 96, 97) <strong>diagregasi ke induk</strong> (94, 91) untuk kompatibilitas peta. Ranking tetap 38 prov.</span></li>
            <li class="flex gap-2"><iconify-icon icon="mdi:alert-circle-outline" style="color:#EA7200;font-size:18px;flex-shrink:0;"></iconify-icon><span>Nilai dalam <strong>nominal Rupiah</strong>, belum disesuaikan inflasi. Hati-hati membandingkan antar tahun secara real.</span></li>
            <li class="flex gap-2"><iconify-icon icon="mdi:alert-circle-outline" style="color:#EA7200;font-size:18px;flex-shrink:0;"></iconify-icon><span>Komoditi level: <code>rp_per_kapita_bulan</code> termasuk non-buyer (zero spending). Untuk buyer-only, lihat <code>rp_per_kapita_buyer_bulan</code> di raw data.</span></li>
            <li class="flex gap-2"><iconify-icon icon="mdi:alert-circle-outline" style="color:#EA7200;font-size:18px;flex-shrink:0;"></iconify-icon><span>Kelas marginal di kab kecil (mis. Upper Class di Yahukimo) bisa noisy karena sample kecil.</span></li>
          </ul>
        </div>
      </div>

      <div class="rule-top pt-12 mt-12">
        <div class="eyebrow">Stack Teknis</div>
        <h3 class="serif-display text-2xl mt-3">Static HTML + Plotly.js + Tailwind + Alpine.js.</h3>
        <p class="mt-3 muted text-sm leading-relaxed max-w-3xl">Dashboard offline-ready: cukup buka file HTML di browser, tanpa server. Regenerate via <code>python generator.py</code> di folder yang sama.</p>
      </div>
    </div>
  </section>

  <footer class="rule-top mt-16 pt-8 pb-4 flex items-center justify-between text-xs muted uppercase tracking-widest">
    <div>Mandiri Institute · Dashboard</div>
    <div>Data: Susenas BPS, weighted population · Generated {generated}</div>
    <div>Palette: Mandiri Official</div>
  </footer>
</main>
</div>
</div>

<script>
const PAYLOAD = {json.dumps(payload)};
const GEOJSON = {json.dumps(geojson)};
const CLASSES = {json.dumps(CLASSES)};
const YEARS = {json.dumps([str(y) for y in YEARS])};
const COLOR_MAKANAN = '#67B2E8';
const COLOR_NONMAKANAN = '#003D79';

// Iconify icon per kelompok pengeluaran Susenas (mdi/lucide/material-symbols)
const KELOMPOK_ICON = {{
  'Padi-Padian': 'mdi:rice', 'Umbi-Umbian': 'mdi:potato',
  'Ikan': 'mdi:fish', 'Daging': 'mdi:food-steak',
  'Telur dan Susu': 'mdi:egg-outline', 'Sayur-sayuran': 'mdi:carrot',
  'Kacang-kacangan': 'mdi:peanut-outline', 'Buah-buahan': 'mdi:fruit-cherries',
  'Minyak dan Kelapa': 'mdi:bottle-tonic-plus-outline', 'Bahan Minuman': 'mdi:coffee-outline',
  'Bumbu-bumbuan': 'mdi:shaker-outline', 'Konsumsi Lainnya': 'mdi:silverware-fork-knife',
  'Makanan dan Minuman Jadi': 'mdi:noodles', 'Rokok dan Tembakau': 'mdi:smoking',
  'Perumahan dan Fasilitas RT': 'mdi:home-outline',
  'Aneka Barang dan Jasa': 'mdi:basket-outline',
  'Pakaian, Alas Kaki, Tutup Kepala': 'mdi:tshirt-crew-outline',
  'Barang Tahan Lama': 'mdi:sofa-outline',
  'Pajak, Pungutan dan Asuransi': 'mdi:file-document-outline',
  'Keperluan Pesta dan Upacara': 'mdi:party-popper',
}};
// Override icon untuk komoditi spesifik (substring match)
const KOMODITI_ICON_OVERRIDE = [
  {{ match: /beras/i, icon: 'mdi:rice' }},
  {{ match: /listrik/i, icon: 'mdi:lightning-bolt-outline' }},
  {{ match: /\\bair\\b/i, icon: 'mdi:water-outline' }},
  {{ match: /gas|elpiji|lpg/i, icon: 'mdi:fire' }},
  {{ match: /bensin|pertalite|pertamax|premium|solar/i, icon: 'mdi:gas-station-outline' }},
  {{ match: /kopi/i, icon: 'mdi:coffee-outline' }},
  {{ match: /teh/i, icon: 'mdi:tea-outline' }},
  {{ match: /telur/i, icon: 'mdi:egg-outline' }},
  {{ match: /ayam/i, icon: 'mdi:food-drumstick-outline' }},
  {{ match: /sapi|kerbau/i, icon: 'mdi:cow' }},
  {{ match: /susu/i, icon: 'mdi:cup-outline' }},
  {{ match: /gula/i, icon: 'mdi:candy-outline' }},
  {{ match: /garam/i, icon: 'mdi:shaker-outline' }},
  {{ match: /minyak/i, icon: 'mdi:bottle-tonic-outline' }},
  {{ match: /pisang/i, icon: 'mdi:fruit-cherries' }},
  {{ match: /jeruk/i, icon: 'mdi:fruit-citrus' }},
  {{ match: /apel/i, icon: 'mdi:food-apple-outline' }},
  {{ match: /tomat/i, icon: 'mdi:fruit-watermelon' }},
  {{ match: /cabai|cabe/i, icon: 'mdi:chili-mild-outline' }},
  {{ match: /bawang/i, icon: 'mdi:onion' }},
  {{ match: /pendidikan|sekolah|kuliah/i, icon: 'mdi:school-outline' }},
  {{ match: /transport|tiket|bus|kereta/i, icon: 'mdi:bus' }},
  {{ match: /pulsa|telepon|internet|hp/i, icon: 'mdi:cellphone' }},
  {{ match: /pesta|upacara|kenduri/i, icon: 'mdi:party-popper' }},
  {{ match: /sewa|kontrak/i, icon: 'mdi:home-city-outline' }},
];
function iconFor(item, kelompok) {{
  for (const o of KOMODITI_ICON_OVERRIDE) {{ if (o.match.test(item)) return o.icon; }}
  return KELOMPOK_ICON[kelompok] || 'mdi:chart-box-outline';
}}

// Wilayah → list kode prov 2-digit (untuk filter, bukan zoom)
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
  return {{ type: 'FeatureCollection',
    features: GEOJSON.features.filter(f => allowedSet.has(f.id)) }};
}}
const PEMEKARAN_REVERSE = {{
  'ID91': ['ID95','ID96','ID97'],
  'ID94': ['ID92'],
}};
// Z-score outlier detection: returns array of pcode dengan |z|>threshold
function findOutliers(slice, threshold = 2.0) {{
  const vals = Object.values(slice);
  if (vals.length < 4) return [];
  const mean = vals.reduce((a,b)=>a+b, 0) / vals.length;
  const variance = vals.reduce((a,b)=>a+(b-mean)**2, 0) / vals.length;
  const sd = Math.sqrt(variance) || 1;
  return Object.entries(slice).filter(([p,v]) => Math.abs((v-mean)/sd) > threshold).map(([p])=>p);
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

// Major cities markers (lon, lat) untuk konteks geografis di peta
const CITIES = [
  {{ name: 'Jakarta', lon: 106.85, lat: -6.21 }},
  {{ name: 'Surabaya', lon: 112.75, lat: -7.27 }},
  {{ name: 'Bandung', lon: 107.61, lat: -6.91 }},
  {{ name: 'Medan', lon: 98.67, lat: 3.59 }},
  {{ name: 'Semarang', lon: 110.40, lat: -6.99 }},
  {{ name: 'Makassar', lon: 119.43, lat: -5.13 }},
  {{ name: 'Palembang', lon: 104.76, lat: -2.97 }},
  {{ name: 'Denpasar', lon: 115.22, lat: -8.66 }},
];

// Quintile bins: split values into 5 buckets
function computeBins(values) {{
  const sorted = values.filter(v => v != null && !isNaN(v)).slice().sort((a, b) => a - b);
  if (sorted.length === 0) return {{ edges: [0,0,0,0,0,1], labels: [] }};
  const q = (p) => sorted[Math.min(Math.floor(p * (sorted.length - 1)), sorted.length - 1)];
  return {{
    edges: [sorted[0], q(0.2), q(0.4), q(0.6), q(0.8), sorted[sorted.length - 1]],
  }};
}}
function fmtRp(v) {{
  if (v >= 1000000) return 'Rp ' + (v/1000000).toFixed(1) + ' jt';
  if (v >= 1000) return 'Rp ' + (v/1000).toFixed(0) + ' rb';
  return 'Rp ' + Math.round(v);
}}
const FONT = 'Inter, sans-serif';
const INK = '#051C2C';
const MUTED = '#667085';

const TABS = [
  {{ id: 'trend',     label: 'Trend',     icon: 'mdi:trending-up' }},
  {{ id: 'engel',     label: 'Engel',     icon: 'mdi:chart-bar-stacked' }},
  {{ id: 'komposisi', label: 'Komposisi', icon: 'mdi:view-grid-outline' }},
  {{ id: 'geografi',  label: 'Geografi',  icon: 'mdi:map-outline' }},
  {{ id: 'komoditi',  label: 'Komoditi',  icon: 'mdi:basket-outline' }},
  {{ id: 'compare', label: 'Compare', icon: 'mdi:compare-horizontal' }},
  {{ id: 'metodologi', label: 'Metodologi', icon: 'mdi:book-open-variant' }},
];
const PAGE_META = {{
  trend: {{ title: 'Pengeluaran konsumsi per kapita Indonesia, 2019 sampai 2025.',
           sub: 'Pertumbuhan dan komposisi makanan vs non-makanan, rata-rata tertimbang nasional.' }},
  engel: {{ title: 'Hukum Engel: makin kaya, makin kecil porsi makanan.',
           sub: 'Komposisi pengeluaran makanan vs non-makanan per kelas masyarakat (wb4).' }},
  komposisi: {{ title: 'Distribusi share pengeluaran per kelompok dan kelas.',
                sub: 'Heatmap 20 kelompok pengeluaran (14 makanan + 6 non-makanan) terhadap 8 kelas masyarakat.' }},
  geografi: {{ title: 'Disparitas geografis pengeluaran per kapita.',
               sub: 'Choropleth 34 provinsi (BPS 2020). Pemekaran Papua diagregasi ke induk.' }},
  komoditi: {{ title: 'Konsumsi per komoditi, per kelas, per provinsi.',
               sub: 'Drill-down 316 komoditi Susenas. Pilih tahun, kelas, dan komoditi untuk melihat sebaran provinsi.' }},
  compare:  {{ title: 'Compare provinsi side-by-side.',
              sub: 'Pilih 2 sampai 4 provinsi untuk lihat metric pengeluaran berdampingan + radar profile.' }},
  metodologi: {{ title: 'Metodologi & sumber data.',
                 sub: 'Formula, bobot, definisi variabel, dan caveat dalam dashboard ini.' }},
}};

const TOUR_STEPS = [
  {{ step: '1 / 4', text: 'Halo! Dashboard ini punya 5 exhibit + Metodologi. Navigate dari sidebar kiri.', target: '.sidebar' }},
  {{ step: '2 / 4', text: 'Tab Geografi & Komoditi punya filter Wilayah → Provinsi. Pilih provinsi spesifik untuk fokus.', target: null }},
  {{ step: '3 / 4', text: 'Tekan Ctrl+K kapan saja untuk cari halaman, komoditi, atau provinsi.', target: null }},
  {{ step: '4 / 4', text: 'Tombol "Salin tautan" simpan filter aktif ke URL. Bisa di-share atau bookmark.', target: null }},
];

// Polished Plotly layout defaults — apply lintas chart untuk konsistensi
const CHART_DEFAULTS = {{
  font: {{ family: FONT, size: 12, color: INK }},
  plot_bgcolor: 'white',
  paper_bgcolor: 'white',
  hoverlabel: {{ bgcolor: 'white', bordercolor: '#003D79', font: {{ family: FONT, size: 13, color: INK }}, namelength: -1 }},
  modebar: {{ bgcolor: 'transparent', color: '#98A2B3', activecolor: '#003D79' }},
}};
const AXIS_DEFAULTS = {{
  showline: true, linecolor: INK, linewidth: 1,
  ticks: 'outside', tickcolor: INK, ticklen: 4,
  tickfont: {{ size: 12, color: INK, family: FONT }},
  gridcolor: '#F0F2F5', gridwidth: 1,
  zerolinecolor: '#E5E8EC', zerolinewidth: 1,
}};

function dashboard() {{
  return {{
    tabs: TABS,
    page: 'trend',
    years: YEARS, classes: CLASSES,
    year: '2025',
    mapKelas: 'All',
    rankTop: [], rankBottom: [],
    komKelas: 'Poor',
    komKelompok: 'Padi-Padian',
    komSelected: 'Beras (beras lokal, kualitas unggul, impor)',
    komRankTop: [], komRankBottom: [],
    hover: {{ visible: false, x: 0, y: 0, prov: '', value: '', rank: '-' }},
    playing: false, _playInterval: null,
    dark: false,
    compareBaseline: false,
    wilayah: 'Indonesia',
    wilayahList: Object.keys(REGION_PROVS),
    provFilter: 'All',
    cmdk: {{ open: false, query: '' }},
    sidebarOpen: false,
    cbMode: false,
    hoveredPcode: null,
    pinnedViews: JSON.parse(localStorage.getItem('pinned_views') || '[]'),
    provPanel: {{ open: false, nama: '', rpTotal: '', rank: '', note: '' }},
    comparePicked: ['ID31', 'ID33'],  // default DKI + Jateng
    kompMode: 'heatmap',  // 'heatmap' | 'treemap'
    tour: {{ active: false, step: 0 }},
    dataUpdated: PAYLOAD.data_updated || '-',
    get pageTitle() {{ return PAGE_META[this.page].title; }},
    get pageSubtitle() {{ return PAGE_META[this.page].sub; }},
    get komShort() {{
      const list = window.KOMODITI_LIST || [];
      const k = list.find(x => x.key === this.komSelected);
      return k ? k.short : (this.komSelected || 'komoditi');
    }},
    get komIcon() {{
      const list = window.KOMODITI_LIST || [];
      const k = list.find(x => x.key === this.komSelected);
      return k ? iconFor(k.short, k.kelompok) : 'mdi:chart-box-outline';
    }},
    get komDesc() {{
      const list = window.KOMODITI_LIST || [];
      const k = list.find(x => x.key === this.komSelected);
      return k ? k.desc : null;
    }},
    get rankMax() {{ return this.rankTop.length ? this.rankTop[0].value : 1; }},
    get provOptions() {{
      // Daftar prov dalam wilayah aktif (sumber: prov_meta_38)
      const codes = REGION_PROVS[this.wilayah];
      const all = Object.entries(PAYLOAD.prov_meta_38);
      const filtered = codes ? all.filter(([p, _]) => codes.includes(pcodeProvCode(p))) : all;
      return filtered.sort((a, b) => a[1].localeCompare(b[1]))
                     .map(([p, n]) => ({{ pcode: pcodeProvCode(p), nama: n }}));
    }},
    onWilayahChange() {{ this.provFilter = 'All'; this.renderForPage(this.page); }},
    get komRankMax() {{ return this.komRankTop.length ? this.komRankTop[0].value : 1; }},
    get kelompokList() {{
      const list = window.KOMODITI_LIST || [];
      const seen = new Set();
      const ordered = [];
      list.forEach(k => {{
        if (!seen.has(k.kelompok)) {{ seen.add(k.kelompok); ordered.push(k.kelompok); }}
      }});
      return ordered;
    }},
    get komoditiInKelompok() {{
      const list = window.KOMODITI_LIST || [];
      return list.filter(k => k.kelompok === this.komKelompok);
    }},
    onKelompokChange() {{
      // Pilih komoditi pertama di kelompok baru
      const items = this.komoditiInKelompok;
      if (items.length) {{
        this.komSelected = items[0].key;
      }}
      this.renderKomoditi();
    }},
    init() {{
      this.applyURLState();
      this.$nextTick(() => {{
        this.renderForPage(this.page);
        this.renderSparklines();
      }});
      this._bindKeyboard();
      // Tour onboarding first visit
      if (!localStorage.getItem('tour_done')) {{
        setTimeout(() => {{ this.tour.active = true; }}, 800);
      }}
    }},
    // ----- Auto-narrated insight -----
    autoNarrative(page) {{
      const t = PAYLOAD.trend;
      if (page === 'trend') {{
        const growthPct = ((t.rp_total[t.rp_total.length-1] / t.rp_total[0] - 1) * 100).toFixed(0);
        const cagr = ((Math.pow(t.rp_total[t.rp_total.length-1] / t.rp_total[0], 1/6) - 1) * 100).toFixed(1);
        const fdShare = (t.share_makanan[t.share_makanan.length-1] - t.share_makanan[0]).toFixed(1);
        const dir = parseFloat(fdShare) < 0 ? 'turun' : 'naik';
        return `Pengeluaran per kapita Indonesia naik ${{growthPct}}% (CAGR ${{cagr}}%) dalam 6 tahun terakhir, dari Rp ${{(t.rp_total[0]/1000).toFixed(0)}} ribu menjadi Rp ${{(t.rp_total[t.rp_total.length-1]/1000).toFixed(0)}} ribu per bulan. Share makanan ${{dir}} ${{Math.abs(parseFloat(fdShare)).toFixed(1)}} poin persentase, sinyal pergeseran ke pengeluaran non-makanan (Hukum Engel).`;
      }}
      return '';
    }},
    // ----- Sparkline mini chart -----
    renderSparklines() {{
      if (!document.getElementById('spark-1')) return;
      const t = PAYLOAD.trend;
      const navy = this.cbMode ? '#0072B2' : '#003D79';
      Plotly.newPlot('spark-1', [{{
        x: t.tahun, y: t.rp_total, type: 'scatter', mode: 'lines+markers',
        line: {{ color: navy, width: 2 }}, marker: {{ size: 4, color: navy }},
        hovertemplate: '%{{x}}: Rp %{{y:,.0f}}<extra></extra>',
        fill: 'tozeroy', fillcolor: this.cbMode ? 'rgba(0,114,178,0.1)' : 'rgba(0,61,121,0.08)',
      }}], {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        xaxis: {{ visible: false }}, yaxis: {{ visible: false }},
        plot_bgcolor: 'transparent', paper_bgcolor: 'transparent',
        showlegend: false,
      }}, {{ displayModeBar: false, responsive: true, staticPlot: false }});
      Plotly.newPlot('spark-3', [{{
        x: t.tahun, y: t.share_makanan, type: 'scatter', mode: 'lines+markers',
        line: {{ color: '#EA7200', width: 2 }}, marker: {{ size: 4, color: '#EA7200' }},
        hovertemplate: '%{{x}}: %{{y:.1f}}%<extra></extra>',
      }}], {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        xaxis: {{ visible: false }}, yaxis: {{ visible: false }},
        plot_bgcolor: 'transparent', paper_bgcolor: 'transparent',
        showlegend: false,
      }}, {{ displayModeBar: false, responsive: true }});
    }},
    // ----- Color blind mode -----
    toggleColorBlind() {{
      this.cbMode = !this.cbMode;
      document.body.classList.toggle('cb-mode', this.cbMode);
      this.$nextTick(() => {{ this.renderForPage(this.page); this.renderSparklines(); }});
    }},
    // ----- Copy chart as image -----
    copyChartAsImage(divId) {{
      Plotly.toImage(divId, {{ format: 'png', width: 1280, height: 720, scale: 2 }})
        .then(url => {{
          const a = document.createElement('a');
          a.href = url; a.download = divId + '.png';
          document.body.appendChild(a); a.click(); document.body.removeChild(a);
        }});
    }},
    // ----- Saved views (pin filter) -----
    isPinned() {{
      const key = this._currentViewKey();
      return this.pinnedViews.some(v => v.key === key);
    }},
    togglePin() {{
      const key = this._currentViewKey();
      const label = this._currentViewLabel();
      const idx = this.pinnedViews.findIndex(v => v.key === key);
      if (idx >= 0) this.pinnedViews.splice(idx, 1);
      else this.pinnedViews.push({{ key, label, hash: window.location.hash }});
      localStorage.setItem('pinned_views', JSON.stringify(this.pinnedViews));
    }},
    _currentViewKey() {{ return [this.page, this.year, this.mapKelas, this.komSelected].join('|'); }},
    _currentViewLabel() {{
      if (this.page === 'komoditi') return `${{this.komShort}} · ${{this.komKelas}} · ${{this.year}}`;
      if (this.page === 'geografi') return `Peta · ${{this.mapKelas}} · ${{this.year}}`;
      return `${{this.page}} · ${{this.year}}`;
    }},
    loadPinned(p) {{ window.location.hash = p.hash; window.location.reload(); }},
    _drawSparklines() {{
      // SVG inline sparkline per rank-row, baca data dari PAYLOAD.sparkline
      document.querySelectorAll('.rank-spark').forEach(svg => {{
        const pcode = svg.getAttribute('data-pcode');
        const series = (PAYLOAD.sparkline || {{}})[pcode];
        if (!series || !series.length) {{ svg.innerHTML = ''; return; }}
        const min = Math.min(...series), max = Math.max(...series);
        const span = max - min || 1;
        const w = 60, h = 22, pad = 2;
        const pts = series.map((v, i) => {{
          const x = pad + (i / (series.length - 1)) * (w - 2*pad);
          const y = h - pad - ((v - min) / span) * (h - 2*pad);
          return `${{x.toFixed(1)}},${{y.toFixed(1)}}`;
        }}).join(' ');
        const lastX = pad + (w - 2*pad);
        const lastY = h - pad - ((series[series.length-1] - min) / span) * (h - 2*pad);
        svg.innerHTML = `<polyline points="${{pts}}" fill="none" stroke="#003D79" stroke-width="1.2"/>` +
                        `<circle cx="${{lastX.toFixed(1)}}" cy="${{lastY.toFixed(1)}}" r="1.5" fill="#003D79"/>`;
      }});
    }},
    pcodeProvMatch(hovered, target) {{
      // hovered is map pcode (34 prov merged), target is rank pcode (38 prov)
      // Match if same prov code OR if target is pemekaran child of hovered
      if (hovered === target) return true;
      const PEM = {{ 'ID92': 'ID94', 'ID95': 'ID91', 'ID96': 'ID91', 'ID97': 'ID91' }};
      return PEM[target] === hovered;
    }},
    // ----- URL state (share link) -----
    applyURLState() {{
      const p = new URLSearchParams(window.location.hash.replace(/^#/, ''));
      if (p.get('page')) this.page = p.get('page');
      if (p.get('year')) this.year = p.get('year');
      if (p.get('kelas')) this.mapKelas = p.get('kelas');
      if (p.get('komKelas')) this.komKelas = p.get('komKelas');
      if (p.get('komKelompok')) this.komKelompok = p.get('komKelompok');
      if (p.get('komSelected')) this.komSelected = p.get('komSelected');
      if (p.get('dark') === '1') this.toggleDark(true);
    }},
    syncURL() {{
      const p = new URLSearchParams();
      p.set('page', this.page);
      p.set('year', this.year);
      if (this.page === 'geografi') p.set('kelas', this.mapKelas);
      if (this.page === 'komoditi') {{
        p.set('komKelas', this.komKelas);
        p.set('komKelompok', this.komKelompok);
        p.set('komSelected', this.komSelected);
      }}
      if (this.dark) p.set('dark', '1');
      history.replaceState(null, '', '#' + p.toString());
    }},
    copyShareLink() {{
      this.syncURL();
      navigator.clipboard.writeText(window.location.href).then(() => {{
        alert('Tautan disalin ke clipboard.');
      }}).catch(() => alert('Gagal menyalin tautan.'));
    }},
    // ----- Dark mode -----
    toggleDark(force) {{
      this.dark = (typeof force === 'boolean') ? force : !this.dark;
      document.body.classList.toggle('dark', this.dark);
      this.syncURL();
      // Re-render chart untuk update warna axis/font
      this.$nextTick(() => this.renderForPage(this.page));
    }},
    // ----- Keyboard nav -----
    _bindKeyboard() {{
      const self = this;
      window.addEventListener('keydown', (e) => {{
        // Cmd+K / Ctrl+K open palette
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {{
          e.preventDefault();
          self.cmdk.open = true;
          self.$nextTick(() => self.$refs.cmdkInput && self.$refs.cmdkInput.focus());
          return;
        }}
        // Esc close
        if (e.key === 'Escape') {{
          self.cmdk.open = false;
          self.hover.visible = false;
          return;
        }}
        // Arrow keys: cycle year (kalau focus tidak di input)
        if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight') &&
            !['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName) &&
            !self.cmdk.open) {{
          const idx = self.years.indexOf(self.year);
          const next = e.key === 'ArrowLeft'
            ? (idx - 1 + self.years.length) % self.years.length
            : (idx + 1) % self.years.length;
          self.year = self.years[next];
          self.renderForPage(self.page);
        }}
      }});
    }},
    // ----- Cmd+K palette results -----
    get cmdkResults() {{
      const q = (this.cmdk.query || '').toLowerCase().trim();
      const results = [];
      // Pages
      this.tabs.forEach(t => {{
        if (!q || t.label.toLowerCase().includes(q)) {{
          results.push({{ kind: 'Halaman', icon: t.icon, label: t.label, value: t.id, action: 'page' }});
        }}
      }});
      // Komoditi (top 8 match)
      const list = window.KOMODITI_LIST || [];
      const matches = q ? list.filter(k => k.short.toLowerCase().includes(q) || k.kelompok.toLowerCase().includes(q)).slice(0, 8) : [];
      matches.forEach(k => {{
        results.push({{ kind: 'Komoditi', icon: iconFor(k.short, k.kelompok), label: k.short, value: k.key, kelompok: k.kelompok, action: 'komoditi' }});
      }});
      // Provinsi
      const provs = Object.keys(PAYLOAD.prov_meta_38 || {{}});
      const provMatches = q ? provs.filter(p => (PAYLOAD.prov_meta_38[p] || '').toLowerCase().includes(q)).slice(0, 6) : [];
      provMatches.forEach(p => {{
        results.push({{ kind: 'Provinsi', icon: 'mdi:map-marker-outline', label: PAYLOAD.prov_meta_38[p], value: p, action: 'provinsi' }});
      }});
      return results.slice(0, 16);
    }},
    cmdkExecute(idx) {{
      const r = this.cmdkResults[idx];
      if (!r) return;
      this.cmdk.open = false;
      this.cmdk.query = '';
      if (r.action === 'page') {{ this.setPage(r.value); }}
      else if (r.action === 'komoditi') {{
        this.komKelompok = r.kelompok;
        this.komSelected = r.value;
        this.setPage('komoditi');
      }}
      else if (r.action === 'provinsi') {{
        this.setPage('geografi');
      }}
    }},
    // ----- Custom map legend (FT/Bloomberg style) -----
    _renderLegend(elId, bins, palette) {{
      const el = document.getElementById(elId);
      if (!el) return;
      const e = bins.edges;
      const html = palette.map((c, i) => {{
        const lo = e[i], hi = e[i+1];
        return `<div class="map-legend-bin"><div class="swatch" style="background:${{c}}"></div><div class="range">${{fmtRp(lo)}}${{i===4?'+':''}}</div></div>`;
      }}).join('');
      el.innerHTML = html;
    }},
    // ----- Download CSV -----
    downloadCSV(which) {{
      let rows = [], filename = '';
      if (which === 'trend') {{
        const t = PAYLOAD.trend;
        rows = [['tahun','rp_total','rp_makanan','rp_nonmakanan','share_makanan_pct']];
        for (let i = 0; i < t.tahun.length; i++) {{
          rows.push([t.tahun[i], t.rp_total[i], t.rp_makanan[i], t.rp_nonmakanan[i], t.share_makanan[i]]);
        }}
        filename = `konsumsi-susenas_trend_2019-2025.csv`;
      }} else if (which === 'engel') {{
        const k = PAYLOAD.nat_kelas[this.year];
        rows = [['kelas','rp_total','share_makanan_pct','share_nonmakanan_pct']];
        CLASSES.forEach(c => {{ if (k[c]) rows.push([c, k[c].rp_total, k[c].share_makanan, k[c].share_nonmakanan]); }});
        filename = `konsumsi-susenas_engel_${{this.year}}.csv`;
      }} else if (which === 'komposisi') {{
        const h = PAYLOAD.heatmap[this.year];
        rows = [['kelompok', ...CLASSES]];
        PAYLOAD.kelompok_order.forEach(kp => {{
          rows.push([kp, ...CLASSES.map(c => (h[c] && h[c][kp] !== undefined) ? h[c][kp] : '')]);
        }});
        filename = `konsumsi-susenas_komposisi_${{this.year}}.csv`;
      }} else if (which === 'geografi') {{
        const slice = (PAYLOAD.rank38[this.year] || {{}})[this.mapKelas] || {{}};
        rows = [['pcode','provinsi','rp_per_kapita_bulan']];
        Object.keys(slice).forEach(p => rows.push([p, PAYLOAD.prov_meta_38[p] || p, slice[p]]));
        filename = `konsumsi-susenas_geografi_${{this.year}}_${{this.mapKelas}}.csv`;
      }} else if (which === 'komoditi') {{
        const slice = (((window.KOMODITI_DATA[this.year] || {{}})[this.komKelas] || {{}})[this.komSelected]) || {{}};
        rows = [['pcode','provinsi','rp_per_kapita_bulan']];
        Object.keys(slice).forEach(p => rows.push([p, PAYLOAD.prov_meta_38[p] || p, slice[p]]));
        filename = `konsumsi-susenas_komoditi_${{this.komShort}}_${{this.komKelas}}_${{this.year}}.csv`.replace(/[^\\w\\d.\\-_]+/g, '-');
      }}
      const csv = rows.map(r => r.map(v => /[",\\n]/.test(String(v)) ? '"' + String(v).replace(/"/g,'""') + '"' : v).join(',')).join('\\n');
      const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }},
    _rendered: {{ trend: true, engel: false, komposisi: false, geografi: false, komoditi: false }},
    renderForPage(id) {{
      const self = this;
      requestAnimationFrame(() => requestAnimationFrame(() => {{
        if (id === 'trend') {{ self.renderTrend(); }}
        else if (id === 'engel') {{ self.renderEngel(); }}
        else if (id === 'komposisi') {{ self.renderHeatmap(); }}
        else if (id === 'geografi') {{ self.renderMap(); }}
        else if (id === 'komoditi') {{ self.renderKomoditi(); }}
        else if (id === 'compare') {{ self.renderCompare(); }}
        self._rendered[id] = true;
      }}));
    }},
    // ----- Compare Provinsi -----
    get compareAvailable() {{
      // Prov pool from prov_meta_38, exclude already-picked
      return Object.entries(PAYLOAD.prov_meta_38)
        .filter(([p]) => !this.comparePicked.includes(p))
        .sort((a,b) => a[1].localeCompare(b[1]))
        .map(([p, n]) => ({{ pcode: p, nama: n }}));
    }},
    comparePcodeName(p) {{ return PAYLOAD.prov_meta_38[p] || p; }},
    addCompareProv(ev) {{
      const p = ev.target.value;
      if (p && !this.comparePicked.includes(p) && this.comparePicked.length < 4) {{
        this.comparePicked.push(p);
        this.renderCompare();
      }}
      ev.target.value = '';
    }},
    removeCompare(idx) {{
      this.comparePicked.splice(idx, 1);
      this.renderCompare();
    }},
    compareMetrics(pcode) {{
      // Per pcode di year aktif: rp_total + share_makanan + rank
      const pc = pcodeProvCode(pcode);
      const slice = (PAYLOAD.rank38[this.year] || {{}})['All'] || {{}};
      const v = slice[pcode];
      const rankSorted = Object.entries(slice).map(([p,vv]) => ({{p,v:vv}})).sort((a,b)=>b.v-a.v);
      const rank = rankSorted.findIndex(r => r.p === pcode);
      // Get share makanan from PAYLOAD.nat_kelas (national level — use as proxy for prov-level since we don't have prov × kelas × share)
      const allKelas = PAYLOAD.nat_kelas[this.year] || {{}};
      const avgShareMakanan = Object.values(allKelas).reduce((s,k)=>s+(k.share_makanan||0), 0) / Math.max(Object.keys(allKelas).length, 1);
      return [
        {{ lbl: 'Per kapita / bulan',     val: 'Rp ' + (v ? v.toLocaleString('id-ID') : '-'), sub: '' }},
        {{ lbl: 'Rank nasional',           val: '#' + (rank >= 0 ? rank+1 : '-'), sub: '/ 38' }},
        {{ lbl: 'Share makanan (estimate)', val: avgShareMakanan.toFixed(1), sub: '%' }},
      ];
    }},
    renderCompare() {{
      // Radar chart: multi-dim profile per prov
      const dims = ['Rp/kapita', 'Rank inv', 'Share makanan inv', 'Trend growth', 'Outlier flag'];
      const traces = this.comparePicked.map((pcode, i) => {{
        const slice = (PAYLOAD.rank38[this.year] || {{}})['All'] || {{}};
        const v = slice[pcode] || 0;
        const allVals = Object.values(slice);
        const max = Math.max(...allVals, 1);
        const min = Math.min(...allVals, 0);
        const norm = (v - min) / (max - min) * 100;
        // Rank inv: kalau rank #1 → 100, rank #38 → 0
        const rankSorted = Object.entries(slice).map(([p,vv]) => ({{p,v:vv}})).sort((a,b)=>b.v-a.v);
        const rank = rankSorted.findIndex(r => r.p === pcode);
        const rankInv = rank >= 0 ? (1 - rank/37) * 100 : 0;
        // Trend growth: 2025 vs 2019 ratio
        const v19 = (PAYLOAD.rank38['2019'] || {{}})['All']?.[pcode] || 1;
        const v25 = (PAYLOAD.rank38['2025'] || {{}})['All']?.[pcode] || 1;
        const growth = Math.min((v25/v19 - 1) * 100, 100);
        // Share makanan estimate inv (lower share = more developed)
        const allKelas = PAYLOAD.nat_kelas[this.year] || {{}};
        const avgShareMakanan = Object.values(allKelas).reduce((s,k)=>s+(k.share_makanan||0), 0) / Math.max(Object.keys(allKelas).length, 1);
        const shareMakananInv = 100 - avgShareMakanan;
        // Outlier flag (binary 0/100)
        const outliers = findOutliers(slice, 1.5);
        const isOutlier = outliers.includes(pcode) ? 100 : 30;
        const palette = ['#003D79','#EA7200','#67B2E8','#C8102E'];
        return {{
          type: 'scatterpolar',
          r: [norm, rankInv, shareMakananInv, growth, isOutlier, norm],
          theta: [...dims, dims[0]],
          fill: 'toself',
          name: PAYLOAD.prov_meta_38[pcode] || pcode,
          line: {{ color: palette[i % 4], width: 2 }},
          fillcolor: palette[i % 4] + '30',
        }};
      }});
      Plotly.react('chart-radar', traces, {{
        polar: {{ radialaxis: {{ visible: true, range: [0, 100], tickfont: {{ size: 10, color: MUTED }} }},
                  angularaxis: {{ tickfont: {{ size: 11, color: INK }} }} }},
        font: {{ family: FONT, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        margin: {{ l: 60, r: 60, t: 30, b: 30 }},
        legend: {{ orientation: 'h', y: -0.1, x: 0.5, xanchor: 'center' }},
      }}, {{ displaylogo: false, responsive: true }});
    }},
    togglePlay(renderMethod) {{
      if (this.playing) {{
        clearInterval(this._playInterval);
        this.playing = false;
        return;
      }}
      this.playing = true;
      const self = this;
      this._playInterval = setInterval(() => {{
        const idx = self.years.indexOf(self.year);
        const next = (idx + 1) % self.years.length;
        self.year = self.years[next];
        self[renderMethod]();
      }}, 1200);
    }},
    setPage(id) {{
      if (this.playing) {{ clearInterval(this._playInterval); this.playing = false; }}
      this.page = id;
      this.renderForPage(id);
      this.syncURL();
    }},
    renderAll() {{ this.renderEngel(); this.renderHeatmap(); this.renderMap(); this.renderKomoditi(); }},

    renderTrend() {{
      const t = PAYLOAD.trend;
      const traces = [
        {{ x: t.tahun, y: t.rp_makanan, name: 'Makanan', type: 'bar', marker: {{ color: COLOR_MAKANAN }}, hovertemplate: '%{{x}}<br>Makanan: Rp %{{y:,.0f}}<extra></extra>' }},
        {{ x: t.tahun, y: t.rp_nonmakanan, name: 'Non-makanan', type: 'bar', marker: {{ color: COLOR_NONMAKANAN }}, hovertemplate: '%{{x}}<br>Non-makanan: Rp %{{y:,.0f}}<extra></extra>' }},
        {{ x: t.tahun, y: t.rp_total, name: 'Total', type: 'scatter', mode: 'lines+markers',
           line: {{ color: INK, width: 2.5 }}, marker: {{ size: 8, color: INK }},
           hovertemplate: '%{{x}}<br>Total: Rp %{{y:,.0f}}<extra></extra>' }},
      ];
      // Compare baseline: horizontal line di rp_total 2019 + label growth %
      const shapes = [];
      if (this.compareBaseline) {{
        const base = t.rp_total[0];
        shapes.push({{
          type: 'line', xref: 'paper', yref: 'y',
          x0: 0, x1: 1, y0: base, y1: base,
          line: {{ color: '#C8102E', width: 1.5, dash: 'dash' }},
        }});
        traces.push({{
          x: t.tahun, y: t.tahun.map(_ => base),
          mode: 'text', type: 'scatter',
          text: t.rp_total.map(v => `+${{((v/base-1)*100).toFixed(0)}}%`),
          textposition: 'top center', textfont: {{ size: 11, color: '#C8102E' }},
          showlegend: false, hoverinfo: 'skip',
        }});
      }}
      // Inline annotations (NYT/FT style: panah ke titik penting)
      const idx2020 = t.tahun.indexOf(2020);
      const idx2023 = t.tahun.indexOf(2023);
      const annotations = [];
      if (idx2020 >= 0) {{
        annotations.push({{
          x: 2020, y: t.rp_total[idx2020], text: '<b>COVID-19</b><br>pertumbuhan melambat',
          xref: 'x', yref: 'y', showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 1,
          arrowcolor: INK, ax: -50, ay: -60,
          font: {{ size: 11, color: INK, family: FONT }},
          bgcolor: 'white', bordercolor: INK, borderwidth: 1, borderpad: 6,
          align: 'left',
        }});
      }}
      if (idx2023 >= 0) {{
        annotations.push({{
          x: 2023, y: t.rp_total[idx2023], text: '<b>Rebound</b><br>pengeluaran naik tajam',
          xref: 'x', yref: 'y', showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 1,
          arrowcolor: '#003D79', ax: 40, ay: -70,
          font: {{ size: 11, color: '#003D79', family: FONT }},
          bgcolor: '#EAF1F8', bordercolor: '#003D79', borderwidth: 1, borderpad: 6,
          align: 'left',
        }});
      }}
      Plotly.react('chart-trend', traces, {{
        barmode: 'stack', bargap: 0.45,
        margin: {{ l: 80, r: 30, t: 30, b: 80 }},
        font: {{ family: FONT, size: 13, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ tickfont: {{ size: 14, color: INK }}, showline: true, linecolor: INK, ticks: 'outside', tickcolor: INK, ticklen: 4 }},
        yaxis: {{ title: {{ text: 'Rp per kapita per bulan', font: {{ size: 12, color: MUTED }} }},
                 tickfont: {{ size: 12, color: MUTED }}, gridcolor: '#EAECF0',
                 tickformat: ',.0f' }},
        legend: {{ orientation: 'h', y: -0.18, x: 0, xanchor: 'left', font: {{ size: 12 }} }},
        annotations, shapes,
      }}, {{ displaylogo: false, responsive: true }});
    }},

    renderEngel() {{
      const k = PAYLOAD.nat_kelas[this.year];
      const x = CLASSES;
      const m = x.map(c => k[c] ? k[c].share_makanan : null);
      const n = x.map(c => k[c] ? k[c].share_nonmakanan : null);
      const traces = [
        {{ x, y: m, name: 'Makanan', type: 'bar', marker: {{ color: COLOR_MAKANAN }},
           hovertemplate: '%{{x}}<br>Makanan: %{{y:.1f}}%<extra></extra>' }},
        {{ x, y: n, name: 'Non-makanan', type: 'bar', marker: {{ color: COLOR_NONMAKANAN }},
           hovertemplate: '%{{x}}<br>Non-makanan: %{{y:.1f}}%<extra></extra>' }},
      ];
      Plotly.react('chart-engel', traces, {{
        barmode: 'stack', bargap: 0.45,
        margin: {{ l: 60, r: 30, t: 20, b: 80 }},
        font: {{ family: FONT, size: 13, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ tickfont: {{ size: 14, color: INK }}, showline: true, linecolor: INK, ticks: 'outside', tickcolor: INK, ticklen: 4, automargin: true }},
        yaxis: {{ title: {{ text: 'Share (%)', font: {{ size: 12, color: MUTED }} }},
                 tickfont: {{ size: 12, color: MUTED }}, gridcolor: '#EAECF0' }},
        legend: {{ orientation: 'h', y: -0.20, x: 0, xanchor: 'left', font: {{ size: 12 }} }},
      }}, {{ displaylogo: false, responsive: true }});
    }},

    renderHeatmap() {{
      const h = PAYLOAD.heatmap[this.year];
      const klp = PAYLOAD.kelompok_order;
      if (this.kompMode === 'treemap') {{
        // Treemap: agregat 20 kelompok across 8 kelas (avg share)
        const avg = klp.map(k => {{
          const vals = CLASSES.map(c => (h[c] && h[c][k] !== undefined) ? h[c][k] : 0);
          return vals.reduce((s,v)=>s+v, 0) / vals.length;
        }});
        const palette = ['#003D79','#2A6FB3','#67B2E8','#A9C4DF','#FFB700','#EA7200','#67B2E8','#A9C4DF','#003D79','#2A6FB3','#67B2E8','#A9C4DF','#FFB700','#EA7200','#003D79','#2A6FB3','#67B2E8','#A9C4DF','#FFB700','#EA7200'];
        Plotly.react('chart-heatmap', [{{
          type: 'treemap',
          labels: klp,
          parents: klp.map(_ => ''),
          values: avg,
          textinfo: 'label+value+percent root',
          texttemplate: '<b>%{{label}}</b><br>%{{value:.1f}}%',
          marker: {{ colors: palette.slice(0, klp.length), line: {{ color: 'white', width: 2 }} }},
          hovertemplate: '<b>%{{label}}</b><br>Share: %{{value:.1f}}%<extra></extra>',
          tiling: {{ packing: 'squarify' }},
        }}], {{
          margin: {{ l: 0, r: 0, t: 20, b: 0 }},
          font: {{ family: FONT, size: 12, color: INK }},
          plot_bgcolor: 'white', paper_bgcolor: 'white',
        }}, {{ displaylogo: false, responsive: true }});
        return;
      }}
      const z = klp.map(k => CLASSES.map(c => (h[c] && h[c][k] !== undefined) ? h[c][k] : null));
      Plotly.react('chart-heatmap', [{{
        type: 'heatmap', x: CLASSES, y: klp, z,
        colorscale: [[0, '#F7F5F0'], [0.4, '#67B2E8'], [0.8, '#003D79'], [1, '#051C2C']],
        hovertemplate: '%{{y}} · %{{x}}<br>Share: %{{z:.1f}}%<extra></extra>',
        colorbar: {{ title: {{ text: 'Share %', font: {{ size: 11, color: MUTED }} }},
                    thickness: 10, len: 0.7, tickfont: {{ size: 11, color: MUTED }} }},
        xgap: 1, ygap: 1,
      }}], {{
        margin: {{ l: 200, r: 60, t: 20, b: 80 }},
        font: {{ family: FONT, size: 12, color: INK }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{ side: 'top', tickfont: {{ size: 12, color: INK }} }},
        yaxis: {{ tickfont: {{ size: 11, color: INK }}, autorange: 'reversed' }},
      }}, {{ displaylogo: false, responsive: true }});
    }},
    // ----- PPT-ready PNG export with branded composition -----
    exportPPT(divId, title, subtitle) {{
      // Compose 1920×1080 canvas: title + chart + source + logo
      const W = 1920, H = 1080;
      const canvas = document.createElement('canvas');
      canvas.width = W; canvas.height = H;
      const ctx = canvas.getContext('2d');
      // White background
      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(0, 0, W, H);
      // Header band (subtle navy stripe top)
      ctx.fillStyle = '#003D79';
      ctx.fillRect(0, 0, W, 6);
      // Title (Source Serif)
      ctx.fillStyle = '#051C2C';
      ctx.font = "600 36px 'Source Serif 4', Georgia, serif";
      ctx.fillText(title || 'Mandiri Institute Dashboard', 60, 90);
      // Subtitle
      ctx.font = "400 18px 'Inter', sans-serif";
      ctx.fillStyle = '#667085';
      ctx.fillText(subtitle || '', 60, 125);
      // Get chart as image
      Plotly.toImage(divId, {{ format: 'png', width: 1700, height: 800, scale: 2 }})
        .then(url => {{
          const img = new Image();
          img.onload = () => {{
            // Draw chart centered (1700×800 fitted in 1800×820 box)
            ctx.drawImage(img, 110, 160, 1700, 800);
            // Source line bottom-left
            ctx.fillStyle = '#667085';
            ctx.font = "400 14px 'Inter', sans-serif";
            const src = `Sumber: Susenas Maret BPS · Mandiri Institute · ${{new Date().toISOString().slice(0,10)}}`;
            ctx.fillText(src, 60, H - 30);
            // Load + draw logo bottom-right
            const logo = new Image();
            logo.onload = () => {{
              const lh = 60, lw = logo.width * (lh / logo.height);
              ctx.drawImage(logo, W - lw - 60, H - lh - 20, lw, lh);
              this._downloadCanvas(canvas, `${{this.page}}-${{this.year}}-Mandiri-Institute.png`);
            }};
            logo.onerror = () => this._downloadCanvas(canvas, `${{this.page}}-${{this.year}}.png`);
            logo.src = '../_assets/logo/mandiri-institute-color.jpg';
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
    // Legacy plain image (no branding)
    downloadImage(divId, format) {{
      Plotly.toImage(divId, {{ format, width: 1600, height: 900, scale: 2 }})
        .then(url => {{
          const a = document.createElement('a');
          a.href = url; a.download = `${{this.page}}-${{this.year}}.${{format}}`;
          document.body.appendChild(a); a.click(); document.body.removeChild(a);
        }});
    }},
    copyCitation(which) {{
      const yr = this.year;
      const today = new Date().toISOString().slice(0, 10);
      const cite = `Mandiri Institute. (${{yr}}). Konsumsi per Kapita per Bulan: ${{which}}, ${{yr}} [Dashboard]. Berdasarkan data Susenas Maret BPS. Diakses ${{today}} dari Dashboard Suite Mandiri Institute.`;
      navigator.clipboard.writeText(cite).then(() => alert('Citation APA disalin ke clipboard:\\n\\n' + cite));
    }},

    renderMap() {{
      const mapSliceFull = PAYLOAD.map[this.year][this.mapKelas] || {{}};
      // Filter wilayah / prov
      const mapSlice = {{}};
      Object.keys(mapSliceFull).forEach(p => {{
        if (inRegion(p, this.wilayah, this.provFilter)) mapSlice[p] = mapSliceFull[p];
      }});
      const mapLocs = Object.keys(mapSlice);
      const mapVals = mapLocs.map(p => mapSlice[p]);
      const allowedSet = new Set(mapLocs);
      const filteredGJ = filteredGeojson(allowedSet);
      // BASE layer: SEMUA prov di scope (termasuk no-data) → grey fill
      const baseFeatures = GEOJSON.features.filter(f => inRegion(f.id, this.wilayah, this.provFilter));
      const baseGJ = {{ type: 'FeatureCollection', features: baseFeatures }};
      const noDataLocs = baseFeatures.map(f => f.id).filter(p => !(p in mapSlice));

      // Quintile bins
      const bins = computeBins(mapVals);
      const palette = ['#E8EFF6', '#A9C4DF', '#67B2E8', '#2A6FB3', '#003D79'];
      const colorscale = [
        [0.0,   palette[0]], [0.2-1e-9, palette[0]],
        [0.2,   palette[1]], [0.4-1e-9, palette[1]],
        [0.4,   palette[2]], [0.6-1e-9, palette[2]],
        [0.6,   palette[3]], [0.8-1e-9, palette[3]],
        [0.8,   palette[4]], [1.0,      palette[4]],
      ];

      // Build rank lookup
      const rankSlice38 = (PAYLOAD.rank38[this.year] || {{}})[this.mapKelas] || {{}};
      const ranked38 = Object.keys(rankSlice38)
        .map(p => ({{ pcode: p, value: rankSlice38[p] }}))
        .sort((a,b) => b.value - a.value);
      const rankByPcode38 = {{}};
      ranked38.forEach((r, i) => {{ rankByPcode38[r.pcode] = i + 1; }});

      const hovertext = mapLocs.map(p => {{
        const nama = PAYLOAD.prov_meta[p] || p;
        const v = mapSlice[p];
        const rank = rankByPcode38[p] || '-';
        return `<b>${{nama}}</b><br>` +
               `<span style="color:#003D79;font-size:18px;font-weight:600">Rp ${{v.toLocaleString('id-ID')}}</span><br>` +
               `<span style="color:#667085">per kapita / bulan</span><br>` +
               `<span style="color:#667085">Kelas: ${{this.mapKelas}} · Rank #${{rank}} dari 38</span>`;
      }});

      // Top-3 provinces label di centroid (filter ke wilayah aktif) — include nilai
      const top3 = ranked38.filter(t => inRegion(t.pcode, this.wilayah, this.provFilter)).slice(0, 3);
      const labelLons = [], labelLats = [], labelText = [];
      top3.forEach(t => {{
        const c = PAYLOAD.centroids[t.pcode];
        if (c) {{
          labelLons.push(c[0]); labelLats.push(c[1]);
          const vRb = (t.value / 1000).toFixed(0);
          labelText.push('<b>' + (PAYLOAD.prov_meta_38[t.pcode] || t.pcode) + '</b><br>Rp ' + vRb + ' rb');
        }}
      }});

      // Semua prov dengan data dapat label nilai kecil di centroid
      const allLabelLons = [], allLabelLats = [], allLabelText = [];
      ranked38.filter(t => inRegion(t.pcode, this.wilayah, this.provFilter)).forEach(t => {{
        const c = PAYLOAD.centroids[t.pcode];
        if (c && !top3.find(x => x.pcode === t.pcode)) {{
          allLabelLons.push(c[0]); allLabelLats.push(c[1]);
          const vRb = (t.value / 1000).toFixed(0);
          allLabelText.push('Rp ' + vRb + ' rb');
        }}
      }});

      const showCities = this.wilayah === 'Indonesia' && this.provFilter === 'All';
      const outliers = findOutliers(mapSlice, 1.8);
      const outlierGJ = {{ type: 'FeatureCollection',
        features: filteredGJ.features.filter(f => outliers.includes(f.id)) }};
      const traces = [
        // BASE: prov no-data → grey
        noDataLocs.length ? {{
          type: 'choropleth', geojson: baseGJ, locations: noDataLocs, z: noDataLocs.map(_=>0),
          featureidkey: 'properties.ADM1_PCODE',
          colorscale: [[0,'#E8E8E8'],[1,'#E8E8E8']], showscale: false,
          marker: {{ line: {{ color: 'white', width: 0.8 }} }},
          hoverinfo: 'skip', showlegend: false,
        }} : null,
        {{
          type: 'choropleth', geojson: filteredGJ, locations: mapLocs, z: mapVals,
          featureidkey: 'properties.ADM1_PCODE',
          zmin: bins.edges[0], zmax: bins.edges[5],
          colorscale, showscale: false,
          marker: {{ line: {{ color: 'white', width: 0.8 }} }},
          hovertext, hovertemplate: '%{{hovertext}}<extra></extra>',
          hoverlabel: {{ bgcolor: 'white', bordercolor: '#003D79', font: {{ family: FONT, size: 13, color: INK }}, align: 'left', namelength: -1 }},
        }},
        // Outlier overlay: tebal amber border untuk |z|>1.8
        outliers.length ? {{
          type: 'choropleth', geojson: outlierGJ, locations: outliers,
          z: outliers.map(p => 1),
          featureidkey: 'properties.ADM1_PCODE',
          colorscale: [[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']],
          showscale: false,
          marker: {{ line: {{ color: '#EA7200', width: 2.5 }} }},
          hoverinfo: 'skip', showlegend: false,
        }} : null,
        showCities ? {{
          type: 'scattergeo', mode: 'markers+text',
          lon: CITIES.map(c => c.lon), lat: CITIES.map(c => c.lat),
          text: CITIES.map(c => c.name), textposition: 'top right',
          textfont: {{ family: FONT, size: 10, color: '#051C2C', weight: 600 }},
          marker: {{ size: 5, color: '#FFB700', line: {{ color: '#051C2C', width: 1 }} }},
          hoverinfo: 'skip', showlegend: false,
        }} : null,
        // Top-3 label (nama + nilai)
        {{
          type: 'scattergeo', mode: 'text',
          lon: labelLons, lat: labelLats, text: labelText,
          textfont: {{ family: 'Source Serif 4, serif', size: 12, color: '#051C2C' }},
          hoverinfo: 'skip', showlegend: false,
        }},
        // Semua prov lain: label nilai kecil
        {{
          type: 'scattergeo', mode: 'text',
          lon: allLabelLons, lat: allLabelLats, text: allLabelText,
          textfont: {{ family: FONT, size: 9, color: '#051C2C' }},
          hoverinfo: 'skip', showlegend: false,
        }},
      ].filter(t => t);

      Plotly.react('chart-map', traces, {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        font: {{ family: FONT, color: INK }},
        geo: (() => {{ const bbox = tightBbox(filteredGJ.features); return {{ visible: false, bgcolor: 'transparent', projection: {{ type: 'mercator' }}, ...(bbox ? {{ lonaxis: {{ range: bbox.lon, autorange: false }}, lataxis: {{ range: bbox.lat, autorange: false }} }} : {{ fitbounds: 'locations' }}), uirevision: this.wilayah + '|' + this.provFilter }}; }})(),
        paper_bgcolor: 'transparent',
      }}, {{ displaylogo: false, responsive: true }});

      // Render custom HTML legend
      this._renderLegend('legend-geografi', bins, palette);

      // Ranking 38 prov
      const rankSlice = (PAYLOAD.rank38[this.year] || {{}})[this.mapKelas] || {{}};
      const ranked = Object.keys(rankSlice)
        .map(p => ({{ pcode: p, nama: PAYLOAD.prov_meta_38[p] || p, value: rankSlice[p] }}))
        .sort((a,b) => b.value - a.value);
      this.rankTop = ranked.slice(0, 10);
      this.rankBottom = ranked.slice().sort((a,b) => a.value - b.value).slice(0, 10);
      this.$nextTick(() => this._drawSparklines());

      // Click drill-down: open Provinsi Profile panel
      const mapEl = document.getElementById('chart-map');
      const self = this;
      if (mapEl && mapEl.removeAllListeners) {{
        mapEl.removeAllListeners('plotly_click');
        mapEl.removeAllListeners('plotly_hover');
        mapEl.removeAllListeners('plotly_unhover');
      }}
      if (mapEl) {{
        mapEl.on('plotly_click', function(d) {{
          if (d.points && d.points[0] && d.points[0].location) {{
            const pcode = d.points[0].location;
            const v = mapSlice[pcode];
            // Find rank in 38-prov list
            const rank38Sorted = Object.entries(rankSlice).map(([p,vv]) => ({{p,v:vv}})).sort((a,b)=>b.v-a.v);
            const rIdx = rank38Sorted.findIndex(r => r.p === pcode || (PEMEKARAN_REVERSE[pcode]||[]).includes(r.p));
            self.provPanel = {{
              open: true,
              nama: PAYLOAD.prov_meta[pcode] || pcode,
              rpTotal: 'Rp ' + v.toLocaleString('id-ID'),
              rank: rIdx >= 0 ? rIdx + 1 : '-',
              note: pcode === 'ID91' ? 'Includes Papua Selatan, Tengah, Pegunungan (pemekaran 2022).' :
                    pcode === 'ID94' ? 'Includes Papua Barat Daya (pemekaran 2022).' :
                    'Standard provinsi 34-prov BPS 2020.'
            }};
          }}
        }});
        mapEl.on('plotly_hover', function(d) {{
          if (d.points && d.points[0]) self.hoveredPcode = d.points[0].location;
        }});
        mapEl.on('plotly_unhover', function() {{ self.hoveredPcode = null; }});
      }}
    }},

    renderKomoditi() {{
      if (!window.KOMODITI_DATA) return;
      // Komoditi data sekarang per 38 prov. Map butuh 34 (aggregate Papua pemekaran).
      const slice38 = (((window.KOMODITI_DATA[this.year] || {{}})[this.komKelas] || {{}})[this.komSelected]) || {{}};
      // Aggregate to 34 prov for choropleth (mean of merged provinces)
      const PEMEKARAN = {{ 'ID92': 'ID94', 'ID95': 'ID91', 'ID96': 'ID91', 'ID97': 'ID91' }};
      const merge = {{}};
      const merge_count = {{}};
      Object.keys(slice38).forEach(p => {{
        const target = PEMEKARAN[p] || p;
        merge[target] = (merge[target] || 0) + slice38[p];
        merge_count[target] = (merge_count[target] || 0) + 1;
      }});
      const slice34full = {{}};
      Object.keys(merge).forEach(p => {{ slice34full[p] = Math.round(merge[p] / merge_count[p]); }});
      // Filter wilayah / prov
      const slice34 = {{}};
      Object.keys(slice34full).forEach(p => {{
        if (inRegion(p, this.wilayah, this.provFilter)) slice34[p] = slice34full[p];
      }});

      const locs = Object.keys(slice34);
      const vals = locs.map(p => slice34[p]);
      const allowedSetK = new Set(locs);
      const filteredGJ = filteredGeojson(allowedSetK);
      // BASE layer: prov in scope without data
      const baseFeaturesK = GEOJSON.features.filter(f => inRegion(f.id, this.wilayah, this.provFilter));
      const baseGJK = {{ type: 'FeatureCollection', features: baseFeaturesK }};
      const noDataK = baseFeaturesK.map(f => f.id).filter(p => !(p in slice34));

      // Quintile bins
      const bins = computeBins(vals);
      const palette = ['#FFF8E5', '#FFE08A', '#FFB700', '#D67900', '#003D79'];
      const colorscale = [
        [0.0,   palette[0]], [0.2-1e-9, palette[0]],
        [0.2,   palette[1]], [0.4-1e-9, palette[1]],
        [0.4,   palette[2]], [0.6-1e-9, palette[2]],
        [0.6,   palette[3]], [0.8-1e-9, palette[3]],
        [0.8,   palette[4]], [1.0,      palette[4]],
      ];

      // Icon (untuk hover card)
      const list = window.KOMODITI_LIST || [];
      const meta = list.find(x => x.key === this.komSelected) || {{}};

      // Ranking 38 untuk hover
      const ranked38 = Object.keys(slice38)
        .map(p => ({{ pcode: p, value: slice38[p] }}))
        .sort((a,b) => b.value - a.value);
      const rankByPcode38 = {{}};
      ranked38.forEach((r, i) => {{ rankByPcode38[r.pcode] = i + 1; }});

      // Top-3 labels (filter ke wilayah aktif)
      const top3 = ranked38.filter(t => inRegion(t.pcode, this.wilayah, this.provFilter)).slice(0, 3);
      const labelLons = [], labelLats = [], labelText = [];
      top3.forEach(t => {{
        const c = PAYLOAD.centroids[t.pcode];
        if (c) {{
          labelLons.push(c[0]); labelLats.push(c[1]);
          labelText.push('<b>' + (PAYLOAD.prov_meta_38[t.pcode] || t.pcode) + '</b>');
        }}
      }});

      const self = this;
      const showCitiesK = this.wilayah === 'Indonesia' && this.provFilter === 'All';
      const traces = [
        // BASE: prov no-data → grey
        noDataK.length ? {{
          type: 'choropleth', geojson: baseGJK, locations: noDataK, z: noDataK.map(_=>0),
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
          hovertext: locs.map(p => {{
            const nama = PAYLOAD.prov_meta[p] || p;
            const v = slice34[p];
            const rank38 = ranked38.findIndex(r => r.pcode === p);
            const valStr = v >= 1000 ? 'Rp ' + v.toLocaleString('id-ID') : 'Rp ' + v;
            return `<b>${{nama}}</b><br>` +
                   `<span style="color:#003D79;font-size:18px;font-weight:600">${{valStr}}</span><br>` +
                   `<span style="color:#667085">${{this.komShort}} · Kelas ${{this.komKelas}} · ${{this.year}}</span><br>` +
                   `<span style="color:#667085">Rank #${{rank38 >= 0 ? rank38+1 : '-'}} dari 38</span>`;
          }}),
          hovertemplate: '%{{hovertext}}<extra></extra>',
          hoverlabel: {{ bgcolor: 'white', bordercolor: '#003D79', font: {{ family: FONT, size: 13, color: INK }}, align: 'left', namelength: -1 }},
        }},
        showCitiesK ? {{
          type: 'scattergeo', mode: 'markers+text',
          lon: CITIES.map(c => c.lon), lat: CITIES.map(c => c.lat),
          text: CITIES.map(c => c.name), textposition: 'top right',
          textfont: {{ family: FONT, size: 10, color: '#051C2C', weight: 600 }},
          marker: {{ size: 5, color: '#003D79', line: {{ color: '#051C2C', width: 1 }} }},
          hoverinfo: 'skip', showlegend: false,
        }} : null,
        {{
          type: 'scattergeo', mode: 'text',
          lon: labelLons, lat: labelLats, text: labelText,
          textfont: {{ family: 'Source Serif 4, serif', size: 12, color: '#051C2C' }},
          hoverinfo: 'skip', showlegend: false,
        }},
      ].filter(t => t);

      Plotly.react('chart-komoditi-map', traces, {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        font: {{ family: FONT, color: INK }},
        geo: (() => {{ const bbox = tightBbox(baseGJK.features.length ? baseGJK.features : filteredGJ.features); return {{ visible: false, bgcolor: 'transparent', projection: {{ type: 'mercator' }}, ...(bbox ? {{ lonaxis: {{ range: bbox.lon, autorange: false }}, lataxis: {{ range: bbox.lat, autorange: false }} }} : {{ fitbounds: 'locations' }}), uirevision: this.wilayah + '|' + this.provFilter }}; }})(),
        paper_bgcolor: 'transparent',
      }}, {{ displaylogo: false, responsive: true }});

      this._renderLegend('legend-komoditi', bins, palette);

      // Disable old custom hover card (we use Plotly default now)
      this.hover.visible = false;
      const mapEl = document.getElementById('chart-komoditi-map');
      mapEl.removeEventListener('mousemove', mapEl._hoverHandler || (() => {{}}));
      mapEl.removeEventListener('mouseleave', mapEl._leaveHandler || (() => {{}}));
      mapEl._hoverHandler = function(ev) {{
        const rect = mapEl.getBoundingClientRect();
        self.hover.x = ev.clientX - rect.left;
        self.hover.y = ev.clientY - rect.top;
      }};
      mapEl._leaveHandler = function() {{ self.hover.visible = false; }};
      mapEl.addEventListener('mousemove', mapEl._hoverHandler);
      mapEl.addEventListener('mouseleave', mapEl._leaveHandler);

      mapEl.removeAllListeners && mapEl.removeAllListeners('plotly_hover');
      mapEl.on('plotly_hover', function(d) {{
        const pt = d.points[0];
        const pcode = pt.location;
        // Cari nilai 38-prov untuk ranking
        const v = slice34[pcode];
        const rank = rankByPcode38[pcode] || '-';
        self.hover.prov = PAYLOAD.prov_meta[pcode] || pcode;
        self.hover.value = v >= 1000 ? 'Rp ' + v.toLocaleString('id-ID') : 'Rp ' + v;
        self.hover.rank = rank;
        self.hover.visible = true;
      }});
      mapEl.on('plotly_unhover', function() {{ self.hover.visible = false; }});

      // Ranking pakai 38 prov asli
      const ranked = Object.keys(slice38).map(p => ({{
        pcode: p, nama: PAYLOAD.prov_meta_38[p] || p, value: slice38[p]
      }})).sort((a,b) => b.value - a.value);
      this.komRankTop = ranked.slice(0, 10);
      this.komRankBottom = ranked.slice().sort((a,b) => a.value - b.value).slice(0, 10);
    }},
  }};
}}
</script>
</body>
</html>
"""


def main():
    df_38, df_34 = load()
    nat, nat_kelas, nat_klp, prov, prov_all = build_aggregates(df_34)
    rank_data_38, rank_meta_38 = build_prov_38(df_38)

    with open(META, "r", encoding="utf-8") as f:
        meta = json.load(f)
    kelompok_order = meta["kelompok_order"]
    klp_makanan = meta["kelompok_makanan"]

    payload = to_js(nat, nat_kelas, nat_klp, prov, prov_all, kelompok_order, klp_makanan)
    payload["rank38"] = rank_data_38
    payload["prov_meta_38"] = rank_meta_38

    # Sparkline data: per pcode, trend 7 tahun (rp_per_kapita_bulan, kelas All)
    sparkline = {}
    for pcode in rank_meta_38.keys():
        sparkline[pcode] = [rank_data_38[str(y)]["All"].get(pcode, 0) for y in YEARS]
    payload["sparkline"] = sparkline

    # Centroid lon/lat per provinsi (untuk label di peta)
    try:
        import geopandas as gpd
        SHP = r"C:\Users\LENOVO\OneDrive - PT Bank Mandiri (Persero) Tbk\Desktop\Mandiri\Software\IDN_shp\idn_admbnda_adm1_bps_20200401.shp"
        gdf = gpd.read_file(SHP)
        centroids = {r["ADM1_PCODE"]: [round(r.geometry.centroid.x, 3), round(r.geometry.centroid.y, 3)] for _, r in gdf.iterrows()}
    except Exception:
        centroids = {}
    payload["centroids"] = centroids

    with open(GEOJSON, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    # Data freshness: mtime CSV terbaru
    from datetime import datetime
    csv_mtime = datetime.fromtimestamp(max(CSV.stat().st_mtime, CSV_KOMODITI.stat().st_mtime)).strftime("%Y-%m-%d")
    payload["data_updated"] = csv_mtime

    html = build_html(payload, geojson, date.today().isoformat())
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT.name} ({OUT.stat().st_size:,} bytes)")

    # Komoditi data sebagai file JS terpisah (dimuat via <script src>)
    build_komoditi_js()


if __name__ == "__main__":
    main()
