# Validasi Empiris Proxy — DKI Jakarta Phase 0

Generated: 2026-05-03 19:09

## Test 1: NTL sebagai Proxy Magnitude Komersial

Apakah cahaya malam (NTL) bisa menggantikan dimensi pendapatan/magnitude?

| Pasangan | r Pearson | r Spearman | n |
|---|---|---|---|
| NTL Level 2025 vs Magnitude (raw) | 0.052 | 0.124 | 182 |
| NTL Level vs Magnitude (log-log) | 0.061 | 0.124 | 182 |
| NTL CAGR vs log Magnitude | -0.026 | -0.022 | 182 |
| NTL Level vs Count Usaha (raw) | 0.021 | 0.052 | 182 |
| NTL Level vs Count Usaha (log-log) | -0.008 | 0.052 | 182 |


**Interpretasi:**
- r > 0.7: NTL dapat menggantikan dimensi magnitude (drop Sakernas mungkin OK)
- r 0.4-0.7: NTL partial proxy, keep both source
- r < 0.4: NTL menangkap dimensi berbeda, WAJIB keep Sakernas

## Test 2: OSM Count sebagai Proxy Podes Count

Apakah OSM bisa menggantikan Podes untuk count usaha?

| Kategori | n desa | OSM coverage | r raw | r log-log | r spearman |
|---|---|---|---|---|---|
| restoran | 267 | 47.0% | 0.295 | 0.498 | 0.51 |
| warung_mamin | 267 | 4.6% | -0.037 | 0.051 | 0.069 |
| minimarket | 267 | 52.6% | 0.383 | 0.387 | 0.331 |
| kelompok_pertokoan | 267 | 21.8% | 0.234 | 0.223 | 0.171 |
| pasar_combined | 267 | 49.7% | 0.553 | 0.572 | 0.556 |


**Interpretasi:**
- OSM coverage >50%, r >0.7: kategori dengan OSM mapping baik (kemungkinan: chain retail, mall)
- OSM coverage 20-50%, r 0.4-0.7: OSM partial proxy, gunakan Podes sebagai primary
- OSM coverage <20%, r <0.4: OSM coverage gap besar (kemungkinan: warung mamin, toko kelontong)

**Kesimpulan empiris:** confirms caveat 7.3 (OSM coverage bias). Podes adalah ground truth untuk count usaha; OSM complementary untuk visualisasi titik dan kategori non-Podes.
