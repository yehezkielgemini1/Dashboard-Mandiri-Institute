# PROMPT untuk Dashboard Agent (v3 — Final, post audit + spatial join)

Halo Dashboard. Build HTML dashboard final "Pendeteksi Kawasan Komersial
Berkembang DKI Jakarta 2021-2025" untuk Mandiri Institute.

**Versi sebelumnya (rev1, rev2) ditarik** — semua data sudah di-rebuild
proper di Phase 0 ini dengan spatial join ke 270 polygon desa BPS adm4 +
empirical validation. **Tugasmu HANYA build UI dari file final, NO DATA
PROCESSING sama sekali.**

================================================================
ATURAN UTAMA
================================================================

1. **JANGAN OLAH DATA.** Semua score, normalisasi, kategori, ranking
   sudah dihitung di `260503_FINAL_eczi_per_desa.csv` dan
   `260503_FINAL_eczi_per_kawasan.csv`. Tugasmu render UI.

2. **Unit analisis 4 tier:** Wilayah Berpotensi (21 kawasan, default) /
   Desa (270) / Kecamatan / Kabkota — dengan toggle.

3. **Terminologi Indonesia ramah** — daftar terjemahan strict di bawah.

4. **FORMAT WAJIB konsisten dengan dashboard Mandiri Institute lainnya.**
   Reference style: `Dashboard/index.html` (portal),
   `Dashboard/ketahanan-pangan/ketahanan-pangan-dashboard.html`,
   `Dashboard/konsumsi-susenas/dashboard.html`. Pakai brand color navy
   #003D79 + accent yellow #FFB700, font Source Serif 4 + Inter, hero
   band navy, ticker bar KPI. Detail di section "Stack Teknis".

5. **WAJIB RETAIN peta Leaflet** dari versi `260502_NASA_emerging-zone-detector.html`
   — peta yang sebelumnya bagus harus di-keep dan extend (choropleth desa,
   marker POI, heatmap NTL, layer toggle). Detail di section "Stack Teknis".

6. **Link kembali ke portal utama:** dashboard wajib punya breadcrumb
   "← Kembali ke Dashboard Suite" pointing ke `../index.html`.

