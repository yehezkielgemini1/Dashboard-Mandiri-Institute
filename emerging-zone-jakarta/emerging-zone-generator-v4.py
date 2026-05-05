#!/usr/bin/env python3
"""
emerging-zone-generator-v4.py
Generate brand-consistent Mandiri Institute dashboard for DKI Jakarta commercial zones.
Reads pre-computed FINAL data files, embeds as JSON, builds 6-page HTML with sidebar layout.
"""

import json
import sys
import os
import math
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / 'data'
OUTPUT = Path(__file__).parent / '260503_NASA_emerging-zone-detector.html'


def jclean(obj):
    """Recursively clean NaN to None for JSON safety."""
    if isinstance(obj, dict):
        return {k: jclean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [jclean(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


def load_data():
    desa = pd.read_csv(DATA_DIR / '260503_FINAL_eczi_per_desa.csv')
    fc = desa.select_dtypes(include='float64').columns
    desa[fc] = desa[fc].round(4)
    desa = desa.where(pd.notnull(desa), None)

    kw = pd.read_csv(DATA_DIR / '260503_FINAL_eczi_per_kawasan.csv')
    fc2 = kw.select_dtypes(include='float64').columns
    kw[fc2] = kw[fc2].round(4)
    kw = kw.where(pd.notnull(kw), None)

    with open(DATA_DIR / 'dki_desa_simplified.geojson', encoding='utf-8') as f:
        geojson = f.read().strip()

    with open(DATA_DIR / 'kawasan_utama_mapping.json', encoding='utf-8') as f:
        kw_map = f.read().strip()

    ntl = pd.read_excel(DATA_DIR / '260503_NASA_jakarta-monthly-areas.xlsx', sheet_name='annual_dry_season')
    ntl['lum_drySeason'] = ntl['lum_drySeason'].round(2)

    osm = pd.read_excel(DATA_DIR / '260503_OSM_poi-lifestyle-jakarta.xlsx', sheet_name='all_lifestyle')
    osm = osm[['lat', 'lon', 'category']].dropna()
    osm['lat'] = osm['lat'].round(4)
    osm['lon'] = osm['lon'].round(4)
    osm_arr = osm.values.tolist()

    tra = pd.read_excel(DATA_DIR / '260502_OSM_transport-jakarta.xlsx', sheet_name=0)
    lat_col = next((c for c in tra.columns if c.lower() == 'lat'), 'lat')
    lon_col = next((c for c in tra.columns if c.lower() in ('lon', 'lng', 'long')), 'lon')
    tra = tra[[lat_col, lon_col]].dropna()
    tra.columns = ['lat', 'lon']
    tra['lat'] = tra['lat'].round(4)
    tra['lon'] = tra['lon'].round(4)
    tra_arr = tra.values.tolist()

    desa_records = jclean(desa.to_dict(orient='records'))
    kw_records = jclean(kw.to_dict(orient='records'))
    ntl_records = jclean(ntl.to_dict(orient='records'))

    return {
        'desa_json': json.dumps(desa_records, separators=(',', ':'), ensure_ascii=False),
        'kw_json': json.dumps(kw_records, separators=(',', ':'), ensure_ascii=False),
        'geojson': geojson,
        'kw_map': kw_map,
        'ntl_json': json.dumps(ntl_records, separators=(',', ':'), ensure_ascii=False),
        'osm_json': json.dumps(osm_arr, separators=(',', ':'), ensure_ascii=False),
        'tra_json': json.dumps(tra_arr, separators=(',', ':'), ensure_ascii=False),
    }


CSS = r"""
:root {
  --navy: #003D79; --navy-deep: #002852; --navy-soft: #1A5394;
  --sky: #67B2E8; --sky-soft: #A9C4DF;
  --yellow: #FFB700; --yellow-soft: #FFE08A;
  --ink: #051C2C; --ink-soft: #2A3F52;
  --rule: #E5E8EC; --rule-strong: #D0D5DD;
  --muted: #667085; --muted-soft: #98A2B3;
  --paper: #FFFFFF; --cream: #F8F6F0; --mist: #F0F6FC;
  --positive: #00875A; --negative: #C8102E; --warning: #EA7200;
  --sp-1: 4px; --sp-2: 8px; --sp-3: 12px; --sp-4: 16px; --sp-5: 24px;
  --sp-6: 32px; --sp-8: 48px; --sp-10: 64px; --sp-12: 96px;
  --elev-1: 0 1px 2px rgba(5,28,44,0.04);
  --elev-2: 0 2px 8px rgba(5,28,44,0.06);
  --elev-3: 0 8px 24px rgba(5,28,44,0.10);
  --elev-4: 0 16px 48px rgba(5,28,44,0.14);
  --fs-xs: 11px; --fs-sm: 13px; --fs-base: 14px; --fs-md: 16px;
  --fs-lg: 20px; --fs-xl: 25px; --fs-2xl: 31px; --fs-3xl: 39px;
  --tr-fast: 0.12s ease; --tr-base: 0.2s ease; --tr-slow: 0.4s ease;
}
html, body { background: var(--paper); color: var(--ink); }
body { font-family: 'Inter', system-ui, sans-serif; font-weight: 400; letter-spacing: -0.003em; }
.serif-display { font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.015em; line-height: 1.08; }
.stat-num { font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.02em; line-height: 1; font-feature-settings: 'tnum' 1, 'lnum' 1; }
.eyebrow { font-size: 11px; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; color: var(--navy); }
.rule-top { border-top: 1px solid var(--rule); }
.rule-bottom { border-bottom: 1px solid var(--rule); }
.ink { color: var(--ink); }
.muted { color: var(--muted); }
.num { font-variant-numeric: tabular-nums; }
.badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--navy); background: var(--mist); border: 1px solid var(--sky); }
.badge-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--sky); display: inline-block; }
.callout { border-left: 3px solid var(--sky); background: var(--mist); padding: var(--sp-4) var(--sp-5); border-radius: 0; }
.callout .label { font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--navy); }
.callout .text { font-family: 'Source Serif 4', Georgia, serif; font-size: var(--fs-md); line-height: 1.45; color: var(--ink); margin-top: 6px; font-weight: 500; }
.chart-footer { border-top: 1px solid var(--rule); margin-top: var(--sp-5); padding-top: var(--sp-4); display: flex; flex-wrap: wrap; gap: var(--sp-5); font-size: var(--fs-xs); color: var(--muted); }
.chart-footer .label { font-weight: 600; color: var(--ink); text-transform: uppercase; letter-spacing: 0.06em; margin-right: 4px; }
.select-flat { border: 0; border-bottom: 1px solid var(--ink); background: transparent; padding: 6px 24px 6px 0; font-size: 15px; font-weight: 500; color: var(--ink); appearance: none; background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%23051C2C'%3e%3cpath fill-rule='evenodd' d='M5.23 7.21a.75.75 0 011.06.02L10 11.06l3.71-3.83a.75.75 0 111.08 1.04l-4.25 4.39a.75.75 0 01-1.08 0L5.21 8.27a.75.75 0 01.02-1.06z' clip-rule='evenodd'/%3e%3c/svg%3e"); background-repeat: no-repeat; background-position: right 0 center; background-size: 18px; }
.select-flat:focus { outline: none; border-bottom-color: var(--sky); }
.chip-action { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: var(--fs-xs); font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--navy); background: white; border: 1px solid var(--rule); cursor: pointer; transition: all var(--tr-base); }
.chip-action:hover { background: var(--mist); border-color: var(--navy); }
.chip-action.active { background: var(--navy); color: white; border-color: var(--navy); }

/* Sidebar */
.sidebar { position: fixed; top: 0; left: 0; bottom: 0; width: 220px; background: var(--navy); color: white; padding: 24px 0; z-index: 40; display: flex; flex-direction: column; overflow-y: auto; }
.sidebar .brand { padding: 0 24px 20px 24px; border-bottom: 1px solid rgba(255,255,255,0.12); }
.sidebar .brand-title { font-family: 'Source Serif 4', Georgia, serif; font-size: 18px; font-weight: 600; line-height: 1.15; color: white; }
.sidebar .brand-sub { font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--sky); margin-top: 4px; font-weight: 600; }
.sidebar .yellow-accent { display: inline-block; width: 10px; height: 10px; background: var(--yellow); margin-bottom: 8px; }
.sidebar .nav-section { padding: 16px 0; }
.sidebar .nav-label { padding: 0 24px; font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(255,255,255,0.4); margin-bottom: 8px; }
.sidebar .nav-item { display: flex; align-items: center; gap: 10px; padding: 10px 24px; font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.7); border-left: 3px solid transparent; cursor: pointer; transition: all 0.15s; background: none; border-top: none; border-right: none; border-bottom: none; width: 100%; text-align: left; position: relative; overflow: hidden; }
.sidebar .nav-item::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 0; background: var(--sky); transition: width var(--tr-base); }
.sidebar .nav-item:hover { color: white; background: rgba(255,255,255,0.05); }
.sidebar .nav-item:hover::before { width: 3px; }
.sidebar .nav-item.active { color: white; border-left-color: var(--sky); background: rgba(103,178,232,0.1); }
.sidebar .nav-item.active::before { width: 3px; }
.sidebar .nav-item iconify-icon { font-size: 18px; }
.sidebar .footer { margin-top: auto; padding: 16px 24px; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(255,255,255,0.4); border-top: 1px solid rgba(255,255,255,0.12); }
.with-sidebar { margin-left: 220px; }

/* Folio */
.folio { position: sticky; top: 0; z-index: 30; background: rgba(255,255,255,0.92); backdrop-filter: blur(8px); border-bottom: 1px solid var(--rule); padding: 8px 0; }
.folio-inner { max-width: 1280px; margin: 0 auto; padding: 0 32px; display: flex; justify-content: space-between; font-size: 10px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); }
.folio .left { color: var(--ink); }
.folio .right { color: var(--muted); }

/* Filter bar */
.filter-bar { position: sticky; top: 33px; z-index: 25; background: var(--cream); border-bottom: 1px solid var(--rule-strong); padding: 8px 0; }
.filter-bar-inner { max-width: 1280px; margin: 0 auto; padding: 0 32px; display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.filter-bar-label { font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); white-space: nowrap; }
.filter-bar .sep { width: 1px; height: 20px; background: var(--rule-strong); }

/* Hero band */
.hero-band { background: linear-gradient(180deg, var(--navy) 0%, #002852 100%); color: white; position: relative; }
.hero-band::after { content: ''; position: absolute; bottom: -1px; left: 0; right: 0; height: 1px; background: var(--yellow); opacity: 0.4; }
.hero-band .eyebrow { color: var(--sky); }
.hero-band h1, .hero-band h2 { color: white; }
.hero-band p { color: rgba(255,255,255,0.78); }

/* Chart card */
.chart-card { background: white; border: 1px solid var(--rule); padding: 24px; }
.chart-card:hover { box-shadow: var(--elev-3); }

/* KPI cards */
.kpi-card { background: white; border: 1px solid var(--rule); padding: 20px 24px; }
.kpi-card.kpi-positive { border-top: 3px solid var(--positive); }
.kpi-card.kpi-negative { border-top: 3px solid var(--negative); }
.kpi-card.kpi-sky { border-top: 3px solid var(--sky); }
.kpi-card.kpi-yellow { border-top: 3px solid var(--yellow); }
.kpi-card.kpi-navy { border-top: 3px solid var(--navy); }
.kpi-card .kpi-label { font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); }
.kpi-card .kpi-val { font-family: 'Source Serif 4', Georgia, serif; font-size: 22px; font-weight: 600; color: var(--ink); margin-top: 6px; line-height: 1.15; }
.kpi-card .kpi-sub { font-size: 11px; color: var(--muted); margin-top: 4px; }

/* Quadrant category colors */
.cat-hotspot { background: #FFF0F0; color: var(--negative); border: 1px solid #FFCDD2; }
.cat-early { background: #FFF6E0; color: var(--warning); border: 1px solid #FFE0A0; }
.cat-mature { background: #E8F4FF; color: var(--navy); border: 1px solid #B3D8F5; }
.cat-low { background: var(--mist); color: var(--muted); border: 1px solid var(--rule); }

/* Pulse badges */
.pulse-grow { background: #E6F4EE; color: var(--positive); border: 1px solid #B3DCC9; }
.pulse-stable { background: #FFF6E0; color: var(--warning); border: 1px solid #FFE0A0; }
.pulse-slow { background: #FFF0F0; color: var(--negative); border: 1px solid #FFCDD2; }
.pulse-na { background: var(--mist); color: var(--muted); border: 1px solid var(--rule); }

/* Rank rows */
.rank-row { display: grid; grid-template-columns: 28px 1fr 120px; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--rule); }
.rank-row:hover { background: var(--mist); }
.rank-num { font-family: 'Source Serif 4', Georgia, serif; font-size: 16px; font-weight: 600; color: var(--sky); text-align: right; }
.rank-name { font-size: 14px; color: var(--ink); font-weight: 500; }
.rank-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
.rank-bar-wrap { position: relative; height: 6px; background: var(--mist); overflow: hidden; margin-top: 6px; }
.rank-bar { position: absolute; left: 0; top: 0; height: 100%; background: var(--navy); }
.rank-val { font-variant-numeric: tabular-nums; font-size: 13px; font-weight: 600; color: var(--ink); }
.rank-cell-right { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }

/* eyebrow-roman */
.eyebrow-roman { font-family: 'Source Serif 4', Georgia, serif; font-style: italic; font-size: var(--fs-md); font-weight: 500; letter-spacing: 0.02em; color: var(--navy); }
.eyebrow-roman::before { content: ''; display: inline-block; width: 24px; height: 1px; background: var(--navy); vertical-align: middle; margin-right: 12px; }

/* Map containers */
.leaflet-map { height: 500px; border: 1px solid var(--rule); }

/* Score breakdown table */
.score-table { width: 100%; border-collapse: collapse; font-size: var(--fs-sm); }
.score-table th { background: var(--navy); color: white; padding: 10px 12px; text-align: left; font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; cursor: pointer; user-select: none; }
.score-table th:hover { background: var(--navy-deep); }
.score-table td { padding: 9px 12px; border-bottom: 1px solid var(--rule); }
.score-table tr:hover td { background: var(--mist); }
.score-table .num { text-align: right; font-variant-numeric: tabular-nums; }

.cat-pill { display: inline-block; padding: 2px 8px; font-size: 10px; font-weight: 700; letter-spacing: 0.06em; }

/* Ref section */
.ref-card { background: white; border: 1px solid var(--rule); padding: 20px; margin-bottom: 12px; }
.ref-card .ref-id { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--sky); }
.ref-card .ref-citation { font-size: var(--fs-sm); color: var(--ink); margin-top: 6px; line-height: 1.5; }
.ref-card .ref-doi { font-size: 11px; color: var(--muted); margin-top: 4px; font-family: monospace; }
.ref-card .ref-finding { font-size: var(--fs-sm); color: var(--muted); margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--rule); line-height: 1.5; }

.warning-box { border: 2px solid var(--yellow); background: #FFF9E6; padding: 20px; margin-bottom: 24px; }
.warning-box .wb-title { font-size: 13px; font-weight: 700; color: var(--ink); margin-bottom: 8px; }
.warning-box .wb-text { font-size: 13px; color: var(--ink); line-height: 1.5; }

.dash-footer { padding: 32px 0; border-top: 1px solid var(--rule); display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); margin-top: 32px; }

.tab-strip { display: flex; gap: 4px; border-bottom: 1px solid var(--rule); margin-bottom: 20px; }
.tab-btn { padding: 10px 18px; font-size: 12px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; transition: all var(--tr-base); }
.tab-btn:hover { color: var(--navy); }
.tab-btn.active { color: var(--navy); border-bottom-color: var(--navy); }

.layer-btn-group { display: inline-flex; gap: 0; margin-bottom: 12px; }
.layer-btn { padding: 8px 14px; font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--ink); background: white; border: 1px solid var(--rule-strong); border-right: none; cursor: pointer; }
.layer-btn:last-child { border-right: 1px solid var(--rule-strong); }
.layer-btn.active { background: var(--navy); color: white; border-color: var(--navy); }

.legend-box { position: absolute; bottom: 12px; right: 12px; background: white; padding: 10px 14px; border: 1px solid var(--rule-strong); font-size: 11px; box-shadow: var(--elev-2); z-index: 1000; max-width: 240px; }
.legend-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.legend-swatch { display: inline-block; width: 14px; height: 14px; border: 1px solid rgba(0,0,0,0.1); }

*:focus-visible { outline: 2px solid var(--sky); outline-offset: 3px; }
button, .chip-action { transition: all var(--tr-base); }

/* ============ TOPNAV (canon, sticky) ============ */
.topnav { background: var(--navy-deep, #002852); padding: 14px 28px; display: flex; align-items: center; gap: 24px; border-bottom: 1px solid rgba(255,255,255,0.08); position: sticky; top: 0; z-index: 1050; color: white; }
.topnav .burger { font-size: 22px; cursor: pointer; opacity: 0.92; display: none; color: white; }
.topnav .brand { font-family: 'Source Serif 4', Georgia, serif; font-size: 17px; font-weight: 600; letter-spacing: -0.01em; color: white; }
.topnav .brand-sub { font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--sky); margin-top: 2px; font-weight: 600; }
.topnav .menu { display: flex; gap: 22px; margin-left: 24px; }
.topnav .menu a { background: none; border: 0; font-family: inherit; font-size: 13px; font-weight: 500; color: white; opacity: 0.85; padding: 6px 0; cursor: pointer; transition: opacity 0.2s; letter-spacing: -0.003em; text-decoration: none; }
.topnav .menu a:hover, .topnav .menu a.active { opacity: 1; color: var(--sky); }
.topnav .right { margin-left: auto; display: flex; gap: 14px; align-items: center; font-size: 12px; opacity: 0.85; }
.topnav .right a { color: white; text-decoration: none; }
.topnav .search { font-size: 22px; cursor: pointer; opacity: 0.85; color: white; }

.nav-drawer-overlay { display: none; position: fixed; inset: 0; background: rgba(5,28,44,0.55); z-index: 1100; opacity: 0; transition: opacity 0.3s; }
.nav-drawer-overlay.open { display: block; opacity: 1; }
.nav-drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(320px, 82vw); background: var(--navy-deep, #002852); z-index: 1200; padding: 76px 28px 28px; box-shadow: -8px 0 32px rgba(0,0,0,0.3); transform: translateX(100%); transition: transform 0.3s ease; color: white; overflow-y: auto; }
.nav-drawer.open { transform: translateX(0); }
.nav-drawer .close-btn { position: absolute; top: 20px; right: 20px; background: none; border: none; cursor: pointer; color: white; padding: 6px; font-size: 26px; }
.nav-drawer .drawer-label { font-size: 10px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: rgba(255,255,255,0.55); margin: 18px 0 10px; }
.nav-drawer ul { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 2px; }
.nav-drawer a, .nav-drawer button { display: flex; align-items: center; gap: 10px; width: 100%; text-align: left; padding: 14px 0; font-family: 'Source Serif 4', Georgia, serif; font-size: 19px; color: white; border: 0; border-bottom: 1px solid rgba(255,255,255,0.12); background: none; cursor: pointer; transition: color 0.15s; text-decoration: none; }
.nav-drawer a:hover, .nav-drawer button:hover { color: var(--sky); }
.nav-drawer iconify-icon { font-size: 18px; opacity: 0.7; }

@media (max-width: 1100px) {
  .topnav .menu { display: none; }
  .topnav .burger { display: inline-flex; }
  .topnav .right .nav-link { display: none; }
}
@media (max-width: 480px) {
  .topnav { padding: 12px 18px; }
  .topnav .brand-sub { display: none; }
}

/* ============ UNIFORM v2: hide legacy sidebar (topnav is now the canonical nav) ============ */
.sidebar, aside.sidebar { display: none !important; }
.with-sidebar { margin-left: 0 !important; }
/* Folio + filter bar offset di bawah topnav (~64px). Topnav dipush ke z-index 1050 supaya di atas folio. */
.folio { top: 0 !important; z-index: 30 !important; }
.filter-bar { top: 33px !important; z-index: 25 !important; }
"""


# -------------- HTML page templates --------------

SIDEBAR_HTML = """
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
    <div class="nav-label">Kawasan Komersial Jakarta</div>
    <template x-for="t in tabs" :key="t.id">
      <button @click="setPage(t.id)" :class="page === t.id ? 'nav-item active' : 'nav-item'">
        <iconify-icon :icon="t.icon"></iconify-icon>
        <span x-text="t.label"></span>
      </button>
    </template>
  </div>
  <div class="footer">
    <div>270 desa &middot; 21 kawasan &middot; 2021-2025</div>
  </div>
</aside>
"""

TOPNAV_HTML = """
<!-- ============ TOP NAV (canon, sticky) — added 2026-05-05 untuk uniform v2 ============ -->
<nav class="topnav">
  <iconify-icon class="burger" icon="mdi:menu" @click="navOpen = true" role="button" aria-label="Buka menu" tabindex="0" @keydown.enter="navOpen = true"></iconify-icon>
  <div>
    <div class="brand">Mandiri Institute</div>
    <div class="brand-sub">Kawasan Komersial Jakarta</div>
  </div>
  <div class="menu">
    <a href="../index.html">Beranda</a>
    <a href="#" :class="page==='ringkasan' ? 'active' : ''" @click.prevent="setPage('ringkasan')">Ringkasan</a>
    <a href="#" :class="page==='cahaya-malam' ? 'active' : ''" @click.prevent="setPage('cahaya-malam')">Luminositas Malam</a>
    <a href="#" :class="page==='aktivitas-komersial' ? 'active' : ''" @click.prevent="setPage('aktivitas-komersial')">Aktivitas Komersial</a>
    <a href="#" :class="page==='skor-potensi' ? 'active' : ''" @click.prevent="setPage('skor-potensi')">Skor Potensi</a>
    <a href="#" :class="page==='detail-kawasan' ? 'active' : ''" @click.prevent="setPage('detail-kawasan')">Detail Kawasan</a>
    <a href="#" :class="page==='metodologi' ? 'active' : ''" @click.prevent="setPage('metodologi')">Metodologi</a>
  </div>
  <div class="right">
    <a class="nav-link" href="../index.html" style="font-weight:500;">Semua Dashboard</a>
    <iconify-icon class="search" icon="mdi:magnify" role="button" aria-label="Cari" tabindex="0"></iconify-icon>
  </div>
</nav>

<!-- Mobile drawer -->
<div class="nav-drawer-overlay" :class="{ 'open': navOpen }" @click="navOpen = false"></div>
<aside class="nav-drawer" :class="{ 'open': navOpen }" aria-label="Menu navigasi">
  <button class="close-btn" @click="navOpen = false" aria-label="Tutup menu">
    <iconify-icon icon="mdi:close"></iconify-icon>
  </button>
  <div class="drawer-label">Navigasi</div>
  <ul>
    <li><a href="../index.html" @click="navOpen = false"><iconify-icon icon="mdi:home-outline"></iconify-icon>Beranda</a></li>
  </ul>
  <div class="drawer-label">Kawasan Komersial Jakarta</div>
  <ul>
    <li><button @click="setPage('ringkasan'); navOpen = false"><iconify-icon icon="mdi:view-dashboard"></iconify-icon>Ringkasan</button></li>
    <li><button @click="setPage('cahaya-malam'); navOpen = false"><iconify-icon icon="mdi:weather-night"></iconify-icon>Luminositas Malam</button></li>
    <li><button @click="setPage('aktivitas-komersial'); navOpen = false"><iconify-icon icon="mdi:store"></iconify-icon>Aktivitas Komersial</button></li>
    <li><button @click="setPage('skor-potensi'); navOpen = false"><iconify-icon icon="mdi:chart-bar"></iconify-icon>Skor Potensi</button></li>
    <li><button @click="setPage('detail-kawasan'); navOpen = false"><iconify-icon icon="mdi:map-marker"></iconify-icon>Detail Kawasan</button></li>
    <li><button @click="setPage('metodologi'); navOpen = false"><iconify-icon icon="mdi:book-open-variant"></iconify-icon>Metodologi</button></li>
  </ul>
</aside>
"""

FOLIO_HTML = """
<div class="folio">
  <div class="folio-inner">
    <span class="left">Mandiri Institute &middot; Kawasan Komersial Jakarta</span>
    <span class="right" x-text="currentTabLabel()"></span>
  </div>
</div>
"""

# FILTER_BAR_HTML deprecated v5.6 — filter sekarang inline di Page 1 Ringkasan

HERO_HTML = """
<div class="hero-band">
  <header class="max-w-[1280px] mx-auto px-8 pt-14 pb-14">
    <div class="eyebrow">Riset Mandiri Institute &middot; Spasial Ekonomi</div>
    <h1 class="serif-display text-4xl md:text-5xl mt-5 max-w-4xl">Kawasan Komersial Berkembang &mdash; DKI Jakarta 2021-2025</h1>
    <p class="mt-5 text-base max-w-3xl leading-relaxed">21 wilayah dan 270 kelurahan, diperingkat dari empat sumber: NASA VIIRS, Podes BPS, Sakernas BPS, OpenStreetMap.</p>
  </header>
</div>
"""

# Page 1 — Ringkasan
PAGE_RINGKASAN = """
<section x-show="page === 'ringkasan'">
  <div class="rule-top pt-8">
    <span class="badge"><span class="badge-dot"></span>Ringkasan Eksekutif</span>
    <div class="eyebrow-roman mt-3">I. Ringkasan Eksekutif</div>
    <h2 class="serif-display text-3xl mt-2 max-w-3xl">Peringkat wilayah berdasarkan dua skor.</h2>
    <p class="mt-3 muted text-sm max-w-3xl"><strong>Skor Potensi</strong> mengukur sinyal pertumbuhan 2021-2025. <strong>Skor Magnitude</strong> mengukur skala aktivitas 2025.</p>
  </div>

  <!-- Inline tier filter (replaces global filter bar) -->
  <div class="chart-card mt-6" style="padding:14px 20px;">
    <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
      <span class="filter-bar-label">Tier</span>
      <div class="flex gap-1">
        <button @click="tier='kawasan'" :class="tier==='kawasan' ? 'chip-action active' : 'chip-action'">Wilayah Berpotensi</button>
        <button @click="tier='desa'" :class="tier==='desa' ? 'chip-action active' : 'chip-action'">Kelurahan/Desa</button>
        <button @click="tier='kecamatan'" :class="tier==='kecamatan' ? 'chip-action active' : 'chip-action'">Kecamatan</button>
        <button @click="tier='kabkota'" :class="tier==='kabkota' ? 'chip-action active' : 'chip-action'">Kabupaten/Kota</button>
      </div>
      <div class="sep"></div>
      <span class="filter-bar-label">Kategori</span>
      <select x-model="filterCategory" class="select-flat" style="font-size:12px;min-width:200px;">
        <option value="all">Semua Kategori</option>
        <option value="Kawasan Komersial Sedang Naik Daun">Emerging Hotspot</option>
        <option value="Kawasan Komersial Mapan">Mature Commercial</option>
        <option value="Awal Pertumbuhan">Early Growth</option>
        <option value="Aktivitas Rendah">Low Activity</option>
      </select>
      <span x-text="'&middot; ' + getCurrentData().length + ' wilayah'" style="font-size:11px;color:var(--muted);margin-left:auto;"></span>
    </div>
  </div>

  <div id="kpi-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-8"></div>

  <div class="mt-10 chart-card">
    <div class="tab-strip">
      <button @click="leaderTab='eczi'" :class="leaderTab==='eczi' ? 'tab-btn active' : 'tab-btn'">Skor Potensi</button>
      <button @click="leaderTab='magnitude'" :class="leaderTab==='magnitude' ? 'tab-btn active' : 'tab-btn'">Skor Magnitude (Kepadatan)</button>
    </div>
    <div class="eyebrow" style="color:var(--muted)" x-text="leaderTab==='eczi' ? 'Peringkat berdasarkan sinyal pertumbuhan tahunan' : 'Peringkat berdasarkan skala aktivitas komersial 2025'"></div>
    <h3 class="serif-display text-2xl mt-2 mb-3">10 Teratas</h3>
    <div id="leaderboard-list"></div>
    <div class="chart-footer">
      <span><span class="label">Sumber</span>NASA VIIRS, Podes BPS, Sakernas BPS, OpenStreetMap</span>
      <span><span class="label">Periode</span>2021-2025</span>
    </div>
  </div>

  <div class="mt-10 chart-card">
    <div class="eyebrow" style="color:var(--muted)">Tren Luminositas Malam 2019-2025</div>
    <h3 class="serif-display text-2xl mt-2 mb-3">Lintasan 5 Wilayah Teratas</h3>
    <div id="ringkasan-spark" style="height:280px;"></div>
    <div class="chart-footer">
      <span><span class="label">Sumber</span>NASA VIIRS, komposit Jul-Sep (kemarau)</span>
    </div>
  </div>
</section>
"""

# Page 2 — Luminositas Malam
PAGE_CAHAYA = """
<section x-show="page === 'cahaya-malam'">
  <div class="rule-top pt-8">
    <span class="badge"><span class="badge-dot"></span>Luminositas Malam (Satelit)</span>
    <div class="eyebrow-roman mt-3">II. Tren Luminositas Malam 2021-2025</div>
    <h2 class="serif-display text-3xl mt-2 max-w-3xl">Pertumbuhan luminositas per kelurahan, 2021-2025.</h2>
    <p class="mt-3 muted text-sm max-w-3xl">Luminositas malam (NASA VIIRS) sebagai proxy intensitas aktivitas spasial. Pertumbuhan tahunan menunjukkan kelurahan yang sedang naik; tingkat kecerahan 2025 menunjukkan skala aktivitas saat ini.</p>
  </div>

  <div class="chart-card mt-8" style="position:relative;">
    <div class="layer-btn-group">
      <button :class="map2Year==='cagr' ? 'layer-btn active' : 'layer-btn'" @click="map2Year='cagr'; renderMap2()">Pertumbuhan Tahunan 2021-2025</button>
      <button :class="map2Year==='level' ? 'layer-btn active' : 'layer-btn'" @click="map2Year='level'; renderMap2()">Tingkat Kecerahan 2025</button>
    </div>
    <div id="map-cahaya" class="leaflet-map" style="position:relative;"></div>
    <div class="chart-footer">
      <span><span class="label">Sumber</span>NASA VIIRS VNP46A2 via Google Earth Engine</span>
      <span><span class="label">Catatan</span>Spatial join 173 nilai unik ke 270 kelurahan; kelurahan kecil berbagi pixel</span>
    </div>
  </div>

  <div class="chart-card mt-8">
    <div class="eyebrow" style="color:var(--muted)">Tren Multi-Wilayah 2019-2025</div>
    <h3 class="serif-display text-xl mt-1 mb-4">Lintasan Luminositas Malam per Wilayah</h3>
    <div id="chart-ntl-timeseries" style="height:430px;"></div>
    <div class="chart-footer">
      <span><span class="label">Unit</span>DNB Radiance (nW/cm&sup2;/sr), komposit Jul-Sep</span>
    </div>
  </div>

  <div class="chart-card mt-8">
    <div class="eyebrow" style="color:var(--muted)">Pertumbuhan Tahunan Rata-rata 2021-2025</div>
    <h3 class="serif-display text-xl mt-1 mb-4">Top 20 Kelurahan</h3>
    <div id="chart-ntl-top20" style="height:560px;"></div>
  </div>

  <div class="chart-card mt-8">
    <div class="eyebrow" style="color:var(--muted)">Indikator Tren Terkini</div>
    <h3 class="serif-display text-xl mt-1 mb-4">Sinyal Awal 2026 per Wilayah</h3>
    <div id="pulse-table"></div>
    <div class="chart-footer">
      <span><span class="label">Indikator</span>Perubahan tahunan luminositas malam awal 2026 vs awal 2025</span>
    </div>
  </div>
</section>
"""

# Page 3 — Aktivitas Komersial
PAGE_AKTIVITAS = """
<section x-show="page === 'aktivitas-komersial'">
  <div class="rule-top pt-8">
    <span class="badge"><span class="badge-dot"></span>Aktivitas Komersial Mikro</span>
    <div class="eyebrow-roman mt-3">III. Tempat Usaha &amp; Gaya Hidup</div>
    <h2 class="serif-display text-3xl mt-2 max-w-3xl">Kepadatan dan keberagaman tempat usaha.</h2>
    <p class="mt-3 muted text-sm max-w-3xl">Podes BPS = jumlah tempat usaha (10 kategori). OpenStreetMap = titik gaya hidup di luar cakupan sensus formal.</p>
  </div>

  <div class="chart-card mt-8" style="position:relative;">
    <div class="layer-btn-group">
      <button :class="page3Layer==='podes' ? 'layer-btn active' : 'layer-btn'" @click="page3Layer='podes'; renderMap3()">Tempat Usaha (Podes)</button>
      <button :class="page3Layer==='heat' ? 'layer-btn active' : 'layer-btn'" @click="page3Layer='heat'; renderMap3()">Heatmap Gaya Hidup</button>
      <button :class="page3Layer==='cluster' ? 'layer-btn active' : 'layer-btn'" @click="page3Layer='cluster'; renderMap3()">Cluster Marker Gaya Hidup</button>
    </div>
    <div id="map-aktivitas" class="leaflet-map" style="position:relative;"></div>
    <div class="chart-footer">
      <span><span class="label">Sumber</span>Podes BPS 2025, OpenStreetMap snapshot 2026</span>
      <span><span class="label">Cakupan</span>270 kelurahan, 8.705 titik gaya hidup, 5.054 titik transportasi</span>
    </div>
  </div>

  <div class="chart-card mt-8">
    <div class="eyebrow" style="color:var(--muted)">Jumlah Tempat Usaha 2025</div>
    <h3 class="serif-display text-xl mt-1 mb-4">Top 10 Kelurahan</h3>
    <div id="chart-podes-top10" style="height:380px;"></div>
  </div>

  <div class="chart-card mt-8">
    <div class="eyebrow" style="color:var(--muted)">Indeks Aktivitas Komersial &mdash; Komposisi Sektor</div>
    <h3 class="serif-display text-xl mt-1 mb-4">Top 15 Kelurahan: Perdagangan vs Akomodasi &amp; Mamin</h3>
    <div id="chart-mag-stacked" style="height:520px;"></div>
    <div style="margin-top:10px;font-size:11px;color:var(--muted);font-style:italic;">Indeks proxy: jumlah usaha &times; rata-rata pendapatan pekerja sektor (Sakernas). Bukan klaim Rupiah absolut.</div>
  </div>

  <div class="chart-card mt-8">
    <div class="eyebrow" style="color:var(--muted)">Indeks Keberagaman Usaha (Shannon)</div>
    <h3 class="serif-display text-xl mt-1 mb-4">Top 15 Kelurahan Paling Beragam</h3>
    <div id="diversity-table"></div>
  </div>
</section>
"""

# Page 4 — Skor
PAGE_SKOR = """
<section x-show="page === 'skor-potensi'">
  <div class="rule-top pt-8">
    <span class="badge"><span class="badge-dot"></span>Skor Potensi &amp; Magnitude</span>
    <div class="eyebrow-roman mt-3">IV. Skor Komposit · Dekomposisi Komponen</div>
    <h2 class="serif-display text-3xl mt-2 max-w-3xl">Pertumbuhan vs kepadatan.</h2>
    <p class="mt-3 muted text-sm max-w-3xl"><strong>Skor Potensi</strong>: siapa yang sedang naik. <strong>Skor Magnitude</strong>: siapa yang sudah besar. Independen, saling melengkapi.</p>
  </div>

  <div class="tab-strip mt-8">
    <button @click="page4Tab='eczi'; $nextTick(()=>renderPage4Eczi(this))" :class="page4Tab==='eczi' ? 'tab-btn active' : 'tab-btn'">Skor Potensi (Pertumbuhan)</button>
    <button @click="page4Tab='magnitude'; $nextTick(()=>renderPage4Mag(this))" :class="page4Tab==='magnitude' ? 'tab-btn active' : 'tab-btn'">Skor Magnitude (Kepadatan)</button>
  </div>

  <div x-show="page4Tab==='eczi'">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div class="chart-card">
        <div class="eyebrow" style="color:var(--muted)">Profil Multi-Dimensi</div>
        <h3 class="serif-display text-xl mt-1 mb-3">Top 5 Wilayah &mdash; 5 Komponen Skor</h3>
        <div id="chart-radar" style="height:380px;"></div>
      </div>
      <div class="chart-card">
        <div class="eyebrow" style="color:var(--muted)">Posisi Strategis</div>
        <h3 class="serif-display text-xl mt-1 mb-3">Pertumbuhan Luminositas Malam vs Gaya Hidup</h3>
        <div id="chart-quadrant" style="height:380px;"></div>
      </div>
    </div>

    <div class="chart-card mt-6">
      <div class="eyebrow" style="color:var(--muted)">Peringkat Lengkap Skor Potensi</div>
      <h3 class="serif-display text-xl mt-1 mb-4">Tabel Lengkap (dapat diurutkan)</h3>
      <div style="overflow-x:auto;">
        <table class="score-table" id="table-eczi"></table>
      </div>
    </div>
  </div>

  <div x-show="page4Tab==='magnitude'">
    <div class="warning-box">
      <div class="wb-title">Catatan Wajib: Indeks Aktivitas Komersial &mdash; Proxy Index untuk Ranking</div>
      <div class="wb-text">
        Angka Rupiah ini = Jumlah Tempat Usaha (Podes) &times; Rata-rata Pendapatan Pekerja Sektor (Sakernas).
        Sakernas mengukur pendapatan PERSONAL pekerja per bulan (Rp 2-5 juta), BUKAN pendapatan per usaha.<br><br>
        Indeks ini valid untuk pembanding RELATIF antar wilayah, BUKAN klaim absolut Rupiah.
      </div>
    </div>

    <div class="chart-card">
      <div class="eyebrow" style="color:var(--muted)">Peringkat Skor Magnitude</div>
      <h3 class="serif-display text-xl mt-1 mb-4">Tabel Lengkap (dapat diurutkan)</h3>
      <div style="overflow-x:auto;">
        <table class="score-table" id="table-magnitude"></table>
      </div>
    </div>
  </div>
</section>
"""

# Page 5 — Detail
PAGE_DETAIL = """
<section x-show="page === 'detail-kawasan'">
  <div class="rule-top pt-8">
    <span class="badge"><span class="badge-dot"></span>Detail per Wilayah</span>
    <div class="eyebrow-roman mt-3">V. Profil Kawasan dan Kelurahan</div>
    <h2 class="serif-display text-3xl mt-2 max-w-3xl">Profil per wilayah.</h2>
    <p class="mt-3 muted text-sm max-w-3xl">Pilih 1 dari 21 wilayah berpotensi atau 270 kelurahan untuk membedah semua komponen skor.</p>
  </div>

  <div class="chart-card mt-8">
    <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
      <span class="filter-bar-label">Pilih wilayah atau kelurahan</span>
      <select
        @change="const v=$event.target.value; const [m,...rest]=v.split('::'); page5Mode=m; page5Selected=rest.join('::'); $nextTick(()=>renderPage5(this))"
        class="select-flat" style="font-size:14px;min-width:340px;flex:1;max-width:520px;">
        <optgroup label="Wilayah Berpotensi (21)">
          <template x-for="k in KAWASAN_DATA.map(x=>x.kawasan).sort()" :key="'k_'+k">
            <option :value="'kawasan::'+k" :selected="page5Mode==='kawasan' && page5Selected===k" x-text="k"></option>
          </template>
        </optgroup>
        <optgroup label="Kabupaten / Kota (6)">
          <template x-for="kk in [...new Set(DESA_DATA.map(x=>x.nama_kabkota))].sort()" :key="'kk_'+kk">
            <option :value="'kabkota::'+kk" :selected="page5Mode==='kabkota' && page5Selected===kk" x-text="kk"></option>
          </template>
        </optgroup>
        <optgroup label="Kecamatan (44)">
          <template x-for="kc in [...new Set(DESA_DATA.map(x=>x.nama_kecamatan))].sort()" :key="'kc_'+kc">
            <option :value="'kecamatan::'+kc" :selected="page5Mode==='kecamatan' && page5Selected===kc" x-text="kc"></option>
          </template>
        </optgroup>
        <optgroup label="Kelurahan / Desa (270)">
          <template x-for="d in DESA_DATA.map(x=>x.nama_desa).sort()" :key="'d_'+d">
            <option :value="'desa::'+d" :selected="page5Mode==='desa' && page5Selected===d" x-text="d"></option>
          </template>
        </optgroup>
      </select>
    </div>
  </div>

  <div id="page5-header" class="chart-card mt-6"></div>

  <div class="tab-strip mt-6">
    <button @click="page5SubTab='ntl'; $nextTick(()=>renderPage5Sub(this))" :class="page5SubTab==='ntl' ? 'tab-btn active' : 'tab-btn'">Luminositas Malam</button>
    <button @click="page5SubTab='podes'; $nextTick(()=>renderPage5Sub(this))" :class="page5SubTab==='podes' ? 'tab-btn active' : 'tab-btn'">Tempat Usaha</button>
    <button @click="page5SubTab='sektor'; $nextTick(()=>renderPage5Sub(this))" :class="page5SubTab==='sektor' ? 'tab-btn active' : 'tab-btn'">Sektor Usaha</button>
    <button @click="page5SubTab='fasilitas'; $nextTick(()=>renderPage5Sub(this))" :class="page5SubTab==='fasilitas' ? 'tab-btn active' : 'tab-btn'">Fasilitas Sekitar</button>
    <button @click="page5SubTab='akses'; $nextTick(()=>renderPage5Sub(this))" :class="page5SubTab==='akses' ? 'tab-btn active' : 'tab-btn'">Aksesibilitas</button>
  </div>

  <div id="page5-subcontent" class="chart-card"></div>
</section>
"""

# Page 6 — Metodologi
PAGE_METODOLOGI = """
<section x-show="page === 'metodologi'">
  <div class="rule-top pt-8">
    <span class="badge"><span class="badge-dot"></span>Metodologi</span>
    <div class="eyebrow-roman mt-3">VI. Cara Baca, Sumber, Bobot, Validasi</div>
    <h2 class="serif-display text-3xl mt-2 max-w-3xl">Cara skor dihitung dan batasannya.</h2>
    <p class="mt-3 muted text-sm max-w-3xl">Empat sumber data publik: NASA VIIRS, Podes BPS, Sakernas BPS, OpenStreetMap. Bobot komposit divalidasi empiris.</p>
  </div>

  <h3 class="serif-display text-xl mt-10 mb-3">A. Cara Membaca Dashboard</h3>
  <div class="chart-card">
    <table class="score-table">
      <thead><tr><th>Skor / Indikator</th><th>Apa yang Diukur</th><th>Cara Membaca</th></tr></thead>
      <tbody>
        <tr><td><strong>Skor Potensi</strong></td><td>Kekuatan sinyal pertumbuhan tahunan 2021-2025</td><td>Skor 0-100. Tinggi = sinyal pertumbuhan kuat dari multi-sumber.</td></tr>
        <tr><td><strong>Skor Magnitude</strong></td><td>Skala aktivitas komersial 2025</td><td>Skor 0-100. Tinggi = wilayah sudah padat aktivitas.</td></tr>
        <tr><td><strong>Tipe Kawasan</strong></td><td>Kombinasi pertumbuhan dan kepadatan</td><td><em>Emerging Hotspot</em> (tinggi keduanya), <em>Mature Commercial</em> (kepadatan tinggi, pertumbuhan moderat), <em>Early Growth</em> (kepadatan rendah, pertumbuhan tinggi), <em>Low Activity</em> (rendah keduanya).</td></tr>
        <tr><td><strong>Tren Terkini (2026)</strong></td><td>Sinyal awal 2026 dari luminositas malam</td><td><em>Pertumbuhan</em>, <em>Stabil</em>, <em>Perlambatan</em> &mdash; berdasarkan perubahan tahunan awal 2026 vs awal 2025.</td></tr>
      </tbody>
    </table>
  </div>

  <h3 class="serif-display text-xl mt-10 mb-3">B. Sumber Data</h3>
  <div class="chart-card">
    <table class="score-table">
      <thead><tr><th>Sumber</th><th>Peran</th><th>Granularity</th><th>Periode</th></tr></thead>
      <tbody>
        <tr><td>NASA VIIRS Luminositas Malam</td><td>Intensitas aktivitas spasial</td><td>270 kelurahan (173 nilai unik via spatial join)</td><td>2019-2025</td></tr>
        <tr><td>Podes BPS Sensus Usaha</td><td>Jumlah tempat usaha (10 kategori)</td><td>270 kelurahan (ground truth)</td><td>2018-2025</td></tr>
        <tr><td>Sakernas BPS</td><td>Pendapatan pekerja sektor</td><td>6 kabupaten/kota DKI</td><td>2021-2025</td></tr>
        <tr><td>OpenStreetMap</td><td>Visualisasi titik gaya hidup &amp; aksesibilitas</td><td>8.705 titik gaya hidup + 5.054 transportasi</td><td>Snapshot 2026</td></tr>
      </tbody>
    </table>
  </div>

  <h3 class="serif-display text-xl mt-10 mb-3">C. Skor Potensi &mdash; Formula dan Bobot</h3>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div class="chart-card">
      <div id="chart-weights" style="height:340px;"></div>
    </div>
    <div class="chart-card">
      <table class="score-table">
        <thead><tr><th>Komponen</th><th>Sub-Komponen</th><th>Bobot</th></tr></thead>
        <tbody>
          <tr><td rowspan="3"><strong>Luminositas Malam (24%)</strong></td><td>Pertumbuhan tahunan rata-rata</td><td class="num">13%</td></tr>
          <tr><td>Perubahan tahun terakhir</td><td class="num">7%</td></tr>
          <tr><td>Tingkat kecerahan 2025</td><td class="num">4%</td></tr>
          <tr><td rowspan="4"><strong>Tempat Usaha (33%)</strong></td><td>Pertumbuhan tahunan rata-rata</td><td class="num">13%</td></tr>
          <tr><td>Perubahan terakhir</td><td class="num">7%</td></tr>
          <tr><td>Jumlah 2025</td><td class="num">9%</td></tr>
          <tr><td>Indeks keberagaman</td><td class="num">4%</td></tr>
          <tr><td rowspan="2"><strong>Aktivitas Komersial (11%)</strong></td><td>Pertumbuhan</td><td class="num">6%</td></tr>
          <tr><td>Tingkat 2025</td><td class="num">5%</td></tr>
          <tr><td rowspan="4"><strong>Gaya Hidup (12%)</strong></td><td>Hiburan / nightlife</td><td class="num">4%</td></tr>
          <tr><td>Gaya hidup / wellness</td><td class="num">3%</td></tr>
          <tr><td>Retail khusus</td><td class="num">3%</td></tr>
          <tr><td>Wisata / budaya</td><td class="num">2%</td></tr>
          <tr><td rowspan="3"><strong>Aksesibilitas (20%)</strong></td><td>Akses transportasi</td><td class="num">12%</td></tr>
          <tr><td>Layanan penunjang</td><td class="num">5%</td></tr>
          <tr><td>Kepadatan tetangga</td><td class="num">3%</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <h3 class="serif-display text-xl mt-10 mb-3">D. Validasi Empiris</h3>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div class="chart-card">
      <div class="eyebrow" style="color:var(--muted)">Uji 1</div>
      <h4 class="serif-display text-lg mt-1 mb-3">Luminositas Malam vs Indeks Komersial</h4>
      <table class="score-table">
        <thead><tr><th>Korelasi</th><th class="num">Nilai</th></tr></thead>
        <tbody>
          <tr><td>Pearson r</td><td class="num">0,052</td></tr>
          <tr><td>Spearman r</td><td class="num">0,124</td></tr>
        </tbody>
      </table>
      <p style="font-size:13px;margin-top:12px;color:var(--ink);line-height:1.5;">Luminositas malam dan Indeks Komersial mengukur dimensi berbeda &mdash; keduanya wajib dipertahankan dalam composite.</p>
    </div>
    <div class="chart-card">
      <div class="eyebrow" style="color:var(--muted)">Uji 2</div>
      <h4 class="serif-display text-lg mt-1 mb-3">Titik OpenStreetMap vs Tempat Usaha Podes</h4>
      <table class="score-table">
        <thead><tr><th>Kategori</th><th class="num">Coverage</th><th class="num">r</th></tr></thead>
        <tbody>
          <tr><td>Pasar</td><td class="num">52,6%</td><td class="num">0,41</td></tr>
          <tr><td>Restoran</td><td class="num">33,2%</td><td class="num">0,38</td></tr>
          <tr><td>Minimarket</td><td class="num">17,8%</td><td class="num">0,25</td></tr>
          <tr><td>Kelompok Pertokoan</td><td class="num">9,4%</td><td class="num">0,22</td></tr>
          <tr><td>Warung Mamin</td><td class="num">4,6%</td><td class="num">0,17</td></tr>
        </tbody>
      </table>
      <p style="font-size:13px;margin-top:12px;color:var(--ink);line-height:1.5;">Coverage OpenStreetMap tidak merata (4,6%-52,6%). Podes BPS adalah ground truth jumlah usaha &mdash; OpenStreetMap dipakai untuk visualisasi titik dan kategori non-Podes.</p>
    </div>
  </div>

  <h3 class="serif-display text-xl mt-10 mb-3">E. Catatan Penting</h3>
  <div class="chart-card">
    <ol style="margin-left:20px;font-size:13px;line-height:1.7;color:var(--ink);">
      <li>Luminositas malam adalah proxy aktivitas spasial, bukan ukuran langsung PDRB atau transaksi.</li>
      <li><span style="color:var(--warning);">&#9888;</span> <strong>Sakernas mengukur pendapatan pekerja per bulan, bukan revenue per usaha.</strong> Jangan baca Indeks Aktivitas sebagai total Rupiah absolut.</li>
      <li>Spatial join VIIRS-kelurahan menghasilkan 173 nilai unik untuk 270 kelurahan; kelurahan kecil berbagi pixel.</li>
      <li>Podes BPS hanya mencakup 10 kategori usaha formal; tempat usaha gaya hidup informal sering luput.</li>
      <li>Indeks keberagaman Shannon dihitung dari 10 kategori Podes; nilai tinggi = mix sektor.</li>
      <li>Skor Potensi distandardisasi 0-100 per komponen sebelum di-bobot, sehingga tidak sensitif outlier ekstrem.</li>
      <li>Beberapa kelurahan dengan data podes ekstrem dilakukan winsorize di p1-p99 (lihat flag winsorize).</li>
      <li>Tren Terkini (2026) = perubahan tahunan luminositas malam awal 2026 vs awal 2025; sinyal awal, bukan kesimpulan tahun penuh.</li>
      <li>OpenStreetMap snapshot 2026 tidak retrospektif &mdash; tidak menggambarkan komposisi 2021.</li>
      <li><span style="color:var(--warning);">&#9888;</span> Indeks Aktivitas adalah proxy untuk peringkat relatif, bukan total revenue absolut.</li>
      <li>Reliability flag muncul ketika &lt;3 sub-komponen tersedia &mdash; baca skor wilayah tersebut dengan hati-hati.</li>
      <li><span style="color:var(--accent);">&#8635;</span> <strong>Sakernas avg revenue per kabkota di-update 4 Mei 2026 dengan filter UMKM v4 (berusaha-only, exclude pekerja/helper).</strong> Rata-rata pendapatan naik 41-194% per kabkota DKI. CAGR 2021-2025 mostly positive post-fix &mdash; sebelumnya sebagian negatif akibat over-count pekerja yang revenue=0. Lihat tabel filter UMKM di bawah.</li>
      <li><span style="color:var(--muted);">&#9432;</span> <strong>Granularitas Sakernas: resolusi kabkota&times;KBLI</strong> (12 kombinasi unik di DKI), di-spread homogen ke 267 desa. Efektif sebagai kabkota fixed effect &mdash; bukan data per desa.</li>
    </ol>
  </div>

  <h3 class="serif-display text-xl mt-10 mb-3">E.1 Filter UMKM Sakernas per Tahun</h3>
  <div class="chart-card">
    <p style="font-size:12px;color:var(--muted);margin-bottom:10px;">Filter berikut diterapkan untuk memastikan hanya pekerja UMKM yang berusaha sendiri yang diikutsertakan (UU No. 20/2008: total pekerja &lt; 100). Konsistensi antar-tahun dijaga meski variabel Sakernas berubah nama.</p>
    <table class="score-table">
      <thead>
        <tr>
          <th>Tahun</th>
          <th>Var Status Pekerjaan</th>
          <th>Filter Status</th>
          <th>Var Jenis Instansi</th>
          <th>Filter UMKM</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>2021</td><td>r12a</td><td>{1, 2, 3}</td><td>r18</td><td>{3, 4}</td></tr>
        <tr><td>2022</td><td>r13a</td><td>{1, 2, 3}</td><td>r19</td><td>{3, 4}</td></tr>
        <tr><td>2023</td><td>r13a</td><td>{1, 2, 3}</td><td>r20</td><td>{3, 4}</td></tr>
        <tr><td>2024</td><td>r14a</td><td>{1, 2, 3}</td><td>r21</td><td>{3, 4}</td></tr>
        <tr><td>2025</td><td>mjj_emprel</td><td>== 2 (berusaha)</td><td>mju_ins</td><td>{4, 5, 6, 7}</td></tr>
      </tbody>
    </table>
    <p style="font-size:11px;color:var(--muted);margin-top:8px;">Plus filter <code>total_pekerja &lt; 100</code> (definisi UMKM UU 20/2008) untuk semua tahun. Filter v4 (berusaha-only) menggantikan filter v3 yang over-count pekerja dan helper.</p>
  </div>

  <h3 class="serif-display text-xl mt-10 mb-3">F. Referensi Akademik</h3>
  <div id="ref-list"></div>

  <h3 class="serif-display text-xl mt-10 mb-3">G. Cadence Update Data</h3>
  <div class="chart-card">
    <table class="score-table">
      <thead><tr><th>Sumber</th><th>Frekuensi</th><th>Implikasi</th></tr></thead>
      <tbody>
        <tr><td>Luminositas Malam VIIRS</td><td>Bulanan (lag 2-4 minggu)</td><td>Refresh indikator Tren Terkini (2026)</td></tr>
        <tr><td>Podes BPS</td><td>Tahunan</td><td>Refresh composite Skor Potensi</td></tr>
        <tr><td>Sakernas BPS</td><td>Tahunan (Februari &amp; Agustus)</td><td>Refresh Indeks Aktivitas Komersial</td></tr>
        <tr><td>OpenStreetMap</td><td>Snapshot saat regenerate dashboard</td><td>Update peta titik gaya hidup &amp; transportasi</td></tr>
      </tbody>
    </table>
  </div>
</section>
"""


# -------------- Big JS block (data-agnostic) --------------

JS_FUNCTIONS = r"""
// ============ HELPERS ============
function fmtNum(v) {
  if (v === null || v === undefined || isNaN(v)) return '-';
  return Number(v).toLocaleString('id-ID');
}
function fmtPct(v, suffix) {
  if (v === null || v === undefined || isNaN(v)) return '-';
  const sign = v >= 0 ? '+' : '';
  const txt = (v * 100).toFixed(1).replace('.', ',');
  return sign + txt + '%' + (suffix || '');
}
function fmtScore(v) {
  if (v === null || v === undefined || isNaN(v)) return '-';
  return Number(v).toFixed(1).replace('.', ',');
}
function fmtRupiah(v) {
  if (v === null || v === undefined || isNaN(v) || v === 0) return '-';
  if (v >= 1e12) return 'Rp ' + (v / 1e12).toFixed(2).replace('.', ',') + ' triliun';
  if (v >= 1e9) return 'Rp ' + (v / 1e9).toFixed(2).replace('.', ',') + ' miliar';
  if (v >= 1e6) return 'Rp ' + (v / 1e6).toFixed(1).replace('.', ',') + ' juta';
  return 'Rp ' + Math.round(v).toLocaleString('id-ID');
}
function catClass(t) {
  if (!t) return 'cat-low';
  if (t.includes('Naik Daun')) return 'cat-hotspot';
  if (t.includes('Mapan')) return 'cat-mature';
  if (t.includes('Awal')) return 'cat-early';
  return 'cat-low';
}
function pulseClass(p) {
  if (!p) return 'pulse-na';
  if (p.includes('Lanjut')) return 'pulse-grow';
  if (p.includes('Melambat')) return 'pulse-slow';
  if (p.includes('Stabil')) return 'pulse-stable';
  return 'pulse-na';
}
// Map kategori raw -> display label (English noun phrase, agreed convention)
const KATEGORI_MAP = {
  'Kawasan Komersial Sedang Naik Daun': 'Emerging Hotspot',
  'Kawasan Komersial Mapan': 'Mature Commercial',
  'Awal Pertumbuhan': 'Early Growth',
  'Aktivitas Rendah': 'Low Activity'
};
function shortCat(t) {
  if (!t) return '-';
  if (KATEGORI_MAP[t]) return KATEGORI_MAP[t];
  if (t.includes('Naik Daun')) return 'Emerging Hotspot';
  if (t.includes('Mapan')) return 'Mature Commercial';
  if (t.includes('Awal')) return 'Early Growth';
  return 'Low Activity';
}
// Map pulse_badge raw -> display label
const PULSE_MAP = {
  'Trend Lanjut Tumbuh': 'Pertumbuhan',
  'Lanjut Tumbuh': 'Pertumbuhan',
  'Stabil': 'Stabil',
  'Mulai Melambat': 'Perlambatan'
};
function displayPulse(p) {
  if (!p) return '-';
  return PULSE_MAP[p] || p;
}

// ============ AGGREGATIONS ============
function aggregateKecamatan() {
  const map = {};
  DESA_DATA.forEach(d => {
    const key = (d.nama_kecamatan || '') + '|' + (d.nama_kabkota || '');
    if (!map[key]) map[key] = {
      nama_kec: d.nama_kecamatan, nama_kabkota: d.nama_kabkota,
      _n: 0, _ezsum: 0, _mgsum: 0, _ntlsum: 0, _pdsum: 0, _magsum: 0,
      podes_count_2025: 0, magnitude_2025: 0,
      magnitude_perdagangan_2025: 0, magnitude_akomamin_2025: 0,
      count_hiburan_nightlife: 0, count_gaya_hidup_wellness: 0,
      count_retail_khusus: 0, count_wisata_budaya: 0, count_layanan_penunjang: 0,
      transport_access_score_raw: 0, catchment_density_1km: 0,
    };
    const r = map[key];
    r._n++;
    r._ezsum += +d.eczi_score || 0;
    r._mgsum += +d.magnitude_score || 0;
    r._ntlsum += +d.ntl_cagr_2021_2025 || 0;
    r._pdsum += +d.podes_cagr_2021_2025 || 0;
    r.podes_count_2025 += +d.podes_count_2025 || 0;
    r.magnitude_2025 += +d.magnitude_2025 || 0;
    r.magnitude_perdagangan_2025 += +d.magnitude_perdagangan_2025 || 0;
    r.magnitude_akomamin_2025 += +d.magnitude_akomamin_2025 || 0;
    r.count_hiburan_nightlife += +d.count_hiburan_nightlife || 0;
    r.count_gaya_hidup_wellness += +d.count_gaya_hidup_wellness || 0;
    r.count_retail_khusus += +d.count_retail_khusus || 0;
    r.count_wisata_budaya += +d.count_wisata_budaya || 0;
    r.count_layanan_penunjang += +d.count_layanan_penunjang || 0;
    r.transport_access_score_raw += +d.transport_access_score_raw || 0;
    r.catchment_density_1km += +d.catchment_density_1km || 0;
  });
  return Object.values(map).map(r => {
    const ez = r._ezsum / r._n;
    return {
      nama_kec: r.nama_kec, nama_kabkota: r.nama_kabkota,
      eczi_score: ez,
      magnitude_score: r._mgsum / r._n,
      ntl_cagr_2021_2025: r._ntlsum / r._n,
      podes_cagr_2021_2025: r._pdsum / r._n,
      podes_count_2025: r.podes_count_2025,
      magnitude_2025: r.magnitude_2025,
      magnitude_perdagangan_2025: r.magnitude_perdagangan_2025,
      magnitude_akomamin_2025: r.magnitude_akomamin_2025,
      tipe_kawasan: ez >= 60 ? 'Kawasan Komersial Sedang Naik Daun' :
                    ez >= 50 ? 'Awal Pertumbuhan' :
                    ez >= 40 ? 'Kawasan Komersial Mapan' : 'Aktivitas Rendah',
    };
  });
}

function aggregateKabkota() {
  const map = {};
  DESA_DATA.forEach(d => {
    const key = d.nama_kabkota || '';
    if (!map[key]) map[key] = {
      nama_kabkota: d.nama_kabkota, _n: 0, _ezsum: 0, _mgsum: 0, _ntlsum: 0, _pdsum: 0,
      podes_count_2025: 0, magnitude_2025: 0,
      magnitude_perdagangan_2025: 0, magnitude_akomamin_2025: 0,
    };
    const r = map[key];
    r._n++;
    r._ezsum += +d.eczi_score || 0;
    r._mgsum += +d.magnitude_score || 0;
    r._ntlsum += +d.ntl_cagr_2021_2025 || 0;
    r._pdsum += +d.podes_cagr_2021_2025 || 0;
    r.podes_count_2025 += +d.podes_count_2025 || 0;
    r.magnitude_2025 += +d.magnitude_2025 || 0;
    r.magnitude_perdagangan_2025 += +d.magnitude_perdagangan_2025 || 0;
    r.magnitude_akomamin_2025 += +d.magnitude_akomamin_2025 || 0;
  });
  return Object.values(map).map(r => {
    const ez = r._ezsum / r._n;
    return {
      nama_kabkota: r.nama_kabkota,
      eczi_score: ez,
      magnitude_score: r._mgsum / r._n,
      ntl_cagr_2021_2025: r._ntlsum / r._n,
      podes_cagr_2021_2025: r._pdsum / r._n,
      podes_count_2025: r.podes_count_2025,
      magnitude_2025: r.magnitude_2025,
      magnitude_perdagangan_2025: r.magnitude_perdagangan_2025,
      magnitude_akomamin_2025: r.magnitude_akomamin_2025,
      tipe_kawasan: ez >= 60 ? 'Kawasan Komersial Sedang Naik Daun' :
                    ez >= 50 ? 'Awal Pertumbuhan' :
                    ez >= 40 ? 'Kawasan Komersial Mapan' : 'Aktivitas Rendah',
    };
  });
}

// ============ PLOTLY DEFAULTS ============
const PLOT_FONT = { family: 'Inter, system-ui, sans-serif', size: 12, color: '#051C2C' };
const PLOT_COLORS = {
  navy: '#003D79', navySoft: '#1A5394', sky: '#67B2E8', yellow: '#FFB700',
  orange: '#EA7200', positive: '#00875A', negative: '#C8102E', muted: '#667085'
};
function basePlotLayout(extra) {
  return Object.assign({
    margin: { l: 60, r: 24, t: 16, b: 50 },
    paper_bgcolor: 'white', plot_bgcolor: 'white',
    font: PLOT_FONT, hovermode: 'closest',
    xaxis: { gridcolor: '#E5E8EC', linecolor: '#D0D5DD', tickcolor: '#D0D5DD' },
    yaxis: { gridcolor: '#E5E8EC', linecolor: '#D0D5DD', tickcolor: '#D0D5DD' },
  }, extra || {});
}
const PLOT_CFG = { responsive: true, displayModeBar: false };

// ============ PAGE 1: RINGKASAN ============
function renderRingkasan(ctx) {
  const data = ctx.getCurrentData();
  // KPI cards
  const sortedEz = [...data].sort((a,b) => (b.eczi_score||0) - (a.eczi_score||0));
  const sortedMg = [...data].sort((a,b) => (b.magnitude_score||0) - (a.magnitude_score||0));
  const meanPodesCagr = data.reduce((s,d) => s + (+d.podes_cagr_2021_2025||0), 0) / Math.max(1, data.length);
  const totalPodes = data.reduce((s,d) => s + (+d.podes_count_2025||0), 0);
  const top1 = sortedEz[0] || {};
  const topMg = sortedMg[0] || {};
  const ezName = ctx.tier === 'kawasan' ? top1.kawasan :
                 ctx.tier === 'desa' ? top1.nama_desa :
                 ctx.tier === 'kecamatan' ? top1.nama_kec : top1.nama_kabkota;
  const mgName = ctx.tier === 'kawasan' ? topMg.kawasan :
                 ctx.tier === 'desa' ? topMg.nama_desa :
                 ctx.tier === 'kecamatan' ? topMg.nama_kec : topMg.nama_kabkota;
  const tierLabel = ctx.tier === 'kawasan' ? 'Wilayah Berpotensi' :
                    ctx.tier === 'desa' ? 'Kelurahan/Desa' :
                    ctx.tier === 'kecamatan' ? 'Kecamatan' : 'Kabupaten/Kota';

  document.getElementById('kpi-grid').innerHTML = `
    <div class="kpi-card kpi-navy">
      <div class="kpi-label">Wilayah Terdeteksi</div>
      <div class="kpi-val stat-num">${fmtNum(data.length)}</div>
      <div class="kpi-sub">${tierLabel}</div>
    </div>
    <div class="kpi-card kpi-sky">
      <div class="kpi-label">Periode Analisis</div>
      <div class="kpi-val">2021-2025</div>
      <div class="kpi-sub">4 tahun pertumbuhan</div>
    </div>
    <div class="kpi-card kpi-yellow">
      <div class="kpi-label">Skor Potensi #1</div>
      <div class="kpi-val">${ezName || '-'}</div>
      <div class="kpi-sub">Skor: <strong>${fmtScore(top1.eczi_score)}</strong></div>
    </div>
    <div class="kpi-card kpi-navy">
      <div class="kpi-label">Skor Magnitude #1</div>
      <div class="kpi-val">${mgName || '-'}</div>
      <div class="kpi-sub">Skor: <strong>${fmtScore(topMg.magnitude_score)}</strong></div>
    </div>
    <div class="kpi-card kpi-positive">
      <div class="kpi-label">Rata-rata Pertumbuhan Tempat Usaha</div>
      <div class="kpi-val stat-num">${fmtPct(meanPodesCagr, ' per tahun')}</div>
      <div class="kpi-sub">Pertumbuhan tahunan rata-rata 2021-2025</div>
    </div>
    <div class="kpi-card kpi-sky">
      <div class="kpi-label">Total Tempat Usaha 2025</div>
      <div class="kpi-val stat-num">${fmtNum(totalPodes)}</div>
      <div class="kpi-sub">Sumber: Sensus Podes BPS</div>
    </div>
  `;

  // Leaderboard
  const board = ctx.leaderTab === 'eczi' ? sortedEz : sortedMg;
  const top10 = board.slice(0, 10);
  const maxVal = ctx.leaderTab === 'eczi' ? (top10[0]?.eczi_score || 100) : (top10[0]?.magnitude_score || 100);
  let listHtml = '';
  top10.forEach((d, i) => {
    const v = ctx.leaderTab === 'eczi' ? d.eczi_score : d.magnitude_score;
    const name = ctx.tier === 'kawasan' ? d.kawasan :
                 ctx.tier === 'desa' ? d.nama_desa :
                 ctx.tier === 'kecamatan' ? d.nama_kec : d.nama_kabkota;
    const sub = ctx.tier === 'desa' ? `${d.nama_kecamatan || ''}, ${d.nama_kabkota || ''}` :
                ctx.tier === 'kawasan' ? d.kabkota :
                ctx.tier === 'kecamatan' ? d.nama_kabkota : '';
    const pct = (v / maxVal * 100);
    const pulse = d.pulse_badge ? `<span class="cat-pill ${pulseClass(d.pulse_badge)}" style="margin-left:6px;">${displayPulse(d.pulse_badge)}</span>` : '';
    listHtml += `
      <div class="rank-row">
        <div class="rank-num">${i+1}</div>
        <div>
          <div class="rank-name">${name || '-'} <span class="cat-pill ${catClass(d.tipe_kawasan)}" style="margin-left:6px;">${shortCat(d.tipe_kawasan)}</span>${pulse}</div>
          <div class="rank-sub">${sub || ''}</div>
          <div class="rank-bar-wrap"><div class="rank-bar" style="width:${pct}%"></div></div>
        </div>
        <div class="rank-cell-right">
          <div class="rank-val">${fmtScore(v)}</div>
        </div>
      </div>
    `;
  });
  document.getElementById('leaderboard-list').innerHTML = listHtml;

  // Sparkline NTL — use top 5 named NTL areas
  const top5Areas = ['SCBD/Sudirman', 'Kelapa Gading', 'PIK (Pantai Indah Kapuk)', 'Blok M', 'Mega Kuningan'];
  // mega kuningan not in NTL areas; substitute Thamrin
  const useAreas = ['SCBD/Sudirman','Kelapa Gading','PIK (Pantai Indah Kapuk)','Blok M','Thamrin'];
  const traces = useAreas.map((a, idx) => {
    const rows = NTL_ANNUAL.filter(r => r.area === a).sort((x,y) => x.year - y.year);
    return {
      x: rows.map(r => r.year), y: rows.map(r => r.lum_drySeason),
      type: 'scatter', mode: 'lines+markers', name: a,
      line: { width: 2, color: [PLOT_COLORS.navy, PLOT_COLORS.sky, PLOT_COLORS.yellow, PLOT_COLORS.orange, PLOT_COLORS.navySoft][idx] }
    };
  });
  Plotly.newPlot('ringkasan-spark', traces, basePlotLayout({
    margin: { l: 50, r: 24, t: 10, b: 40 },
    yaxis: { title: 'DNB Radiance', gridcolor: '#E5E8EC' },
    xaxis: { gridcolor: '#E5E8EC' },
    legend: { orientation: 'h', y: -0.2 }
  }), PLOT_CFG);
}

// ============ PAGE 2: CAHAYA MALAM ============
let _map2 = null, _map2Layer = null, _map2Lookup = {};
function initMap2() {
  if (_map2) return;
  _map2 = L.map('map-cahaya', { center: [-6.18, 106.83], zoom: 11, zoomControl: true, scrollWheelZoom: false });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { attribution: 'OSM, CARTO', maxZoom: 19 }).addTo(_map2);
  DESA_DATA.forEach(d => { _map2Lookup[d.desa_pcode] = d; });
}
function colorScale_cagr(v) {
  if (v === null || v === undefined || isNaN(v)) return '#F5F5F5';
  if (v >= 0.10) return '#7F2704';
  if (v >= 0.05) return '#D94801';
  if (v >= 0.02) return '#F16913';
  if (v >= 0.00) return '#FDAE6B';
  return '#FEE6CE';
}
function colorScale_level(v) {
  if (v === null || v === undefined || isNaN(v)) return '#F5F5F5';
  if (v >= 60) return '#003D79';
  if (v >= 40) return '#1A5394';
  if (v >= 20) return '#67B2E8';
  if (v >= 10) return '#A9C4DF';
  return '#E5E8EC';
}
function renderMap2() {
  initMap2();
  if (_map2Layer) _map2.removeLayer(_map2Layer);
  const mode = (typeof Alpine !== 'undefined' && Alpine.$data) ? null : null;
  const ctx = document.querySelector('[x-data]').__x.$data;
  const useLevel = ctx.map2Year === 'level';
  _map2Layer = L.geoJSON(GEOJSON, {
    style: function(f) {
      const d = _map2Lookup[f.properties.desa_pcode];
      const v = d ? (useLevel ? d.ntl_level_2025 : d.ntl_cagr_2021_2025) : null;
      return {
        fillColor: useLevel ? colorScale_level(v) : colorScale_cagr(v),
        weight: 0.5, color: 'white', fillOpacity: 0.78
      };
    },
    onEachFeature: function(f, lyr) {
      const d = _map2Lookup[f.properties.desa_pcode];
      if (!d) return;
      lyr.bindPopup(`
        <div style="font-family:Inter,sans-serif;font-size:12px;min-width:180px;">
          <div style="font-weight:700;font-size:13px;color:#003D79;">${d.nama_desa}</div>
          <div style="color:#667085;margin-bottom:6px;">${d.nama_kecamatan}, ${d.nama_kabkota}</div>
          <div>Pertumbuhan: <strong>${fmtPct(d.ntl_cagr_2021_2025, ' per tahun')}</strong></div>
          <div>Tingkat 2025: <strong>${fmtScore(d.ntl_level_2025)}</strong></div>
        </div>
      `);
    }
  }).addTo(_map2);

  // Update legend
  const oldLegend = document.querySelector('#map-cahaya .legend-box');
  if (oldLegend) oldLegend.remove();
  const legendDiv = document.createElement('div');
  legendDiv.className = 'legend-box';
  if (useLevel) {
    legendDiv.innerHTML = `
      <div style="font-weight:700;font-size:11px;margin-bottom:6px;">Tingkat Kecerahan 2025</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#003D79;"></span>≥ 60</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#1A5394;"></span>40 - 60</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#67B2E8;"></span>20 - 40</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#A9C4DF;"></span>10 - 20</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#E5E8EC;"></span>&lt; 10</div>
    `;
  } else {
    legendDiv.innerHTML = `
      <div style="font-weight:700;font-size:11px;margin-bottom:6px;">Pertumbuhan Tahunan</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#7F2704;"></span>≥ +10% / tahun</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#D94801;"></span>+5% s/d +10%</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#F16913;"></span>+2% s/d +5%</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#FDAE6B;"></span>0 s/d +2%</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#FEE6CE;"></span>negatif</div>
    `;
  }
  document.getElementById('map-cahaya').appendChild(legendDiv);
  setTimeout(() => _map2.invalidateSize(), 80);
}

function renderCahayaMalam(ctx) {
  renderMap2();
  // Time series: top 8 areas by 2025 lum
  const areas = [...new Set(NTL_ANNUAL.map(r => r.area))];
  const byArea = areas.map(a => ({
    area: a,
    last: (NTL_ANNUAL.filter(r => r.area === a && r.year === 2025)[0] || {}).lum_drySeason || 0
  })).sort((a,b) => b.last - a.last).slice(0, 8);
  const colors = [PLOT_COLORS.navy, PLOT_COLORS.sky, PLOT_COLORS.yellow, PLOT_COLORS.orange,
                  PLOT_COLORS.navySoft, PLOT_COLORS.positive, PLOT_COLORS.negative, PLOT_COLORS.muted];
  const traces = byArea.map((a, i) => {
    const rows = NTL_ANNUAL.filter(r => r.area === a.area).sort((x,y) => x.year - y.year);
    return { x: rows.map(r => r.year), y: rows.map(r => r.lum_drySeason),
             type: 'scatter', mode: 'lines+markers', name: a.area,
             line: { width: 2, color: colors[i] }, marker: { size: 5 } };
  });
  Plotly.newPlot('chart-ntl-timeseries', traces, basePlotLayout({
    yaxis: { title: 'DNB Radiance', gridcolor: '#E5E8EC' },
    xaxis: { gridcolor: '#E5E8EC' },
    legend: { orientation: 'h', y: -0.18 }
  }), PLOT_CFG);

  // Top 20 desa by NTL CAGR
  const sorted = [...DESA_DATA].sort((a,b) => (b.ntl_cagr_2021_2025||-Infinity) - (a.ntl_cagr_2021_2025||-Infinity)).slice(0, 20);
  Plotly.newPlot('chart-ntl-top20', [{
    type: 'bar', orientation: 'h',
    y: sorted.map(d => d.nama_desa).reverse(),
    x: sorted.map(d => (d.ntl_cagr_2021_2025||0)*100).reverse(),
    text: sorted.map(d => fmtPct(d.ntl_cagr_2021_2025, ' per tahun')).reverse(),
    textposition: 'outside',
    marker: { color: PLOT_COLORS.orange },
  }], basePlotLayout({
    margin: { l: 130, r: 90, t: 10, b: 40 },
    xaxis: { title: 'Pertumbuhan tahunan rata-rata (%)', gridcolor: '#E5E8EC' },
    yaxis: { tickfont: { size: 11 } }
  }), PLOT_CFG);

  // Pulse table
  const kawPulse = KAWASAN_DATA.filter(k => k.pulse_badge && k.pulse_badge !== 'tidak tersedia')
    .sort((a,b) => (b.pulse_yoy_2026||0) - (a.pulse_yoy_2026||0));
  let html = '<table class="score-table"><thead><tr><th>Wilayah</th><th>Kab/Kota</th><th>Tren Terkini (2026)</th><th class="num">Perubahan Tahunan</th></tr></thead><tbody>';
  kawPulse.forEach(k => {
    html += `<tr>
      <td><strong>${k.kawasan}</strong></td>
      <td>${k.kabkota || '-'}</td>
      <td><span class="cat-pill ${pulseClass(k.pulse_badge)}">${displayPulse(k.pulse_badge)}</span></td>
      <td class="num">${k.pulse_yoy_2026 != null ? (k.pulse_yoy_2026 >= 0 ? '+' : '') + Number(k.pulse_yoy_2026).toFixed(2).replace('.',',') + '%' : '-'}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  document.getElementById('pulse-table').innerHTML = html;
}

// ============ PAGE 3: AKTIVITAS ============
let _map3 = null, _map3Layer = null;
function initMap3() {
  if (_map3) return;
  _map3 = L.map('map-aktivitas', { center: [-6.18, 106.83], zoom: 11, zoomControl: true, scrollWheelZoom: false });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { attribution: 'OSM, CARTO', maxZoom: 19 }).addTo(_map3);
}
function colorPodes(v) {
  if (v === null || v === undefined || isNaN(v)) return '#F5F5F5';
  if (v >= 200) return '#003D79';
  if (v >= 100) return '#1A5394';
  if (v >= 50) return '#67B2E8';
  if (v >= 20) return '#A9C4DF';
  return '#E5E8EC';
}
function renderMap3() {
  initMap3();
  if (!_map3) return;  // init may have failed (Leaflet not loaded etc.)
  if (_map3Layer) {
    try { _map3.removeLayer(_map3Layer); } catch (e) {}
    _map3Layer = null;
  }
  // Alpine v3 API (we load v3, not v2) — `__x.$data` is v2 and would throw "undefined"
  let ctx = {};
  try {
    const root = document.querySelector('[x-data]');
    if (root && typeof Alpine !== 'undefined' && Alpine.$data) ctx = Alpine.$data(root) || {};
    else if (root && root._x_dataStack) ctx = root._x_dataStack[0] || {};
  } catch (e) {}
  const layer = ctx.page3Layer || 'podes';
  if (layer === 'podes') {
    _map3Layer = L.geoJSON(GEOJSON, {
      style: f => {
        const d = _map2Lookup[f.properties.desa_pcode];
        return { fillColor: colorPodes(d ? d.podes_count_2025 : null), weight: 0.5, color: 'white', fillOpacity: 0.78 };
      },
      onEachFeature: (f, lyr) => {
        const d = _map2Lookup[f.properties.desa_pcode];
        if (!d) return;
        lyr.bindPopup(`<div style="font-family:Inter;font-size:12px;"><strong style="color:#003D79;">${d.nama_desa}</strong><br>${d.nama_kecamatan}<br>Tempat usaha: <strong>${fmtNum(d.podes_count_2025)}</strong><br>Keberagaman: ${fmtScore(d.podes_diversity_shannon)}</div>`);
      }
    }).addTo(_map3);
  } else if (layer === 'heat') {
    const pts = OSM_POI.map(p => [p[0], p[1], 0.5]);
    _map3Layer = L.heatLayer(pts, { radius: 18, blur: 22, maxZoom: 17, gradient: { 0.2: '#67B2E8', 0.5: '#FFB700', 0.8: '#EA7200', 1.0: '#C8102E' } }).addTo(_map3);
  } else if (layer === 'cluster') {
    const cluster = L.markerClusterGroup({ maxClusterRadius: 50, disableClusteringAtZoom: 16 });
    OSM_POI.forEach(p => {
      const m = L.circleMarker([p[0], p[1]], { radius: 4, color: '#003D79', fillColor: '#67B2E8', fillOpacity: 0.7, weight: 1 });
      m.bindPopup(`<div style="font-family:Inter;font-size:12px;">Kategori: <strong>${p[2]}</strong></div>`);
      cluster.addLayer(m);
    });
    _map3.addLayer(cluster);
    _map3Layer = cluster;
  }
  // Legend
  const oldLegend = document.querySelector('#map-aktivitas .legend-box');
  if (oldLegend) oldLegend.remove();
  const ld = document.createElement('div');
  ld.className = 'legend-box';
  if (layer === 'podes') {
    ld.innerHTML = `<div style="font-weight:700;font-size:11px;margin-bottom:6px;">Jumlah Tempat Usaha 2025</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#003D79;"></span>≥ 200</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#1A5394;"></span>100 - 200</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#67B2E8;"></span>50 - 100</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#A9C4DF;"></span>20 - 50</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#E5E8EC;"></span>&lt; 20</div>`;
  } else if (layer === 'heat') {
    ld.innerHTML = `<div style="font-weight:700;font-size:11px;margin-bottom:6px;">Densitas Gaya Hidup</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#67B2E8;"></span>Rendah</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#FFB700;"></span>Sedang</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#EA7200;"></span>Tinggi</div>
      <div class="legend-row"><span class="legend-swatch" style="background:#C8102E;"></span>Sangat Tinggi</div>`;
  } else {
    ld.innerHTML = `<div style="font-weight:700;font-size:11px;margin-bottom:6px;">Cluster Marker</div>
      <div style="font-size:11px;color:#667085;">8.705 titik gaya hidup OSM. Klik cluster untuk zoom.</div>`;
  }
  document.getElementById('map-aktivitas').appendChild(ld);
  setTimeout(() => _map3.invalidateSize(), 80);
}

function renderAktivitasKomersial(ctx) {
  renderMap3();
  // Top 10 podes
  const top10 = [...DESA_DATA].sort((a,b) => (b.podes_count_2025||0) - (a.podes_count_2025||0)).slice(0, 10);
  Plotly.newPlot('chart-podes-top10', [{
    type: 'bar', orientation: 'h',
    y: top10.map(d => d.nama_desa).reverse(),
    x: top10.map(d => d.podes_count_2025||0).reverse(),
    text: top10.map(d => fmtNum(d.podes_count_2025)).reverse(),
    textposition: 'outside',
    marker: { color: PLOT_COLORS.navy }
  }], basePlotLayout({
    margin: { l: 130, r: 70, t: 10, b: 40 },
    xaxis: { title: 'Jumlah Tempat Usaha 2025', gridcolor: '#E5E8EC' }
  }), PLOT_CFG);

  // Top 15 stacked
  const top15 = [...DESA_DATA].sort((a,b) => (b.magnitude_2025||0) - (a.magnitude_2025||0)).slice(0, 15);
  const labels = top15.map(d => d.nama_desa).reverse();
  Plotly.newPlot('chart-mag-stacked', [
    { type: 'bar', orientation: 'h', name: 'Perdagangan',
      y: labels, x: top15.map(d => d.magnitude_perdagangan_2025||0).reverse(),
      marker: { color: PLOT_COLORS.navy }
    },
    { type: 'bar', orientation: 'h', name: 'Akomodasi & Mamin',
      y: labels, x: top15.map(d => d.magnitude_akomamin_2025||0).reverse(),
      marker: { color: PLOT_COLORS.yellow }
    }
  ], basePlotLayout({
    barmode: 'stack',
    margin: { l: 130, r: 30, t: 10, b: 60 },
    xaxis: { title: 'Indeks Aktivitas Komersial 2025 (proxy)', gridcolor: '#E5E8EC' },
    legend: { orientation: 'h', y: -0.12 }
  }), PLOT_CFG);

  // Diversity table
  const div15 = [...DESA_DATA].sort((a,b) => (b.podes_diversity_shannon||0) - (a.podes_diversity_shannon||0)).slice(0, 15);
  let html = '<table class="score-table"><thead><tr><th>Kelurahan</th><th>Kab/Kota</th><th class="num">Indeks Keberagaman</th><th class="num">Jumlah Usaha</th><th>Kategori</th></tr></thead><tbody>';
  div15.forEach(d => {
    html += `<tr>
      <td><strong>${d.nama_desa}</strong></td>
      <td>${d.nama_kabkota}</td>
      <td class="num">${fmtScore(d.podes_diversity_shannon)}</td>
      <td class="num">${fmtNum(d.podes_count_2025)}</td>
      <td><span class="cat-pill ${catClass(d.tipe_kawasan)}">${shortCat(d.tipe_kawasan)}</span></td>
    </tr>`;
  });
  html += '</tbody></table>';
  document.getElementById('diversity-table').innerHTML = html;
}

// ============ PAGE 4: SKOR ============
function renderSkorPotensi(ctx) {
  if (ctx.page4Tab === 'eczi') renderPage4Eczi(ctx);
  else renderPage4Mag(ctx);
}
function renderPage4Eczi(ctx) {
  const data = ctx.getCurrentData();
  // Radar — top 5
  const top5 = [...data].sort((a,b) => (b.eczi_score||0) - (a.eczi_score||0)).slice(0, 5);
  const cats = ['Luminositas Malam','Tempat Usaha','Aktivitas Komersial','Gaya Hidup','Aksesibilitas'];
  const colors = [PLOT_COLORS.navy, PLOT_COLORS.sky, PLOT_COLORS.yellow, PLOT_COLORS.orange, PLOT_COLORS.positive];
  const traces = top5.map((d, i) => {
    let g1, g2, g3, g4, g5;
    if (ctx.tier === 'kawasan') {
      g1 = d.g1_cahaya_malam; g2 = d.g2_tempat_usaha; g3 = d.g3_magnitude; g4 = d.g4_gaya_hidup; g5 = d.g5_aksesibilitas;
    } else {
      g1 = d.g1; g2 = d.g2; g3 = d.g3; g4 = d.g4; g5 = d.g5;
    }
    const name = ctx.tier === 'kawasan' ? d.kawasan :
                 ctx.tier === 'desa' ? d.nama_desa :
                 ctx.tier === 'kecamatan' ? d.nama_kec : d.nama_kabkota;
    const vals = [g1, g2, g3, g4, g5].map(v => v == null ? 0 : v);
    return {
      type: 'scatterpolar', name: name,
      r: vals.concat([vals[0]]), theta: cats.concat([cats[0]]),
      fill: 'toself', opacity: 0.55,
      line: { color: colors[i], width: 2 },
      marker: { color: colors[i] }
    };
  });
  Plotly.newPlot('chart-radar', traces, {
    polar: { radialaxis: { visible: true, range: [0, 100], gridcolor: '#E5E8EC' }, angularaxis: { gridcolor: '#E5E8EC' } },
    margin: { l: 30, r: 30, t: 10, b: 30 },
    paper_bgcolor: 'white', font: PLOT_FONT,
    legend: { orientation: 'h', y: -0.05, font: { size: 10 } }
  }, PLOT_CFG);

  // Quadrant scatter — desa-level (always 270)
  const desa = DESA_DATA;
  const xs = desa.map(d => d.g1 || 0);
  const ys = desa.map(d => d.g4 || 0);
  const xMed = [...xs].sort((a,b) => a-b)[Math.floor(xs.length/2)];
  const yMed = [...ys].sort((a,b) => a-b)[Math.floor(ys.length/2)];
  const colorMap = { 'Kawasan Komersial Sedang Naik Daun': PLOT_COLORS.negative, 'Kawasan Komersial Mapan': PLOT_COLORS.navy,
                     'Awal Pertumbuhan': PLOT_COLORS.yellow, 'Aktivitas Rendah': PLOT_COLORS.muted };
  const cols = desa.map(d => colorMap[d.tipe_kawasan] || PLOT_COLORS.muted);
  const labels = desa.map(d => `${d.nama_desa}<br>Skor Potensi: ${fmtScore(d.eczi_score)}`);
  Plotly.newPlot('chart-quadrant', [{
    type: 'scatter', mode: 'markers',
    x: xs, y: ys,
    marker: { size: 8, color: cols, opacity: 0.7, line: { width: 0.5, color: 'white' } },
    text: labels, hovertemplate: '%{text}<extra></extra>'
  }], basePlotLayout({
    margin: { l: 60, r: 24, t: 20, b: 60 },
    xaxis: { title: 'Skor Pertumbuhan Luminositas Malam (0-100)', gridcolor: '#E5E8EC', range: [0, 100] },
    yaxis: { title: 'Skor Gaya Hidup (0-100)', gridcolor: '#E5E8EC', range: [0, 100] },
    shapes: [
      { type: 'line', x0: xMed, x1: xMed, y0: 0, y1: 100, line: { color: '#D0D5DD', width: 1, dash: 'dash' } },
      { type: 'line', x0: 0, x1: 100, y0: yMed, y1: yMed, line: { color: '#D0D5DD', width: 1, dash: 'dash' } },
    ],
    annotations: [
      { x: 95, y: 95, text: 'Emerging Hotspot &<br>Gaya Hidup Tinggi', showarrow: false, font: { size: 9, color: '#667085' }, align: 'right' },
      { x: 5, y: 95, text: 'Gaya Hidup<br>Tinggi', showarrow: false, font: { size: 9, color: '#667085' }, align: 'left' },
      { x: 95, y: 5, text: 'Pertumbuhan<br>Luminositas Tinggi', showarrow: false, font: { size: 9, color: '#667085' }, align: 'right' },
      { x: 5, y: 5, text: 'Aktivitas<br>Rendah', showarrow: false, font: { size: 9, color: '#667085' }, align: 'left' }
    ]
  }), PLOT_CFG);

  // Eczi table
  const sorted = [...data].sort((a,b) => (b.eczi_score||0) - (a.eczi_score||0));
  let html = '<thead><tr><th onclick="sortTable(\'eczi\',\'rank\')">#</th>';
  if (ctx.tier === 'kawasan') html += '<th>Wilayah</th><th>Kab/Kota</th>';
  else if (ctx.tier === 'desa') html += '<th>Kelurahan</th><th>Kab/Kota</th>';
  else if (ctx.tier === 'kecamatan') html += '<th>Kecamatan</th><th>Kab/Kota</th>';
  else html += '<th>Kabupaten/Kota</th><th></th>';
  html += '<th class="num">Skor Potensi</th><th class="num">Luminositas Malam</th><th class="num">Tempat Usaha</th><th class="num">Aktivitas Komersial</th><th class="num">Gaya Hidup</th><th class="num">Aksesibilitas</th><th>Kategori</th><th>Tren Terkini (2026)</th></tr></thead><tbody>';
  sorted.forEach((d, i) => {
    let g1, g2, g3, g4, g5;
    if (ctx.tier === 'kawasan') { g1=d.g1_cahaya_malam; g2=d.g2_tempat_usaha; g3=d.g3_magnitude; g4=d.g4_gaya_hidup; g5=d.g5_aksesibilitas; }
    else { g1=d.g1; g2=d.g2; g3=d.g3; g4=d.g4; g5=d.g5; }
    const name = ctx.tier === 'kawasan' ? d.kawasan : ctx.tier === 'desa' ? d.nama_desa : ctx.tier === 'kecamatan' ? d.nama_kec : d.nama_kabkota;
    const sub = ctx.tier === 'kawasan' ? d.kabkota : ctx.tier === 'desa' ? d.nama_kabkota : ctx.tier === 'kecamatan' ? d.nama_kabkota : '';
    const pulse = d.pulse_badge ? `<span class="cat-pill ${pulseClass(d.pulse_badge)}">${displayPulse(d.pulse_badge)}</span>` : '-';
    html += `<tr>
      <td>${i+1}</td>
      <td><strong>${name}</strong></td>
      <td>${sub || ''}</td>
      <td class="num"><strong>${fmtScore(d.eczi_score)}</strong></td>
      <td class="num">${fmtScore(g1)}</td>
      <td class="num">${fmtScore(g2)}</td>
      <td class="num">${fmtScore(g3)}</td>
      <td class="num">${fmtScore(g4)}</td>
      <td class="num">${fmtScore(g5)}</td>
      <td><span class="cat-pill ${catClass(d.tipe_kawasan)}">${shortCat(d.tipe_kawasan)}</span></td>
      <td>${pulse}</td>
    </tr>`;
  });
  html += '</tbody>';
  document.getElementById('table-eczi').innerHTML = html;
}
function renderPage4Mag(ctx) {
  const data = ctx.getCurrentData();
  const sorted = [...data].sort((a,b) => (b.magnitude_score||0) - (a.magnitude_score||0));
  let html = '<thead><tr><th>#</th>';
  if (ctx.tier === 'kawasan') html += '<th>Wilayah</th><th>Kab/Kota</th>';
  else if (ctx.tier === 'desa') html += '<th>Kelurahan</th><th>Kab/Kota</th>';
  else if (ctx.tier === 'kecamatan') html += '<th>Kecamatan</th><th>Kab/Kota</th>';
  else html += '<th>Kabupaten/Kota</th><th></th>';
  html += '<th class="num">Skor Magnitude</th><th class="num">Indeks Aktivitas 2025</th><th class="num">Jumlah Tempat Usaha</th><th>Tipe Kawasan</th></tr></thead><tbody>';
  sorted.forEach((d, i) => {
    const name = ctx.tier === 'kawasan' ? d.kawasan : ctx.tier === 'desa' ? d.nama_desa : ctx.tier === 'kecamatan' ? d.nama_kec : d.nama_kabkota;
    const sub = ctx.tier === 'kawasan' ? d.kabkota : ctx.tier === 'desa' ? d.nama_kabkota : ctx.tier === 'kecamatan' ? d.nama_kabkota : '';
    const mag = ctx.tier === 'kawasan' ? d.magnitude_total : d.magnitude_2025;
    const podes = ctx.tier === 'kawasan' ? d.podes_count_total : d.podes_count_2025;
    const flag = d.low_reliability_flag ? '<span title="Reliability rendah" style="color:var(--warning);">&#9888;</span>' : '';
    html += `<tr>
      <td>${i+1}</td>
      <td><strong>${name}</strong> ${flag}</td>
      <td>${sub || ''}</td>
      <td class="num"><strong>${fmtScore(d.magnitude_score)}</strong></td>
      <td class="num">${fmtRupiah(mag)}</td>
      <td class="num">${fmtNum(podes)}</td>
      <td><span class="cat-pill ${catClass(d.tipe_kawasan)}">${shortCat(d.tipe_kawasan)}</span></td>
    </tr>`;
  });
  html += '</tbody>';
  document.getElementById('table-magnitude').innerHTML = html;
}

// ============ PAGE 5: DETAIL ============
function getPage5Item(ctx) {
  if (ctx.page5Mode === 'kawasan') {
    return KAWASAN_DATA.find(k => k.kawasan === ctx.page5Selected);
  }
  if (ctx.page5Mode === 'kabkota') {
    // Aggregate kabkota on-the-fly from member desa
    const members = DESA_DATA.filter(d => d.nama_kabkota === ctx.page5Selected);
    if (!members.length) return null;
    return aggregateGroup(members, ctx.page5Selected, 'Kabupaten/Kota');
  }
  if (ctx.page5Mode === 'kecamatan') {
    const members = DESA_DATA.filter(d => d.nama_kecamatan === ctx.page5Selected);
    if (!members.length) return null;
    return aggregateGroup(members, ctx.page5Selected, 'Kecamatan');
  }
  return DESA_DATA.find(d => d.nama_desa === ctx.page5Selected);
}
function aggregateGroup(members, name, tier_label) {
  const mean = (k) => {
    const vals = members.map(m => m[k]).filter(v => v !== null && v !== undefined && !isNaN(v));
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  };
  // Mode tipe_kawasan
  const tipeCount = {};
  members.forEach(m => { if (m.tipe_kawasan) tipeCount[m.tipe_kawasan] = (tipeCount[m.tipe_kawasan]||0) + 1; });
  const tipeMode = Object.entries(tipeCount).sort((a,b) => b[1]-a[1])[0]?.[0] || null;
  const pulseCount = {};
  members.forEach(m => { if (m.pulse_badge) pulseCount[m.pulse_badge] = (pulseCount[m.pulse_badge]||0) + 1; });
  const pulseMode = Object.entries(pulseCount).sort((a,b) => b[1]-a[1])[0]?.[0] || null;
  return {
    kawasan: name,
    nama_desa: name,
    nama_kabkota: tier_label === 'Kabupaten/Kota' ? name : (members[0]?.nama_kabkota || ''),
    nama_kecamatan: tier_label === 'Kecamatan' ? name : '',
    deskripsi: `Agregasi ${members.length} kelurahan`,
    tier_label: tier_label,
    member_desas: members.map(m => m.nama_desa),
    tipe_kawasan: tipeMode,
    pulse_badge: pulseMode,
    eczi_score: mean('eczi_score'),
    magnitude_score: mean('magnitude_score'),
    g1: mean('g1'), g2: mean('g2'), g3: mean('g3'), g4: mean('g4'), g5: mean('g5'),
    podes_count_2025: mean('podes_count_2025'),
    podes_cagr_2021_2025: mean('podes_cagr_2021_2025'),
    podes_diversity_shannon: mean('podes_diversity_shannon'),
    ntl_cagr_2021_2025: mean('ntl_cagr_2021_2025'),
    ntl_level_2025: mean('ntl_level_2025'),
    lum_2021: mean('lum_2021'), lum_2024: mean('lum_2024'), lum_2025: mean('lum_2025'),
    magnitude_2025: mean('magnitude_2025'),
    transport_access_score_raw: mean('transport_access_score_raw'),
    catchment_density_1km: mean('catchment_density_1km'),
    count_hiburan_nightlife: mean('count_hiburan_nightlife'),
    count_gaya_hidup_wellness: mean('count_gaya_hidup_wellness'),
    count_retail_khusus: mean('count_retail_khusus'),
    count_wisata_budaya: mean('count_wisata_budaya'),
    count_layanan_penunjang: mean('count_layanan_penunjang'),
  };
}
function renderPage5(ctx) {
  const item = getPage5Item(ctx);
  if (!item) return;
  const isKaw = ctx.page5Mode === 'kawasan';
  const name = isKaw ? item.kawasan : item.nama_desa;
  const sub = isKaw ? item.kabkota : `${item.nama_kecamatan}, ${item.nama_kabkota}`;
  const desc = isKaw ? (item.deskripsi || '') : '';
  const pulse = item.pulse_badge ? `<span class="cat-pill ${pulseClass(item.pulse_badge)}" style="margin-left:8px;">${displayPulse(item.pulse_badge)}</span>` : '';
  document.getElementById('page5-header').innerHTML = `
    <div class="eyebrow" style="color:var(--muted);">${isKaw ? 'Wilayah Berpotensi' : 'Kelurahan'}</div>
    <h2 class="serif-display text-3xl mt-1">${name}</h2>
    <div class="muted" style="margin-top:4px;font-size:13px;">${sub}</div>
    <div style="margin-top:10px;">
      <span class="cat-pill ${catClass(item.tipe_kawasan)}">${shortCat(item.tipe_kawasan)}</span>
      ${pulse}
    </div>
    ${desc ? `<p style="margin-top:14px;font-style:italic;color:var(--ink);font-size:14px;line-height:1.5;">${desc}</p>` : ''}
    <div class="grid grid-cols-2 gap-4 mt-6">
      <div style="border-left:3px solid var(--navy);padding-left:14px;">
        <div class="eyebrow" style="color:var(--muted);">Skor Potensi</div>
        <div class="stat-num" style="font-size:42px;color:var(--navy);">${fmtScore(item.eczi_score)}</div>
      </div>
      <div style="border-left:3px solid var(--yellow);padding-left:14px;">
        <div class="eyebrow" style="color:var(--muted);">Skor Magnitude</div>
        <div class="stat-num" style="font-size:42px;color:var(--ink);">${fmtScore(item.magnitude_score)}</div>
      </div>
    </div>
  `;
  renderPage5Sub(ctx);
}
function renderPage5Sub(ctx) {
  const item = getPage5Item(ctx);
  if (!item) return;
  const isKaw = ctx.page5Mode === 'kawasan';
  const sub = ctx.page5SubTab;
  const c = document.getElementById('page5-subcontent');

  if (sub === 'ntl') {
    const lum2021 = isKaw ? null : item.lum_2021;
    const lum2024 = isKaw ? null : item.lum_2024;
    const lum2025 = isKaw ? null : item.lum_2025;
    const cagr = item.ntl_cagr_2021_2025;
    const qual = item.quality_flag;
    c.innerHTML = `
      <div class="eyebrow" style="color:var(--muted);">Luminositas Malam</div>
      <h3 class="serif-display text-xl mt-1 mb-3">Lintasan ${isKaw ? 'gabungan member' : 'kelurahan'}</h3>
      ${isKaw ? `<div style="font-size:13px;color:var(--muted);margin-bottom:16px;">Pertumbuhan tahunan rata-rata wilayah: <strong style="color:var(--ink);">${fmtPct(cagr, ' per tahun')}</strong></div>` :
        `<div id="page5-ntl-bar" style="height:240px;"></div>
        <div style="font-size:13px;color:var(--muted);margin-top:14px;">Pertumbuhan tahunan rata-rata: <strong style="color:var(--ink);">${fmtPct(cagr, ' per tahun')}</strong>${qual ? ` &middot; Quality flag: <em>${qual}</em>` : ''}</div>`}
      <div style="margin-top:14px;">
        ${item.pulse_badge ? `<span class="cat-pill ${pulseClass(item.pulse_badge)}">Tren Terkini (2026): ${displayPulse(item.pulse_badge)}</span>` : ''}
      </div>
    `;
    if (!isKaw) {
      Plotly.newPlot('page5-ntl-bar', [{
        type: 'bar',
        x: ['2021', '2024', '2025'],
        y: [lum2021, lum2024, lum2025],
        text: [lum2021, lum2024, lum2025].map(v => v == null ? '-' : Number(v).toFixed(1).replace('.',',')),
        textposition: 'outside',
        marker: { color: [PLOT_COLORS.muted, PLOT_COLORS.sky, PLOT_COLORS.navy] }
      }], basePlotLayout({
        margin: { l: 50, r: 24, t: 20, b: 40 },
        yaxis: { title: 'DNB Radiance', gridcolor: '#E5E8EC' }
      }), PLOT_CFG);
    }
  }
  else if (sub === 'podes') {
    const cnt = isKaw ? item.podes_count_total : item.podes_count_2025;
    const cagr = item.podes_cagr_2021_2025;
    const div = item.podes_diversity_shannon;
    const flag = item.podes_winsorize_flag;
    c.innerHTML = `
      <div class="eyebrow" style="color:var(--muted);">Tempat Usaha (Podes)</div>
      <h3 class="serif-display text-xl mt-1 mb-3">Skala dan Pertumbuhan</h3>
      <div id="page5-podes-bar" style="height:240px;"></div>
      <div style="font-size:13px;color:var(--ink);margin-top:14px;line-height:1.7;">
        Jumlah tempat usaha 2025: <strong>${fmtNum(cnt)}</strong><br>
        Pertumbuhan tahunan rata-rata: <strong>${fmtPct(cagr, ' per tahun')}</strong><br>
        Indeks keberagaman (Shannon): <strong>${fmtScore(div)}</strong>
        ${flag ? '<br><span style="color:var(--warning);">&#9888; Data podes diwinsorize (outlier ekstrem dipangkas).</span>' : ''}
      </div>
    `;
    Plotly.newPlot('page5-podes-bar', [{
      type: 'bar',
      x: ['Tempat Usaha 2025'],
      y: [cnt],
      text: [fmtNum(cnt)],
      textposition: 'outside',
      marker: { color: PLOT_COLORS.navy },
      width: [0.4]
    }], basePlotLayout({
      margin: { l: 50, r: 24, t: 30, b: 30 },
      yaxis: { gridcolor: '#E5E8EC' },
      annotations: [{ x: 0, y: cnt, text: fmtPct(cagr, ' per tahun'), showarrow: false, yshift: 30, font: { size: 13, color: PLOT_COLORS.positive } }]
    }), PLOT_CFG);
  }
  else if (sub === 'sektor') {
    const perd = isKaw ? null : item.magnitude_perdagangan_2025;
    const akm = isKaw ? null : item.magnitude_akomamin_2025;
    if (isKaw) {
      const total = item.magnitude_total;
      c.innerHTML = `
        <div class="eyebrow" style="color:var(--muted);">Sektor Usaha</div>
        <h3 class="serif-display text-xl mt-1 mb-3">Indeks Aktivitas Komersial Wilayah</h3>
        <div style="font-size:13px;color:var(--ink);">Total indeks aktivitas wilayah: <strong>${fmtRupiah(total)}</strong></div>
        <div style="font-size:11px;color:var(--muted);margin-top:8px;font-style:italic;">Indeks proxy: jumlah usaha &times; rata-rata pendapatan pekerja sektor (Sakernas). Bukan klaim Rupiah absolut.</div>
      `;
    } else {
      c.innerHTML = `
        <div class="eyebrow" style="color:var(--muted);">Sektor Usaha</div>
        <h3 class="serif-display text-xl mt-1 mb-3">Komposisi Indeks 2025</h3>
        <div id="page5-donut" style="height:300px;"></div>
        <div style="font-size:11px;color:var(--muted);margin-top:8px;font-style:italic;">Indeks proxy: jumlah usaha &times; rata-rata pendapatan pekerja sektor (Sakernas). Bukan klaim Rupiah absolut.</div>
      `;
      Plotly.newPlot('page5-donut', [{
        type: 'pie', hole: 0.55,
        labels: ['Perdagangan', 'Akomodasi & Mamin'],
        values: [perd || 0, akm || 0],
        marker: { colors: [PLOT_COLORS.navy, PLOT_COLORS.yellow] },
        textinfo: 'label+percent'
      }], { margin: { l: 20, r: 20, t: 20, b: 20 }, paper_bgcolor: 'white', font: PLOT_FONT, showlegend: false }, PLOT_CFG);
    }
  }
  else if (sub === 'fasilitas') {
    const cats = ['Hiburan / Nightlife', 'Gaya Hidup / Wellness', 'Retail Khusus', 'Wisata / Budaya', 'Layanan Penunjang'];
    const vals = [item.count_hiburan_nightlife, item.count_gaya_hidup_wellness, item.count_retail_khusus, item.count_wisata_budaya, item.count_layanan_penunjang].map(v => v || 0);
    c.innerHTML = `
      <div class="eyebrow" style="color:var(--muted);">Fasilitas Sekitar (OSM)</div>
      <h3 class="serif-display text-xl mt-1 mb-3">Komposisi Tempat Usaha Gaya Hidup</h3>
      <div id="page5-facil" style="height:280px;"></div>
    `;
    Plotly.newPlot('page5-facil', [{
      type: 'bar', orientation: 'h',
      y: cats.slice().reverse(), x: vals.slice().reverse(),
      text: vals.slice().reverse().map(v => fmtNum(v)),
      textposition: 'outside',
      marker: { color: PLOT_COLORS.sky }
    }], basePlotLayout({
      margin: { l: 160, r: 60, t: 10, b: 30 },
      xaxis: { gridcolor: '#E5E8EC' }
    }), PLOT_CFG);
  }
  else if (sub === 'akses') {
    const trans = item.transport_access_score_raw;
    const catch_ = isKaw ? item.catchment_density_1km_total : item.catchment_density_1km;
    c.innerHTML = `
      <div class="eyebrow" style="color:var(--muted);">Aksesibilitas</div>
      <h3 class="serif-display text-xl mt-1 mb-3">Akses Transportasi & Catchment</h3>
      <div id="page5-akses" style="height:240px;"></div>
    `;
    Plotly.newPlot('page5-akses', [{
      type: 'bar',
      x: ['Skor Akses Transportasi', 'Densitas Catchment 1km'],
      y: [trans || 0, catch_ || 0],
      text: [fmtScore(trans), fmtNum(catch_)],
      textposition: 'outside',
      marker: { color: [PLOT_COLORS.navy, PLOT_COLORS.orange] }
    }], basePlotLayout({
      margin: { l: 50, r: 24, t: 30, b: 40 },
      yaxis: { gridcolor: '#E5E8EC' }
    }), PLOT_CFG);
  }
}

// ============ PAGE 6: METODOLOGI ============
function renderMetodologi(ctx) {
  // Weights donut
  Plotly.newPlot('chart-weights', [{
    type: 'pie', hole: 0.45,
    labels: ['Luminositas Malam (24%)', 'Tempat Usaha (33%)', 'Aktivitas Komersial (11%)', 'Gaya Hidup (12%)', 'Aksesibilitas (20%)'],
    values: [24, 33, 11, 12, 20],
    marker: { colors: ['#003D79', '#1A5394', '#67B2E8', '#FFB700', '#EA7200'] },
    textinfo: 'label+percent', textposition: 'outside'
  }], { margin: { l: 30, r: 30, t: 20, b: 20 }, paper_bgcolor: 'white', font: PLOT_FONT, showlegend: false }, PLOT_CFG);

  // References
  const refs = [
    { id: 'R1', cit: 'Henderson, J. V., Storeygard, A., & Weil, D. N. (2012). Measuring Economic Growth from Outer Space. American Economic Review, 102(2), 994-1028.', doi: '10.1257/aer.102.2.994', finding: 'Luminositas malam adalah proxy konsisten untuk pertumbuhan ekonomi sub-nasional.' },
    { id: 'R2', cit: 'Donaldson, D., & Storeygard, A. (2016). The View from Above: Applications of Satellite Data in Economics. Journal of Economic Perspectives, 30(4), 171-198.', doi: '10.1257/jep.30.4.171', finding: 'Review penggunaan data satelit untuk ekonomi spasial; mendukung VIIRS sebagai proxy.' },
    { id: 'R3', cit: 'Bluhm, R., & Krause, M. (2022). Top lights: Bright cities and their contribution to economic development. Journal of Development Economics, 157.', doi: '10.1016/j.jdeveco.2022.102880', finding: 'Saturasi luminositas malam di kota besar; penting koreksi BRDF.' },
    { id: 'R4', cit: 'Glaeser, E. L., & Gottlieb, J. D. (2009). The Wealth of Cities. Journal of Economic Literature, 47(4), 983-1028.', doi: '10.1257/jel.47.4.983', finding: 'Densitas tempat usaha gaya hidup berkorelasi dengan urbanisasi pendapatan tinggi.' },
    { id: 'R5', cit: 'Couture, V., & Handbury, J. (2020). Urban revival in America. Journal of Urban Economics, 119.', doi: '10.1016/j.jue.2020.103267', finding: 'Konsumsi gaya hidup (restoran, hiburan) memprediksi gentrifikasi urban.' },
    { id: 'R6', cit: 'Rauch, F. (2014). Cities as spatial clusters. Journal of Economic Geography, 14(4), 759-773.', doi: '10.1093/jeg/lbt034', finding: 'Indeks keberagaman ekonomi memprediksi resilience urban.' },
    { id: 'R7', cit: 'Duranton, G., & Puga, D. (2004). Micro-foundations of urban agglomeration economies. Handbook of Regional and Urban Economics, 4, 2063-2117.', doi: '10.1016/S1574-0080(04)80005-1', finding: 'Aksesibilitas transportasi adalah determinan kunci aglomerasi komersial.' },
    { id: 'R8', cit: 'Barzin, S., DAcci, L., & Rich, B. (2022). Measuring economic activity from space using nighttime lights. Annals of Regional Science.', doi: '10.1007/s00168-022-01129-7', finding: 'Validasi VIIRS untuk ekonomi sub-nasional di negara berkembang.' },
    { id: 'R9', cit: 'OpenStreetMap contributors. (2024). OpenStreetMap Data Quality Assessment. ISPRS International Journal of Geo-Information.', doi: '10.3390/ijgi13010001', finding: 'OSM coverage tidak merata; perlu kombinasi dengan sensus resmi.' },
  ];
  let html = '';
  refs.forEach(r => {
    html += `<div class="ref-card">
      <div class="ref-id">${r.id}</div>
      <div class="ref-citation">${r.cit}</div>
      <div class="ref-doi"><a href="https://doi.org/${r.doi}" target="_blank" rel="noopener" style="color:var(--muted);text-decoration:none;">DOI: ${r.doi}</a></div>
      <div class="ref-finding">${r.finding}</div>
    </div>`;
  });
  document.getElementById('ref-list').innerHTML = html;
}

// ============ SANITY CHECKS ============
function runSanityChecks() {
  console.log('=== Sanity Checks ===');
  console.log('DESA_DATA rows:', DESA_DATA.length, DESA_DATA.length === 270 ? 'PASS' : 'FAIL');
  console.log('KAWASAN_DATA rows:', KAWASAN_DATA.length, KAWASAN_DATA.length === 21 ? 'PASS' : 'FAIL');
  console.log('GEOJSON features:', GEOJSON.features.length, GEOJSON.features.length === 270 ? 'PASS' : 'FAIL');
  const topEz = [...DESA_DATA].sort((a,b) => (b.eczi_score||0) - (a.eczi_score||0))[0];
  console.log('Top ECZI desa:', topEz.nama_desa, topEz.nama_desa === 'Cideng' ? 'PASS' : 'FAIL');
  const pej = DESA_DATA.find(d => d.nama_desa === 'Pejagalan');
  console.log('Pejagalan rank_magnitude:', pej?.rank_magnitude, pej?.rank_magnitude === 5 ? 'PASS' : 'FAIL');
  const topKaw = [...KAWASAN_DATA].sort((a,b) => (b.eczi_score||0) - (a.eczi_score||0))[0];
  console.log('Top kawasan ECZI:', topKaw.kawasan, topKaw.kawasan === 'Mega Kuningan' ? 'PASS' : 'FAIL');
  const topKawMg = [...KAWASAN_DATA].sort((a,b) => (b.magnitude_score||0) - (a.magnitude_score||0))[0];
  console.log('Top kawasan magnitude:', topKawMg.kawasan, topKawMg.kawasan === 'PIK (Pantai Indah Kapuk)' ? 'PASS' : 'FAIL');
  const blokm = KAWASAN_DATA.find(k => k.kawasan === 'Blok M & Sekitarnya');
  console.log('Blok M pulse:', blokm?.pulse_badge, blokm?.pulse_badge === 'Trend Lanjut Tumbuh' ? 'PASS' : 'FAIL');
}

// ============ ALPINE ROOT ============
function dashboard() {
  return {
    page: 'ringkasan',
    tier: 'kawasan',
    filterCategory: 'all',
    leaderTab: 'eczi',
    page4Tab: 'eczi',
    page5Mode: 'kawasan',
    page5Selected: 'Mega Kuningan',
    page5SubTab: 'ntl',
    page3Layer: 'podes',
    map2Year: 'cagr',
    navOpen: false,

    tabs: [
      { id: 'ringkasan', label: 'Ringkasan', icon: 'mdi:view-dashboard' },
      { id: 'cahaya-malam', label: 'Luminositas Malam', icon: 'mdi:weather-night' },
      { id: 'aktivitas-komersial', label: 'Aktivitas Komersial', icon: 'mdi:store' },
      { id: 'skor-potensi', label: 'Skor Potensi', icon: 'mdi:chart-bar' },
      { id: 'detail-kawasan', label: 'Detail Kawasan', icon: 'mdi:map-marker' },
      { id: 'metodologi', label: 'Metodologi', icon: 'mdi:book-open-variant' }
    ],

    init() {
      this.$nextTick(() => {
        this.renderAll();
        runSanityChecks();
      });
      this.$watch('page', () => this.$nextTick(() => this.renderAll()));
      this.$watch('tier', () => this.$nextTick(() => this.renderAll()));
      this.$watch('filterCategory', () => this.$nextTick(() => this.renderAll()));
      this.$watch('leaderTab', () => this.$nextTick(() => { if (this.page === 'ringkasan') renderRingkasan(this); }));
      // Bridge for topnav anchors + landing-page deeplink (#page=...)
      window.gotoPage = (id) => this.setPage(id);
    },

    setPage(id) {
      this.page = id;
      try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch (e) { window.scrollTo(0, 0); }
    },
    currentTabLabel() { return (this.tabs.find(t => t.id === this.page) || {}).label || ''; },

    getCurrentData() {
      let data;
      if (this.tier === 'kawasan') data = KAWASAN_DATA;
      else if (this.tier === 'desa') data = DESA_DATA;
      else if (this.tier === 'kecamatan') data = aggregateKecamatan();
      else data = aggregateKabkota();
      if (this.filterCategory !== 'all') {
        data = data.filter(d => d.tipe_kawasan === this.filterCategory);
      }
      return data;
    },

    renderAll() {
      if (this.page === 'ringkasan') renderRingkasan(this);
      else if (this.page === 'cahaya-malam') renderCahayaMalam(this);
      else if (this.page === 'aktivitas-komersial') renderAktivitasKomersial(this);
      else if (this.page === 'skor-potensi') renderSkorPotensi(this);
      else if (this.page === 'detail-kawasan') renderPage5(this);
      else if (this.page === 'metodologi') renderMetodologi(this);
    }
  };
}

// expose
window.dashboard = dashboard;
window.renderRingkasan = renderRingkasan;
window.renderCahayaMalam = renderCahayaMalam;
window.renderAktivitasKomersial = renderAktivitasKomersial;
window.renderSkorPotensi = renderSkorPotensi;
window.renderPage4Eczi = renderPage4Eczi;
window.renderPage4Mag = renderPage4Mag;
window.renderPage5 = renderPage5;
window.renderPage5Sub = renderPage5Sub;
window.renderMetodologi = renderMetodologi;
window.renderMap2 = renderMap2;
window.renderMap3 = renderMap3;
"""


def build_html(data):
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pendeteksi Kawasan Komersial Berkembang DKI Jakarta 2021-2025 | Mandiri Institute</title>
<script src="../_assets/plotly.min.js"></script>
<script src="../_assets/tailwind.min.js"></script>
<script src="../_assets/iconify-icon.min.js"></script>
<script src="../_assets/icons.js"></script>
<script defer src="../_assets/alpine.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>
<link href="../_assets/fonts/fonts.css" rel="stylesheet">
<style>
{CSS}
</style>
</head>
<body>

<div x-data="dashboard()" x-init="init()">

{TOPNAV_HTML}

{SIDEBAR_HTML}

<div class="with-sidebar">

{HERO_HTML}

<main class="max-w-[1280px] mx-auto px-8 pb-16">

{PAGE_RINGKASAN}

{PAGE_CAHAYA}

{PAGE_AKTIVITAS}

{PAGE_SKOR}

{PAGE_DETAIL}

{PAGE_METODOLOGI}

</main>

<footer class="dash-footer max-w-[1280px] mx-auto px-8">
  <div>Mandiri Institute &middot; Riset Spasial Ekonomi</div>
  <div>Diperbarui 5 Mei 2026 &middot; Metodologi v2.2 &middot; Generator v5.7</div>
</footer>

</div>
</div>

<script>
const DESA_DATA = {data['desa_json']};
const KAWASAN_DATA = {data['kw_json']};
const GEOJSON = {data['geojson']};
const KAWASAN_MAP = {data['kw_map']};
const NTL_ANNUAL = {data['ntl_json']};
const OSM_POI = {data['osm_json']};
const TRANSPORT_POI = {data['tra_json']};

{JS_FUNCTIONS}
</script>
</body>
</html>"""


if __name__ == '__main__':
    print('Loading data...')
    data = load_data()
    print('Building HTML...')
    html = build_html(data)
    OUTPUT.write_text(html, encoding='utf-8')
    sz = OUTPUT.stat().st_size / 1024
    print(f'Generated: {OUTPUT}')
    print(f'Size: {sz:.0f} KB')
    # Auto-run language patch (kategori + pulse data values di JSON embed
    # tetap raw Indonesia karena untuk join; patch_language.py ganti ke
    # English noun phrase per spec Lead/Scraping audit)
    patch_script = OUTPUT.parent / 'patch_language.py'
    if patch_script.exists():
        print('\nApplying language patch...')
        import subprocess
        import sys
        subprocess.run([sys.executable, str(patch_script)], check=False)
    else:
        print('[WARN] patch_language.py not found; language mapping NOT applied')
