# Metodologi: Pendeteksi Kawasan Komersial Berkembang — DKI Jakarta

**Versi:** 2.1 (2026-05-03 night) — post weighted composite + symmetric winsorize
**Owner:** Mandiri Institute — Scraping + data_processing + Dashboard agents
**Scope awal:** DKI Jakarta (Phase 0); akan diperluas ke Jabodetabek, Bandung Raya, DIY, Surabaya, Malang Raya

**Perubahan v2.1 (final lock):**
- Composite Potensi pakai weighted by kategori: hotel=50, kelompok_pertokoan=30, pasar_permanen=10, restoran=5, minimarket=4, penginapan=4, pasar_semi=3, pasar_tanpa_bangunan=2, warung_mamin=1, toko_kelontong=1
- Sakernas pakai 5 vintage 2021-2025 dengan geomean CAGR (lebih defensible dari OLS regression yang sensitive ke single-year anomaly)
- **DROP magnitude_change_2024_2025 dari composite** karena 75% desa di -60% (sistemik noise Sakernas avg 2024 spike). Realokasi: mag_cagr 5%→6%, mag_level 3%→5%. Group 3 total tetap 11%.
- **Symmetric winsorize 5th-95th percentile** untuk semua growth metrics (NTL, Podes, Magnitude). Outliers ekstrim Pulau Harapan (+977%), Bungur (+434%), Tegal Parang (-90%) neutralized.
- 6 desa Kepulauan Seribu di-flag `low_reliability_flag=1` karena sample size kecil

**Perubahan v2.0 (sebelumnya):**
- Spatial join NTL pixel ke 270 polygon desa (sebelumnya kabkota proxy 6 nilai → 173 nilai unik)
- Spatial join OSM POI ke 270 polygon desa
- Validasi empiris korelasi NTL ↔ Magnitude (r 0.05, hampir nol → independent dimension)
- Validasi empiris korelasi OSM ↔ Podes per kategori (r 0.05-0.55, OSM bukan proxy reliable)
- Audit Podes 2021: 79% pattern wajar (gradient COVID-recovery), 0.9% truly anomali
- Setiap source punya peran unik yang TIDAK bisa digantikan source lain (terbukti empiris)

---

## 1. Tujuan dan Pertanyaan Riset

Dashboard ini mendeteksi kawasan komersial yang sedang berkembang pesat berdasarkan multi-source evidence, mencakup kuliner, kafe, retail, dan tempat hangout. Bukan untuk analisis kredit atau ekspansi financing — fokus pada **urban activity intensity** dan **commercial zone lifecycle mapping**.

Pertanyaan kunci:
- Kawasan mana yang menunjukkan sinyal pertumbuhan aktivitas komersial terkuat secara konsisten?
- Apakah pertumbuhan bersifat jangka panjang (struktural) atau baru muncul belakangan (momentum)?
- Di mana gap antara aktivitas spasial (NTL) dan ekosistem bisnis nyata (Podes, Sakernas)?

---

## 2. Unit Analisis

**Unit primer:** Desa / Kelurahan (granularity tertinggi, sesuai resolusi Podes)

**Zoom hierarchy 5 tier (v2.1):**
- Desa / Kelurahan (270 base units)
- Kecamatan (44, agregasi sum dari desa)
- **Wilayah Berpotensi / Kawasan Utama** (21 informal commercial zones — BARU di v2.1)
- Kabupaten / Kota (6, agregasi sum)
- Provinsi (1, DKI Jakarta)

**Wilayah Berpotensi** adalah grouping informal yang dikenal masyarakat (Blok M, PIK, Kelapa Gading, Mega Kuningan, dll) — TIDAK setara dengan kecamatan administratif. Mapping desa → kawasan tercatat di `kawasan_utama_mapping.json`. 21 kawasan mencakup:

- 16 named area klasik (Blok M, SCBD, Kemang, Cipete, PIK, PIK 2 area, Kelapa Gading, Pluit, Ancol, Kalideres, Cengkareng, Cilincing, Cawang, Pesanggrahan, Thamrin, Pantai Mutiara)
- 5 cluster baru hasil temuan spatial join NTL/OSM (Mega Kuningan, Tanjung Duren Mall Corridor, Cipayung Cluster, Jagakarsa, Sunter & Tanjung Priok, Sarinah & Tanah Abang)

**Rule agregasi desa → kawasan utama:**
- Volume metrics (count usaha, magnitude, POI count): SUM
- Growth metrics (CAGR, change): MEAN weighted by volume desa member
- Score 0-100: MEAN of member desa scores
- Diversity: MAX (kawasan reflect highest diversity di antara members)
- Transport access: MAX (best access among members)
- Pulse badge: priority Trend Lanjut Tumbuh > Stabil > Mulai Melambat
- Quadrant: re-classified dari aggregated metrics (median split di 21 kawasan, bukan 270 desa)

**Spatial reference:** Shapefile BPS adm4 desa (270 polygon DKI dari `idn_admbnda_adm4_bps_20200401.shp`)

---

## 3. Sumber Data dan Peran Masing-masing (Empirically Validated)