7. **Output:** `260503_NASA_emerging-zone-detector.html` di
   `Dashboard\emerging-zone-jakarta\` (overwrite versi lama).
   Update juga `Dashboard\index.html` portal entry kalau ada perubahan
   judul/jumlah desa.

================================================================
DATA SOURCES
================================================================

Semua di `Dashboard\emerging-zone-jakarta\data\`:

**Source utama (yang dipakai untuk UI):**

1. `260503_FINAL_eczi_per_desa.csv` — file primary (level desa, 270 baris)
   Kolom yang tersedia:
   - Identitas: rank_eczi, rank_magnitude, desa_pcode, nama_desa,
     nama_kecamatan, nama_kabkota, centroid_lat, centroid_lon
   - Komponen Layer 1 NTL: ntl_cagr_2021_2025, ntl_change_2024_2025,
     ntl_level_2025, ntl_recovery_2021_2025, n_pixels, quality_flag
   - Komponen Layer 2 Podes: podes_count_2025, podes_cagr_2021_2025,
     podes_change_2024_2025, podes_level_2025, podes_diversity_shannon,
     podes_winsorize_flag
   - Komponen Layer 3 Magnitude: magnitude_2025, magnitude_cagr_2021_2025,
     magnitude_change_2024_2025, magnitude_perdagangan_2025,
     magnitude_akomamin_2025
   - Komponen Layer 4 OSM: count_hiburan_nightlife,
     count_gaya_hidup_wellness, count_retail_khusus, count_wisata_budaya
   - Komponen Layer 5 Aksesibilitas: transport_access_score_raw,
     count_layanan_penunjang, catchment_density_1km
   - Pulse sidecar: pulse_badge, pulse_yoy_2026
   - Normalized 0-100: n_ntl_cagr, n_ntl_change, n_ntl_level, n_podes_*,
     n_mag_*, n_osm_*, n_tra_*
   - Group scores: g1, g2, g3, g4, g5 (0-100 per group)
   - **eczi_score** (composite primary, 0-100)
   - **magnitude_score** (composite secondary, 0-100)
   - **tipe_kawasan** (4 kategori sudah classified)
   - low_reliability_flag (1 untuk Kep Seribu)

2. `260503_FINAL_eczi_per_kawasan.csv` — TIER ADDITIONAL: Wilayah Berpotensi
   - 21 baris (per kawasan utama: Blok M, PIK, Kelapa Gading, Mega Kuningan,
     SCBD, Kemang, Cipete, Tanjung Duren Mall Corridor, Cipayung Cluster, dll)
   - Aggregasi dari 270 desa via mapping kawasan → desa member
   - Setiap kawasan ada deskripsi + list desa member transparan
   - Kolom mirror per_desa, plus: kawasan, kabkota, deskripsi, n_desa_member,
     desa_members, desa_missing

3. `kawasan_utama_mapping.json` — mapping desa → kawasan utama (reference)

4. `METHODOLOGY.md` v2.1 — full methodology lengkap (read first)
5. `260503_VALIDATION_correlations.xlsx` + `260503_VALIDATION_summary.md`
   — empirical validation

**Source untuk visualisasi peta (jangan olah, langsung render):**

4. `260503_OSM_poi-lifestyle-jakarta.xlsx` — 8.705 POI dengan lat/lon
   untuk titik di peta (sheet `all_lifestyle`)
5. `260502_OSM_transport-jakarta.xlsx` — 5.054 transport node
6. `260502_NASA_jakarta-area-analysis.xlsx` sheet `pixel_change_map` —
   6.557 pixel NTL untuk heatmap

**Shapefile untuk choropleth:**

7. Shapefile desa DKI (270 polygon): `C:\Users\LENOVO\OneDrive - PT Bank Mandiri (Persero) Tbk\Desktop\Mandiri\Software\IDN_shp\idn_admbnda_adm4_bps_20200401.shp`
   Filter `ADM1_PCODE == 'ID31'`. Convert ke GeoJSON kalau perlu.

================================================================
ATURAN TERMINOLOGI (STRICT — JANGAN DILANGGAR)
================================================================

| ❌ JANGAN | ✅ WAJIB |
|---|---|
| ECZI | Skor Potensi Zona Komersial |
| Sustained Explosive | Pertumbuhan Berkelanjutan Cepat |
| Mature Emerging | Sudah Mapan, Mulai Melambat |
| Late Bloomer | Berkembang Belakangan |
| Stable/Declining | Stagnan atau Menurun |
| Emerging Hotspot | Kawasan Komersial Sedang Naik Daun |
| Early-stage | Awal Pertumbuhan |
| Mature Commercial | Kawasan Komersial Mapan |
| Low Activity | Aktivitas Rendah |
| Continuing growth | Trend Lanjut Tumbuh |
| Steady | Stabil |
| Slowing/reversing | Mulai Melambat |
| NTL | Cahaya Malam (Satelit) |
| POI | Tempat Usaha/Fasilitas |
| KBLI | Kode Sektor Usaha (KBLI) |
| CAGR | Pertumbuhan Tahunan Rata-rata |
| YoY | Perbandingan Tahun ke Tahun |
| OSM | OpenStreetMap |
| BPS | Badan Pusat Statistik |
| Podes | Sensus Potensi Desa (Podes) |
| Sakernas | Survei Angkatan Kerja Nasional (Sakernas) |
| MRT | Mass Rapid Transit (MRT) |
| KRL | Kereta Rel Listrik (KRL) |
| TJ | TransJakarta |
| min-max normalization | Normalisasi Skala 0-100 |
| log1p | Transformasi Logaritmik |
| Shannon diversity | Indeks Keberagaman Shannon |
| F&B | Makanan & Minuman |
| ECZI score | Skor Potensi |
| g1 g2 g3 g4 g5 | Cahaya Malam, Tempat Usaha, Aktivitas Komersial, Gaya Hidup, Aksesibilitas |
| D1 D2 D3 D4 D5 | (sda, jangan singkatan) |

**Aturan tampilan:**

- Setiap halaman ada **paragraf pembuka 2-3 kalimat** Indonesia ringan
- Setiap chart ada **caption** singkat 1 kalimat
- Tooltip pakai bahasa Indonesia, bukan kode variabel
- Angka teknis wajib ada unit eksplisit:
  "Pertumbuhan +12,7% per tahun" bukan "0.127"
- Tanggal Indonesia: "3 Mei 2026" bukan "2026-05-03"
- Mata uang: "Rp 4,27 miliar" bukan "Rp 4,270,000,000"
- Header tabel jangan singkatan

================================================================
STRUKTUR DASHBOARD: 6 HALAMAN
================================================================

### Halaman 1 — Ringkasan Eksekutif

Paragraf pembuka:
"Dashboard ini memetakan kawasan komersial DKI Jakarta yang sedang
berkembang berdasarkan kombinasi 4 sumber data: cahaya malam satelit,
jumlah tempat usaha (Podes BPS), pendapatan sektor komersial (Sakernas BPS),
dan kepadatan fasilitas dari OpenStreetMap. Skor 0-100 menunjukkan potensi
kawasan, semakin tinggi semakin kuat sinyal pertumbuhan."

**TOGGLE TIER UTAMA di header dashboard:**
Pengguna bisa pilih tier analisis:
- "Wilayah Berpotensi" (21 kawasan informal: Blok M, PIK, Kelapa Gading, dll) ← DEFAULT
- "Desa / Kelurahan" (270 desa BPS)
- "Kecamatan" (44, agregasi dari desa)
- "Kabupaten / Kota" (6, agregasi)

Default tampilan: tier "Wilayah Berpotensi" (paling intuitif untuk pembaca casual).
User bisa zoom in ke desa untuk detail.

Konten:
- 6 KPI Cards berdampingan:
  * "Kawasan dengan Skor Potensi Tertinggi": [nama_desa] — [eczi_score]/100
  * "Magnitude Aktivitas Komersial Tertinggi": [nama_desa] — Rp [magnitude_2025]
  * "Pertumbuhan Cahaya Malam Tertinggi": [nama_desa] — +[%]/tahun
  * "Total Tempat Usaha DKI 2025": [sum podes_count_2025]
  * "Rentang Kuadran Tipe Kawasan": 4 kategori
  * "Update Terakhir": April 2026 (Cahaya Malam) | 2025 (Podes/Sakernas)
- DUAL Leaderboard tab:
  * Tab 1: "10 Kawasan Teratas — Skor Potensi" (sort by eczi_score)
    Kolom: Rank | Nama Desa | Kabupaten/Kota | Skor (0-100) | Tipe Kawasan | Trend Terkini (badge)
  * Tab 2: "10 Kawasan Teratas — Magnitude" (sort by magnitude_score)
    Kolom: Rank | Nama Desa | Kabupaten/Kota | Skor Magnitude | Total Potensi (Rp) | Tipe Kawasan
- Sparkline mini Cahaya Malam 2019-2026 untuk top 5 desa (dari NTL monthly)
- Footer disclaimer:
  "Cahaya malam adalah proxy intensitas aktivitas urban, BUKAN ukuran
  langsung PDRB, transaksi, atau daya beli."

### Halaman 2 — Peta Cahaya Malam & Pertumbuhan (Layer 1)

Paragraf pembuka:
"Halaman ini menampilkan tren intensitas cahaya malam DKI Jakarta dari
satelit NASA periode 2019-2026. Cahaya malam berkorelasi dengan intensitas
aktivitas urban — kawasan yang semakin terang biasanya mengalami
peningkatan aktivitas spasial."

Konten:
- Peta choropleth desa DKI dengan warna berdasar **n_ntl_cagr** (atau
  ntl_cagr_2021_2025), pakai shapefile + GeoJSON
- Filter slider tahun 2019-2026 → update peta berdasar lum bulan tersebut
  (dari monthly data)
- Time series multi-line untuk semua desa atau filter top 20 (dari NTL monthly)
- Bar chart "Pertumbuhan Tahunan Rata-rata 2021-2025 per Desa" sortir desc
  → tampilkan 30 teratas + 30 terbawah (bisa toggle)
- "Indikator Trend Terkini" panel — kartu badge per desa (yang ada pulse data):
  * 🟢 Trend Lanjut Tumbuh
  * 🟡 Stabil
  * 🔴 Mulai Melambat
- Catatan kecil: "Trend Terkini = perbandingan Januari-April 2025 vs
  Januari-April 2026. INDIKATOR TAMBAHAN, tidak masuk Skor Potensi yang
  di-anchor di tahun 2025."

### Halaman 3 — Aktivitas Komersial Mikro (Layer 2 + 4)

Paragraf pembuka:
"Halaman ini menampilkan kepadatan tempat usaha dan fasilitas komersial.
Data jumlah usaha dari Sensus Potensi Desa BPS (270 desa lengkap), dan
visualisasi titik fasilitas spesifik seperti bioskop, gym, museum dari
OpenStreetMap."

Konten:
- Peta interaktif Leaflet:
  * Layer dasar: shapefile desa polygon
  * Layer 1: choropleth Podes count per desa (slider toggle)
  * Layer 2: heatmap OSM lifestyle density
  * Layer 3 (toggle): marker individual untuk:
    - Hiburan & Kehidupan Malam (bioskop, klub, teater)
    - Gaya Hidup & Wellness (gym, spa, salon)
    - Wisata & Budaya (museum, galeri)
    - Transportasi (warna by tier MRT/KRL/halte)
- Bar chart "10 Desa Teratas — Jumlah Tempat Usaha":
  Sortir podes_count_2025 desc, tooltip menampilkan breakdown 10 kategori Podes
- Stacked bar "Distribusi Sektor per Desa Top 30":
  X: nama_desa, stack: Perdagangan (KBLI 7) vs Akomodasi & Mamin (KBLI 9)
  Pakai magnitude_perdagangan_2025 + magnitude_akomamin_2025
- Tabel "Indeks Keberagaman Usaha (Shannon) per Desa":
  Sortir podes_diversity_shannon desc
  Caption: "Skor lebih tinggi = mix usaha lebih beragam, indikator
  vitalitas urban yang lebih kuat (Jacobs, 1961)"

### Halaman 4 — Skor Potensi & Magnitude (Composite)

Paragraf pembuka:
"Halaman ini menampilkan dua skor utama hasil composite multi-source:
**Skor Potensi Zona Komersial** (mengukur sinyal pertumbuhan, growth-focus)
dan **Skor Magnitude Aktivitas Komersial** (mengukur ukuran ekonomi
komersial saat ini, level-focus). Klasifikasi 4 tipe kawasan membantu
memetakan posisi setiap desa dalam siklus pertumbuhan."

Konten Tab 1 — Skor Potensi:
- Leaderboard 270 desa (sortir eczi_score desc)
- Filter: kabupaten/kota, tipe kawasan, search nama desa
- Expandable row per desa: radar chart 5 grup (g1-g5 nilainya 0-100)
- Caption per komponen group:
  * Cahaya Malam (Bobot 24%): cagr 13% + change 7% + level 4%
  * Tempat Usaha (Bobot 33%): cagr 13% + change 7% + level 9% + diversity 4%
  * Aktivitas Komersial (Bobot 11%): cagr 5% + change 3% + level 3%
  * Gaya Hidup (Bobot 12%): hiburan 4% + wellness 3% + retail 3% + wisata 2%
  * Aksesibilitas (Bobot 20%): transport 12% + layanan 5% + catchment 3%
- Scatter quadrant "Tipe Kawasan":
  X-axis = n_ntl_cagr (Skor Pertumbuhan Cahaya Malam, 0-100)
  Y-axis = g4 (Skor Gaya Hidup, 0-100)
  Size = n_tra_access
  Color = tipe_kawasan
  Threshold: median split (sudah dihitung di file final)

Konten Tab 2 — Skor Magnitude:
- Leaderboard 270 desa (sortir magnitude_score desc)
- Wajib disclaimer dalam box ⚠️ kuning bold:

  "Indeks Aktivitas Komersial — Proxy Index untuk Ranking
  
  Angka Rupiah ini = Jumlah Tempat Usaha (Podes) × Rata-rata Pendapatan
  Pekerja Sektor (Sakernas).
  
  Sakernas mengukur pendapatan PERSONAL pekerja per bulan (Rp 2-5 juta),
  BUKAN revenue per usaha. Indeks ini valid untuk pembanding RELATIF
  antar desa, BUKAN klaim absolute Rupiah.
  
  Untuk total revenue absolute akurat, perlu Sensus Ekonomi BPS
  (firm-level), tidak tersedia di Phase 0."

- Bar chart top 10 desa by Indeks Aktivitas Komersial 2025
- Stacked breakdown: Perdagangan vs Akomodasi-Mamin
- Trend 2021 → 2024 → 2025 stepped chart per desa (multi-select)

### Halaman 5 — Detail per Kawasan (Drilldown)

Paragraf pembuka:
"Pilih desa di sidebar untuk melihat profil lengkap kawasan: tren cahaya
malam, jumlah tempat usaha per kategori, indeks aktivitas komersial,
fasilitas sekitar, dan klasifikasi tipe kawasan."

Konten per desa (5 tab):
- Tab "Cahaya Malam": time series 2019-2026 + pulse + tabel komponen NTL
- Tab "Tempat Usaha (Podes)": 10 kategori, 5 vintage, growth metrics,
  warning kalau podes_winsorize_flag = TRUE
- Tab "Aktivitas Sektor": Indeks Komersial per sektor + disclaimer
  proxy index (sda Halaman 4)
- Tab "Fasilitas Sekitar": peta + list POI dalam radius 1 km dari centroid
- Tab "Aksesibilitas": jarak ke MRT/KRL/halte terdekat + skor

### Halaman 6 — Metodologi & Validasi

Paragraf pembuka:
"Halaman ini menjelaskan secara transparan bagaimana skor dihitung,
sumber data yang dipakai, validasi empiris, dan referensi akademik."

Konten:
1. Section "Cara Membaca Dashboard": ringkasan 1 paragraf per halaman
2. Section "Sumber Data": tabel 4 layer + peran unik (dari METHODOLOGY.md)
3. Section "Skor Potensi: Formula dan Bobot":
   - Tabel 5 grup × 12 komponen + bobot
   - Diagram donut bobot
   - Penjelasan log-transform untuk variabel level
4. Section "Validasi Empiris" — IMPORTANT:
   - Test 1: NTL ↔ Magnitude. Tampilkan tabel + scatter plot.
     Konfirmasi r ~0.05 → multi-source dibenarkan empiris
   - Test 2: OSM ↔ Podes per kategori. Tampilkan korelasi r per kategori.
     Konfirmasi OSM tidak proxy reliable, Podes ground truth
5. Section "Batasan dan Catatan Penting" — 11 caveat dari METHODOLOGY.md
   sect 7.1-7.11. Tampilkan dengan icon ⚠️ untuk yang kritis (7.2 dan 7.9b).
6. Section "Referensi Akademik": 9 ref dari METHODOLOGY.md sect 8 dengan
   DOI link aktif
7. Section "Cadence Update Data":
   - Cahaya Malam: bulanan
   - Tempat Usaha (Podes): tahunan
   - Pendapatan Sektor (Sakernas): tahunan
   - OpenStreetMap: per kebutuhan

================================================================
STACK TEKNIS — WAJIB IKUT FORMAT MANDIRI INSTITUTE
================================================================

Dashboard ini WAJIB konsisten dengan dashboard lain di portal
(`Dashboard/index.html`). Reference dashboard yang harus diikuti:
- `Dashboard/ketahanan-pangan/ketahanan-pangan-dashboard.html`
- `Dashboard/konsumsi-susenas/dashboard.html`
- `Dashboard/index.html` (portal utama)
- `Dashboard/emerging-zone-jakarta/260502_NASA_emerging-zone-detector.html`
  (versi LAMA — referensi untuk peta Leaflet yang BAGUS, retain)

### Brand & Visual System (WAJIB konsisten)

Color palette (Mandiri Official):
- `--navy: #003D79` (primary)
- `--navy-deep: #002852`
- `--sky: #67B2E8`
- `--yellow: #FFB700` (accent)
- `--ink: #051C2C`
- `--rule: #D0D5DD`
- `--muted: #667085`
- `--paper: #FFFFFF`
- `--cream: #F4F1EA`
- `--mist: #EAF1F8`

