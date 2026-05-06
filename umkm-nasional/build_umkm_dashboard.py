"""Generate UMKM Nasional dashboard HTML.
Loads 4 CSVs (counts/revenue/pekerja/growth) and emits dashboard.html
with embedded JSON + Plotly charts + standardized filter bar."""
import json
import math
from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
DATA = HERE / 'data'
OUTPUT = HERE / 'dashboard.html'

YEARS = [2021, 2022, 2023, 2024, 2025]


def jclean(o):
    if isinstance(o, dict): return {k: jclean(v) for k, v in o.items()}
    if isinstance(o, list): return [jclean(v) for v in o]
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)): return None
    return o


def load():
    counts = pd.read_csv(DATA / 'umkm_counts.csv')
    rev    = pd.read_csv(DATA / 'umkm_revenue.csv')
    pek    = pd.read_csv(DATA / 'umkm_pekerja.csv')
    growth = pd.read_csv(DATA / 'umkm_growth.csv')
    return counts, rev, pek, growth


def main():
    counts, rev, pek, growth = load()
    print(f'Loaded counts: {len(counts):,} rows')

    # Build wilayah map: {prov_name: [kabkota_name, ...]}
    wilayah = {}
    for prov, sub in counts.groupby('nama_provinsi')['nama_kabkota'].unique().items():
        wilayah[prov] = sorted(sub.tolist())

    # National aggregation per (tahun, sektor, ukuran)
    nat = (counts.groupby(['tahun', 'sektor_label', 'ukuran'], as_index=False)
                 ['jumlah_umkm_weighted'].sum())

    # Provincial aggregation per (tahun, prov, sektor, ukuran)
    prov_agg = (counts.groupby(['tahun', 'nama_provinsi', 'sektor_label', 'ukuran'], as_index=False)
                      ['jumlah_umkm_weighted'].sum())

    # Kabkota aggregation per (tahun, prov, kabkota, sektor, ukuran)
    # Already at this granularity — just rename for clarity
    kk_agg = counts.copy()

    # Revenue avg per (tahun, prov, kabkota, sektor, ukuran) — weighted by n_pendapatan
    rev_clean = rev.dropna(subset=['avg_pendapatan']).copy()
    pek_clean = pek.dropna(subset=['avg_pekerja']).copy()

    # Combine into a long-form list per [tahun][prov][kabkota] for client-side filter
    # Strategy: emit AS-IS at finest granularity; client aggregates on filter change
    print('Building data dict...')

    # Strip zero rows + round to int (n is weighted, fractional digits add bytes)
    counts_nz = counts[counts['jumlah_umkm_weighted'] > 0].copy()
    counts_nz['n'] = counts_nz['jumlah_umkm_weighted'].round().astype(int)
    print(f'Non-zero count rows: {len(counts_nz):,} of {len(counts):,}')

    # Build compact array-of-arrays format to minimize JSON size:
    # Use indexes for prov/kabkota/sektor/ukuran instead of full strings
    prov_idx = {p: i for i, p in enumerate(sorted(counts_nz['nama_provinsi'].unique()))}
    kabkota_idx = {kk: i for i, kk in enumerate(sorted(counts_nz['nama_kabkota'].unique()))}
    sektor_idx = {s: i for i, s in enumerate(sorted(counts_nz['sektor_label'].unique()))}
    ukuran_idx = {u: i for i, u in enumerate(['Mikro', 'Kecil', 'Menengah'])}

    # Build compact rows: [tahun, prov_i, kabkota_i, sektor_i, ukuran_i, n]
    rows = []
    for r in counts_nz.itertuples(index=False):
        rows.append([
            int(r.tahun),
            prov_idx[r.nama_provinsi],
            kabkota_idx[r.nama_kabkota],
            sektor_idx[r.sektor_label],
            ukuran_idx[r.ukuran],
            int(r.n)
        ])

    # Reverse lookup arrays for client
    prov_list = sorted(counts_nz['nama_provinsi'].unique())
    kabkota_list = sorted(counts_nz['nama_kabkota'].unique())
    sektor_list = sorted(counts_nz['sektor_label'].unique())
    ukuran_list = ['Mikro', 'Kecil', 'Menengah']

    payload = {
        'wilayah': wilayah,
        'years': YEARS,
        'provs': prov_list,
        'kabkotas': kabkota_list,
        'sektors': sektor_list,
        'ukurans': ukuran_list,
        'rows': rows,  # [[tahun, prov_i, kabkota_i, sektor_i, ukuran_i, n], ...]
    }
    print(f'  rows: {len(payload["rows"]):,} compact records')

    # Render template
    template = (HERE / '_template.html').read_text(encoding='utf-8')
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    html = template.replace('/*__PAYLOAD__*/', payload_json)
    OUTPUT.write_text(html, encoding='utf-8')
    sz = OUTPUT.stat().st_size / 1024
    print(f'\nGenerated: {OUTPUT}')
    print(f'Size: {sz:.0f} KB')


if __name__ == '__main__':
    main()