Empat source dipakai karena **validasi empiris membuktikan tiap source menangkap dimensi berbeda yang tidak bisa digantikan source lain** (lihat Section 7.11).

| Source | Peran Unik | Kekuatan | Keterbatasan |
|---|---|---|---|
| **Podes BPS (5 vintage)** | **Ground truth jumlah usaha** per desa | Sensus admin BPS, 270 desa complete coverage, 10 kategori detail | Hanya count, tidak ada koordinat per usaha, tidak ada revenue |
| **OSM Overpass** | **Visualisasi titik koordinat** + kategori non-Podes | 21.000+ POI dengan lat/lon precise, kategori granular (cinema, gym, spa) | Coverage tidak merata (warung mamin cuma 5%), korelasi r 0.05-0.55 dengan Podes |
| **Sakernas BPS** | **Dimensi pendapatan/quality** | Satu-satunya source income data, 5 vintage 2021-2025 | Granularity kabkota (12 unique values untuk 267 desa), pendapatan personal bukan firm revenue |
| **NTL NASA VIIRS** | **Dimensi pertumbuhan aktivitas spasial** | 270 desa dengan 173 nilai unik post spatial join, longitudinal 2019-2026 monthly | TIDAK proxy revenue/usaha (r ~0 empirically), dipengaruhi residential/infrastruktur |

### Prinsip Pemilihan Source (Post Empirical Validation)

- **Podes adalah ground truth count usaha** — empirically more complete than OSM (OSM cover 5-50% tergantung kategori)
- **OSM dipakai untuk visualisasi peta** (koordinat per POI) + kategori yang tidak ada di Podes (cinema, gym, museum, spa)
- **Sakernas wajib retained** untuk dimensi income — NTL terbukti TIDAK bisa proxy revenue (r=0.05)
- **NTL menangkap dimensi pertumbuhan aktivitas spasial** — independent dari magnitude commerce
- **Multi-source** bukan redundansi tapi necessity — empirical evidence menunjukkan tiap source capture aspek yang berbeda

---

## 4. Variabel per Source

### 4A. NTL (NASA VIIRS VNP46A2)

- **Band:** DNB_BRDF_Corrected_NTL
- **Resolusi:** 500m
- **Periode:** 2019-2025 (monthly composite; annual composite Jul-Sep untuk pixel change map)
- **Composite method:** Median per bulan per pixel (robust outlier); Jul-Sep (kemarau) untuk annual aggregate
- **Quality tracking:** `valid_obs_count` per bulan per area — bulan dengan <8 observasi diberi flag `low_quality`

Variabel output:
- `lum_median` per bulan per area
- `valid_obs_count` per bulan per area
- `ntl_CAGR_2019_2025`: CAGR luminositas median Jul-Sep
- `ntl_change_2024_2025`: perubahan % luminositas 2024 ke 2025
- `ntl_level_2025`: luminositas median Jul-Sep 2025
- `recovery_index`: lum_2025 / lum_2019

**Catatan metodologis NTL:**
> Nighttime light BUKAN ukuran langsung PDRB, transaksi, atau daya beli. Digunakan sebagai proxy intensitas aktivitas ekonomi spasial mengikuti Henderson et al. (2012) dan Gibson et al. (2020). Saturasi pada kawasan CBD (>80 DNB units) dapat menekan sinyal pertumbuhan — interpretasi perlu konteks.

### 4B. Podes BPS — Business Count

**Vintage yang dipakai:** 2018 (baseline), 2024 (short-base), 2025 (latest)
**Vintage tambahan:** 2020, 2021 (validasi konsistensi)

10 kategori usaha (Block 8 Podes — Fasilitas Usaha Desa):

| Kode | Kategori | Tipe | Overlap OSM? |
|---|---|---|---|
| a | Kelompok pertokoan (≥10 toko, 1 lokasi) | Unique Podes | Partial (mall) |
| b | Pasar bangunan permanen | Unique Podes | Partial (marketplace) |
| c | Pasar semi permanen | Unique Podes | Partial |
| d | Pasar tanpa bangunan (pasar subuh, terapung) | Unique Podes | Tidak ada |
| e | Minimarket / swalayan / supermarket | Overlap | OSM convenience + supermarket |
| f | Restoran / rumah makan | Overlap | OSM restaurant + fast_food |
| g | Warung / kedai makanan minuman | Overlap (kasar) | OSM cafe + ice_cream (approx) |
| h | Hotel | Overlap | OSM tourism=hotel |
| i | Penginapan (hostel/motel/losmen/wisma) | Overlap | OSM hostel/motel |
| j | Toko / warung kelontong | Unique Podes | Coverage OSM rendah |

Variabel output:
- `count_{kategori}_{tahun}` per desa (long + wide format)
- `biz_CAGR_2018_2025` per desa per kategori: (count_2025/count_2018)^(1/7) - 1
- `biz_change_2024_2025` per desa per kategori: (count_2025-count_2024)/count_2024
- `biz_count_total_2025` per desa (sum semua kategori)
- `biz_diversity_shannon`: Shannon entropy dari distribusi 10 kategori di 2025
- Edge case tags: `new_emergence` (0→>0), `absent` (0→0), `extinct` (>0→0)