Typography:
- Body: 'Inter', system-ui, sans-serif
- Display headings: 'Source Serif 4', Georgia, serif (font-weight 500-600)
- Eyebrow text: 11px font-weight 600 letter-spacing 0.14em uppercase color sky

Pakai `_assets/` shared resources kalau ada:
- `../_assets/tailwind.min.js`
- `../_assets/iconify-icon.min.js`
- `../_assets/icons.js`
- `../_assets/alpine.min.js`
- `../_assets/fonts/fonts.css`

### Layout Pattern Wajib (mirror dashboard lain)

1. **Top brand band** (top of page): "Mandiri Institute · Dashboard Suite"
   dengan yellow accent square + tagline + breadcrumb back ke index.html
2. **Hero section** dengan navy background:
   - Eyebrow "Riset Mandiri Institute · Spasial Ekonomi"
   - Yellow accent square 12x12 px sebelum title
   - H1 serif-display besar (5xl-6xl)
   - Description paragraph dengan opacity 78%
   - Ticker bar dengan 4 KPI utama (mirror format ticker di index.html)
3. **Tab navigation** (sticky di bawah hero) untuk 6 halaman
4. **Content per tab** dengan layout konsisten

### PETA INTERAKTIF (WAJIB RETAIN dari versi 260502)

