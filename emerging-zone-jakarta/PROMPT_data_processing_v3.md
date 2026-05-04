# Prompt untuk data_processing Agent (v3 — Final)

## Konteks

Setelah audit empiris cross-check Podes 2025 vs OSM 2026, ditemukan:
- 79% data Podes konsisten pattern wajar (43% normal + 36% gradient COVID-recovery)
- Hanya 23 baris (0.9%) truly anomali ekstrim (Bungur 12→788, Kebayoran Lama Utara 1→90, dll)
- Sakernas ternyata punya 5 vintage 2021-2025 (bukan 3 seperti yang saya kira)
- Korelasi OSM-Podes lemah (r 0.23-0.39) — confirms caveat 7.3 OSM coverage bias

## Yang Perlu Kamu Kerjakan

### Task 1: Re-compute Composite Potensi dengan Weighted by Kategori + Winsorize

File input: `composite-potensi-DKI.csv` (existing) — kolom kategori, count, avg_pendapatan_kabkota_kbli

**Bobot kategori (relative weight per usaha):**

| Kategori Podes | Bobot |
|---|---|
| hotel | 50 |
| kelompok_pertokoan | 30 |
| pasar_permanen | 10 |
| restoran | 5 |
| minimarket | 4 |
| penginapan | 4 |
| pasar_semipermanen | 3 |
| pasar_tanpa_bangunan | 2 |
| warung_mamin | 1 |
| toko_kelontong | 1 |

Bobot ini reflect estimasi revenue per unit usaha (hotel >> warung mikro).

**Formula baru per (desa, vintage_year, sektor):**

```
potensi_weighted = sum(bobot_kategori × count_kategori × avg_pendapatan_kabkota_kbli)
                   per kategori dalam sektor (KBLI 7 atau 9)
```

**Winsorize 23 baris anomali:**

Detect baseline: untuk tiap (desa, kategori), kalau growth ratio count_2024/count_2021 > 95th percentile DKI, **cap baseline 2021** ke value 95th percentile-nya. Tujuannya: menghindari false CAGR ekstrem dari typo data.

List 23 baris anomali (lihat audit hasil sebelumnya): Bungur, Kebayoran Lama Utara, Johar Baru, Sungai Bambu, Karet Semanggi, Pulo Gebang, Cibubur, Pluit, Karet Kuningan, Senen, Cikini, Cideng, Semper Timur, Kebon Kosong, Menteng Atas, Bambu Apus, Bidara Cina, Tanjung Priuk (dan beberapa lain — detect via threshold).

### Task 2: Sakernas 5-vintage CAGR

Pakai 5 vintage 2021-2025 untuk hitung CAGR yang lebih smooth.

**Method:** OLS regression slope `log(avg_pendapatan)` vs `year` per (kabkota, KBLI). Slope = annual log growth rate. Convert ke CAGR via `exp(slope) - 1`.

Atau alternative: geometric mean rate `[(2025/2021)^(1/4) + ... ] / 4` jika lebih simpel.

**Output:** `sakernas-revenue-DKI.csv` updated dengan kolom:
- `cagr_2021_2025_regression` per (kabkota, KBLI)
- `change_2024_2025` per (kabkota, KBLI)
- `level_2025` per (kabkota, KBLI)

### Task 3: Output Files

Generate 2 file untuk Scraping agent assemble:

1. `260503_composite-potensi-weighted-DKI.csv`
   - Per desa per vintage per sektor (perdagangan/akomamin)
   - Kolom: nama_desa, kabkota_id, vintage_year, sektor, count, potensi_weighted, winsorize_flag
   - Sektor terpisah (KBLI 7 = perdagangan, KBLI 9 = akomamin)

2. `260503_sakernas-revenue-5vintage-DKI.csv`
   - Per kabkota per KBLI per year
   - Kolom: kabkota_id, kbli2, year, avg_pendapatan, n_responden, weight_sum, low_reliability_flag
   - Plus per kabkota per KBLI: cagr_2021_2025_regression, change_2024_2025, level_2025

Save ke: `Mandiri Institute\Dashboard\emerging-zone-jakarta\data\`

### Task 4: Update Handoff

`data_processing/podes-sakernas-emerging-zone.md`:
- List 23 baris yang ke-winsorize (transparent)
- Catat formula weighted-by-kategori (bobot 50/30/10/5/4/4/3/2/1/1)
- Catat method Sakernas 5-vintage regression
- Confirm pairing vintage Podes 2018→Sakernas 2021 (backward fill OK)

### Catatan Penting

- Winsorize 23 baris saja (light intervention, bukan replace baseline)
- Jangan ganti 2021 baseline karena 79% data wajar pattern COVID
- Sakernas pakai 5 vintage full untuk smoothness
- Bobot kategori adalah expert judgment, dokumentasikan sebagai caveat

### Estimasi

~30-45 menit. Setelah selesai, notify Scraping agent untuk final assembly.