### 4C. Sakernas — Avg Revenue per Sektor

**Periode:** 2019-2025 (7 tahun, parquet sudah ready)
**Level:** Kabupaten/Kota (level terendah yang reliable dari survey)
**Sektor:** KBLI yang relevan ke akomodasi, mamin, perdagangan (dikonfirmasi data_processing agent — variabel Sakernas perlu verifikasi KBLI mapping)

Variabel output:
- `avg_revenue_{sektor}_{tahun}` per kabkota
- `rev_CAGR_2019_2025` per kabkota per sektor
- `rev_change_2024_2025` per kabkota per sektor
- `rev_level_2025` per kabkota per sektor
- `reliability_flag`: low_reliability jika sample <30 per (kabkota, KBLI, tahun)

### 4D. OSM — Lifestyle & Leisure POI (Complement)

Fokus pada kategori yang **tidak ada di Podes**. Dibagi 5 sub-grup:

**Group A: Entertainment & Nightlife**
`amenity=cinema`, `amenity=theatre`, `amenity=nightclub`, `amenity=karaoke_box`, `amenity=arts_centre`, `amenity=music_venue`, `amenity=bar`, `amenity=pub`

**Group B: Lifestyle & Wellness**
`leisure=fitness_centre`, `leisure=sports_centre`, `amenity=spa`, `shop=beauty`, `shop=hairdresser`, `shop=massage`, `leisure=swimming_pool`

**Group C: Specialty Retail**
`shop=books`, `shop=electronics`, `shop=mobile_phone`, `shop=clothes`, `shop=shoes`, `shop=jewelry`, `shop=optician`, `shop=bicycle`, `shop=florist`

**Group D: Tourism & Cultural**
`tourism=museum`, `tourism=gallery`, `tourism=attraction`, `tourism=viewpoint`

**Group E: Auto & Public Service (supporting infra)**
`amenity=fuel`, `amenity=bank`, `amenity=atm`, `amenity=clinic`, `amenity=pharmacy`

Variabel output:
- Count per sub-grup per desa (via point-in-polygon dengan shapefile desa)
- `poi_lifestyle_density` per km2 (complement only — tidak overlap Podes)

### 4E. OSM — Transport & Accessibility

**Node type dan bobot aksesibilitas:**

| Tipe | Tag OSM | Bobot (akses) |
|---|---|---|
| MRT/subway | `railway=station["station"="subway"]` | 4 |
| KRL/commuter rail | `railway=station` | 3 |
| Terminal bus / hub | `amenity=bus_station`, `public_transport=station` | 2 |
| Halte TransJakarta | `highway=bus_stop` | 1 |

Formula transport_access_score per desa:
```
score = sum(weight_i / distance_km_i) untuk semua node dalam radius 2km
normalized 0-100 via min-max
```

**Catatan:** Halte TJ mendominasi jumlah (4.830) tapi bobot per titik minimal (1) agar tidak over-represent.

---

## 5. Cross-Check Podes vs OSM (Phase 2 — Bukan Komponen Score)

**Update 2026-05-03:** Setelah feedback data_processing, cross-check Podes vs OSM **tidak masuk composite scoring**. Group 2 (business count) menggunakan **Podes saja** sebagai source. OSM coverage bias asymmetric (CBD over-mapped, fringe under-mapped) menyebabkan `max(podes, osm)` blend bias inflate count area central.

Cross-check tetap akan dilakukan sebagai **QA layer terpisah** (Phase 2, setelah dashboard v1) untuk:
- Identifikasi desa dengan diskrepansi besar antara administratif (Podes) vs digital footprint (OSM)
- Investigasi kategori dengan coverage gap (kemungkinan toko kelontong Podes tidak terpetakan OSM)
- Validasi konsistensi pelaporan Podes lintas vintage

**Logika reconciliation tetap diretain untuk Phase 2:**

```
consistency_ratio = osm_count / podes_count per (desa, kategori)
flag:
  "high_consistency"         : 0.5 <= ratio <= 2.0
  "osm_overcount"            : ratio > 2.0
  "osm_undercount"           : ratio < 0.5
  "podes_zero_osm_present"   : podes==0 & osm>0
  "osm_zero_podes_present"   : podes>0 & osm==0
```

**Limitasi:**
- Mapping warung mamin (Podes) ke cafe/ice_cream (OSM) bersifat approx
- Toko kelontong dan pasar tradisional hampir tidak terpetakan di OSM Indonesia
- OSM sudah di-deduplicate via `osm_id` sebelum counting

---

## 6. Composite Scoring: Emerging Commercial Zone Index (ECZI)

### 6.1 Periode Baseline: 2021-2025 (4 tahun, post-COVID)

**Final lock setelah feedback data_processing:**

Semua dimensi growth menggunakan baseline **2021-2025**, bukan 2019-2025. Alasan:

