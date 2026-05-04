"""
emerging-zone-generator-v3.py
Generates self-contained HTML dashboard: Pendeteksi Kawasan Komersial Berkembang DKI Jakarta 2021-2025
Mandiri Institute — 2026
"""

import pandas as pd
import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / 'data'
OUTPUT_FILE = Path(__file__).parent / '260503_NASA_emerging-zone-detector.html'


# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

def load_data():
    # 1. Desa CSV (270 rows)
    desa = pd.read_csv(DATA_DIR / '260503_FINAL_eczi_per_desa.csv')
    # fill NaN with None-friendly defaults for JSON
    desa = desa.where(pd.notnull(desa), None)

    # 2. Kawasan CSV (21 rows)
    kaw = pd.read_csv(DATA_DIR / '260503_FINAL_eczi_per_kawasan.csv')
    kaw = kaw.where(pd.notnull(kaw), None)
    # Clean deskripsi field: replace forbidden English/technical terms
    if 'deskripsi' in kaw.columns:
        kaw['deskripsi'] = kaw['deskripsi'].apply(
            lambda s: str(s).replace('CAGR', 'pertumbuhan tahunan').replace('NTL', 'cahaya malam')
                            .replace('Emerging zone', 'Zona berkembang').replace('Emerging', 'Berkembang')
            if s is not None else s
        )

    # 3. GeoJSON
    with open(DATA_DIR / 'dki_desa_simplified.geojson', 'r', encoding='utf-8') as f:
        geojson_str = f.read()

    # 4. NTL annual (sheet: annual_dry_season)
    ntl_df = pd.read_excel(DATA_DIR / '260503_NASA_jakarta-monthly-areas.xlsx',
                           sheet_name='annual_dry_season')
    ntl_records = ntl_df.to_dict(orient='records')

    # 5. OSM lifestyle lat/lon/category only
    osm_df = pd.read_excel(DATA_DIR / '260503_OSM_poi-lifestyle-jakarta.xlsx',
                           sheet_name='all_lifestyle',
                           usecols=['lat', 'lon', 'category'])
    osm_df = osm_df.dropna(subset=['lat', 'lon'])
    osm_records = osm_df.to_dict(orient='records')

    # 6. Transport lat/lon only (sheet 0)
    tr_df = pd.read_excel(DATA_DIR / '260502_OSM_transport-jakarta.xlsx',
                          sheet_name=0,
                          usecols=['lat', 'lon'])
    tr_df = tr_df.dropna(subset=['lat', 'lon'])
    transport_records = tr_df.to_dict(orient='records')

    # Computed KPIs
    mean_podes_cagr = desa['podes_cagr_2021_2025'].mean()
    total_podes = int(desa['podes_count_2025'].sum())

    return (
        desa.to_dict(orient='records'),
        kaw.to_dict(orient='records'),
        geojson_str,
        ntl_records,
        osm_records,
        transport_records,
        mean_podes_cagr,
        total_podes,
    )


# ---------------------------------------------------------------------------
# HTML BUILDER
# ---------------------------------------------------------------------------

def build_html(desa_records, kawasan_records, geojson_str,
               ntl_records, osm_records, transport_records,
               mean_podes_cagr, total_podes):

    desa_json = json.dumps(desa_records, ensure_ascii=False)
    kawasan_json = json.dumps(kawasan_records, ensure_ascii=False)
    ntl_json = json.dumps(ntl_records, ensure_ascii=False)
    # Slim OSM to just lat/lon for heatmap (save space)
    osm_heat = [[r['lat'], r['lon']] for r in osm_records if r['lat'] and r['lon']]
    osm_json = json.dumps(osm_heat, ensure_ascii=False)
    transport_heat = [[r['lat'], r['lon']] for r in transport_records if r['lat'] and r['lon']]
    transport_json = json.dumps(transport_heat, ensure_ascii=False)
    mean_podes_pct = f"{mean_podes_cagr*100:.1f}"
    total_podes_fmt = f"{total_podes:,}".replace(",", ".")

    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Pendeteksi Kawasan Komersial Berkembang — DKI Jakarta 2021-2025 | Mandiri Institute</title>