Versi 260502_NASA_emerging-zone-detector.html sudah punya peta Leaflet
yang bagus. WAJIB di-retain dan extend, jangan dihapus:

- Peta utama Leaflet di Halaman 2 dan Halaman 3
- Layer choropleth desa polygon (warna by ECZI atau NTL CAGR)
- Layer titik POI individual dengan popup
- Layer heatmap NTL
- Layer toggle untuk tier (kawasan/desa/kecamatan/kabkota)
- Tile basemap CartoDB Positron atau OSM standard
- Marker cluster untuk POI density tinggi

Tools: Leaflet.js + Leaflet.heat + Leaflet.markercluster (semua via CDN)

### Stack Komplet

- HTML statis self-contained, dependency CDN
- Plotly.js untuk chart (consistent dengan dashboard lain)
- Leaflet.js + Leaflet.heat + Leaflet.markercluster untuk peta interaktif
- Tailwind CSS via CDN (atau pakai _assets/tailwind.min.js)
- Alpine.js untuk reactive state (optional, kalau butuh tab/filter)
- Source Serif 4 + Inter fonts via fonts.css atau Google Fonts
- Iconify untuk semua icon (no inline SVG kompleks)

- File output: `Dashboard\emerging-zone-jakarta\260503_NASA_emerging-zone-detector.html`
- Mobile responsive minimal tablet width (1024px+)