1. **Sakernas constraint:** schema KBLI 2019 tidak terdiseminasi penuh; Sakernas 2020 short-form COVID (variabel `status_pek` hilang). Realistic baseline Sakernas = 2021.
2. **Apple-to-apple alignment:** untuk komparabilitas antar source (NTL + Podes + Sakernas), semua CAGR 2021-2025.
3. **Post-COVID interpretation:** baseline 2021 menangkap "post-COVID emerging trajectory" yang lebih relevan untuk konteks 2026.

**Historical reference 2019-2025 dan Podes 2018-2025 tetap tersedia di sub-sheet** sebagai konteks longitudinal, tidak masuk composite scoring.

### 6.2 Dual Horizon Analysis

Setiap dimensi growth dihitung dalam dua horizon:
- **Jangka panjang (CAGR):** 2021-2025 (4 tahun) — semua source align
- **Jangka pendek (momentum):** 2024-2025 (1 tahun)

Tagging desa via kuadran CAGR x short-term:

| CAGR 2021-2025 | Short 2024-2025 | Label | Interpretasi |
|---|---|---|---|
| High | High | Sustained Explosive | Akselerasi berlanjut |
| High | Low | Mature Emerging | Pernah tumbuh pesat, kini melambat |
| Low | High | Late Bloomer | Momentum baru, belum terbukti sustained |
| Low | Low | Stable / Declining | Tidak ada sinyal pertumbuhan |

### 6.3 Bobot Scoring Final (Lock 2026-05-03)

Bobot final hasil iterasi data_processing + Scraping. Adjustment dari draft v1: NTL +2%, Podes +3%, Sakernas -7%, OSM Lifestyle -3%, Accessibility +5%.

| Group | Source | Komponen | Bobot | Group Total |
|---|---|---|---|---|
| **1. Spatial Activity (NTL)** | NASA VIIRS | NTL CAGR 2021-2025 | 13% | **24%** |
| | | NTL change 2024-2025 | 7% | |
| | | NTL level 2025 | 4% | |
| **2. Business Density & Growth** | Podes (only) | Podes count CAGR 2021-2025 | 13% | **33%** |
| | | Podes count change 2024-2025 | 7% | |
| | | Podes count level 2025 | 9% | |
| | | Podes diversity (Shannon 10 kategori) | 4% | |
| **3. Magnitude Komersial (Podes × Sakernas)** | Composite weighted | Magnitude CAGR 2021-2025 | 6% | **11%** |
| | | ~~Magnitude change 2024-2025~~ | ~~3%~~ DROPPED v2.1 | |
| | | Magnitude level 2025 (weighted) | 5% | |
| **4. Lifestyle & Leisure POI** | OSM | Entertainment & Nightlife | 4% | **12%** |
| | | Lifestyle & Wellness | 3% | |
| | | Specialty retail | 3% | |
| | | Tourism & Cultural | 2% | |
| **5. Accessibility & Catchment** | OSM | Transport access (weighted MRT/KRL) | 12% | **20%** |
| | | Auto & service density | 5% | |
| | | Residential catchment proxy | 3% | |
| **TOTAL** | | | **100%** | **100%** |

### 6.4 Honest Growth vs Level Breakdown

Klaim awal "CAGR 32% / Short 16% / Level 18%" tidak akurat karena Group 4+5 entirely level-based (snapshot 2026):

| Tipe signal | Bobot total | Komponen |
|---|---|---|
| **Growth (CAGR + short)** | **48%** | NTL 20%, Podes 20%, Sakernas 8% |
| **Level (snapshot/density)** | **52%** | NTL level 4%, Podes level+diversity 13%, Sakernas level 3%, OSM 4+5 = 32% |

OSM growth signal (POI count delta YoY) tidak achievable di Phase 0 karena single snapshot. Phase 1 dengan multi-snapshot OSM bisa add growth dimension untuk Group 4-5.

### 6.5 Normalisasi (Spec Final)

Berbeda treatment untuk variabel level vs growth:

```
Level variables (count, NTL value, revenue, density):
    log1p(x) → min-max 0-100
    
Growth variables (CAGR, change_pct):
    direct → min-max 0-100

Composite = Σ (weight_komponen × normalized_indicator)
```

**Justifikasi log-transform untuk level:** distribusi NTL, revenue, dan business count sangat right-skew di DKI:
- NTL: SCBD 95.6 vs PIK 2 4.4 = 21x range
- Tanpa log1p, satu outlier mendominasi seluruh ranking via min-max
- log1p compress range, distribusi mendekati normal, semua desa kontribusi proporsional

Min-max dihitung dari distribusi seluruh desa dalam satu region (Phase 0: DKI 267 desa). Saat ekspansi ke 5 mega-region (Phase 1), normalisasi recalibrate dengan opsi:
- Global min-max (semua desa lintas region) — comparable absolute
- Within-region min-max (per mega-region) — comparable relative

### 6.6 NTL Recent Pulse (Sidecar Indicator — Tidak Masuk Score)

Karena Podes dan Sakernas hanya tersedia sampai 2025 sementara NTL bisa di-update kapan saja (lag VIIRS ~2-4 minggu), composite ECZI score di-anchor di 2025 untuk apple-to-apple consistency. Untuk tetap menampilkan momentum terkini, ditambahkan **sidecar indicator** terpisah: NTL Recent Pulse.

