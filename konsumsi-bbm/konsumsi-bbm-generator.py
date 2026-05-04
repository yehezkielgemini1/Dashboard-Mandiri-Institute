"""
Generator dashboard Konsumsi BBM per Kelas Masyarakat (2019-2025).
Input: 260423_Data Harga BBM_stata.xlsx (sheet 'Per Kelas Detail').
Output: konsumsi-bbm-dashboard.html (single file, data embed).
Stack: Plotly.js + Tailwind CSS (CDN), Alpine.js untuk filter dropdown.
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd

SRC = Path(
    r"C:\Users\LENOVO\OneDrive - PT Bank Mandiri (Persero) Tbk\Desktop\Mandiri"
    r"\Mandiri Institute\Deck\Kelas Masyarakat\Konsumsi\Konsumsi_BBM"
    r"\260423_Data Harga BBM_stata.xlsx"
)
HERE = Path(__file__).parent
OUT = HERE / "konsumsi-bbm-dashboard.html"
PROV_CSV = HERE / "bbm_provinsi_kelas_stata.csv"
GEOJSON = HERE / "provinsi_bps_simplified.geojson"

# Pemekaran Papua 2022+ tidak ada di shapefile BPS 2020. Agregasi ke induk untuk peta.
PEMEKARAN_MAP = {
    92: 94,   # Papua Barat Daya -> Papua Barat
    95: 91,   # Papua Selatan -> Papua
    96: 91,   # Papua Tengah -> Papua
    97: 91,   # Papua Pegunungan -> Papua
}

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
CLASSES = ["Poor", "Vulnerable", "Lower AMC", "Upper AMC",
           "Lower MC", "Middle MC", "Upper MC", "Upper Class"]
FUELS = ["Tidak beli", "Premium", "Pertalite", "Pertamax", "Pertamax Turbo"]

# Mandiri palette
COLORS = {
    "Tidak beli": "#B6B8BA",       # Grey
    "Premium": "#EA7200",          # Orange
    "Pertalite": "#FFB700",        # Yellow
    "Pertamax": "#67B2E8",         # Sky Blue
    "Pertamax Turbo": "#003D79",   # Mandiri Blue
}


def parse():
    raw = pd.read_excel(SRC, sheet_name="Per Kelas Detail", header=None)
    data = {}
    for i, year in enumerate(YEARS):
        # "Tahun XXXX" at row 4 + i*9, header row+1, data rows+2..+6
        base = 4 + i * 9
        assert str(raw.iloc[base, 0]).strip() == f"Tahun {year}", f"Expected 'Tahun {year}' at row {base}, got {raw.iloc[base,0]}"
        header_row = raw.iloc[base + 1].tolist()
        assert str(header_row[0]).strip() == "Jenis BBM", f"Row offset wrong at year {year}"
        year_matrix = {}
        for j, fuel in enumerate(FUELS):
            row = raw.iloc[base + 2 + j].tolist()
            assert str(row[0]).strip() == fuel, f"Fuel mismatch year {year}: {row[0]} vs {fuel}"
            year_matrix[fuel] = [float(row[1 + k]) for k in range(len(CLASSES))]
        # total konsumen per kelas (buyers + non-buyers) untuk hitung %
        totals = [sum(year_matrix[f][k] for f in FUELS) for k in range(len(CLASSES))]
        data[year] = {"raw": year_matrix, "totals": totals}
    return data


def insights(data):
    """Kumpulan insight ringkas: pergeseran 2019 vs 2025 per kelas (buyers only)."""
    def buyer_share(year, kelas_idx, fuel):
        buyers_total = sum(
            data[year]["raw"][f][kelas_idx] for f in FUELS if f != "Tidak beli"
        )
        if buyers_total == 0:
            return 0.0
        return data[year]["raw"][fuel][kelas_idx] / buyers_total * 100

    rows = []
    for k, kelas in enumerate(CLASSES):
        pert_2019 = buyer_share(2019, k, "Pertalite")
        pert_2025 = buyer_share(2025, k, "Pertalite")
        pmax_2019 = buyer_share(2019, k, "Pertamax")
        pmax_2025 = buyer_share(2025, k, "Pertamax")
        rows.append({
            "kelas": kelas,
            "pertalite_2019": round(pert_2019, 1),
            "pertalite_2025": round(pert_2025, 1),
            "pertamax_2019": round(pmax_2019, 1),
            "pertamax_2025": round(pmax_2025, 1),
            "delta_pertalite": round(pert_2025 - pert_2019, 1),
            "delta_pertamax": round(pmax_2025 - pmax_2019, 1),
        })
    return rows


def parse_provinsi():
    """
    Baca CSV provinsi, agregasi pemekaran Papua ke induk, hitung share buyers-only
    per (tahun, kelas/All, jenis BBM, prov).

    Return:
      prov_meta: {pcode: nama}
      prov_data: {year: {kelas: {fuel: {pcode: share_buyers_only_pct}}}}
                 kelas includes "All" (agregasi semua kelas).
    """
    df = pd.read_csv(PROV_CSV)
    df["kode_prov"] = df["kode_prov"].replace(PEMEKARAN_MAP)
    df["pcode"] = "ID" + df["kode_prov"].astype(int).astype(str).str.zfill(2)
    # Re-aggregate n_tertimbang after pemekaran merge
    agg = (df.groupby(["tahun", "pcode", "kelas", "jenis_bbm"])
             ["n_tertimbang"].sum().reset_index())

    # nama prov (ambil yang induk)
    prov_meta = (df.groupby("pcode")["nama_prov"].first().to_dict())

    # Build nested dict
    out = {}
    buyers_mask = agg["jenis_bbm"] != "Tidak beli"
    for year in YEARS:
        out[year] = {}
        year_df = agg[agg["tahun"] == year]

        # Per kelas
        for kelas in CLASSES:
            k_df = year_df[year_df["kelas"] == kelas]
            out[year][kelas] = _shares(k_df, buyers_only=True)
        # All kelas
        all_df = (year_df.groupby(["pcode", "jenis_bbm"])
                         ["n_tertimbang"].sum().reset_index())
        out[year]["All"] = _shares(all_df, buyers_only=True)
    return prov_meta, out


def _shares(sub, buyers_only=True):
    """Given df with cols pcode, jenis_bbm, n_tertimbang: return {fuel: {pcode: pct}}."""
    if buyers_only:
        sub = sub[sub["jenis_bbm"] != "Tidak beli"]
    totals = sub.groupby("pcode")["n_tertimbang"].sum()
    fuels = ["Premium", "Pertalite", "Pertamax", "Pertamax Turbo"]
    result = {}
    for fuel in fuels:
        f_df = sub[sub["jenis_bbm"] == fuel].set_index("pcode")["n_tertimbang"]
        result[fuel] = {
            p: round(float(f_df.get(p, 0)) / float(totals[p]) * 100, 2)
            for p in totals.index if totals[p] > 0
        }
    return result


def load_geojson():
    with open(GEOJSON, "r", encoding="utf-8") as f:
        return json.load(f)


def build_html(data, insight_rows, prov_meta, prov_data, geojson):
    chart_data = {
        str(y): {
            "classes": CLASSES,
            "fuels": {f: data[y]["raw"][f] for f in FUELS},
            "totals": data[y]["totals"],
        }
        for y in YEARS
    }

    top = sorted(insight_rows, key=lambda r: r["delta_pertalite"], reverse=True)[0]
    bottom = sorted(insight_rows, key=lambda r: r["delta_pertamax"], reverse=True)[0]

    generated = date.today().isoformat()

    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Distribusi Konsumen BBM per Kelas Masyarakat, 2019-2025</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&display=swap" rel="stylesheet">
<style>
  :root {{
    --ink: #051C2C;         /* deep near-black ink, editorial */
    --mandiri: #003D79;
    --yellow: #FFB700;
    --rule: #D0D5DD;
    --muted: #667085;
    --paper: #FFFFFF;
    --cream: #F7F5F0;
  }}
  html, body {{ background: var(--paper); color: var(--ink); }}
  body {{ font-family: 'Inter', system-ui, sans-serif; font-weight: 400; letter-spacing: -0.003em; }}
  .serif {{ font-family: 'Source Serif 4', Georgia, serif; }}
  .eyebrow {{ font-size: 11px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--mandiri); }}
  .eyebrow-light {{ color: var(--yellow); }}
  .rule-top {{ border-top: 1px solid var(--rule); }}
  .rule-bottom {{ border-bottom: 1px solid var(--rule); }}
  .hair-accent {{ border-top: 3px solid var(--mandiri); }}
  .ink {{ color: var(--ink); }}
  .muted {{ color: var(--muted); }}
  .serif-display {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.015em; line-height: 1.08; }}
  .stat-num {{ font-family: 'Source Serif 4', Georgia, serif; font-weight: 500; letter-spacing: -0.02em; line-height: 1; }}
  .btn-pill {{ border: 1px solid var(--rule); background: white; color: var(--ink); padding: 8px 16px; font-size: 13px; font-weight: 500; transition: all 0.15s; }}
  .btn-pill:hover {{ border-color: var(--ink); }}
  .btn-pill.active {{ background: var(--ink); color: white; border-color: var(--ink); }}
  .select-flat {{ border: 0; border-bottom: 1px solid var(--ink); background: transparent; padding: 6px 24px 6px 0; font-size: 15px; font-weight: 500; color: var(--ink); appearance: none; background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%23051C2C'%3e%3cpath fill-rule='evenodd' d='M5.23 7.21a.75.75 0 011.06.02L10 11.06l3.71-3.83a.75.75 0 111.08 1.04l-4.25 4.39a.75.75 0 01-1.08 0L5.21 8.27a.75.75 0 01.02-1.06z' clip-rule='evenodd'/%3e%3c/svg%3e"); background-repeat: no-repeat; background-position: right 0 center; background-size: 18px; }}
  .select-flat:focus {{ outline: none; border-bottom-color: var(--mandiri); }}
  table.editorial {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
  table.editorial thead th {{ text-align: left; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); border-bottom: 1px solid var(--ink); padding: 12px 16px; }}
  table.editorial tbody td {{ padding: 14px 16px; border-bottom: 1px solid var(--rule); }}
  table.editorial tbody tr:hover {{ background: var(--cream); }}
  .num {{ font-variant-numeric: tabular-nums; }}
</style>
</head>
<body>

<!-- Top nav bar, editorial style -->
<div class="rule-bottom">
  <div class="max-w-[1440px] mx-auto px-8 py-4 flex items-center justify-between text-xs uppercase tracking-widest">
    <div class="font-semibold ink">Mandiri Institute</div>
    <div class="flex gap-8 muted">
      <span>Dashboard</span>
      <span>Konsumsi BBM</span>
      <span class="ink font-semibold">2019 &ndash; 2025</span>
    </div>
  </div>
</div>

<!-- Hero -->
<header class="max-w-[1440px] mx-auto px-8 pt-16 pb-12">
  <div class="eyebrow">Riset Mandiri Institute · Kelas Masyarakat</div>
  <h1 class="serif-display text-5xl md:text-6xl mt-5 max-w-4xl">
    Bagaimana pola konsumsi BBM bergeser di antara kelas masyarakat Indonesia.
  </h1>
  <p class="mt-6 text-lg muted max-w-3xl leading-relaxed">
    Pergeseran dari Premium ke Pertalite dan Pertamax pasca-2022, ditelusuri melalui Susenas Maret BPS
    2019 sampai 2025 (Blok 42) dan klasifikasi wb4 Mandiri Institute.
  </p>
  <div class="mt-10 flex gap-12 text-sm rule-top pt-6">
    <div>
      <div class="eyebrow" style="color: var(--muted);">Sumber</div>
      <div class="mt-1 ink font-medium">Susenas BPS, Blok 42</div>
    </div>
    <div>
      <div class="eyebrow" style="color: var(--muted);">Cakupan</div>
      <div class="mt-1 ink font-medium">34 provinsi, nasional tertimbang</div>
    </div>
    <div>
      <div class="eyebrow" style="color: var(--muted);">Generated</div>
      <div class="mt-1 ink font-medium">{generated}</div>
    </div>
  </div>
</header>

<main x-data="dashboard()" class="max-w-[1440px] mx-auto px-8 pb-16 space-y-16">

  <!-- Filter bar, minimal -->
  <section class="rule-top pt-8 flex flex-wrap items-end gap-10">
    <div>
      <div class="eyebrow" style="color: var(--muted);">Tahun survei</div>
      <select x-model="year" @change="render()" class="select-flat mt-2">
        <template x-for="y in years" :key="y">
          <option :value="y" x-text="y"></option>
        </template>
      </select>
    </div>
    <div>
      <div class="eyebrow" style="color: var(--muted);">Tampilan</div>
      <div class="mt-2 flex gap-2">
        <button @click="mode='share'; render()" :class="mode==='share' ? 'btn-pill active' : 'btn-pill'">Share buyers only</button>
        <button @click="mode='raw'; render()" :class="mode==='raw' ? 'btn-pill active' : 'btn-pill'">Jumlah konsumen</button>
      </div>
    </div>
    <div class="ml-auto text-xs muted max-w-xs text-right">
      Konvensi kelas: Poor, Vulnerable, Lower/Upper AMC, Lower/Middle/Upper MC, Upper Class.
    </div>
  </section>

  <!-- Main chart -->
  <section>
    <div class="eyebrow">Exhibit 1</div>
    <h2 class="serif-display text-3xl mt-3 max-w-3xl">
      Komposisi jenis BBM per kelas masyarakat.
    </h2>
    <p class="mt-3 muted text-base max-w-3xl" x-text="subtitle"></p>
    <div class="hair-accent mt-8 pt-2"></div>
    <div id="chart-main" class="mt-2" style="height:540px;"></div>
  </section>

  <!-- Key figures -->
  <section class="rule-top pt-12">
    <div class="eyebrow">Angka kunci</div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-12 mt-8">
      <div class="border-t-2 pt-5" style="border-color: var(--mandiri);">
        <div class="eyebrow" style="color: var(--muted);">Pergeseran Pertalite, 2019 vs 2025</div>
        <div class="stat-num text-6xl mt-4 ink">
          +<span x-text="topDelta"></span><span class="text-3xl align-top muted ml-1">pp</span>
        </div>
        <div class="mt-2 text-sm font-semibold ink uppercase tracking-wide">Kelas <span x-text="topKelas"></span></div>
        <p class="mt-4 text-base leading-relaxed ink max-w-md">
          Kenaikan share Pertalite terbesar terjadi di kelas <span x-text="topKelas" class="font-semibold"></span>,
          naik dari <span class="num" x-text="topFrom"></span>% pada 2019 menjadi <span class="num" x-text="topTo"></span>% pada 2025.
          Konsisten dengan program konversi Premium ke Pertalite pasca 2022.
        </p>
      </div>
      <div class="border-t-2 pt-5" style="border-color: #EA7200;">
        <div class="eyebrow" style="color: var(--muted);">Perubahan Pertamax, 2019 vs 2025</div>
        <div class="stat-num text-6xl mt-4" style="color:#EA7200;">
          <span x-text="botDelta"></span><span class="text-3xl align-top muted ml-1">pp</span>
        </div>
        <div class="mt-2 text-sm font-semibold ink uppercase tracking-wide">Kelas <span x-text="botKelas"></span></div>
        <p class="mt-4 text-base leading-relaxed ink max-w-md">
          Kelas <span x-text="botKelas" class="font-semibold"></span> mencatat perubahan terbesar pada share Pertamax,
          dari <span class="num" x-text="botFrom"></span>% pada 2019 menjadi <span class="num" x-text="botTo"></span>% pada 2025.
        </p>
      </div>
    </div>
  </section>

  <!-- Table -->
  <section class="rule-top pt-12">
    <div class="eyebrow">Exhibit 2</div>
    <h2 class="serif-display text-3xl mt-3 max-w-3xl">
      Ringkasan perubahan share per kelas, buyers only.
    </h2>
    <p class="mt-3 muted text-base max-w-3xl">
      Perbandingan share Pertalite dan Pertamax antara 2019 dan 2025 di tiap kelas masyarakat. Selisih disajikan dalam poin persentase (pp).
    </p>
    <div class="overflow-x-auto mt-8">
      <table class="editorial">
        <thead>
          <tr>
            <th>Kelas</th>
            <th class="text-right">Pertalite 2019</th>
            <th class="text-right">Pertalite 2025</th>
            <th class="text-right">Δ Pertalite</th>
            <th class="text-right">Pertamax 2019</th>
            <th class="text-right">Pertamax 2025</th>
            <th class="text-right">Δ Pertamax</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="r in insights" :key="r.kelas">
            <tr>
              <td class="font-semibold ink" x-text="r.kelas"></td>
              <td class="text-right num muted" x-text="r.pertalite_2019.toFixed(1)"></td>
              <td class="text-right num muted" x-text="r.pertalite_2025.toFixed(1)"></td>
              <td class="text-right num font-semibold"
                :style="'color: ' + (r.delta_pertalite >= 0 ? '#003D79' : '#C8102E')"
                x-text="(r.delta_pertalite >= 0 ? '+' : '') + r.delta_pertalite.toFixed(1)"></td>
              <td class="text-right num muted" x-text="r.pertamax_2019.toFixed(1)"></td>
              <td class="text-right num muted" x-text="r.pertamax_2025.toFixed(1)"></td>
              <td class="text-right num font-semibold"
                :style="'color: ' + (r.delta_pertamax >= 0 ? '#003D79' : '#C8102E')"
                x-text="(r.delta_pertamax >= 0 ? '+' : '') + r.delta_pertamax.toFixed(1)"></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </section>

  <!-- Map per provinsi -->
  <section class="rule-top pt-12">
    <div class="eyebrow">Exhibit 3</div>
    <h2 class="serif-display text-3xl mt-3 max-w-3xl">
      Geografi konsumen BBM: share per provinsi, buyers only.
    </h2>
    <p class="mt-3 muted text-base max-w-3xl">
      Peta choropleth 34 provinsi (shapefile BPS 2020). Empat provinsi pemekaran Papua 2022+
      diagregasi kembali ke induk (Papua / Papua Barat) agar kompatibel dengan basis peta.
    </p>

    <div class="mt-8 flex flex-wrap items-end gap-10">
      <div>
        <div class="eyebrow" style="color: var(--muted);">Tahun</div>
        <select x-model="mapYear" @change="renderMap()" class="select-flat mt-2">
          <template x-for="y in years" :key="'my'+y"><option :value="y" x-text="y"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Kelas masyarakat</div>
        <select x-model="mapKelas" @change="renderMap()" class="select-flat mt-2">
          <option value="All">Semua kelas</option>
          <template x-for="k in classes" :key="'mk'+k"><option :value="k" x-text="k"></option></template>
        </select>
      </div>
      <div>
        <div class="eyebrow" style="color: var(--muted);">Jenis BBM</div>
        <select x-model="mapFuel" @change="renderMap()" class="select-flat mt-2">
          <template x-for="f in mapFuels" :key="'mf'+f"><option :value="f" x-text="f"></option></template>
        </select>
      </div>
    </div>

    <div class="hair-accent mt-8 pt-2"></div>
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-10 mt-2">
      <!-- Peta col 1-2 -->
      <div id="chart-map" class="lg:col-span-2" style="height:780px;"></div>
      <!-- Ranking col 3, 2 rows stacked -->
      <div class="flex flex-col gap-8">
        <div>
          <div class="eyebrow" style="color: var(--muted);">Tertinggi</div>
          <div class="mt-3 text-sm">
            <template x-for="(r, i) in rankTop" :key="'t'+r.pcode">
              <div class="flex justify-between items-baseline py-2 rule-bottom">
                <span><span class="muted num mr-2" x-text="(i+1)+'.'"></span><span class="ink font-medium" x-text="r.nama"></span></span>
                <span class="num font-semibold ink" x-text="r.value.toFixed(1)+'%'"></span>
              </div>
            </template>
          </div>
        </div>
        <div>
          <div class="eyebrow" style="color: var(--muted);">Terendah</div>
          <div class="mt-3 text-sm">
            <template x-for="(r, i) in rankBottom" :key="'b'+r.pcode">
              <div class="flex justify-between items-baseline py-2 rule-bottom">
                <span><span class="muted num mr-2" x-text="(i+1)+'.'"></span><span class="ink font-medium" x-text="r.nama"></span></span>
                <span class="num font-semibold ink" x-text="r.value.toFixed(1)+'%'"></span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="rule-top pt-8 pb-4 flex items-center justify-between text-xs muted uppercase tracking-widest">
    <div>Mandiri Institute · Dashboard</div>
    <div>Data: Susenas BPS, weighted population</div>
    <div>Palette: Mandiri Official</div>
  </footer>
</main>

<script>
const CHART_DATA = {json.dumps(chart_data)};
const COLORS = {json.dumps(COLORS)};
const INSIGHTS = {json.dumps(insight_rows)};
const FUELS = {json.dumps(FUELS)};
const PROV_META = {json.dumps(prov_meta)};
const PROV_DATA = {json.dumps(prov_data)};
const GEOJSON = {json.dumps(geojson)};
const CLASSES = {json.dumps(CLASSES)};
const MAP_FUELS = ["Premium", "Pertalite", "Pertamax", "Pertamax Turbo"];

function dashboard() {{
  const topPert = INSIGHTS.slice().sort((a,b) => b.delta_pertalite - a.delta_pertalite)[0];
  const extremePmax = INSIGHTS.slice().sort((a,b) =>
    Math.abs(b.delta_pertamax) - Math.abs(a.delta_pertamax))[0];
  return {{
    years: {json.dumps([str(y) for y in YEARS])},
    classes: CLASSES,
    mapFuels: MAP_FUELS,
    year: '2025',
    mode: 'share',
    mapYear: '2025', mapKelas: 'All', mapFuel: 'Pertalite',
    rankTop: [], rankBottom: [],
    insights: INSIGHTS,
    topKelas: topPert.kelas, topDelta: topPert.delta_pertalite.toFixed(1),
    topFrom: topPert.pertalite_2019.toFixed(1), topTo: topPert.pertalite_2025.toFixed(1),
    botKelas: extremePmax.kelas,
    botDelta: (extremePmax.delta_pertamax >= 0 ? '+' : '') + extremePmax.delta_pertamax.toFixed(1),
    botFrom: extremePmax.pertamax_2019.toFixed(1), botTo: extremePmax.pertamax_2025.toFixed(1),
    get subtitle() {{
      return this.mode === 'share'
        ? 'Share jenis BBM di tiap kelas, buyers only (non-buyer dikeluarkan). Angka dalam %.'
        : 'Jumlah konsumen tertimbang per jenis BBM per kelas. Angka dalam juta orang.';
    }},
    init() {{ this.render(); this.renderMap(); }},
    renderMap() {{
      const slice = PROV_DATA[this.mapYear][this.mapKelas][this.mapFuel] || {{}};
      const locations = Object.keys(slice);
      const values = locations.map(p => slice[p]);
      const text = locations.map(p => PROV_META[p] || p);

      const trace = {{
        type: 'choropleth',
        geojson: GEOJSON,
        locations, z: values, text,
        featureidkey: 'properties.ADM1_PCODE',
        colorscale: [[0,'#E6EEF6'],[0.3,'#A9C4DF'],[0.6,'#4A7FB0'],[1,'#003D79']],
        marker: {{ line: {{ color: 'white', width: 0.6 }} }},
        colorbar: {{
          title: {{ text: 'Share %', font: {{ size: 11, color: '#667085' }} }},
          thickness: 10, len: 0.7, x: 1.0,
          tickfont: {{ size: 11, color: '#667085' }},
        }},
        hovertemplate: '<b>%{{text}}</b><br>' + this.mapFuel + ': %{{z:.1f}}%<extra></extra>',
      }};
      const layout = {{
        margin: {{ l: 0, r: 0, t: 0, b: 0 }},
        font: {{ family: 'Inter, sans-serif', color: '#051C2C' }},
        geo: {{
          fitbounds: 'locations', visible: false,
          projection: {{ type: 'mercator', scale: 1.05 }},
          bgcolor: 'white',
          domain: {{ x: [0, 1], y: [0, 1] }},
        }},
        paper_bgcolor: 'white',
      }};
      Plotly.react('chart-map', [trace], layout, {{ displaylogo: false, responsive: true }});

      const ranked = locations.map(p => ({{ pcode: p, nama: PROV_META[p] || p, value: slice[p] }}))
                              .sort((a,b) => b.value - a.value);
      this.rankTop = ranked.slice(0, 5);
      this.rankBottom = ranked.slice(-5).reverse();
    }},
    render() {{
      const d = CHART_DATA[this.year];
      const traces = FUELS.map(fuel => {{
        let y;
        if (this.mode === 'share') {{
          if (fuel === 'Tidak beli') return null;
          y = d.classes.map((_, k) => {{
            const buyersTotal = FUELS
              .filter(f => f !== 'Tidak beli')
              .reduce((s, f) => s + d.fuels[f][k], 0);
            return buyersTotal > 0 ? d.fuels[fuel][k] / buyersTotal * 100 : 0;
          }});
        }} else {{
          y = d.fuels[fuel].map(v => v / 1e6);
        }}
        return {{
          x: d.classes, y, name: fuel, type: 'bar',
          marker: {{ color: COLORS[fuel] }},
          hovertemplate: this.mode === 'share'
            ? '%{{x}}<br>' + fuel + ': %{{y:.1f}}%<extra></extra>'
            : '%{{x}}<br>' + fuel + ': %{{y:.2f}} juta<extra></extra>',
        }};
      }}).filter(t => t);

      const layout = {{
        barmode: 'stack',
        bargap: 0.45,
        margin: {{ l: 60, r: 20, t: 30, b: 80 }},
        font: {{ family: 'Inter, sans-serif', size: 13, color: '#051C2C' }},
        plot_bgcolor: 'white', paper_bgcolor: 'white',
        xaxis: {{
          title: '',
          tickangle: 0,
          tickfont: {{ size: 14, color: '#051C2C', family: 'Inter, sans-serif' }},
          automargin: true,
          showline: true, linecolor: '#051C2C', linewidth: 1,
          ticks: 'outside', tickcolor: '#051C2C', ticklen: 4,
        }},
        yaxis: {{
          title: {{ text: this.mode === 'share' ? 'Share (%)' : 'Konsumen (juta orang)', font: {{ size: 12, color: '#667085' }}, standoff: 10 }},
          tickfont: {{ size: 12, color: '#667085' }},
          gridcolor: '#EAECF0', gridwidth: 1,
          zerolinecolor: '#051C2C', zerolinewidth: 1,
        }},
        legend: {{
          orientation: 'h', y: -0.22, x: 0, xanchor: 'left',
          font: {{ size: 12, color: '#051C2C' }},
          itemsizing: 'constant',
        }},
      }};
      Plotly.react('chart-main', traces, layout,
        {{ displaylogo: false, responsive: true }});
    }},
  }};
}}
</script>
</body>
</html>
"""
    return html


def main():
    data = parse()
    insight_rows = insights(data)
    prov_meta, prov_data = parse_provinsi()
    geojson = load_geojson()
    # Convert year keys to str to match JS
    prov_data = {str(y): v for y, v in prov_data.items()}
    html = build_html(data, insight_rows, prov_meta, prov_data, geojson)
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