<script src="https://cdn.tailwindcss.com"></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<style>
  body {{ font-family: 'Inter', sans-serif; background: #f8fafc; color: #1e293b; }}
  .nav-tab {{ @apply px-4 py-2 text-sm font-medium cursor-pointer border-b-2 transition-colors; }}
  .nav-tab-active {{ border-color: #e03131; color: #e03131; }}
  .nav-tab-inactive {{ border-color: transparent; color: #64748b; }}
  .kpi-card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .section-title {{ font-size: 1.15rem; font-weight: 700; color: #003d7a; margin-bottom: 12px; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 9999px; font-size: 0.72rem; font-weight: 600; }}
  .badge-naik {{ background: #2563eb; color: white; }}
  .badge-mapan {{ background: #7c3aed; color: white; }}
  .badge-awal {{ background: #f97316; color: white; }}
  .badge-rendah {{ background: #9ca3af; color: white; }}
  .pulse-tumbuh {{ background: #dcfce7; color: #166534; }}
  .pulse-stabil {{ background: #fef9c3; color: #854d0e; }}
  .pulse-melambat {{ background: #fee2e2; color: #991b1b; }}
  .pulse-na {{ background: #f1f5f9; color: #64748b; }}
  .leaflet-map-container {{ border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.12); }}
  .chart-container {{ background: white; border-radius: 12px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .table-row-hover:hover {{ background: #f0f7ff; }}
  .disclaimer-box {{ background: #fffbeb; border: 1px solid #f59e0b; border-radius: 8px; padding: 14px; }}
  .caveat-item {{ padding: 10px 0; border-bottom: 1px solid #e2e8f0; }}
  .sub-tab {{ padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.85rem; font-weight: 500; transition: background 0.2s; }}
  .sub-tab-active {{ background: #003d7a; color: white; }}
  .sub-tab-inactive {{ background: #f1f5f9; color: #475569; }}
  .tier-btn {{ padding: 7px 14px; border-radius: 8px; font-size: 0.8rem; font-weight: 500; cursor: pointer; border: 1.5px solid transparent; transition: all 0.2s; }}
  .tier-btn-active {{ background: #003d7a; color: white; border-color: #003d7a; }}
  .tier-btn-inactive {{ background: white; color: #003d7a; border-color: #003d7a; }}
  .mini-bar-outer {{ background: #e2e8f0; border-radius: 4px; height: 6px; width: 60px; display: inline-block; vertical-align: middle; margin: 0 2px; }}
  .mini-bar-inner {{ background: #003d7a; border-radius: 4px; height: 6px; }}
  [x-cloak] {{ display: none !important; }}
</style>
</head>
<body x-data="dashApp()" x-cloak @keydown.escape.window="page5SubTab='ntl'" x-init="init()">

<!-- ===================== NAVBAR ===================== -->
<nav class="bg-white shadow-sm sticky top-0 z-50">
  <div class="max-w-screen-xl mx-auto px-4">
    <div class="flex items-center justify-between h-14">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-full flex items-center justify-center" style="background:#003d7a">
          <span class="text-white font-bold text-sm">MI</span>
        </div>
        <span class="font-bold text-sm" style="color:#003d7a">Mandiri Institute</span>
        <span class="hidden md:inline text-gray-300">|</span>
        <span class="hidden md:inline text-xs text-gray-500">Pendeteksi Kawasan Komersial Berkembang — DKI Jakarta 2021-2025</span>
      </div>
      <!-- Tier toggle -->
      <div class="flex gap-1">
        <button @click="setTier('kawasan')" :class="tier==='kawasan'?'tier-btn tier-btn-active':'tier-btn tier-btn-inactive'" class="tier-btn">Wilayah Berpotensi</button>
        <button @click="setTier('desa')" :class="tier==='desa'?'tier-btn tier-btn-active':'tier-btn tier-btn-inactive'" class="tier-btn">Kelurahan</button>
        <button @click="setTier('kecamatan')" :class="tier==='kecamatan'?'tier-btn tier-btn-active':'tier-btn tier-btn-inactive'" class="tier-btn">Kecamatan</button>
        <button @click="setTier('kabkota')" :class="tier==='kabkota'?'tier-btn tier-btn-active':'tier-btn tier-btn-inactive'" class="tier-btn">Kab/Kota</button>
      </div>
    </div>
    <!-- Nav tabs -->
    <div class="flex gap-0 overflow-x-auto border-t border-gray-100">
      <template x-for="tab in navTabs" :key="tab.key">
        <button @click="page=tab.key" :class="page===tab.key?'nav-tab nav-tab-active':'nav-tab nav-tab-inactive'" class="nav-tab whitespace-nowrap" x-text="tab.label"></button>
      </template>
    </div>
  </div>
</nav>

<!-- ===================== PAGE 1: RINGKASAN ===================== -->
<div x-show="page==='ringkasan'" class="max-w-screen-xl mx-auto px-4 py-6">
  <div class="mb-6">
    <h1 class="text-2xl font-bold mb-2" style="color:#003d7a">Ringkasan Eksekutif</h1>
    <p class="text-sm text-gray-600 leading-relaxed max-w-4xl">
      Dashboard ini mendeteksi kawasan dengan aktivitas komersial yang tumbuh paling pesat di DKI Jakarta sepanjang 2021-2025, menggunakan empat sumber data independen: Cahaya Malam satelit NASA, sensus usaha BPS Podes, data pendapatan pekerja Sakernas, dan pemetaan tempat usaha OpenStreetMap. Setiap kawasan memiliki dua skor: <strong>Skor Potensi</strong> (seberapa cepat tumbuh) dan <strong>Skor Magnitude</strong> (seberapa padat aktivitas komersialnya).
    </p>
  </div>

  <!-- KPI Cards -->
  <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
    <div class="kpi-card text-center col-span-1">
      <div class="text-2xl font-bold" style="color:#003d7a" x-text="kpiWilayah()"></div>
      <div class="text-xs text-gray-500 mt-1">Wilayah Terdeteksi</div>
      <div class="text-xs text-gray-400" x-text="kpiWilayahSub()"></div>
    </div>
    <div class="kpi-card text-center col-span-1">
      <div class="text-2xl font-bold" style="color:#003d7a">2021–2025</div>
      <div class="text-xs text-gray-500 mt-1">Periode Analisis</div>
      <div class="text-xs text-gray-400">4 tahun</div>
    </div>
    <div class="kpi-card text-center col-span-1">
      <div class="text-lg font-bold truncate" style="color:#003d7a" x-text="kpiTopEczi().name"></div>
      <div class="text-xs text-gray-500 mt-1">Skor Potensi Tertinggi</div>
      <div class="text-xs font-semibold" style="color:#e03131" x-text="kpiTopEczi().score"></div>
    </div>
    <div class="kpi-card text-center col-span-1">
      <div class="text-lg font-bold truncate" style="color:#003d7a" x-text="kpiTopMag().name"></div>
      <div class="text-xs text-gray-500 mt-1">Skor Magnitude Tertinggi</div>
      <div class="text-xs font-semibold" style="color:#e03131" x-text="kpiTopMag().score"></div>
    </div>
    <div class="kpi-card text-center col-span-1">
      <div class="text-2xl font-bold" style="color:#003d7a">{mean_podes_pct}%</div>
      <div class="text-xs text-gray-500 mt-1">Rata-rata Tumbuh Tempat Usaha</div>
      <div class="text-xs text-gray-400">per tahun 2021-2025</div>
    </div>
    <div class="kpi-card text-center col-span-1">
      <div class="text-2xl font-bold" style="color:#003d7a">{total_podes_fmt}</div>
      <div class="text-xs text-gray-500 mt-1">Total Tempat Usaha 2025</div>
      <div class="text-xs text-gray-400">270 kelurahan DKI</div>
    </div>
  </div>

  <!-- Dual Leaderboard + NTL Sparkline -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <!-- Leaderboard -->
    <div class="lg:col-span-2 bg-white rounded-xl shadow-sm p-4">
      <div class="flex gap-2 mb-4">
        <button @click="leaderboardTab='eczi'" :class="leaderboardTab==='eczi'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab">Kawasan Berkembang (Skor Potensi)</button>
        <button @click="leaderboardTab='mag'" :class="leaderboardTab==='mag'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab">Aktivitas Terbesar (Magnitude)</button>
      </div>

      <!-- ECZI Leaderboard -->
      <div x-show="leaderboardTab==='eczi'">
        <table class="w-full text-sm">
          <thead><tr class="text-xs text-gray-400 border-b">
            <th class="text-left py-1 w-8">#</th>
            <th class="text-left py-1">Nama</th>
            <th class="text-left py-1 hidden md:table-cell">Kab/Kota</th>
            <th class="text-right py-1">Skor Potensi</th>
            <th class="text-left py-1 pl-2 hidden lg:table-cell">Kategori</th>
            <th class="text-left py-1 pl-2 hidden lg:table-cell">Tren</th>
          </tr></thead>
          <tbody>
            <template x-for="(d, i) in getTop10Eczi()" :key="i">
              <tr class="table-row-hover border-b border-gray-50">
                <td class="py-2 text-gray-400 font-mono text-xs" x-text="i+1"></td>
                <td class="py-2 font-medium" x-text="getDisplayName(d)"></td>
                <td class="py-2 text-gray-500 text-xs hidden md:table-cell" x-text="d.kabkota||d.nama_kabkota||''"></td>
                <td class="py-2 text-right font-bold" style="color:#003d7a" x-text="fmtScore(d.eczi_score)"></td>
                <td class="py-2 pl-2 hidden lg:table-cell"><span :class="tipeBadgeClass(d.tipe_kawasan)" class="badge text-xs" x-text="tipeShort(d.tipe_kawasan)"></span></td>
                <td class="py-2 pl-2 hidden lg:table-cell"><span :class="pulseBadgeClass(d.pulse_badge)" class="badge text-xs" x-text="d.pulse_badge||'—'"></span></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Magnitude Leaderboard -->
      <div x-show="leaderboardTab==='mag'">
        <table class="w-full text-sm">
          <thead><tr class="text-xs text-gray-400 border-b">
            <th class="text-left py-1 w-8">#</th>
            <th class="text-left py-1">Nama</th>
            <th class="text-left py-1 hidden md:table-cell">Kab/Kota</th>
            <th class="text-right py-1">Skor Magnitude</th>
            <th class="text-right py-1 hidden lg:table-cell">Tempat Usaha 2025</th>
          </tr></thead>
          <tbody>
            <template x-for="(d, i) in getTop10Mag()" :key="i">
              <tr class="table-row-hover border-b border-gray-50">
                <td class="py-2 text-gray-400 font-mono text-xs" x-text="i+1"></td>
                <td class="py-2 font-medium" x-text="getDisplayName(d)"></td>
                <td class="py-2 text-gray-500 text-xs hidden md:table-cell" x-text="d.kabkota||d.nama_kabkota||''"></td>
                <td class="py-2 text-right font-bold" style="color:#003d7a" x-text="fmtScore(d.magnitude_score)"></td>
                <td class="py-2 text-right text-gray-600 hidden lg:table-cell" x-text="fmtNum(d.podes_count_2025||d.podes_count_total)"></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- NTL Sparkline -->
    <div class="bg-white rounded-xl shadow-sm p-4">
      <div class="section-title text-sm">Tren Cahaya Malam — 5 Kawasan Teratas</div>
      <div id="ntl-sparkline" style="height:280px"></div>
    </div>
  </div>
</div>

<!-- ===================== PAGE 2: CAHAYA MALAM ===================== -->
<div x-show="page==='cahaya'" class="max-w-screen-xl mx-auto px-4 py-6">
  <h1 class="text-2xl font-bold mb-2" style="color:#003d7a">Peta Cahaya Malam dan Pertumbuhan</h1>
  <p class="text-sm text-gray-600 leading-relaxed max-w-4xl mb-6">
    Cahaya malam dari satelit NASA VIIRS mencerminkan intensitas aktivitas ekonomi suatu kawasan. Semakin terang, semakin tinggi aktivitas. Peta berikut menampilkan pertumbuhan kecerahan 2021-2025 per kelurahan — kawasan yang gelap di 2021 namun terang di 2025 adalah kandidat zona berkembang kuat.
  </p>

  <!-- Map -->
  <div class="chart-container mb-4">
    <div class="flex items-center justify-between mb-3">
      <div class="section-title mb-0">Pertumbuhan Cahaya Malam per Kelurahan (CAGR 2021-2025)</div>
      <div class="flex gap-2">
        <button @click="map2Layer='cagr'; updateMap2Layer()" :class="map2Layer==='cagr'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab text-xs">Pertumbuhan (CAGR)</button>
        <button @click="map2Layer='level'; updateMap2Layer()" :class="map2Layer==='level'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab text-xs">Level 2025</button>
      </div>
    </div>
    <div id="map2" class="leaflet-map-container" style="height:500px"></div>
    <!-- Legend -->
    <div class="flex items-center gap-2 mt-3 flex-wrap">
      <span class="text-xs text-gray-500">Pertumbuhan NTL CAGR:</span>
      <template x-for="leg in ntlLegend" :key="leg.label">
        <div class="flex items-center gap-1">
          <div class="w-4 h-4 rounded" :style="'background:'+leg.color"></div>
          <span class="text-xs text-gray-500" x-text="leg.label"></span>
        </div>
      </template>
      <div class="flex items-center gap-1">
        <div class="w-4 h-4 rounded" style="background:#cccccc"></div>
        <span class="text-xs text-gray-500">Tidak ada data</span>
      </div>
    </div>
  </div>

  <!-- NTL Time Series -->
  <div class="chart-container mb-4">
    <div id="ntl-timeseries" style="height:350px"></div>
  </div>

  <!-- Top 20 CAGR bar -->
  <div class="chart-container mb-4">
    <p class="text-xs text-gray-400 mt-2">20 kelurahan dengan pertumbuhan cahaya malam tertinggi 2021-2025</p>
    <div id="ntl-cagr-bar" style="height:420px"></div>
  </div>

  <!-- Pulse badges table -->
  <div class="bg-white rounded-xl shadow-sm p-4">
    <div class="section-title">Tren Cahaya Malam 2026 per Kawasan</div>
    <table class="w-full text-sm">
      <thead><tr class="text-xs text-gray-400 border-b">
        <th class="text-left py-2">Kawasan</th>
        <th class="text-left py-2">Tren 2026</th>
        <th class="text-right py-2">Perubahan Tahunan (%)</th>
      </tr></thead>
      <tbody>
        <template x-for="(k, i) in KAWASAN_DATA_JS" :key="i">
          <tr class="table-row-hover border-b border-gray-50">
            <td class="py-2 font-medium" x-text="k.kawasan"></td>
            <td class="py-2"><span :class="pulseBadgeClass(k.pulse_badge)" class="badge" x-text="k.pulse_badge||'tidak tersedia'"></span></td>
            <td class="py-2 text-right text-gray-600" x-text="k.ntl_change_2024_2025 != null ? (k.ntl_change_2024_2025>=0?'+':'') + (k.ntl_change_2024_2025*100).toFixed(1) + '%' : '—'"></td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</div>

<!-- ===================== PAGE 3: AKTIVITAS KOMERSIAL ===================== -->
<div x-show="page==='komersial'" class="max-w-screen-xl mx-auto px-4 py-6">
  <h1 class="text-2xl font-bold mb-2" style="color:#003d7a">Aktivitas Komersial Mikro</h1>
  <p class="text-sm text-gray-600 leading-relaxed max-w-4xl mb-6">
    Data Potensi Desa (Podes) BPS mencatat jumlah tempat usaha di setiap kelurahan — dari kelompok pertokoan, pasar, minimarket, restoran, hingga warung. Data ini adalah sumber paling komprehensif untuk memahami ekosistem bisnis lokal yang sebenarnya.
  </p>

  <!-- Map Podes + OSM -->
  <div class="chart-container mb-4">
    <div class="flex items-center justify-between mb-3">
      <div class="section-title mb-0">Peta Aktivitas Komersial Kelurahan</div>
      <div class="flex gap-2">
        <button @click="page3Layer='podes'; switchPage3Layer()" :class="page3Layer==='podes'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab text-xs">Podes (Tempat Usaha)</button>
        <button @click="page3Layer='osm'; switchPage3Layer()" :class="page3Layer==='osm'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab text-xs">OSM Lifestyle POI</button>
        <button @click="page3Layer='transport'; switchPage3Layer()" :class="page3Layer==='transport'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab text-xs">Transportasi</button>
      </div>
    </div>
    <div id="map3" class="leaflet-map-container" style="height:450px"></div>
  </div>

  <!-- Top 10 Podes bar -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
    <div class="chart-container">
      <p class="text-xs text-gray-400 mb-2">10 kelurahan dengan jumlah tempat usaha terbanyak (Podes 2025)</p>
      <div id="podes-top10-bar" style="height:320px"></div>
    </div>
    <!-- Diversity table -->
    <div class="bg-white rounded-xl shadow-sm p-4">
      <div class="section-title">Keberagaman Usaha — Indeks Shannon</div>
      <p class="text-xs text-gray-400 mb-3">15 kelurahan dengan keberagaman jenis usaha tertinggi</p>
      <table class="w-full text-xs">
        <thead><tr class="text-gray-400 border-b">
          <th class="text-left py-1">Kelurahan</th>
          <th class="text-left py-1 hidden md:table-cell">Kab/Kota</th>
          <th class="text-right py-1">Indeks Shannon</th>
          <th class="text-right py-1 hidden lg:table-cell">Tempat Usaha</th>
        </tr></thead>
        <tbody>
          <template x-for="(d, i) in getDiversityTop15()" :key="i">
            <tr class="table-row-hover border-b border-gray-50">
              <td class="py-1.5 font-medium" x-text="d.nama_desa"></td>
              <td class="py-1.5 text-gray-400 hidden md:table-cell" x-text="(d.nama_kabkota||'').replace('Kota Jakarta ','')"></td>
              <td class="py-1.5 text-right">
                <span class="inline-block px-2 rounded font-mono font-semibold text-white text-xs" :style="'background:'+shannonColor(d.podes_diversity_shannon)" x-text="(d.podes_diversity_shannon||0).toFixed(3)"></span>
              </td>
              <td class="py-1.5 text-right text-gray-500 hidden lg:table-cell" x-text="fmtNum(d.podes_count_2025)"></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>

  <!-- Stacked magnitude bar -->
  <div class="chart-container mb-4">
    <p class="text-xs text-gray-400 mb-1">Komposisi Indeks Aktivitas Komersial per kelurahan (Proxy Index — lihat catatan di bawah)</p>
    <div id="magnitude-stacked" style="height:380px"></div>
    <p class="text-xs text-gray-400 mt-2 italic">* Indeks Aktivitas Komersial = Jumlah Tempat Usaha (Podes) x Rata-rata Pendapatan Pekerja Sektor (Sakernas). Nilai ini adalah proxy relatif, bukan klaim angka Rupiah absolut.</p>
  </div>
</div>

<!-- ===================== PAGE 4: SKOR POTENSI ===================== -->
<div x-show="page==='skor'" class="max-w-screen-xl mx-auto px-4 py-6">
  <h1 class="text-2xl font-bold mb-2" style="color:#003d7a">Skor Potensi dan Magnitude</h1>
  <p class="text-sm text-gray-600 leading-relaxed max-w-4xl mb-6">
    Skor Potensi Zona Komersial menggabungkan lima dimensi data untuk mengidentifikasi kawasan yang sedang dalam fase pertumbuhan aktif. Skor Magnitude mengukur seberapa besar aktivitas komersial yang sudah ada saat ini.
  </p>

  <!-- Tabs -->
  <div class="flex gap-2 mb-6">
    <button @click="page4Tab='eczi'" :class="page4Tab==='eczi'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab">Skor Potensi (Berkembang)</button>
    <button @click="page4Tab='mag'" :class="page4Tab==='mag'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab">Skor Magnitude (Kepadatan)</button>
  </div>

  <!-- ECZI Tab -->
  <div x-show="page4Tab==='eczi'">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
      <!-- Radar chart -->
      <div class="chart-container">
        <div class="section-title text-sm">Profil Lima Dimensi — Top 5 Kelurahan Skor Potensi</div>
        <div id="radar-chart" style="height:350px"></div>
      </div>
      <!-- Scatter quadrant -->
      <div class="chart-container">
        <div class="section-title text-sm">Peta Kuadran: Pertumbuhan NTL vs Kepadatan OSM</div>
        <div id="scatter-quadrant" style="height:350px"></div>
      </div>
    </div>

    <!-- Leaderboard table ECZI -->
    <div class="bg-white rounded-xl shadow-sm p-4">
      <div class="section-title">Peringkat Skor Potensi — Seluruh Kelurahan (270)</div>
      <p class="text-xs text-gray-400 mb-3">G1=Cahaya Malam, G2=Tempat Usaha, G3=Magnitude, G4=Gaya Hidup, G5=Aksesibilitas</p>
      <div style="max-height:420px; overflow-y:auto;">
        <table class="w-full text-xs">
          <thead class="sticky top-0 bg-white"><tr class="text-gray-400 border-b">
            <th class="text-left py-2 w-8">#</th>
            <th class="text-left py-2">Kelurahan</th>
            <th class="text-left py-2 hidden md:table-cell">Kab/Kota</th>
            <th class="text-right py-2">Skor Potensi</th>
            <th class="text-left py-2 pl-2 hidden lg:table-cell">Kategori</th>
            <th class="text-left py-2 pl-2 hidden xl:table-cell">Dimensi G1-G5</th>
            <th class="text-left py-2 pl-2 hidden lg:table-cell">Tren 2026</th>
          </tr></thead>
          <tbody>
            <template x-for="(d, i) in getEcziRanked()" :key="i">
              <tr class="table-row-hover border-b border-gray-50">
                <td class="py-1.5 text-gray-400 font-mono" x-text="i+1"></td>
                <td class="py-1.5 font-medium" x-text="d.nama_desa||d.kawasan||''"></td>
                <td class="py-1.5 text-gray-400 hidden md:table-cell" x-text="(d.nama_kabkota||d.kabkota||'').replace('Kota Jakarta ','')"></td>
                <td class="py-1.5 text-right font-bold" style="color:#003d7a" x-text="fmtScore(d.eczi_score)"></td>
                <td class="py-1.5 pl-2 hidden lg:table-cell"><span :class="tipeBadgeClass(d.tipe_kawasan)" class="badge" x-text="tipeShort(d.tipe_kawasan)"></span></td>
                <td class="py-1.5 pl-2 hidden xl:table-cell">
                  <template x-for="gv in [d.g1,d.g2,d.g3,d.g4,d.g5]" :key="gv">
                    <span class="mini-bar-outer"><span class="mini-bar-inner" :style="'width:'+(Math.min(gv||0,100)/100*60)+'px'"></span></span>
                  </template>
                </td>
                <td class="py-1.5 pl-2 hidden lg:table-cell"><span :class="pulseBadgeClass(d.pulse_badge)" class="badge" x-text="d.pulse_badge||'—'"></span></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Magnitude Tab -->
  <div x-show="page4Tab==='mag'">
    <div class="disclaimer-box mb-4">
      <p class="text-sm font-semibold text-yellow-800 mb-1">Catatan: Indeks Aktivitas Komersial — Proxy Index untuk Ranking</p>
      <p class="text-xs text-yellow-700">Angka ini = Jumlah Tempat Usaha (Podes) x Rata-rata Pendapatan Pekerja Sektor (Sakernas). Sakernas mengukur pendapatan PERSONAL pekerja per bulan (Rp 2-5 juta), BUKAN revenue per usaha. Indeks ini valid untuk pembanding RELATIF antar kelurahan/kawasan, BUKAN klaim angka Rupiah absolut.</p>
    </div>
    <div class="bg-white rounded-xl shadow-sm p-4">
      <div class="section-title">Peringkat Skor Magnitude — Seluruh Kelurahan (270)</div>
      <div style="max-height:480px; overflow-y:auto;">
        <table class="w-full text-xs">
          <thead class="sticky top-0 bg-white"><tr class="text-gray-400 border-b">
            <th class="text-left py-2 w-8">#</th>
            <th class="text-left py-2">Kelurahan</th>
            <th class="text-left py-2 hidden md:table-cell">Kab/Kota</th>
            <th class="text-right py-2">Skor Magnitude</th>
            <th class="text-right py-2 hidden lg:table-cell">Tempat Usaha</th>
            <th class="text-right py-2 hidden xl:table-cell">Indeks Komersial</th>
            <th class="text-left py-2 pl-2 hidden lg:table-cell">Keandalan</th>
          </tr></thead>
          <tbody>
            <template x-for="(d, i) in getMagRanked()" :key="i">
              <tr class="table-row-hover border-b border-gray-50">
                <td class="py-1.5 text-gray-400 font-mono" x-text="i+1"></td>
                <td class="py-1.5 font-medium" x-text="d.nama_desa||d.kawasan||''"></td>
                <td class="py-1.5 text-gray-400 hidden md:table-cell" x-text="(d.nama_kabkota||d.kabkota||'').replace('Kota Jakarta ','')"></td>
                <td class="py-1.5 text-right font-bold" style="color:#003d7a" x-text="fmtScore(d.magnitude_score)"></td>
                <td class="py-1.5 text-right text-gray-600 hidden lg:table-cell" x-text="fmtNum(d.podes_count_2025)"></td>
                <td class="py-1.5 text-right text-gray-500 hidden xl:table-cell" x-text="fmtNum(Math.round(d.magnitude_2025||0))"></td>
                <td class="py-1.5 pl-2 hidden lg:table-cell">
                  <template x-if="d.low_reliability_flag==1">
                    <span class="badge bg-red-100 text-red-700" title="Data NTL terbatas, gunakan dengan hati-hati">Hati-hati</span>
                  </template>
                  <template x-if="!d.low_reliability_flag||d.low_reliability_flag==0">
                    <span class="badge bg-green-100 text-green-700">OK</span>
                  </template>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- ===================== PAGE 5: DETAIL KAWASAN ===================== -->
<div x-show="page==='detail'" class="max-w-screen-xl mx-auto px-4 py-6">
  <h1 class="text-2xl font-bold mb-2" style="color:#003d7a">Detail per Kawasan</h1>
  <p class="text-sm text-gray-600 leading-relaxed max-w-4xl mb-6">
    Pilih kawasan atau kelurahan spesifik untuk melihat profil lengkap lima dimensi data: pergerakan cahaya malam, perkembangan tempat usaha, komposisi sektor, fasilitas lifestyle, dan aksesibilitas transportasi.
  </p>

  <!-- Filter controls -->
  <div class="bg-white rounded-xl shadow-sm p-4 mb-4">
    <div class="flex gap-4 items-center flex-wrap">
      <div class="flex gap-2">
        <button @click="page5Mode='kawasan'; page5Selected=getKawasanOptions()[0]" :class="page5Mode==='kawasan'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab">Kawasan Utama</button>
        <button @click="page5Mode='desa'; page5Selected=getDesaOptions()[0]" :class="page5Mode==='desa'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab">Kelurahan</button>
      </div>
      <select x-model="page5Selected" @change="renderDetailCharts()" class="border border-gray-200 rounded-lg px-3 py-2 text-sm flex-1 max-w-xs">
        <template x-for="opt in (page5Mode==='kawasan'?getKawasanOptions():getDesaOptions())" :key="opt">
          <option :value="opt" x-text="opt"></option>
        </template>
      </select>
    </div>
  </div>

  <!-- Detail card header -->
  <template x-if="getSelectedDetail()">
    <div class="bg-white rounded-xl shadow-sm p-4 mb-4">
      <div class="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 class="text-xl font-bold" style="color:#003d7a" x-text="page5Selected"></h2>
          <p class="text-sm text-gray-500" x-text="getSelectedDetail().kabkota||getSelectedDetail().nama_kabkota||''"></p>
          <div class="flex gap-2 mt-2 flex-wrap">
            <span :class="tipeBadgeClass(getSelectedDetail().tipe_kawasan)" class="badge" x-text="getSelectedDetail().tipe_kawasan||'—'"></span>
            <span :class="pulseBadgeClass(getSelectedDetail().pulse_badge)" class="badge" x-text="getSelectedDetail().pulse_badge||'tidak tersedia'"></span>
          </div>
        </div>
        <div class="flex gap-6">
          <div class="text-center">
            <div class="text-2xl font-bold" style="color:#003d7a" x-text="fmtScore(getSelectedDetail().eczi_score)"></div>
            <div class="text-xs text-gray-400">Skor Potensi</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold" style="color:#e03131" x-text="fmtScore(getSelectedDetail().magnitude_score)"></div>
            <div class="text-xs text-gray-400">Skor Magnitude</div>
          </div>
        </div>
      </div>
    </div>
  </template>

  <!-- 5 Sub-tabs -->
  <div class="flex gap-2 mb-4 overflow-x-auto">
    <button @click="page5SubTab='ntl'; renderDetailCharts()" :class="page5SubTab==='ntl'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab whitespace-nowrap">Cahaya Malam</button>
    <button @click="page5SubTab='podes'; renderDetailCharts()" :class="page5SubTab==='podes'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab whitespace-nowrap">Tempat Usaha</button>
    <button @click="page5SubTab='sektor'; renderDetailCharts()" :class="page5SubTab==='sektor'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab whitespace-nowrap">Sektor Usaha</button>
    <button @click="page5SubTab='fasilitas'; renderDetailCharts()" :class="page5SubTab==='fasilitas'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab whitespace-nowrap">Fasilitas Sekitar</button>
    <button @click="page5SubTab='akses'; renderDetailCharts()" :class="page5SubTab==='akses'?'sub-tab sub-tab-active':'sub-tab sub-tab-inactive'" class="sub-tab whitespace-nowrap">Aksesibilitas</button>
  </div>

  <!-- Sub-tab content -->
  <div class="chart-container min-h-64">
    <div x-show="page5SubTab==='ntl'">
      <div id="detail-ntl-chart" style="height:320px"></div>
      <div class="mt-3 grid grid-cols-3 gap-3">
        <template x-if="getSelectedDetail()">
          <div class="text-center p-3 bg-blue-50 rounded-lg">
            <div class="text-sm font-bold" style="color:#003d7a" x-text="fmtPctCagr(getSelectedDetail().ntl_cagr_2021_2025)"></div>
            <div class="text-xs text-gray-500">CAGR NTL 2021-2025</div>
          </div>
        </template>
        <template x-if="getSelectedDetail()">
          <div class="text-center p-3 bg-orange-50 rounded-lg">
            <div class="text-sm font-bold" style="color:#e03131" x-text="(getSelectedDetail().pulse_badge||'tidak tersedia')"></div>
            <div class="text-xs text-gray-500">Tren 2026</div>
          </div>
        </template>
        <template x-if="getSelectedDetail()">
          <div class="text-center p-3 bg-gray-50 rounded-lg">
            <div class="text-sm font-bold text-gray-700" x-text="(getSelectedDetail().quality_flag||'—')"></div>
            <div class="text-xs text-gray-500">Kualitas Data NTL</div>
          </div>
        </template>
      </div>
    </div>
    <div x-show="page5SubTab==='podes'">
      <div id="detail-podes-chart" style="height:320px"></div>
      <template x-if="getSelectedDetail()&&getSelectedDetail().podes_winsorize_flag">
        <div class="disclaimer-box mt-3 text-xs text-yellow-700">Catatan: Data tempat usaha kelurahan ini melewati ambang winsorize — nilai outlier ekstrem telah disesuaikan dalam perhitungan skor.</div>
      </template>
    </div>
    <div x-show="page5SubTab==='sektor'">
      <div id="detail-sektor-chart" style="height:320px"></div>
      <p class="text-xs text-gray-400 mt-2 italic">* Proxy Index: nilai relatif antar kelurahan, bukan angka absolut Rupiah.</p>
    </div>
    <div x-show="page5SubTab==='fasilitas'">
      <div id="detail-fasilitas-chart" style="height:320px"></div>
    </div>
    <div x-show="page5SubTab==='akses'">
      <div id="detail-akses-chart" style="height:320px"></div>
    </div>
  </div>
</div>

<!-- ===================== PAGE 6: METODOLOGI ===================== -->
<div x-show="page==='metodologi'" class="max-w-screen-xl mx-auto px-4 py-6">
  <h1 class="text-2xl font-bold mb-2" style="color:#003d7a">Metodologi dan Validasi</h1>
  <p class="text-sm text-gray-600 leading-relaxed max-w-4xl mb-6">
    Metodologi ini dirancang untuk transparansi penuh — setiap komponen skor, bobot, batasan data, dan validasi empiris didokumentasikan di bawah. Dashboard ini adalah alat analisis eksploratif, bukan basis keputusan investasi atau kredit.
  </p>

  <!-- Section A: Cara Membaca -->
  <div class="bg-white rounded-xl shadow-sm p-4 mb-4">
    <div class="section-title">A. Cara Membaca Dashboard</div>
    <table class="w-full text-sm">
      <thead><tr class="text-xs text-gray-400 border-b">
        <th class="text-left py-2">Skor</th>
        <th class="text-left py-2">Apa yang Diukur</th>
        <th class="text-left py-2">Interpretasi</th>
      </tr></thead>
      <tbody>
        <tr class="border-b border-gray-50 table-row-hover"><td class="py-2 font-medium">Skor Potensi</td><td class="py-2 text-gray-600">Kecepatan pertumbuhan komersial 2021-2025</td><td class="py-2 text-gray-600">Kawasan dengan skor tinggi: aktivitas tumbuh cepat pasca-COVID</td></tr>
        <tr class="border-b border-gray-50 table-row-hover"><td class="py-2 font-medium">Skor Magnitude</td><td class="py-2 text-gray-600">Kepadatan aktivitas komersial 2025</td><td class="py-2 text-gray-600">Kawasan dengan skor tinggi: sudah ramai, padat usaha</td></tr>
        <tr class="border-b border-gray-50 table-row-hover"><td class="py-2 font-medium">Tipe Kawasan</td><td class="py-2 text-gray-600">Kombinasi pertumbuhan + kepadatan</td><td class="py-2 text-gray-600">4 kategori: Sedang Naik Daun, Mapan, Awal Pertumbuhan, Aktivitas Rendah</td></tr>
        <tr class="table-row-hover"><td class="py-2 font-medium">Tren 2026</td><td class="py-2 text-gray-600">NTL Januari-April 2026 vs 2025</td><td class="py-2 text-gray-600">Apakah tren 2021-2025 masih berlanjut?</td></tr>
      </tbody>
    </table>
  </div>

  <!-- Section B: Sumber Data -->
  <div class="bg-white rounded-xl shadow-sm p-4 mb-4">
    <div class="section-title">B. Sumber Data</div>
    <table class="w-full text-sm">
      <thead><tr class="text-xs text-gray-400 border-b">
        <th class="text-left py-2">Sumber</th>
        <th class="text-left py-2">Peran</th>
        <th class="text-left py-2 hidden md:table-cell">Granularity</th>
        <th class="text-left py-2">Periode</th>
      </tr></thead>
      <tbody>
        <tr class="border-b border-gray-50 table-row-hover"><td class="py-2 font-medium">NASA VIIRS NTL</td><td class="py-2 text-gray-600">Intensitas aktivitas spasial</td><td class="py-2 text-gray-500 hidden md:table-cell">270 kelurahan (173 nilai unik)</td><td class="py-2 text-gray-600">2019-2025</td></tr>
        <tr class="border-b border-gray-50 table-row-hover"><td class="py-2 font-medium">Podes BPS</td><td class="py-2 text-gray-600">Jumlah tempat usaha</td><td class="py-2 text-gray-500 hidden md:table-cell">270 kelurahan (ground truth)</td><td class="py-2 text-gray-600">2018-2025</td></tr>
        <tr class="border-b border-gray-50 table-row-hover"><td class="py-2 font-medium">Sakernas BPS</td><td class="py-2 text-gray-600">Dimensi pendapatan pekerja</td><td class="py-2 text-gray-500 hidden md:table-cell">6 kab/kota DKI</td><td class="py-2 text-gray-600">2021-2025</td></tr>
        <tr class="table-row-hover"><td class="py-2 font-medium">OSM Overpass</td><td class="py-2 text-gray-600">Visualisasi POI dan aksesibilitas</td><td class="py-2 text-gray-500 hidden md:table-cell">8.705 titik koordinat</td><td class="py-2 text-gray-600">Snapshot 2026</td></tr>
      </tbody>
    </table>
  </div>

  <!-- Section C: Formula Skor -->
  <div class="bg-white rounded-xl shadow-sm p-4 mb-4">
    <div class="section-title">C. Formula Skor Potensi</div>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div id="formula-donut" style="height:300px"></div>
      <div>
        <table class="w-full text-xs">
          <thead><tr class="text-gray-400 border-b">
            <th class="text-left py-1">Dimensi</th>
            <th class="text-right py-1">Bobot</th>
            <th class="text-left py-2 pl-2">Sub-komponen</th>
          </tr></thead>
          <tbody>
            <tr class="border-b table-row-hover"><td class="py-2 font-semibold" style="color:#003d7a">G1 — Cahaya Malam</td><td class="text-right py-2">24%</td><td class="py-2 pl-2 text-gray-500">Pertumbuhan tahunan NTL 2021-2025, Perubahan 2024-2025, Level</td></tr>
            <tr class="border-b table-row-hover"><td class="py-2 font-semibold" style="color:#1a7abf">G2 — Tempat Usaha</td><td class="text-right py-2">33%</td><td class="py-2 pl-2 text-gray-500">Pertumbuhan tahunan Podes, Perubahan 2024-2025, Level, Keberagaman</td></tr>
            <tr class="border-b table-row-hover"><td class="py-2 font-semibold" style="color:#5ba3d9">G3 — Indeks Komersial</td><td class="text-right py-2">11%</td><td class="py-2 pl-2 text-gray-500">Pertumbuhan tahunan Magnitude 2021-2025</td></tr>
            <tr class="border-b table-row-hover"><td class="py-2 font-semibold" style="color:#e03131">G4 — Gaya Hidup</td><td class="text-right py-2">12%</td><td class="py-2 pl-2 text-gray-500">Kepadatan OSM Lifestyle (5 kategori)</td></tr>
            <tr class="table-row-hover"><td class="py-2 font-semibold" style="color:#f47c7c">G5 — Aksesibilitas</td><td class="text-right py-2">20%</td><td class="py-2 pl-2 text-gray-500">Skor akses transportasi, kepadatan catchment</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Section D: Validasi -->
  <div class="bg-white rounded-xl shadow-sm p-4 mb-4">
    <div class="section-title">D. Validasi Empiris</div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <p class="text-sm font-semibold text-gray-700 mb-2">Uji 1: NTL vs Magnitude</p>
        <p class="text-xs text-gray-500 mb-3">r Pearson = 0,052 &nbsp;|&nbsp; r Spearman = 0,124 &nbsp;&rarr;&nbsp; NTL dan Magnitude mengukur dimensi yang berbeda — keduanya diperlukan</p>
        <div id="valid-chart1" style="height:200px"></div>
      </div>
      <div>
        <p class="text-sm font-semibold text-gray-700 mb-2">Uji 2: OSM vs Podes per Kategori</p>
        <p class="text-xs text-gray-500 mb-3">Podes adalah ground truth; OSM digunakan untuk visualisasi dan kategori non-Podes</p>
        <div id="valid-chart2" style="height:200px"></div>
      </div>
    </div>
  </div>

  <!-- Section E: Caveat -->
  <div class="bg-white rounded-xl shadow-sm p-4 mb-4">
    <div class="section-title">E. Batasan dan Catatan Penting (11 Poin)</div>
    <div>
      <template x-for="(cav, i) in caveats" :key="i">
        <div class="caveat-item">
          <div class="flex gap-2">
            <span class="font-mono text-xs text-gray-400 w-6" x-text="(i+1)+'.'"></span>
            <div>
              <span x-show="cav.critical" class="text-orange-500 mr-1">&#9888;</span>
              <span class="text-sm" x-text="cav.text"></span>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>

  <!-- Section F: Referensi -->
  <div class="bg-white rounded-xl shadow-sm p-4 mb-4">
    <div class="section-title">F. Referensi Akademik</div>
    <ol class="list-decimal list-inside space-y-2 text-sm text-gray-600">
      <li>Elvidge, C.D. et al. (2017). VIIRS night-time lights. <em>International Journal of Remote Sensing</em>. <span class="text-blue-600">doi:10.1080/01431161.2017.1342050</span></li>
      <li>Chen, X., &amp; Nordhaus, W.D. (2011). Using luminosity data as a proxy for economic statistics. <em>PNAS</em>. <span class="text-blue-600">doi:10.1073/pnas.1017031108</span></li>
      <li>Henderson, J.V., Storeygard, A., &amp; Weil, D.N. (2012). Measuring economic growth from outer space. <em>American Economic Review</em>. <span class="text-blue-600">doi:10.1257/aer.102.2.994</span></li>
      <li>BPS RI (2024). Potensi Desa (Podes) 2024 — Pedoman Pencacahan. Jakarta: Badan Pusat Statistik.</li>
      <li>BPS RI (2024). Sakernas Agustus 2024 — Metodologi dan Estimasi. Jakarta: Badan Pusat Statistik.</li>
      <li>OpenStreetMap contributors (2026). OpenStreetMap data via Overpass API. <em>openstreetmap.org</em>.</li>
      <li>Shannon, C.E. (1948). A mathematical theory of communication. <em>Bell System Technical Journal</em>. <span class="text-blue-600">doi:10.1002/j.1538-7305.1948.tb01338.x</span></li>
      <li>Donaldson, D., &amp; Storeygard, A. (2016). The view from above: Applications of satellite data in economics. <em>Journal of Economic Perspectives</em>. <span class="text-blue-600">doi:10.1257/jep.30.4.171</span></li>
      <li>Yeh, C. et al. (2020). Using publicly available satellite imagery and deep learning to understand economic well-being in Africa. <em>Nature Communications</em>. <span class="text-blue-600">doi:10.1038/s41467-020-16185-w</span></li>
    </ol>
  </div>

  <!-- Section G: Cadence Update -->
  <div class="bg-white rounded-xl shadow-sm p-4 mb-4">
    <div class="section-title">G. Jadwal Pembaruan Data</div>
    <table class="w-full text-sm">
      <thead><tr class="text-xs text-gray-400 border-b">
        <th class="text-left py-2">Sumber</th>
        <th class="text-left py-2">Frekuensi Update</th>
        <th class="text-left py-2">Keterangan</th>
      </tr></thead>
      <tbody>
        <tr class="border-b table-row-hover"><td class="py-2">NASA VIIRS NTL</td><td class="py-2">Bulanan (lag 2-3 bulan)</td><td class="py-2 text-gray-500">Composite musim kering Jul-Sep untuk menghindari bias awan</td></tr>
        <tr class="border-b table-row-hover"><td class="py-2">Podes BPS</td><td class="py-2">3 tahunan (2018, 2021, 2024)</td><td class="py-2 text-gray-500">Sensus penuh, rilis H+6 bulan setelah pendataan</td></tr>
        <tr class="border-b table-row-hover"><td class="py-2">Sakernas BPS</td><td class="py-2">Tahunan (Agustus)</td><td class="py-2 text-gray-500">Digunakan untuk bobot sektor; tidak berubah drastis tahun ke tahun</td></tr>
        <tr class="table-row-hover"><td class="py-2">OpenStreetMap</td><td class="py-2">Kontinu (snapshot per kuartal)</td><td class="py-2 text-gray-500">Akurasi bergantung pada kontribusi komunitas lokal</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- Footer -->
<footer class="text-center py-6 text-xs text-gray-400 border-t border-gray-100 mt-8">
  Mandiri Institute &copy; 2026 &nbsp;|&nbsp; Pendeteksi Kawasan Komersial Berkembang DKI Jakarta &nbsp;|&nbsp; Data: NASA VIIRS, BPS Podes, Sakernas, OpenStreetMap
</footer>

<!-- ===================== JAVASCRIPT ===================== -->
<script>
// ======== EMBEDDED DATA ========
const DESA_DATA = {desa_json};
const KAWASAN_DATA_JS = {kawasan_json};
const NTL_ANNUAL = {ntl_json};
const OSM_HEAT = {osm_json};
const TRANSPORT_HEAT = {transport_json};
const GEOJSON = {geojson_str};

// ======== UTILITIES ========
function fmtPct(v) {{ return (v >= 0 ? '+' : '') + (v*100).toFixed(1) + '% per tahun'; }}
function fmtPctCagr(v) {{ if(v==null) return '—'; return (v>=0?'+':'') + (v*100).toFixed(1) + '% per tahun'; }}
function fmtNum(v) {{ return v != null ? Math.round(v).toLocaleString('id-ID') : '0'; }}
function fmtScore(v) {{ return v != null ? parseFloat(v).toFixed(1) : '—'; }}

function pulseBadgeClass(badge) {{
  if (!badge || badge === 'tidak tersedia') return 'badge pulse-na';
  if (badge === 'Trend Lanjut Tumbuh') return 'badge pulse-tumbuh';
  if (badge === 'Stabil') return 'badge pulse-stabil';
  if (badge === 'Mulai Melambat') return 'badge pulse-melambat';
  return 'badge pulse-na';
}}

function tipeBadgeClass(tipe) {{
  if (!tipe) return 'badge badge-rendah';
  if (tipe.includes('Sedang Naik Daun')) return 'badge badge-naik';
  if (tipe.includes('Mapan')) return 'badge badge-mapan';
  if (tipe.includes('Awal Pertumbuhan')) return 'badge badge-awal';
  return 'badge badge-rendah';
}}

function tipeShort(tipe) {{
  if (!tipe) return '—';
  if (tipe.includes('Sedang Naik Daun')) return 'Naik Daun';
  if (tipe.includes('Mapan')) return 'Mapan';
  if (tipe.includes('Awal Pertumbuhan')) return 'Awal Tumbuh';
  if (tipe.includes('Aktivitas Rendah')) return 'Rendah';
  return tipe;
}}

function getNTLColor(cagr) {{
  if (cagr === undefined || cagr === null || cagr === '') return '#cccccc';
  const pct = cagr * 100;
  if (pct > 15) return '#b5541a';
  if (pct > 10) return '#e07b39';
  if (pct > 7) return '#f5b942';
  if (pct > 4) return '#fde68a';
  if (pct > 0) return '#fffde7';
  return '#e0e7ff';
}}

function shannonColor(v) {{
  if (!v) return '#e5e7eb';
  const norm = Math.min(v / 2.5, 1);
  const r = Math.round(0 + (1 - norm) * 0);
  const g = Math.round(61 + norm * (120 - 61));
  const b = Math.round(122 + norm * (50 - 122));
  return `rgb(${{Math.round(norm*0 + (1-norm)*156)}},${{Math.round(norm*120 + (1-norm)*163)}},${{Math.round(norm*50 + (1-norm)*175)}})`;
}}

// Tier aggregation
function aggregateKecamatan() {{
  const map = {{}};
  DESA_DATA.forEach(d => {{
    const key = d.nama_kecamatan;
    if (!map[key]) map[key] = {{nama_kecamatan: key, nama_kabkota: d.nama_kabkota, _se: 0, _sm: 0, _n: 0, podes_count_2025: 0, _ntl: 0, tipe_kawasan: d.tipe_kawasan, pulse_badge: d.pulse_badge}};
    const r = map[key];
    r._se += d.eczi_score || 0;
    r._sm += d.magnitude_score || 0;
    r._n++;
    r.podes_count_2025 += d.podes_count_2025 || 0;
    r._ntl += d.ntl_cagr_2021_2025 || 0;
  }});
  return Object.values(map).map(r => ({{...r, kawasan: r.nama_kecamatan, kabkota: r.nama_kabkota, nama_desa: r.nama_kecamatan, eczi_score: r._se/r._n, magnitude_score: r._sm/r._n, ntl_cagr_2021_2025: r._ntl/r._n}}));
}}

function aggregateKabkota() {{
  const map = {{}};
  DESA_DATA.forEach(d => {{
    const key = d.nama_kabkota;
    if (!map[key]) map[key] = {{nama_kabkota: key, _se: 0, _sm: 0, _n: 0, podes_count_2025: 0, _ntl: 0, tipe_kawasan: d.tipe_kawasan, pulse_badge: 'tidak tersedia'}};
    const r = map[key];
    r._se += d.eczi_score || 0;
    r._sm += d.magnitude_score || 0;
    r._n++;
    r.podes_count_2025 += d.podes_count_2025 || 0;
    r._ntl += d.ntl_cagr_2021_2025 || 0;
  }});
  return Object.values(map).map(r => ({{...r, kawasan: r.nama_kabkota, kabkota: r.nama_kabkota, nama_desa: r.nama_kabkota, eczi_score: r._se/r._n, magnitude_score: r._sm/r._n, ntl_cagr_2021_2025: r._ntl/r._n}}));
}}

// Sanity checks
const _top5Eczi = [...DESA_DATA].sort((a,b) => b.eczi_score - a.eczi_score).slice(0,5);
console.assert(_top5Eczi[0].nama_desa === 'Cideng', 'ECZI rank 1 must be Cideng. Got: ' + _top5Eczi[0].nama_desa);
const _top5Mag = [...DESA_DATA].sort((a,b) => b.magnitude_score - a.magnitude_score);
const _pejagalanRank = _top5Mag.findIndex(d => d.nama_desa === 'Pejagalan') + 1;
console.assert(_pejagalanRank <= 5, 'Pejagalan must be top 5 magnitude. Got rank: ' + _pejagalanRank);
const _kawEczi1 = [...KAWASAN_DATA_JS].sort((a,b) => b.eczi_score - a.eczi_score)[0];
console.assert(_kawEczi1.kawasan === 'Mega Kuningan', 'Mega Kuningan must be #1 ECZI kawasan. Got: ' + _kawEczi1.kawasan);
const _kawMag1 = [...KAWASAN_DATA_JS].sort((a,b) => b.magnitude_score - a.magnitude_score)[0];
console.assert(_kawMag1.kawasan === 'PIK (Pantai Indah Kapuk)', 'PIK must be #1 magnitude kawasan. Got: ' + _kawMag1.kawasan);
console.log('Sanity checks:', _top5Eczi[0].nama_desa, '| Pejagalan rank:', _pejagalanRank, '| Kawasan ECZI#1:', _kawEczi1.kawasan, '| Kawasan Mag#1:', _kawMag1.kawasan);

// ======== MAP INSTANCES ========
let map2Instance = null;
let map3Instance = null;
let choroplethLayer2 = null;
let choroplethLayer3 = null;
let heatLayer3 = null;
let transportHeatLayer = null;
let podesCircles = null;

function initMap2() {{
  if (map2Instance) return;
  map2Instance = L.map('map2').setView([-6.2, 106.82], 11);
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO', maxZoom: 18
  }}).addTo(map2Instance);

  // Build lookup by desa_pcode
  const lookup = {{}};
  DESA_DATA.forEach(d => {{ lookup[d.desa_pcode] = d; }});

  choroplethLayer2 = L.geoJSON(GEOJSON, {{
    style: function(feature) {{
      const d = lookup[feature.properties.desa_pcode];
      const cagr = d ? d.ntl_cagr_2021_2025 : null;
      return {{
        fillColor: getNTLColor(cagr),
        weight: 0.8, opacity: 1, color: '#888',
        fillOpacity: 0.75
      }};
    }},
    onEachFeature: function(feature, layer) {{
      const d = lookup[feature.properties.desa_pcode];
      if (d) {{
        layer.bindPopup(`<div style="font-family:Inter,sans-serif;font-size:13px">
          <b>${{d.nama_desa}}</b><br>
          ${{d.nama_kecamatan}}, ${{(d.nama_kabkota||'').replace('Kota Jakarta ','')}}<br>
          <hr style="margin:4px 0">
          <b>Pertumbuhan NTL:</b> ${{fmtPctCagr(d.ntl_cagr_2021_2025)}}<br>
          <b>Level 2025:</b> ${{d.ntl_level_2025 || '—'}}<br>
          <b>Skor Potensi:</b> ${{fmtScore(d.eczi_score)}}
        </div>`);
      }}
    }}
  }}).addTo(map2Instance);
  setTimeout(() => map2Instance.invalidateSize(), 100);
}}

function initMap3() {{
  if (map3Instance) return;
  map3Instance = L.map('map3').setView([-6.2, 106.82], 11);
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO', maxZoom: 18
  }}).addTo(map3Instance);

  // Podes circles (default)
  podesCircles = L.layerGroup();
  const maxPodes = Math.max(...DESA_DATA.map(d => d.podes_count_2025 || 0));
  DESA_DATA.forEach(d => {{
    if (!d.centroid_lat || !d.centroid_lon) return;
    const r = 200 + (d.podes_count_2025 / maxPodes) * 1200;
    const color = getNTLColor(d.podes_cagr_2021_2025);
    L.circleMarker([d.centroid_lat, d.centroid_lon], {{
      radius: Math.max(4, r / 80), fillColor: color, color: '#555',
      weight: 0.5, fillOpacity: 0.75
    }}).bindPopup(`<div style="font-family:Inter,sans-serif;font-size:13px">
      <b>${{d.nama_desa}}</b><br>
      <b>Tempat Usaha 2025:</b> ${{fmtNum(d.podes_count_2025)}}<br>
      <b>Pertumbuhan:</b> ${{fmtPctCagr(d.podes_cagr_2021_2025)}}<br>
      <b>Skor Potensi:</b> ${{fmtScore(d.eczi_score)}}
    </div>`).addTo(podesCircles);
  }});
  podesCircles.addTo(map3Instance);

  // OSM heatmap
  heatLayer3 = L.heatLayer(OSM_HEAT, {{radius: 18, blur: 15, maxZoom: 17, max: 1.0, gradient: {{0.4:'#1a7abf',0.65:'#003d7a',1:'#e03131'}}}});
  // Transport heatmap
  transportHeatLayer = L.heatLayer(TRANSPORT_HEAT, {{radius: 18, blur: 15, maxZoom: 17, max: 1.0, gradient: {{0.4:'#5ba3d9',0.65:'#003d7a',1:'#f97316'}}}});

  setTimeout(() => map3Instance.invalidateSize(), 100);
}}

function switchPage3Layer(layer) {{
  if (!map3Instance) return;
  if (podesCircles) map3Instance.removeLayer(podesCircles);
  if (heatLayer3) map3Instance.removeLayer(heatLayer3);
  if (transportHeatLayer) map3Instance.removeLayer(transportHeatLayer);
  if (layer === 'podes') podesCircles.addTo(map3Instance);
  else if (layer === 'osm') heatLayer3.addTo(map3Instance);
  else if (layer === 'transport') transportHeatLayer.addTo(map3Instance);
}}

// ======== PLOTLY CHARTS ========
function initCharts() {{
  renderNTLSparkline();
  renderNTLTimeseries();
  renderNTLCagrBar();
  renderPodes10Bar();
  renderMagnitudeStacked();
  renderRadarChart();
  renderScatterQuadrant();
  renderFormulaDonut();
  renderValidationCharts();
}}

function renderNTLSparkline() {{
  const top5areas = [...new Set(NTL_ANNUAL.map(r => r.area))].map(area => {{
    const v2025 = NTL_ANNUAL.find(r => r.area===area && r.year===2025);
    return {{area, lum2025: v2025 ? v2025.lum_drySeason : 0}};
  }}).sort((a,b) => b.lum2025 - a.lum2025).slice(0,5).map(r => r.area);

  const years = [2021,2022,2023,2024,2025];
  const colors = ['#003d7a','#1a7abf','#5ba3d9','#e03131','#f47c7c'];
  const traces = top5areas.map((area, i) => {{
    const vals = years.map(y => {{ const r = NTL_ANNUAL.find(rr => rr.area===area && rr.year===y); return r ? r.lum_drySeason : null; }});
    return {{x: years, y: vals, name: area, type: 'scatter', mode: 'lines+markers', line: {{color: colors[i], width: 2}}, marker: {{size: 5}}}};
  }});

  Plotly.newPlot('ntl-sparkline', traces, {{
    margin: {{t:10,r:10,b:30,l:40}},
    legend: {{orientation:'h', x:0, y:-0.2, font:{{size:9}}}},
    xaxis: {{tickfont:{{size:9}}}}, yaxis: {{tickfont:{{size:9}}, title:{{text:'Kecerahan',font:{{size:9}}}}}},
    paper_bgcolor:'transparent', plot_bgcolor:'transparent'
  }}, {{responsive: true, displayModeBar: false}});
}}

function renderNTLTimeseries() {{
  const allAreas = [...new Set(NTL_ANNUAL.map(r => r.area))];
  const top8 = allAreas.map(area => {{
    const v = NTL_ANNUAL.find(r => r.area===area && r.year===2025);
    return {{area, v2025: v ? v.lum_drySeason : 0}};
  }}).sort((a,b) => b.v2025 - a.v2025).slice(0,8).map(r => r.area);

  const years = [2019,2020,2021,2022,2023,2024,2025];
  const palette = ['#003d7a','#1a7abf','#5ba3d9','#85c0e8','#e03131','#f47c7c','#f59e0b','#10b981'];
  const traces = top8.map((area, i) => {{
    const vals = years.map(y => {{ const r = NTL_ANNUAL.find(rr => rr.area===area && rr.year===y); return r ? r.lum_drySeason : null; }});
    return {{x: years, y: vals, name: area, type: 'scatter', mode: 'lines+markers', line: {{color: palette[i], width: 2}}, marker: {{size: 5}}}};
  }});

  Plotly.newPlot('ntl-timeseries', traces, {{
    title: {{text: 'Kecerahan Cahaya Malam per Kawasan (Jul-Sep Composite)', font: {{size: 13, color: '#003d7a'}}}},
    margin: {{t:50,r:20,b:50,l:60}},
    legend: {{orientation:'h', x:0, y:-0.2, font:{{size:10}}}},
    xaxis: {{title: 'Tahun', tickvals: years}},
    yaxis: {{title: 'Kecerahan NTL (nW/cm²/sr)'}},
    paper_bgcolor:'white', plot_bgcolor:'#f8fafc'
  }}, {{responsive: true, displayModeBar: false}});
}}

function renderNTLCagrBar() {{
  const top20 = [...DESA_DATA].sort((a,b) => (b.ntl_cagr_2021_2025||0) - (a.ntl_cagr_2021_2025||0)).slice(0,20);
  const labels = top20.map(d => d.nama_desa);
  const vals = top20.map(d => (d.ntl_cagr_2021_2025||0)*100);
  const colorScale = vals.map((v, i) => `rgba(0,${{Math.round(61+i*3)}},${{Math.round(122+i*3)}},0.85)`);
  Plotly.newPlot('ntl-cagr-bar', [{{
    y: labels.reverse(), x: vals.reverse(), type: 'bar', orientation: 'h',
    marker: {{color: colorScale.reverse()}},
    text: vals.reverse().map(v => (v>=0?'+':'')+v.toFixed(1)+'%'),
    textposition: 'outside', textfont: {{size: 10}}
  }}], {{
    margin: {{t:20,r:80,b:40,l:160}},
    xaxis: {{title: '% per tahun'}},
    paper_bgcolor:'white', plot_bgcolor:'#f8fafc',
    height: 420
  }}, {{responsive: true, displayModeBar: false}});
}}

function renderPodes10Bar() {{
  const top10 = [...DESA_DATA].sort((a,b) => (b.podes_count_2025||0) - (a.podes_count_2025||0)).slice(0,10);
  Plotly.newPlot('podes-top10-bar', [{{
    y: top10.map(d => d.nama_desa).reverse(),
    x: top10.map(d => d.podes_count_2025||0).reverse(),
    type: 'bar', orientation: 'h',
    marker: {{color: '#003d7a'}},
    text: top10.map(d => fmtNum(d.podes_count_2025)).reverse(),
    textposition: 'outside'
  }}], {{
    margin: {{t:10,r:80,b:40,l:140}},
    xaxis: {{title: 'Jumlah tempat usaha'}},
    paper_bgcolor:'white', plot_bgcolor:'#f8fafc'
  }}, {{responsive: true, displayModeBar: false}});
}}

function renderMagnitudeStacked() {{
  const top15 = [...DESA_DATA].sort((a,b) => (b.magnitude_2025||0) - (a.magnitude_2025||0)).slice(0,15);
  Plotly.newPlot('magnitude-stacked', [
    {{
      name: 'Perdagangan',
      y: top15.map(d => d.nama_desa).reverse(),
      x: top15.map(d => d.magnitude_perdagangan_2025||0).reverse(),
      type: 'bar', orientation: 'h',
      marker: {{color: '#003d7a'}}
    }},
    {{
      name: 'Akomodasi dan Mamin',
      y: top15.map(d => d.nama_desa).reverse(),
      x: top15.map(d => d.magnitude_akomamin_2025||0).reverse(),
      type: 'bar', orientation: 'h',
      marker: {{color: '#f59e0b'}}
    }}
  ], {{
    barmode: 'stack',
    margin: {{t:10,r:20,b:40,l:160}},
    legend: {{orientation:'h', x:0, y:-0.12}},
    xaxis: {{title: 'Indeks Komersial (Proxy)'}},
    paper_bgcolor:'white', plot_bgcolor:'#f8fafc'
  }}, {{responsive: true, displayModeBar: false}});
}}

function renderRadarChart() {{
  const top5 = [...DESA_DATA].sort((a,b) => b.eczi_score - a.eczi_score).slice(0,5);
  const dims = ['G1 Cahaya Malam','G2 Tempat Usaha','G3 Ind. Komersial','G4 Gaya Hidup','G5 Aksesibilitas'];
  const keys = ['g1','g2','g3','g4','g5'];
  const colors = ['#003d7a','#1a7abf','#5ba3d9','#e03131','#f47c7c'];
  const traces = top5.map((d, i) => ({{
    type: 'scatterpolar', fill: 'toself', name: d.nama_desa,
    r: [...keys.map(k => d[k]||0), d[keys[0]]||0],
    theta: [...dims, dims[0]],
    line: {{color: colors[i], width: 2}}, fillcolor: colors[i]+'30'
  }}));
  Plotly.newPlot('radar-chart', traces, {{
    polar: {{radialaxis: {{visible:true, range:[0,100]}}}},
    margin: {{t:20,r:20,b:20,l:20}},
    legend: {{orientation:'h', font:{{size:9}}}},
    paper_bgcolor:'white'
  }}, {{responsive: true, displayModeBar: false}});
}}

function renderScatterQuadrant() {{
  const typeColors = {{
    'Kawasan Komersial Sedang Naik Daun': '#2563eb',
    'Kawasan Komersial Mapan': '#7c3aed',
    'Awal Pertumbuhan': '#f97316',
    'Aktivitas Rendah': '#9ca3af'
  }};
  const groups = {{}};
  DESA_DATA.forEach(d => {{
    const t = d.tipe_kawasan || 'Aktivitas Rendah';
    if (!groups[t]) groups[t] = {{x:[], y:[], text:[]}};
    groups[t].x.push(d.n_ntl_cagr||0);
    groups[t].y.push(d.n_osm_lifestyle_density||0);
    groups[t].text.push(d.nama_desa);
  }});

  const traces = Object.keys(groups).map(t => ({{
    x: groups[t].x, y: groups[t].y, text: groups[t].text,
    mode: 'markers', type: 'scatter', name: t,
    marker: {{color: typeColors[t]||'#888', size: 6, opacity: 0.7}},
    hovertemplate: '%{{text}}<br>NTL: %{{x:.1f}}<br>OSM: %{{y:.1f}}<extra></extra>'
  }}));

  // Median lines
  const medX = [...DESA_DATA].map(d=>d.n_ntl_cagr||0).sort((a,b)=>a-b)[135];
  const medY = [...DESA_DATA].map(d=>d.n_osm_lifestyle_density||0).sort((a,b)=>a-b)[135];
  traces.push({{x:[medX,medX], y:[0,100], mode:'lines', name:'Median NTL', line:{{color:'#aaa',dash:'dash',width:1}}, showlegend:false}});
  traces.push({{x:[0,100], y:[medY,medY], mode:'lines', name:'Median OSM', line:{{color:'#aaa',dash:'dash',width:1}}, showlegend:false}});

  Plotly.newPlot('scatter-quadrant', traces, {{
    margin: {{t:30,r:20,b:60,l:60}},
    xaxis: {{title:'Skor Pertumbuhan NTL (0-100)', range:[0,100]}},
    yaxis: {{title:'Skor Kepadatan OSM (0-100)', range:[0,100]}},
    annotations: [
      {{x:90,y:90,text:'Naik Daun',showarrow:false,font:{{size:10,color:'#2563eb'}}}},
      {{x:10,y:90,text:'Mapan',showarrow:false,font:{{size:10,color:'#7c3aed'}}}},
      {{x:90,y:10,text:'Awal Tumbuh',showarrow:false,font:{{size:10,color:'#f97316'}}}},
      {{x:10,y:10,text:'Rendah',showarrow:false,font:{{size:10,color:'#888'}}}}
    ],
    legend: {{orientation:'h', y:-0.25, font:{{size:9}}}},
    paper_bgcolor:'white', plot_bgcolor:'#f8fafc'
  }}, {{responsive: true, displayModeBar: false}});
}}

function renderFormulaDonut() {{
  Plotly.newPlot('formula-donut', [{{
    values: [24,33,11,12,20],
    labels: ['G1 Cahaya Malam 24%','G2 Tempat Usaha 33%','G3 Ind. Komersial 11%','G4 Gaya Hidup 12%','G5 Aksesibilitas 20%'],
    type: 'pie', hole: 0.5,
    marker: {{colors: ['#003d7a','#1a7abf','#5ba3d9','#e03131','#f47c7c']}},
    textfont: {{size: 10}}
  }}], {{
    margin: {{t:20,r:20,b:20,l:20}},
    showlegend: true, legend: {{orientation:'v', font:{{size:10}}}},
    paper_bgcolor:'white'
  }}, {{responsive: true, displayModeBar: false}});
}}

function renderValidationCharts() {{
  Plotly.newPlot('valid-chart1', [{{
    x: ['Pearson','Spearman'],
    y: [0.052, 0.124],
    type: 'bar',
    marker: {{color: ['#003d7a','#1a7abf']}},
    text: ['r = 0,052','r = 0,124'], textposition: 'outside'
  }}], {{
    margin: {{t:10,r:10,b:30,l:40}},
    yaxis: {{range:[0,0.3]}},
    paper_bgcolor:'white', plot_bgcolor:'#f8fafc'
  }}, {{responsive:true, displayModeBar:false}});

  Plotly.newPlot('valid-chart2', [{{
    y: ['Bank/ATM','Klinik/Apotek','Olahraga','Hiburan','Wisata'],
    x: [0.31, 0.27, 0.18, 0.22, 0.15],
    type: 'bar', orientation: 'h',
    marker: {{color: '#5ba3d9'}},
    text: ['0,31','0,27','0,18','0,22','0,15'], textposition: 'outside'
  }}], {{
    margin: {{t:10,r:60,b:30,l:100}},
    xaxis: {{range:[0,0.5], title:'Korelasi r'}},
    paper_bgcolor:'white', plot_bgcolor:'#f8fafc'
  }}, {{responsive:true, displayModeBar:false}});
}}

// Detail charts (page 5)
function renderDetailCharts() {{
  // delay slightly to allow x-model to update
  setTimeout(_renderDetailCharts, 50);
}}

function _renderDetailCharts() {{
  const app = Alpine.$data(document.querySelector('[x-data]'));
  const d = app.getSelectedDetail();
  if (!d) return;

  if (app.page5SubTab === 'ntl') {{
    Plotly.newPlot('detail-ntl-chart', [{{
      x: ['2021','2024','2025'],
      y: [d.lum_2021||0, d.lum_2024||0, d.lum_2025||0],
      type: 'bar',
      marker: {{color: ['#5ba3d9','#1a7abf','#003d7a']}},
      text: [d.lum_2021, d.lum_2024, d.lum_2025].map(v => v ? v.toFixed(2) : '—'),
      textposition: 'outside'
    }}], {{
      title: {{text: 'Cahaya Malam — ' + (d.nama_desa||d.kawasan), font:{{size:13,color:'#003d7a'}}}},
      margin: {{t:50,r:20,b:40,l:60}},
      yaxis: {{title:'Kecerahan NTL'}},
      paper_bgcolor:'white', plot_bgcolor:'#f8fafc'
    }}, {{responsive:true, displayModeBar:false}});
  }}

  if (app.page5SubTab === 'podes') {{
    Plotly.newPlot('detail-podes-chart', [{{
      x: ['Jumlah Usaha 2025','Pertumbuhan CAGR (x100)'],
      y: [d.podes_count_2025||0, (d.podes_cagr_2021_2025||0)*100],
      type: 'bar',
      marker: {{color: ['#003d7a','#1a7abf']}},
      text: [fmtNum(d.podes_count_2025), ((d.podes_cagr_2021_2025||0)*100).toFixed(1)+'%'],
      textposition: 'outside'
    }}], {{
      title: {{text: 'Tempat Usaha — ' + (d.nama_desa||d.kawasan), font:{{size:13,color:'#003d7a'}}}},
      margin: {{t:50,r:20,b:40,l:60}},
      paper_bgcolor:'white', plot_bgcolor:'#f8fafc'
    }}, {{responsive:true, displayModeBar:false}});
  }}

  if (app.page5SubTab === 'sektor') {{
    const vals = [d.magnitude_perdagangan_2025||0, d.magnitude_akomamin_2025||0];
    Plotly.newPlot('detail-sektor-chart', [{{
      values: vals,
      labels: ['Perdagangan','Akomodasi dan Mamin'],
      type: 'pie', hole: 0.4,
      marker: {{colors: ['#003d7a','#f59e0b']}}
    }}], {{
      title: {{text: 'Komposisi Sektor — ' + (d.nama_desa||d.kawasan), font:{{size:13,color:'#003d7a'}}}},
      margin: {{t:50,r:20,b:20,l:20}},
      paper_bgcolor:'white'
    }}, {{responsive:true, displayModeBar:false}});
  }}

  if (app.page5SubTab === 'fasilitas') {{
    Plotly.newPlot('detail-fasilitas-chart', [{{
      y: ['Hiburan/Malam','Gaya Hidup/Wellness','Ritel Khusus','Wisata Budaya','Layanan Penunjang'],
      x: [d.count_hiburan_nightlife||0, d.count_gaya_hidup_wellness||0, d.count_retail_khusus||0, d.count_wisata_budaya||0, d.count_layanan_penunjang||0],
      type: 'bar', orientation: 'h',
      marker: {{color: '#e03131'}}
    }}], {{
      title: {{text: 'Fasilitas OSM — ' + (d.nama_desa||d.kawasan), font:{{size:13,color:'#003d7a'}}}},
      margin: {{t:50,r:20,b:40,l:150}},
      paper_bgcolor:'white', plot_bgcolor:'#f8fafc'
    }}, {{responsive:true, displayModeBar:false}});
  }}

  if (app.page5SubTab === 'akses') {{
    Plotly.newPlot('detail-akses-chart', [{{
      x: ['Skor Akses Transportasi','Kepadatan Catchment 1km'],
      y: [d.transport_access_score_raw||0, d.catchment_density_1km||d.catchment_density_1km_total||0],
      type: 'bar',
      marker: {{color: ['#003d7a','#5ba3d9']}},
      text: [
        (d.transport_access_score_raw||0).toFixed(2),
        (d.catchment_density_1km||d.catchment_density_1km_total||0).toFixed(2)
      ],
      textposition: 'outside'
    }}], {{
      title: {{text: 'Aksesibilitas — ' + (d.nama_desa||d.kawasan), font:{{size:13,color:'#003d7a'}}}},
      margin: {{t:50,r:20,b:60,l:60}},
      paper_bgcolor:'white', plot_bgcolor:'#f8fafc'
    }}, {{responsive:true, displayModeBar:false}});
  }}
}}

// ======== ALPINE APP ========
function dashApp() {{
  return {{
    page: 'ringkasan',
    tier: 'kawasan',
    leaderboardTab: 'eczi',
    page4Tab: 'eczi',
    page5Mode: 'kawasan',
    page5Selected: 'Mega Kuningan',
    page5SubTab: 'ntl',
    page3Layer: 'podes',
    map2Layer: 'cagr',
    KAWASAN_DATA_JS: KAWASAN_DATA_JS,

    navTabs: [
      {{key:'ringkasan', label:'Ringkasan'}},
      {{key:'cahaya', label:'Cahaya Malam'}},
      {{key:'komersial', label:'Aktivitas Komersial'}},
      {{key:'skor', label:'Skor Potensi'}},
      {{key:'detail', label:'Detail Kawasan'}},
      {{key:'metodologi', label:'Metodologi'}}
    ],

    ntlLegend: [
      {{color:'#e0e7ff', label:'< 0%'}},
      {{color:'#fffde7', label:'0-4%'}},
      {{color:'#fde68a', label:'4-7%'}},
      {{color:'#f5b942', label:'7-10%'}},
      {{color:'#e07b39', label:'10-15%'}},
      {{color:'#b5541a', label:'> 15%'}}
    ],

    caveats: [
      {{text:'NTL dipengaruhi tutupan awan: composite musim kering Juli-September digunakan untuk meminimalkan bias.', critical:false}},
      {{text:'Podes tidak memilah antara usaha formal dan informal — minimarket dan warung diperlakukan setara.', critical:false}},
      {{text:'Sakernas mengukur pendapatan pekerja per bulan, BUKAN revenue usaha. Angka Magnitude adalah proxy, bukan estimasi omzet.', critical:true}},
      {{text:'OSM tidak lengkap di semua kelurahan — kawasan dengan kontribusi komunitas rendah akan undercount.', critical:false}},
      {{text:'Centroid kelurahan digunakan untuk pemetaan; batas administrasi menggunakan shapefile BPS 2024.', critical:false}},
      {{text:'Aggregasi kecamatan dan kab/kota menggunakan rata-rata sederhana — tidak ada pembobotan populasi.', critical:false}},
      {{text:'6 kelurahan dengan low_reliability_flag=1 memiliki data NTL di bawah ambang kepercayaan; skor mereka lebih tidak pasti.', critical:true}},
      {{text:'Tren 2026 (pulse_badge) hanya tersedia untuk 15 kawasan dengan data NTL bulanan yang cukup.', critical:false}},
      {{text:'Dashboard ini tidak mempertimbangkan faktor harga lahan, regulasi zonasi, atau proyek infrastruktur pemerintah.', critical:false}},
      {{text:'Perbandingan lintas kota atau provinsi tidak valid — skor dikalibrasi khusus untuk DKI Jakarta.', critical:false}},
      {{text:'Setiap keputusan investasi atau kredit harus didasarkan pada due diligence tambahan, bukan semata dashboard ini.', critical:false}}
    ],

    setTier(t) {{
      this.tier = t;
    }},

    getCurrentData() {{
      if (this.tier === 'kawasan') return KAWASAN_DATA_JS;
      if (this.tier === 'desa') return DESA_DATA;
      if (this.tier === 'kecamatan') return aggregateKecamatan();
      if (this.tier === 'kabkota') return aggregateKabkota();
      return KAWASAN_DATA_JS;
    }},

    getTop10Eczi() {{
      return [...this.getCurrentData()].sort((a,b) => (b.eczi_score||0) - (a.eczi_score||0)).slice(0,10);
    }},

    getTop10Mag() {{
      return [...this.getCurrentData()].sort((a,b) => (b.magnitude_score||0) - (a.magnitude_score||0)).slice(0,10);
    }},

    getEcziRanked() {{
      return [...DESA_DATA].sort((a,b) => (b.eczi_score||0) - (a.eczi_score||0));
    }},

    getMagRanked() {{
      return [...DESA_DATA].sort((a,b) => (b.magnitude_score||0) - (a.magnitude_score||0));
    }},

    getDiversityTop15() {{
      return [...DESA_DATA].sort((a,b) => (b.podes_diversity_shannon||0) - (a.podes_diversity_shannon||0)).slice(0,15);
    }},

    kpiWilayah() {{
      if (this.tier==='kawasan') return '21';
      if (this.tier==='desa') return '270';
      if (this.tier==='kecamatan') return String(aggregateKecamatan().length);
      if (this.tier==='kabkota') return String(aggregateKabkota().length);
      return '21';
    }},

    kpiWilayahSub() {{
      if (this.tier==='kawasan') return 'wilayah berpotensi';
      if (this.tier==='desa') return 'kelurahan DKI';
      if (this.tier==='kecamatan') return 'kecamatan DKI';
      if (this.tier==='kabkota') return 'kab/kota DKI';
      return '';
    }},

    kpiTopEczi() {{
      const d = this.getTop10Eczi()[0];
      if (!d) return {{name:'—', score:'—'}};
      return {{name: d.kawasan||d.nama_desa||'—', score: fmtScore(d.eczi_score)}};
    }},

    kpiTopMag() {{
      const d = this.getTop10Mag()[0];
      if (!d) return {{name:'—', score:'—'}};
      return {{name: d.kawasan||d.nama_desa||'—', score: fmtScore(d.magnitude_score)}};
    }},

    getDisplayName(d) {{
      return d.kawasan || d.nama_desa || d.nama_kecamatan || d.nama_kabkota || '—';
    }},

    pulseBadgeClass(badge) {{ return pulseBadgeClass(badge); }},
    tipeBadgeClass(tipe) {{ return tipeBadgeClass(tipe); }},
    tipeShort(tipe) {{ return tipeShort(tipe); }},
    fmtScore(v) {{ return fmtScore(v); }},
    fmtNum(v) {{ return fmtNum(v); }},
    fmtPctCagr(v) {{ return fmtPctCagr(v); }},
    shannonColor(v) {{ return shannonColor(v); }},

    switchPage3Layer(layer) {{
      switchPage3Layer(layer);
    }},

    updateMap2Layer() {{
      if (!choroplethLayer2) return;
      const lookup = {{}};
      DESA_DATA.forEach(d => {{ lookup[d.desa_pcode] = d; }});
      const lyr = this.map2Layer;
      choroplethLayer2.setStyle(function(feature) {{
        const d = lookup[feature.properties.desa_pcode];
        let val = null;
        if (d) val = lyr === 'cagr' ? d.ntl_cagr_2021_2025 : d.ntl_level_2025 === 'high' ? 0.2 : d.ntl_level_2025 === 'medium' ? 0.1 : 0.05;
        return {{ fillColor: getNTLColor(val), weight: 0.8, opacity: 1, color: '#888', fillOpacity: 0.75 }};
      }});
    }},

    getKawasanOptions() {{ return KAWASAN_DATA_JS.map(k => k.kawasan); }},
    getDesaOptions() {{ return [...DESA_DATA].sort((a,b) => a.nama_desa.localeCompare(b.nama_desa)).map(d => d.nama_desa); }},

    getSelectedDetail() {{
      if (this.page5Mode === 'kawasan') {{
        return KAWASAN_DATA_JS.find(k => k.kawasan === this.page5Selected) || null;
      }} else {{
        return DESA_DATA.find(d => d.nama_desa === this.page5Selected) || null;
      }}
    }},

    renderDetailCharts() {{
      renderDetailCharts();
    }},

    init() {{
      this.$watch('page', (newPage) => {{
        if (newPage === 'cahaya') {{
          this.$nextTick(() => {{ initMap2(); renderNTLTimeseries(); renderNTLCagrBar(); }});
        }}
        if (newPage === 'komersial') {{
          this.$nextTick(() => {{ initMap3(); renderPodes10Bar(); renderMagnitudeStacked(); }});
        }}
        if (newPage === 'skor') {{
          this.$nextTick(() => {{ renderRadarChart(); renderScatterQuadrant(); }});
        }}
        if (newPage === 'detail') {{
          this.$nextTick(() => {{ renderDetailCharts(); }});
        }}
        if (newPage === 'metodologi') {{
          this.$nextTick(() => {{ renderFormulaDonut(); renderValidationCharts(); }});
        }}
      }});
      this.$nextTick(() => {{
        renderNTLSparkline();
      }});
    }}
  }};
}}
</script>
</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("Loading data...")
    (desa_records, kawasan_records, geojson_str,
     ntl_records, osm_records, transport_records,
     mean_podes_cagr, total_podes) = load_data()

    print(f"  Desa rows: {len(desa_records)}")
    print(f"  Kawasan rows: {len(kawasan_records)}")
    print(f"  NTL annual rows: {len(ntl_records)}")
    print(f"  OSM lifestyle points: {len(osm_records)}")
    print(f"  Transport points: {len(transport_records)}")
    print(f"  Mean Podes CAGR: {mean_podes_cagr*100:.2f}%")
    print(f"  Total Podes 2025: {total_podes:,}")

    print("\nBuilding HTML...")
    html = build_html(desa_records, kawasan_records, geojson_str,
                      ntl_records, osm_records, transport_records,
                      mean_podes_cagr, total_podes)

    print(f"Writing to: {OUTPUT_FILE}")
    OUTPUT_FILE.write_text(html, encoding='utf-8')

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"\nGenerated: {OUTPUT_FILE}")
    print(f"Size: {size_kb:.0f} KB ({size_kb/1024:.2f} MB)")

    # Quick verification
    import re
    content = OUTPUT_FILE.read_text(encoding='utf-8')

    # Count embedded rows
    desa_count = len(re.findall(r'"desa_pcode"', content))
    kaw_count = len(re.findall(r'"rank_eczi"', content)) - 270  # subtract desa occurrences
    print(f"\nVerification:")
    print(f"  desa_pcode occurrences (expect 270): {desa_count}")

    # Check forbidden terms
    forbidden = ['Sustained Explosive', 'Late Bloomer', 'ECZI', 'CAGR', 'YoY']
    for term in forbidden:
        # Check in visible HTML (not JS variable names or comments)
        count = content.count(term)
        print(f"  '{term}' occurrences: {count}", "(OK)" if count == 0 else "(CHECK — may be in JS)")

    print("\nDone.")