**Metode:**
- Apple-to-apple comparison: median NTL Jan-Apr 2025 vs median NTL Jan-Apr 2026 (window bulan sama, minimize seasonality)
- Output per area: `pulse_yoy_pct` dan badge

**Threshold badge:**

| pulse_yoy_pct | Badge | Interpretasi |
|---|---|---|
| >= +5% | **Continuing growth** | Trend masih akselerasi |
| -5% s/d +5% | **Steady** | Stabil, tidak ada signal jelas |
| <= -5% | **Slowing/reversing** | Momentum turun, perlu watch |

**Konfidensi:** `n_months_2026` < 4 = lower confidence (VIIRS lag untuk bulan tertentu).

**Bukan komponen score** — hanya visual layer di leaderboard untuk menjawab "Apakah pattern 2021-2025 masih lanjut di 2026?"

**Update cadence:** Re-run script bulanan untuk refresh pulse. Composite ECZI tetap update tahunan saat Podes/Sakernas baru rilis.

### 6.7 Klasifikasi Kuadran Final

Dari scatter NTL growth score (x) vs POI lifestyle density (y):

| Kuadran | Label | Karakteristik tipikal |
|---|---|---|
| Hi growth + Hi POI | **Emerging Commercial Hotspot** | PIK 2 (expected) |
| Hi growth + Lo POI | **Early-stage Emerging** | Cilincing, Kalideres |
| Lo growth + Hi POI | **Mature Commercial** | Blok M, SCBD, Kelapa Gading |
| Lo growth + Lo POI | **Low Activity** | perlu investigasi konteks |

---

## 7. Limitasi dan Caveat (9 Poin Wajib Disclose)

### 7.1 Sakernas — Granularity Asymmetric (kabkota → desa interpolation)

Sakernas signal hanya bervariasi di **6 kabkota DKI × 2 KBLI = 12 unique values**, di-spread ke 267 desa. Effectively kabkota fixed effect, bukan desa-level differentiator. Group 3 weight 11% sudah reflect ini. Saat dashboard menampilkan ranking desa, pembaca perlu paham bahwa Group 3 tidak benar-benar membedakan desa-desa dalam satu kabkota.

### 7.2 Sakernas — Avg Revenue BUKAN Premium Signal di Sektor Target DKI

**Temuan empiris dari data_processing (2026-05-03):** setelah filter UMKM expand ke kategori jenis instansi 3 (Lembaga profit: PT/CV/UD/Koperasi/Firma) + 4 (Usaha perorangan/RT), avg revenue 2025 sektor perdagangan + akomodasi mamin di DKI menunjukkan pola counter-intuitive:

- Jakarta Selatan: 4.376k → 2.828k (-35%)
- Jakarta Timur: 4.092k → 2.882k (-30%)

Penjelasan: kategori 3 (CV/UD/Koperasi) di Sakernas 2025 didominasi mikro-formal-entity self-employed dengan laba lebih rendah dari usaha perorangan informal di sektor sama. **Formalisasi legal entity ≠ revenue premium di sektor perdagangan & mamin DKI.**

**Implikasi interpretasi:** Group 3 (Sakernas avg revenue) lebih tepat dibaca sebagai **median earned income proxy** untuk sektor target, BUKAN "formal premium signal" atau "high-quality commercial zone indicator". Desa dengan Group 3 score tinggi tidak otomatis berarti high-revenue commercial zone.

### 7.3 OSM — Coverage Bias Asymmetric

OSM coverage tidak uniform di DKI:
- CBD over-mapped (banyak kontributor aktif)
- Pinggiran (Cengkareng, Kalideres, Cilincing) under-mapped
- Asymmetric error → bias inflate count area central kalau dipakai untuk count

Konsekuensi: Group 4 (OSM lifestyle) weight diturunkan ke 12% (dari draft 15%). Group 5 (transport node) tetap reliable karena infrastruktur transport jauh lebih konsisten dipetakan.

### 7.4 Periode CAGR 2021-2025 (Sakernas Constraint)

Bukan 2019-2025 yang awalnya kita pikirkan. Sakernas 2019 schema KBLI tidak terdiseminasi penuh, 2020 short-form COVID. Realistic baseline = 2021. NTL + Podes + Sakernas semua align ke 2021-2025 (4 tahun) untuk apple-to-apple. Periode lama (NTL 2019-2025, Podes 2018-2025) tetap available di sub-sheet sebagai historical reference, tidak masuk composite scoring.

### 7.5 Podes 2024 ≈ 2025 untuk Sebagian Desa DKI

Untuk sebagian desa, Podes 2024 dan 2025 melaporkan angka yang sama persis (kemungkinan tidak ada update sensus aktual antara dua vintage). Akibatnya `change_pct_2024_2025` untuk desa-desa tersebut = 0, **bukan karena stagnasi nyata, melainkan artefak data**. Saat ranking, hati-hati interpretasi short-change Podes terutama untuk desa kecil.

### 7.6 NTL Saturasi di CBD