### Footer Konsisten

Footer di akhir halaman:
```
Mandiri Institute · Dashboard Suite | Plotly.js · Leaflet.js · Tailwind CSS
| Sumber: NASA VIIRS · Podes BPS · Sakernas BPS · OpenStreetMap
```

Plus link "← Kembali ke Portal" di footer pointing ke `../index.html`

================================================================
SANITY CHECK SEBELUM DELIVER
================================================================

Sebelum handoff, validasi hasil:

✓ 270 desa muncul di leaderboard (bukan 16 named area)
✓ Pejagalan masuk top 5 Magnitude (BUKAN top emerging — itu Mapan)
✓ Melawai (Blok M area) badge "Trend Lanjut Tumbuh" di pulse
✓ Karet Semanggi/Kuningan/Tanjung Duren cluster di top emerging
✓ Distribusi tipe kawasan 4 kategori reasonable (bukan semua satu kuadran)
✓ Sumbu X scatter quadrant menunjukkan distribusi continuous (bukan
  cluster vertikal — kalau masih cluster, ada bug load data)
✓ Disclaimer 7.9b proxy index muncul jelas di Halaman 4 Tab 2
✓ Tidak ada label "Sustained Explosive", "Late Bloomer", dll
  (semua sudah translate Indonesia)
✓ Header tabel jangan singkatan (no ECZI, D1, D2, dll)
✓ Validation correlation Test 1 dan Test 2 ditampilkan di Halaman 6

================================================================
DELIVERABLE
================================================================

1. `260503_NASA_emerging-zone-detector.html` (replace existing)
2. Update handoff `dashboard/emerging-zone-jakarta-dashboard.md` dengan:
   - Sanity check passed/flagged
   - File yang dipakai
   - 1 paragraf executive summary menjawab:
     "Berdasarkan dual leaderboard, kawasan mana paling menjanjikan
      sebagai emerging dan kawasan mana paling besar magnitude
      komersialnya?"
3. Update _INDEX.md
4. Notify Lead

================================================================
JIKA ADA HAMBATAN
================================================================

JANGAN coba olah data sendiri. Kalau ada data yang missing/aneh, raise
ke Lead. Kalau bobot ECZI mau diubah, ROYAL TRUE — diskusi dulu, jangan
modify.
````