Sinyal NTL pada kawasan CBD sangat terang (>80 DNB units, contoh SCBD 95.6) cenderung terkompresi — growth signal lebih sulit terdeteksi vs kawasan baseline rendah (PIK 2 dari 2 ke 8 jelas, SCBD dari 87 ke 95 lebih subtle). Log-transform di normalisasi membantu, tapi tidak fully eliminate.

### 7.7 NTL Recent Pulse Tidak Masuk Score

NTL Recent Pulse 2025-2026 ditampilkan di dashboard sebagai **sidecar badge** (Continuing growth / Steady / Slowing-reversing), bukan komponen ECZI score. Alasan: Podes dan Sakernas tidak punya update 2026 sehingga composite anchor harus di 2025. Pembaca perlu paham bahwa "ECZI score" dan "NTL Pulse" adalah dua signal yang berbeda waktunya.

### 7.8 Hidden Imbalance Level vs Growth (52% vs 48%)

Klaim awal "growth-heavy scoring" tidak akurat. Setelah audit:
- Growth signal: 48% (NTL 20% + Podes 20% + Sakernas 8%)
- Level/density signal: 52% (NTL 4% + Podes 13% + Sakernas 3% + OSM Group 4-5 = 32%)

OSM (Group 4 dan 5) entirely level-based karena single snapshot di Phase 0. Phase 1 dengan multi-snapshot OSM bisa rebalance.

### 7.9b Group 3 BUKAN Total Revenue Absolute (Proxy Index untuk Ranking)

Hasil `count_Podes × avg_pendapatan_Sakernas` di file `composite-potensi-DKI.csv` adalah proxy index magnitude, **bukan total revenue firm-level**. Alasan:

- Sakernas mengukur pendapatan personal pekerja/pemilik usaha (Rp 2-5 juta/bulan), bukan revenue per usaha (yang seharusnya Rp 100-500 juta/usaha/tahun untuk UMKM).
- Sumber yang ideal untuk total revenue absolute: Sensus Ekonomi BPS (firm-level), tidak tersedia di Phase 0.
- Sanity check Pejagalan: angka Rp 4.27 M/tahun = 1.5% dari potensi konsumsi penduduknya (Rp ~270 M/tahun), terlalu rendah untuk total revenue real.

**Index ini valid untuk:**
- Ranking relatif antar desa (scaling konsisten di semua desa)
- Analisis perubahan tahun (CAGR, short change)
- Pembanding antar sektor (perdagangan vs akomodasi-mamin)

**Index ini TIDAK valid untuk:**
- Estimasi nominal total uang yang berputar di sektor
- Klaim absolute "Rp X miliar/tahun"

**Display strategy di dashboard (Opsi C):**

| Page | Tampilan | Tujuan |
|---|---|---|
| Overview | Skor Aktivitas Komersial (0-100, normalized) | Untuk ranking, no risk of misinterpretation |
| Drilldown | Nilai Rupiah dengan disclaimer eksplisit | Untuk pembaca kritis yang ingin lihat angka detail |
| Metodologi | Penjelasan formula + caveat | Transparansi penuh |

**Naming convention:**
- Bukan "Total Revenue Komersial"
- Pakai: **"Indeks Aktivitas Komersial"** atau **"Skor Magnitude Komersial"**
- Footnote wajib: "Indeks proxy = jumlah usaha × rata-rata pendapatan pekerja per kabupaten/kota. BUKAN total pendapatan firm-level. Gunakan untuk pembanding relatif."

### 7.10 Sensitivity Test Sub-bobot Group 4+5 Belum Dilakukan

Sub-bobot Entertainment 4% > Wellness 3% > Specialty 3% > Tourism 2% adalah expert-judgment, belum diuji empiris. Sebelum lock final, akan dilakukan sensitivity test:
- Jalankan ranking dengan flat 3% per sub-grup vs current
- Kalau top-20 desa ranking stable → sub-bobot tidak critical
- Kalau swing → flag eksplisit di dashboard "ranking sensitive ke pembobotan lifestyle sub-group"

Test ini akan dilakukan **setelah desa-level integration tersedia** (post Dashboard agent build).

---

### 7.10b Drop magnitude_change_2024_2025 dari Composite (v2.1)

Audit weighted composite menunjukkan distribusi `change_2024_2025` magnitude ekstrim skewed:
- Median: -65% (75% desa di bawah -60%)
- Mean: -59.4%
- Min: -90% | Max: +977% (Pulau Harapan)

Akar masalah: Sakernas avg_pendapatan tahun 2024 punya spike sampling (terutama kabkota daratan DKI dengan -54% to -76% YoY 2024→2025), bukan perubahan struktural commerce. **Memakai komponen ini di composite scoring akan dominate ranking dengan noise sampling, bukan sinyal real.**

**Solusi v2.1:** Drop `magnitude_change_2024_2025` dari composite (3% bobot). Realokasi:
- mag_cagr: 5% → 6% (CAGR lebih smooth, dari geomean 5 vintage)
- mag_level: 3% → 5%
- Total Group 3 tetap 11%

`magnitude_change_2024_2025` masih disimpan di file output untuk transparency, tapi **tidak masuk skor**. Bisa ditampilkan di drilldown dashboard sebagai informational saja, bukan untuk ranking.

### 7.10c Symmetric Winsorize 5th-95th Percentile (v2.1)

Semua growth metrics (NTL CAGR/change, Podes CAGR/change, Magnitude CAGR) di-winsorize symmetric **5th-95th percentile** sebelum normalisasi min-max. Bukan asymmetric 99th saja.

Alasan symmetric (vs upper-cap saja):
- Bottom outliers juga problematic (Tegal Parang -90%, Pekayon -71% magnitude change)
- Distribusi sangat skewed dari Sakernas noise — perlu cap kedua sisi

Hasil winsorize v2.1:
- 28-34 desa capped per metrik (~10-13% dari 267 desa)
- Range yang sangat ekstrim ter-truncate, ranking lebih reflektif sinyal real
- 6 desa Kepulauan Seribu di-flag `low_reliability_flag=1` karena sample size kecil di Sakernas, tapi tetap muncul di leaderboard dengan badge transparency

### 7.11 Validasi Empiris Proxy (BARU — v2.0)

Sebelum lock methodology final, dilakukan **empirical validation** untuk dua hipotesis:
- H1: Apakah NTL bisa menggantikan Sakernas (proxy revenue)?
- H2: Apakah OSM count bisa menggantikan Podes count?

**Test 1 — NTL ↔ Magnitude Komersial (per 182 desa berkualitas)**

| Pasangan | r Pearson | r Spearman |
|---|---|---|
| NTL Level 2025 vs Magnitude (raw) | 0.052 | 0.124 |
| NTL Level vs Magnitude (log-log) | 0.061 | 0.124 |
| NTL CAGR vs log Magnitude | -0.026 | -0.022 |
| NTL Level vs Count Usaha (log-log) | -0.008 | 0.052 |

**Kesimpulan H1:** **Hipotesis ditolak.** Korelasi NTL dengan magnitude komersial hampir nol (r < 0.13 di semua pengujian). NTL **TIDAK bisa proxy revenue** di level desa DKI. Mendukung Mellander et al. (2015) yang menyatakan NTL lemah sebagai magnitude indicator di micro-level. **Sakernas WAJIB retained** untuk dimensi income.

**Test 2 — OSM Count ↔ Podes Count per Kategori (267 desa)**

| Kategori | OSM Coverage | r Pearson Raw | r log-log | r Spearman | Kesimpulan |
|---|---|---|---|---|---|
| Pasar tradisional | 49.7% | 0.553 | 0.572 | 0.556 | Medium proxy |
| Restoran | 47.0% | 0.295 | 0.498 | 0.510 | Medium-low proxy |
| Minimarket | 52.6% | 0.383 | 0.387 | 0.331 | Lemah proxy |
| Kelompok pertokoan | 21.8% | 0.234 | 0.223 | 0.171 | Lemah proxy |
| **Warung mamin** | **4.6%** | **-0.037** | **0.051** | **0.069** | **GAGAL proxy** |

**Kesimpulan H2:** **Hipotesis ditolak.** OSM tidak bisa replace Podes untuk count usaha. Coverage gap besar — terutama warung mamin (OSM cover hanya 4.6% dari 18.916 warung Podes). **Podes adalah ground truth** untuk count.

**Implikasi metodologis:**
- Multi-source design **dibenarkan empirically** — tidak ada source yang cukup standalone
- NTL dan Sakernas menangkap dimensi **independen** (r ~0) — keduanya wajib di composite
- OSM **valuable untuk visualisasi titik dan kategori non-Podes**, bukan sebagai count proxy
- Caveat 7.3 (OSM coverage bias asymmetric) **dibuktikan empirically**

**File output:** `260503_VALIDATION_correlations.xlsx` + `260503_VALIDATION_summary.md`

---

## 7B. Caveat Tambahan (Diretain dari Versi Lama)

### NTL — Quality observation
- Monthly composite DKI Jakarta terbukti **semua 84 bulan (2019-2025) berkualitas "high"** (valid_obs >= 20 setiap bulan). Caveat awal "musim hujan noisy" tidak terbukti di DKI. Mungkin berbeda untuk wilayah dengan curah hujan ekstrem (Bogor, Malang) saat Phase 1.
- Jul-Sep composite tidak capture year-end shopping season peak (Nov-Des).

### OSM — Atribut
- Nama terisi 98%, alamat 1%, brand 52% — analisis berbasis count/density lebih robust dari atribut.
- Toko kelontong dan pasar tradisional severely under-represented di OSM Indonesia, hanya tertangkap via Podes.

### Podes — Definisi
- Kolom (3) jarak dan (4) flag tidak dipakai dalam scoring — hanya jumlah (2).
- Definisi "warung mamin" vs "restoran" berbeda threshold (pajak) — ada grey area di pemetaan ke OSM equivalent.

---

## 8. Referensi Akademik

### Layer A: Nighttime Lights

1. **Henderson, J.V., Storeygard, A., & Weil, D.N. (2012).** Measuring Economic Growth from Outer Space. *American Economic Review*, 102(2), 994-1028. DOI: 10.1257/aer.102.2.994
   - *Justifikasi:* Dasar penggunaan NTL sebagai proxy aktivitas ekonomi spasial; elastisitas 0.3 antara NTL growth dan GDP growth

2. **Gibson, J., Olivia, S., & Boe-Gibson, G. (2020).** Night Lights in Economics: Sources and Uses. *Journal of Economic Surveys*, 34(5), 955-980. DOI: 10.1111/joes.12387
   - *Justifikasi:* Review penggunaan NTL di negara berkembang; mendukung Jul-Sep composite untuk Indonesia

3. **Elvidge, C.D., Baugh, K., Zhizhin, M., Hsu, F.C., & Ghosh, T. (2017).** VIIRS night-time lights. *International Journal of Remote Sensing*, 38(21), 5860-5879. DOI: 10.1080/01431161.2017.1342050
   - *Justifikasi:* Deskripsi teknis VIIRS DNB Black Marble (VNP46A2); validasi BRDF-corrected band

4. **Mellander, C., Lobo, J., Stolarick, K., & Matheson, Z. (2015).** Night-Time Light Data: A Good Proxy Measure for Economic Activity? *PLOS ONE*, 10(10), e0139779. DOI: 10.1371/journal.pone.0139779
   - *Justifikasi:* NTL sebagai proxy kepadatan ekonomi lebih kuat daripada sebagai sole growth indicator; mendukung level score sebagai komponen terpisah dari growth score

### Layer B: POI dan Urban Vitality

5. **Yue, Y., Zhuang, Y., Yeh, A.G.O., Xie, J., Ma, C., & Li, Q. (2017).** Measurements of POI-based mixed use and their relationships with neighbourhood vibrancy. *International Journal of Geographical Information Science*, 31(4), 658-675. DOI: 10.1080/13658816.2016.1248508
   - *Justifikasi:* POI density dan Shannon diversity berkorelasi dengan vibrancy kawasan — basis poi_diversity_shannon di scoring

6. **Li, M., Yu, Z., & Li, R. (2023).** Spatial Characteristics and Influencing Factors of Multiscale Night-Time Economy. *ISPRS International Journal of Geo-Information*, 12(5), 205. DOI: 10.3390/ijgi12050205 *(perlu verifikasi)*
   - *Justifikasi:* Clustering F&B dan entertainment sebagai inti night-time commercial circuit; transport sebagai faktor terkuat kedua

7. **Jacobs, J. (1961).** *The Death and Life of Great American Cities.* New York: Random House.
   - *Justifikasi:* Fondasi teoritis mixed-use dan diversity sebagai prasyarat vitalitas kawasan; basis Shannon diversity index di scoring

### Layer C: Built Environment dan Aksesibilitas

8. **Ewing, R., & Cervero, R. (2010).** Travel and the Built Environment: A Meta-Analysis. *Journal of the American Planning Association*, 76(3), 265-294. DOI: 10.1080/01944361003766766
   - *Justifikasi:* Land use mix dan proximity ke transit node sebagai prediktor terkuat footfall komersial

9. **Hansen, W.G. (1959).** How Accessibility Shapes Land Use. *Journal of the American Institute of Planners*, 25(2), 73-76. DOI: 10.1080/01944365908978307
   - *Justifikasi:* Fondasi formula transport_access_score: weighted sum interaksi potential dengan decay jarak (weight/distance)

---

## 9. File Inventory

### Input data (di `Dashboard\emerging-zone-jakarta\data\`)

| File | Source agent | Status |
|---|---|---|
| `260502_NASA_jakarta-area-analysis.xlsx` | Scraping | Ready |
| `260502_OSM_poi-commercial-jakarta.xlsx` | Scraping | Ready |
| `260502_OSM_transport-jakarta.xlsx` | Scraping | Ready |
| `260503_OSM_poi-lifestyle-jakarta.xlsx` | Scraping | Ready |
| `260503_NASA_jakarta-monthly-areas.xlsx` | Scraping | Ready |
| `260503_NASA_jakarta-recent-pulse.xlsx` | Scraping | Ready (sidecar indicator) |
| `260503_BPS_podes-business-DKI.xlsx` | data_processing | Ready (v3, di Riset Initiatives folder) |
| `260503_BPS_sakernas-revenue-DKI.xlsx` | data_processing | Ready (v3, di Riset Initiatives folder) |
| `podes-business-DKI.csv` | data_processing | Ready (di Dashboard data folder) |
| `sakernas-revenue-DKI.csv` | data_processing | Ready (v3, di Dashboard data folder) |
| `composite-potensi-DKI.csv` | data_processing | Ready (input feature, BUKAN final composite) |
| `260503_NASA_jakarta-growth-2021baseline.csv` | Scraping | Ready (NTL CAGR 2021-2025 final baseline) |
| `metadata.json` | Scraping | Ready (v2 pending update) |
| `METHODOLOGY.md` | Scraping | Ready (this file) |

### Output dashboard

| File | Owner | Status |
|---|---|---|
| `260503_NASA_emerging-zone-detector.html` | Dashboard | Pending (blocked by data_processing) |

---

*Dokumen ini diupdate setiap kali ada perubahan metodologi signifikan. Versi history dicatat di changelog handoff.*
