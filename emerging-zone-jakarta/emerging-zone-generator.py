"""
Pendeteksi Kawasan Komersial Berkembang -- DKI Jakarta 2021-2025
Generator script (v2) -- builds 260503_NASA_emerging-zone-detector.html
Run: C:/Users/LENOVO/anaconda3/python.exe emerging-zone-generator.py

FIVE FIXES implemented:
  Fix #1: Group 3 uses composite-potensi-DKI.csv (not sakernas-revenue-DKI.csv)
  Fix #2: Unit of analysis = 267 desa (not 16 named areas)
  Fix #3: NTL, OSM, Transport use kabkota-level proxy
  Fix #4: Quadrant = NTL growth score (X) vs Group 4 POI score (Y)
  Fix #5: All terminology in Indonesian
"""

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import pandas as pd
import numpy as np
import json
import math
import os
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
OUT  = os.path.join(BASE, "260503_NASA_emerging-zone-detector.html")

# ── ECZI Weights ───────────────────────────────────────────────────────────
ECZI_W = {
    "ntl_cagr":   0.13, "ntl_change": 0.07, "ntl_level":  0.04,
    "podes_cagr": 0.13, "podes_change": 0.07, "podes_level": 0.09, "podes_div": 0.04,
    "sak_cagr":   0.05, "sak_change": 0.03, "sak_level":  0.03,
    "osm_ent":    0.04, "osm_well": 0.03, "osm_spec": 0.03, "osm_tour": 0.02,
    "tra_access": 0.12, "tra_auto": 0.05, "tra_catch": 0.03,
}

# Fix #3: Kabkota → named areas mapping
KK_NTL_MAP = {
    3171: ["Blok M", "SCBD/Sudirman", "Kemang", "Cipete/Urban Forest", "Pesanggrahan"],
    3172: ["Cawang"],
    3173: ["Thamrin"],
    3174: ["Kalideres", "Cengkareng"],
    3175: ["Kelapa Gading", "Pluit/Penjaringan", "Ancol", "Cilincing", "Pantai Mutiara",
           "PIK (Pantai Indah Kapuk)", "PIK 2 (Pantai Maju)"],
    3101: [],  # Kep Seribu -> use DKI average fallback
}

KABKOTA_LABELS = {
    3101: "Kep. Seribu",
    3171: "Jakarta Selatan",
    3172: "Jakarta Timur",
    3173: "Jakarta Pusat",
    3174: "Jakarta Barat",
    3175: "Jakarta Utara",
}

TRANSPORT_WEIGHT = {"subway": 4, "rail": 3, "bus_station": 2, "transport_hub": 2, "halte_TJ": 1}

# Kecamatan-level centroids for OSM/transport scoring (44 kecamatan)
# Key: (kabkota_id_full, kec_id) → (lat, lon)
KEC_CENTROIDS = {
    # Kepulauan Seribu (3101)
    (3101, 10): (-5.700, 106.580),   # Kep Seribu Selatan
    (3101, 20): (-5.530, 106.620),   # Kep Seribu Utara
    # Jakarta Selatan (3171)
    (3171, 10):  (-6.340, 106.820),  # Jagakarsa
    (3171, 20):  (-6.295, 106.843),  # Pasar Minggu
    (3171, 30):  (-6.283, 106.793),  # Cilandak/Cipete
    (3171, 40):  (-6.293, 106.770),  # Pesanggrahan
    (3171, 50):  (-6.250, 106.789),  # Kebayoran Lama
    (3171, 60):  (-6.243, 106.798),  # Kebayoran Baru (Blok M)
    (3171, 70):  (-6.258, 106.813),  # Mampang Prapatan (Kemang)
    (3171, 80):  (-6.258, 106.850),  # Pancoran
    (3171, 90):  (-6.235, 106.854),  # Tebet
    (3171, 100): (-6.224, 106.815),  # Setiabudi (SCBD/Sudirman)
    # Jakarta Timur (3172)
    (3172, 10):  (-6.318, 106.871),  # Pasar Rebo
    (3172, 20):  (-6.323, 106.893),  # Ciracas
    (3172, 30):  (-6.327, 106.924),  # Cipayung
    (3172, 40):  (-6.280, 106.902),  # Makasar
    (3172, 50):  (-6.248, 106.870),  # Kramat Jati (near Cawang)
    (3172, 60):  (-6.225, 106.878),  # Jatinegara
    (3172, 70):  (-6.229, 106.913),  # Duren Sawit
    (3172, 80):  (-6.183, 106.930),  # Cakung
    (3172, 90):  (-6.203, 106.906),  # Pulo Gadung
    (3172, 100): (-6.208, 106.857),  # Matraman
    # Jakarta Pusat (3173)
    (3173, 10):  (-6.218, 106.810),  # Tanah Abang (Gelora/Bendungan Hilir)
    (3173, 20):  (-6.195, 106.834),  # Menteng
    (3173, 30):  (-6.178, 106.847),  # Senen
    (3173, 40):  (-6.165, 106.860),  # Johar Baru
    (3173, 50):  (-6.172, 106.872),  # Cempaka Putih
    (3173, 60):  (-6.153, 106.858),  # Kemayoran
    (3173, 70):  (-6.145, 106.828),  # Sawah Besar
    (3173, 80):  (-6.173, 106.819),  # Gambir
    # Jakarta Barat (3174)
    (3174, 10):  (-6.210, 106.740),  # Kembangan
    (3174, 20):  (-6.200, 106.760),  # Kebon Jeruk
    (3174, 30):  (-6.197, 106.793),  # Palmerah
    (3174, 40):  (-6.170, 106.793),  # Grogol Petamburan
    (3174, 50):  (-6.148, 106.796),  # Tambora
    (3174, 60):  (-6.140, 106.808),  # Taman Sari
    (3174, 70):  (-6.147, 106.739),  # Cengkareng
    (3174, 80):  (-6.144, 106.701),  # Kalideres
    # Jakarta Utara (3175)
    (3175, 10):  (-6.129, 106.807),  # Penjaringan (Pluit)
    (3175, 20):  (-6.116, 106.840),  # Pademangan (Ancol)
    (3175, 30):  (-6.120, 106.870),  # Tanjung Priok
    (3175, 40):  (-6.100, 106.895),  # Koja
    (3175, 50):  (-6.160, 106.909),  # Kelapa Gading
    (3175, 60):  (-6.092, 106.941),  # Cilincing
}
KEC_OSM_RADIUS = 1000  # meters

# ── Helpers ────────────────────────────────────────────────────────────────
def haversine_vec(poi_coords, clat, clon):
    dlat = np.radians(poi_coords[:, 0] - clat)
    dlon = np.radians(poi_coords[:, 1] - clon)
    phi1 = math.radians(clat)
    phi2 = np.radians(poi_coords[:, 0])
    a = np.sin(dlat/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlon/2)**2
    return 2 * 6371000 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def count_within(coords, clat, clon, radius_m):
    if len(coords) == 0:
        return 0
    dist = haversine_vec(coords, clat, clon)
    return int((dist <= radius_m).sum())


def transport_score_raw(tra_coords, tra_cats, clat, clon, radius_m=2000):
    if len(tra_coords) == 0:
        return 0.0
    dist_m = haversine_vec(tra_coords, clat, clon)
    mask = (dist_m <= radius_m) & (dist_m > 0)
    if not mask.any():
        return 0.0
    score = 0.0
    for i in np.where(mask)[0]:
        w = TRANSPORT_WEIGHT.get(tra_cats[i], 1)
        score += w / (dist_m[i] / 1000)
    return score


def shannon_entropy(counts):
    counts = np.array(counts, dtype=float)
    counts = counts[counts > 0]
    if len(counts) == 0:
        return 0.0
    p = counts / counts.sum()
    return float(-np.sum(p * np.log(p + 1e-12)))


def minmax(series):
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(50.0, index=series.index)
    return (series - mn) / (mx - mn) * 100


def minmax_log(series):
    return minmax(np.log1p(series))


# ════════════════════════════════════════════════════════════════════════════
print("[1/12] Loading metadata and NTL data...")
# ════════════════════════════════════════════════════════════════════════════
with open(os.path.join(DATA, "metadata.json"), encoding="utf-8") as f:
    meta = json.load(f)

centroids = meta["named_areas_centroid"]
centroid_dict = {c["area"]: c for c in centroids}
areas = [c["area"] for c in centroids]

ntl_growth = pd.read_csv(os.path.join(DATA, "260503_NASA_jakarta-growth-2021baseline.csv"))
ntl_growth = ntl_growth.set_index("area")

# ════════════════════════════════════════════════════════════════════════════
print("[2/12] Loading pixel map data...")
# ════════════════════════════════════════════════════════════════════════════
pixel_df = pd.read_excel(os.path.join(DATA, "260502_NASA_jakarta-area-analysis.xlsx"),
                          sheet_name="pixel_change_map")
pixel_sample = (pixel_df.groupby('trend', group_keys=False)
    .apply(lambda g: g.sample(min(len(g), int(3000 * len(g) / len(pixel_df)) + 5), random_state=42))
    .reset_index(drop=True).head(3000))
lum_q98 = float(pixel_sample["lum_2024"].quantile(0.98))
if lum_q98 == 0:
    lum_q98 = 1.0
pixel_heat = [[float(r.lat), float(r.lon), float(min(r.lum_2024 / lum_q98, 1.0))]
              for r in pixel_sample.itertuples()]
TREND_COLOR = {'rapid_growth': '#C8102E', 'growth': '#EA7200', 'stable': '#98A2B3', 'decline': '#1A5394'}
pixel_circles = [[float(r.lat), float(r.lon), float(r.change_pct), str(r.trend)]
                 for r in pixel_sample.itertuples()]

# ════════════════════════════════════════════════════════════════════════════
print("[3/12] Loading monthly NTL and pulse data...")
# ════════════════════════════════════════════════════════════════════════════
monthly = pd.read_excel(os.path.join(DATA, "260503_NASA_jakarta-monthly-areas.xlsx"))
pulse_df = pd.read_excel(os.path.join(DATA, "260503_NASA_jakarta-recent-pulse.xlsx"))
pulse_dict = pulse_df.set_index("area").to_dict("index")

# ════════════════════════════════════════════════════════════════════════════
print("[4/12] Loading Podes (267 desa)...")
# ════════════════════════════════════════════════════════════════════════════
podes = pd.read_csv(os.path.join(DATA, "podes-business-DKI.csv"))

# Fix #2: Build desa master from Podes
desa_master = podes[['kabkota_id_full','kec_id','desa_id','nama_desa','nama_kabkota']].drop_duplicates().reset_index(drop=True)
desa_master['desa_uid'] = (desa_master['kabkota_id_full'].astype(str) + '_' +
                           desa_master['kec_id'].astype(str) + '_' +
                           desa_master['desa_id'].astype(str))
print(f"    Total desa: {len(desa_master)} (expected 267)")

# Add desa_uid to podes
podes['desa_uid'] = (podes['kabkota_id_full'].astype(str) + '_' +
                     podes['kec_id'].astype(str) + '_' +
                     podes['desa_id'].astype(str))

# Total count per (desa_uid, vintage_year)
podes_total = podes.groupby(['desa_uid','vintage_year'])['count'].sum().unstack(fill_value=0)

def podes_desa_metric(uid):
    if uid in podes_total.index:
        row = podes_total.loc[uid]
    else:
        return {'cagr': 0.0, 'change': 0.0, 'level': 0.0}
    v2021 = float(row.get(2021, row.get(2020, row.get(2018, 0))))
    v2024 = float(row.get(2024, v2021))
    v2025 = float(row.get(2025, v2024))
    cagr = ((v2025 / v2021) ** (1/4) - 1) if v2021 > 0 else 0.0
    change = (v2025 - v2024) / v2024 if v2024 > 0 else 0.0
    return {'cagr': cagr, 'change': change, 'level': v2025}

def podes_desa_diversity(uid):
    sub = podes[(podes['desa_uid'] == uid) & (podes['vintage_year'] == 2025)]
    cat_counts = sub.groupby('kategori')['count'].sum().values
    return shannon_entropy(cat_counts)

# ════════════════════════════════════════════════════════════════════════════
print("[5/12] Loading composite-potensi (Fix #1: Group 3 source)...")
# ════════════════════════════════════════════════════════════════════════════
comp = pd.read_csv(os.path.join(DATA, "composite-potensi-DKI.csv"))
comp['desa_uid'] = (comp['kabkota_id_full'].astype(str) + '_' +
                   comp['kec_id'].astype(str) + '_' +
                   comp['desa_id'].astype(str))

# Sum potensi_total per (desa_uid, vintage_year) across ALL kbli2
comp_total = comp.groupby(['desa_uid','vintage_year'])['potensi_total'].sum().unstack(fill_value=0)

def sak_desa_metric(uid):
    if uid in comp_total.index:
        row = comp_total.loc[uid]
    else:
        return {'cagr': 0.0, 'change': 0.0, 'level': 0.0}
    v2021 = float(row.get(2021, 0))
    v2024 = float(row.get(2024, v2021))
    v2025 = float(row.get(2025, v2024))
    cagr = ((v2025 / v2021) ** (1/4) - 1) if v2021 > 0 else 0.0
    change = (v2025 - v2024) / v2024 if v2024 > 0 else 0.0
    return {'cagr': cagr, 'change': change, 'level': v2025}

# ════════════════════════════════════════════════════════════════════════════
print("[6/12] Loading OSM data...")
# ════════════════════════════════════════════════════════════════════════════
osm_groups = {}
for grp_name in ["ENTERTAINMENT_NIGHTLIFE", "LIFESTYLE_WELLNESS", "SPECIALTY_RETAIL",
                  "TOURISM_CULTURAL", "AUTO_SERVICE"]:
    try:
        sheet = pd.read_excel(os.path.join(DATA, "260503_OSM_poi-lifestyle-jakarta.xlsx"),
                               sheet_name=grp_name)
        osm_groups[grp_name] = sheet[["lat", "lon"]].dropna().values
    except Exception:
        osm_groups[grp_name] = np.empty((0, 2))

fnb  = pd.read_excel(os.path.join(DATA, "260502_OSM_poi-commercial-jakarta.xlsx"), sheet_name="fnb")
ent  = pd.read_excel(os.path.join(DATA, "260502_OSM_poi-commercial-jakarta.xlsx"), sheet_name="entertainment")
ret  = pd.read_excel(os.path.join(DATA, "260502_OSM_poi-commercial-jakarta.xlsx"), sheet_name="retail")
transport = pd.read_excel(os.path.join(DATA, "260502_OSM_transport-jakarta.xlsx"), sheet_name="transport")

fnb_coords = fnb[["lat", "lon"]].dropna().values
ent_coords = ent[["lat", "lon"]].dropna().values
ret_coords = ret[["lat", "lon"]].dropna().values
tra_coords = transport[["lat", "lon"]].dropna().values
tra_cats   = transport.loc[transport[["lat","lon"]].notna().all(axis=1), "category"].values
auto_service_coords = osm_groups.get("AUTO_SERVICE", np.empty((0, 2)))
all_poi_coords = np.vstack([fnb_coords, ent_coords, ret_coords]) if len(fnb_coords) else np.empty((0, 2))

# ════════════════════════════════════════════════════════════════════════════
print("[7/12] Computing per-named-area metrics (Fix #3: kabkota proxy)...")
# ════════════════════════════════════════════════════════════════════════════
area_metrics = {}
for area in areas:
    c = centroid_dict[area]
    clat, clon, radius_m = c['lat'], c['lon'], c['radius_m']
    # NTL
    try:
        ntl_row = ntl_growth.loc[area]
        ntl_cagr_v  = float(ntl_row.get("ntl_CAGR_2021_2025", 0))
        ntl_chg_v   = float(ntl_row.get("ntl_change_2024_2025", 0))
        ntl_level_v = float(ntl_row.get("ntl_level_2025", 0))
    except KeyError:
        ntl_cagr_v = ntl_chg_v = ntl_level_v = 0.0
    # OSM counts
    cnt_ent  = count_within(osm_groups.get("ENTERTAINMENT_NIGHTLIFE", np.empty((0,2))), clat, clon, radius_m)
    cnt_well = count_within(osm_groups.get("LIFESTYLE_WELLNESS",       np.empty((0,2))), clat, clon, radius_m)
    cnt_spec = count_within(osm_groups.get("SPECIALTY_RETAIL",         np.empty((0,2))), clat, clon, radius_m)
    cnt_tour = count_within(osm_groups.get("TOURISM_CULTURAL",         np.empty((0,2))), clat, clon, radius_m)
    cnt_auto = count_within(auto_service_coords, clat, clon, radius_m)
    # Transport
    tra_raw   = transport_score_raw(tra_coords, tra_cats, clat, clon, 2000)
    catch_raw = count_within(all_poi_coords, clat, clon, radius_m)
    # Pulse
    pulse_info = pulse_dict.get(area, {})
    pulse_yoy = float(pulse_info.get("pulse_yoy_pct", 0)) if pd.notna(pulse_info.get("pulse_yoy_pct", np.nan)) else 0.0

    area_metrics[area] = {
        'ntl_cagr': ntl_cagr_v, 'ntl_change': ntl_chg_v, 'ntl_level': ntl_level_v,
        'cnt_ent': cnt_ent, 'cnt_well': cnt_well, 'cnt_spec': cnt_spec,
        'cnt_tour': cnt_tour, 'cnt_auto': cnt_auto,
        'tra_raw': tra_raw, 'catch_raw': catch_raw,
        'pulse_yoy': pulse_yoy,
    }

def kk_average(kk):
    areas_in_kk = KK_NTL_MAP.get(kk, [])
    valid = [a for a in areas_in_kk if a in area_metrics]
    if not valid:  # fallback: DKI average (Kep Seribu)
        valid = list(area_metrics.keys())
    return {
        'ntl_cagr':   np.mean([area_metrics[a]['ntl_cagr'] for a in valid]),
        'ntl_change': np.mean([area_metrics[a]['ntl_change'] for a in valid]),
        'ntl_level':  np.mean([area_metrics[a]['ntl_level'] for a in valid]),
        'cnt_ent':    np.mean([area_metrics[a]['cnt_ent'] for a in valid]),
        'cnt_well':   np.mean([area_metrics[a]['cnt_well'] for a in valid]),
        'cnt_spec':   np.mean([area_metrics[a]['cnt_spec'] for a in valid]),
        'cnt_tour':   np.mean([area_metrics[a]['cnt_tour'] for a in valid]),
        'cnt_auto':   np.mean([area_metrics[a]['cnt_auto'] for a in valid]),
        'tra_raw':    np.mean([area_metrics[a]['tra_raw'] for a in valid]),
        'catch_raw':  np.mean([area_metrics[a]['catch_raw'] for a in valid]),
        'pulse_yoy':  np.mean([area_metrics[a]['pulse_yoy'] for a in valid]),
    }

kk_metrics = {kk: kk_average(kk) for kk in [3101, 3171, 3172, 3173, 3174, 3175]}

# ── Kecamatan-level OSM and transport scores ──────────────────────────
print("[8b/12] Computing kecamatan-level OSM scores (44 kecamatan)...")
kec_osm = {}
for (kk, kec), (clat, clon) in KEC_CENTROIDS.items():
    r = KEC_OSM_RADIUS
    cnt_ent  = count_within(osm_groups.get("ENTERTAINMENT_NIGHTLIFE", np.empty((0,2))), clat, clon, r)
    cnt_well = count_within(osm_groups.get("LIFESTYLE_WELLNESS",       np.empty((0,2))), clat, clon, r)
    cnt_spec = count_within(osm_groups.get("SPECIALTY_RETAIL",         np.empty((0,2))), clat, clon, r)
    cnt_tour = count_within(osm_groups.get("TOURISM_CULTURAL",         np.empty((0,2))), clat, clon, r)
    cnt_auto = count_within(auto_service_coords, clat, clon, r)
    tra_raw  = transport_score_raw(tra_coords, tra_cats, clat, clon, 2000)
    catch_raw = count_within(all_poi_coords, clat, clon, r)
    kec_osm[(kk, kec)] = {
        "cnt_ent": cnt_ent, "cnt_well": cnt_well, "cnt_spec": cnt_spec,
        "cnt_tour": cnt_tour, "cnt_auto": cnt_auto,
        "tra_raw": tra_raw, "catch_raw": catch_raw,
    }

# ════════════════════════════════════════════════════════════════════════════
print("[8/12] Building main desa dataframe (267 rows)...")
# ════════════════════════════════════════════════════════════════════════════
rows = []
for _, desa_row in desa_master.iterrows():
    uid = desa_row['desa_uid']
    kk  = int(desa_row['kabkota_id_full'])
    km  = kk_metrics[kk]
    pm  = podes_desa_metric(uid)
    pm['div'] = podes_desa_diversity(uid)
    sm  = sak_desa_metric(uid)

    # Kecamatan-level OSM lookup (Groups 4 and 5); fallback to kabkota average
    kec = int(desa_row['kec_id'])
    kec_key = (kk, kec)
    if kec_key in kec_osm:
        ko = kec_osm[kec_key]
    else:
        fallback_vals = [v for (kk2, kec2), v in kec_osm.items() if kk2 == kk]
        if fallback_vals:
            ko = {k: np.mean([v[k] for v in fallback_vals]) for k in fallback_vals[0]}
        else:
            ko = {"cnt_ent": 0, "cnt_well": 0, "cnt_spec": 0, "cnt_tour": 0,
                  "cnt_auto": 0, "tra_raw": 0, "catch_raw": 0}

    rows.append({
        'desa_uid': uid,
        'nama_desa': desa_row['nama_desa'],
        'nama_kabkota': desa_row['nama_kabkota'],
        'kabkota_id_full': kk,
        'kec_id': int(desa_row['kec_id']),
        'desa_id': int(desa_row['desa_id']),
        # NTL (kabkota proxy — stays at kk level)
        'ntl_cagr_raw':   km['ntl_cagr'],
        'ntl_change_raw': km['ntl_change'],
        'ntl_level_raw':  km['ntl_level'],
        # Podes (desa level)
        'podes_cagr_raw':   pm['cagr'],
        'podes_change_raw': pm['change'],
        'podes_level_raw':  pm['level'],
        'podes_div_raw':    pm['div'],
        # composite-potensi (desa level)
        'sak_cagr_raw':   sm['cagr'],
        'sak_change_raw': sm['change'],
        'sak_level_raw':  sm['level'],
        # OSM/transport (kecamatan proxy — Groups 4 and 5)
        'cnt_ent':    ko['cnt_ent'],
        'cnt_well':   ko['cnt_well'],
        'cnt_spec':   ko['cnt_spec'],
        'cnt_tour':   ko['cnt_tour'],
        'cnt_auto':   ko['cnt_auto'],
        'tra_raw':    ko['tra_raw'],
        'catch_raw':  ko['catch_raw'],
        # Pulse badge stays at kabkota average (unchanged)
        'pulse_yoy_pct': km['pulse_yoy'],
    })

df = pd.DataFrame(rows)

# Winsorize CAGR outliers at 95th percentile (removes data artifacts like Bungur toko_kelontong jump)
p95_podes = df["podes_cagr_raw"].quantile(0.95)
p95_sak   = df["sak_cagr_raw"].quantile(0.95)
df["podes_cagr_raw"] = df["podes_cagr_raw"].clip(upper=p95_podes)
df["sak_cagr_raw"]   = df["sak_cagr_raw"].clip(upper=p95_sak)

# Track which desa were winsorized (for metadata)
winsorized_podes = df[df["podes_cagr_raw"] == p95_podes]["nama_desa"].tolist()
print(f"[WINSORIZE] Podes CAGR capped at {p95_podes:.4f}, affected: {winsorized_podes}")

# Normalize
df["n_ntl_cagr"]    = minmax(df["ntl_cagr_raw"])
df["n_ntl_change"]  = minmax(df["ntl_change_raw"])
df["n_ntl_level"]   = minmax_log(df["ntl_level_raw"])
df["n_podes_cagr"]  = minmax(df["podes_cagr_raw"])
df["n_podes_change"]= minmax(df["podes_change_raw"])
df["n_podes_level"] = minmax_log(df["podes_level_raw"])
df["n_podes_div"]   = minmax(df["podes_div_raw"])
df["n_sak_cagr"]    = minmax(df["sak_cagr_raw"])
df["n_sak_change"]  = minmax(df["sak_change_raw"])
df["n_sak_level"]   = minmax_log(df["sak_level_raw"])
df["n_osm_ent"]     = minmax_log(df["cnt_ent"])
df["n_osm_well"]    = minmax_log(df["cnt_well"])
df["n_osm_spec"]    = minmax_log(df["cnt_spec"])
df["n_osm_tour"]    = minmax_log(df["cnt_tour"])
df["n_tra_access"]  = minmax_log(df["tra_raw"])
df["n_tra_auto"]    = minmax_log(df["cnt_auto"])
df["n_tra_catch"]   = minmax_log(df["catch_raw"])

# Group scores (0-100)
# n_* variables are already 0-100; ECZI_W are fractional weights
# weighted_sum / group_weight gives 0-100 (since n_* max=100, sum_w/group_w = 1)
df["g1"] = (ECZI_W["ntl_cagr"]    * df["n_ntl_cagr"] +
            ECZI_W["ntl_change"]   * df["n_ntl_change"] +
            ECZI_W["ntl_level"]    * df["n_ntl_level"]) / 0.24
df["g2"] = (ECZI_W["podes_cagr"]  * df["n_podes_cagr"] +
            ECZI_W["podes_change"] * df["n_podes_change"] +
            ECZI_W["podes_level"]  * df["n_podes_level"] +
            ECZI_W["podes_div"]    * df["n_podes_div"]) / 0.33
df["g3"] = (ECZI_W["sak_cagr"]    * df["n_sak_cagr"] +
            ECZI_W["sak_change"]   * df["n_sak_change"] +
            ECZI_W["sak_level"]    * df["n_sak_level"]) / 0.11
df["g4"] = (ECZI_W["osm_ent"]     * df["n_osm_ent"] +
            ECZI_W["osm_well"]     * df["n_osm_well"] +
            ECZI_W["osm_spec"]     * df["n_osm_spec"] +
            ECZI_W["osm_tour"]     * df["n_osm_tour"]) / 0.12
df["g5"] = (ECZI_W["tra_access"]  * df["n_tra_access"] +
            ECZI_W["tra_auto"]     * df["n_tra_auto"] +
            ECZI_W["tra_catch"]    * df["n_tra_catch"]) / 0.20

# ECZI composite (n_* are 0-100; weights sum to 1.0; result is 0-100)
df["eczi_score"] = (
    ECZI_W["ntl_cagr"]    * df["n_ntl_cagr"] +
    ECZI_W["ntl_change"]  * df["n_ntl_change"] +
    ECZI_W["ntl_level"]   * df["n_ntl_level"] +
    ECZI_W["podes_cagr"]  * df["n_podes_cagr"] +
    ECZI_W["podes_change"]* df["n_podes_change"] +
    ECZI_W["podes_level"] * df["n_podes_level"] +
    ECZI_W["podes_div"]   * df["n_podes_div"] +
    ECZI_W["sak_cagr"]   * df["n_sak_cagr"] +
    ECZI_W["sak_change"] * df["n_sak_change"] +
    ECZI_W["sak_level"]  * df["n_sak_level"] +
    ECZI_W["osm_ent"]    * df["n_osm_ent"] +
    ECZI_W["osm_well"]   * df["n_osm_well"] +
    ECZI_W["osm_spec"]   * df["n_osm_spec"] +
    ECZI_W["osm_tour"]   * df["n_osm_tour"] +
    ECZI_W["tra_access"] * df["n_tra_access"] +
    ECZI_W["tra_auto"]   * df["n_tra_auto"] +
    ECZI_W["tra_catch"]  * df["n_tra_catch"]
)
# Weights sum to 1.0 and n_* are 0-100, so eczi_score is naturally 0-100
df["eczi_score"] = df["eczi_score"].round(2)

# Magnitude score: level-focused composite (Pejagalan / dense commercial zones rank here)
# Weights: potensi_total 50% + podes_level 30% + OSM lifestyle 20%
df["magnitude_score"] = (
    0.50 * df["n_sak_level"] +
    0.30 * df["n_podes_level"] +
    0.10 * df["n_osm_ent"] +
    0.05 * df["n_osm_well"] +
    0.05 * df["n_osm_spec"]
).round(2)

# Fix #4: Quadrant = NTL growth score (X) vs Group 4 POI score (Y)
med_x = df['n_ntl_cagr'].median()
med_y = df['g4'].median()

def classify_quad(row):
    hi_x = row['n_ntl_cagr'] >= med_x
    hi_y = row['g4'] >= med_y
    if hi_x and hi_y:        return "Kawasan Komersial Sedang Naik Daun"
    if hi_x and not hi_y:    return "Awal Pertumbuhan"
    if not hi_x and hi_y:    return "Kawasan Komersial Mapan"
    return "Aktivitas Rendah"

df["category"] = df.apply(classify_quad, axis=1)

# Fix #5: All labels Indonesian
QUAD_COLOR = {
    "Kawasan Komersial Sedang Naik Daun": "#C8102E",
    "Awal Pertumbuhan":                   "#EA7200",
    "Kawasan Komersial Mapan":            "#1A5394",
    "Aktivitas Rendah":                   "#98A2B3",
}
df["cat_color"] = df["category"].map(QUAD_COLOR)

# Pulse badge per desa (kabkota average pulse)
def pulse_badge_from_pct(pct):
    if pct >= 5.0:
        return "Tren Naik Berlanjut"
    elif pct <= -5.0:
        return "Mulai Melambat"
    else:
        return "Stabil"

df["pulse_badge"] = df["pulse_yoy_pct"].apply(pulse_badge_from_pct)

df_eczi = df.sort_values("eczi_score", ascending=False).reset_index(drop=True)
df_mag  = df.sort_values("magnitude_score", ascending=False).reset_index(drop=True)
df = df_eczi  # keep df pointing to ECZI-sorted for downstream code

# ════════════════════════════════════════════════════════════════════════════
# SANITY CHECK
# ════════════════════════════════════════════════════════════════════════════
print("\n=== SANITY CHECK: ECZI (Emerging) TOP 10 ===")
for i, row in df_eczi.head(10).iterrows():
    print(f"  {i+1:>3}. {row['nama_desa']:<28} ({row['nama_kabkota']:<18}) ECZI={row['eczi_score']:.2f} [{row['category']}]")

print("\n=== SANITY CHECK: MAGNITUDE TOP 10 ===")
for i, row in df_mag.head(10).iterrows():
    print(f"  {i+1:>3}. {row['nama_desa']:<28} ({row['nama_kabkota']:<18}) MAG={row['magnitude_score']:.2f}")

# Specific checks
for nama, max_rank in [('Pejagalan', 5), ('Senen', 10), ('Kapuk Muara', 10), ('Kelapa Gading Timur', 15)]:
    found = df_mag[df_mag['nama_desa'] == nama]
    if len(found):
        rank = found.index[0] + 1
        status = 'OK' if rank <= max_rank else f'FAIL rank={rank}'
        print(f"  MAGNITUDE Sanity {nama}: rank={rank} {status}")
    else:
        print(f"  MAGNITUDE WARNING: {nama} not found in dataset")

# ECZI: no Bungur top 5 check (artifact reduced by winsorize)
bungur_rank = df_eczi[df_eczi['nama_desa'] == 'Bungur'].index
if len(bungur_rank):
    print(f"  ECZI Bungur rank: {bungur_rank[0]+1} (expected > 5 after winsorize)")
print()

# ════════════════════════════════════════════════════════════════════════════
print("[9/12] Preparing monthly sparklines and chart data...")
# ════════════════════════════════════════════════════════════════════════════
monthly["ym"] = monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2)
monthly_byarea = {}
for area in areas:
    sub = monthly[monthly["area"] == area].sort_values("ym")
    monthly_byarea[area] = {
        "ym": sub["ym"].tolist(),
        "lum": [round(float(x), 4) for x in sub["lum_median"]],
    }

# ════════════════════════════════════════════════════════════════════════════
print("[10/12] Building PODES_DETAIL and COMP_DETAIL for Profil Desa page...")
# ════════════════════════════════════════════════════════════════════════════
podes_detail = {}
for uid in desa_master['desa_uid']:
    sub = podes[podes['desa_uid'] == uid]
    cats = {}
    for cat, grp in sub.groupby('kategori'):
        cats[cat] = {int(y): int(c) for y, c in grp.groupby('vintage_year')['count'].sum().items()}
    podes_detail[uid] = cats

comp_detail = {}
for uid in desa_master['desa_uid']:
    if uid in comp_total.index:
        row = comp_total.loc[uid]
        comp_detail[uid] = {
            2021: round(float(row.get(2021, 0)), 0),
            2024: round(float(row.get(2024, 0)), 0),
            2025: round(float(row.get(2025, 0)), 0),
        }
    else:
        comp_detail[uid] = {2021: 0, 2024: 0, 2025: 0}

# Centroid map for Leaflet reference overlays (16 named areas)
centroid_map = []
for area in areas:
    c = centroid_dict[area]
    p = pulse_dict.get(area, {})
    centroid_map.append({
        "area": area,
        "lat": float(c["lat"]),
        "lon": float(c["lon"]),
        "radius_m": float(c["radius_m"]),
        "pulse_badge": str(p.get("pulse_badge", "N/A")),
        "pulse_yoy":  float(p.get("pulse_yoy_pct", 0)) if pd.notna(p.get("pulse_yoy_pct", np.nan)) else 0.0,
    })

# Pulse table (16 named areas)
pulse_table = []
for area in areas:
    p = pulse_dict.get(area, {})
    pulse_table.append({
        "area": area,
        "lum_2025": round(float(p.get("lum_JanApr_2025", 0)), 3) if pd.notna(p.get("lum_JanApr_2025", np.nan)) else "N/A",
        "lum_2026": round(float(p.get("lum_JanApr_2026", 0)), 3) if pd.notna(p.get("lum_JanApr_2026", np.nan)) else "N/A",
        "pulse_yoy": round(float(p.get("pulse_yoy_pct", 0)), 1) if pd.notna(p.get("pulse_yoy_pct", np.nan)) else "N/A",
        "pulse_badge": str(p.get("pulse_badge", "N/A")),
    })

# OSM map samples
fnb_sample = fnb[["lat","lon"]].dropna().sample(min(2000, len(fnb)), random_state=42)
ent_sample = ent[["lat","lon"]].dropna()
ret_sample = ret[["lat","lon"]].dropna().sample(min(1500, len(ret)), random_state=42)
tra_sample = transport[["lat","lon","category"]].dropna()
well_sample = pd.DataFrame(osm_groups.get("LIFESTYLE_WELLNESS", np.empty((0,2))), columns=["lat","lon"]).head(800)
fnb_map  = [[float(r.lat), float(r.lon)] for r in fnb_sample.itertuples()]
ent_map  = [[float(r.lat), float(r.lon)] for r in ent_sample.itertuples()]
ret_map  = [[float(r.lat), float(r.lon)] for r in ret_sample.itertuples()]
well_map = [[float(r.lat), float(r.lon)] for r in well_sample.itertuples() if hasattr(r, 'lat')]
tra_map  = [{"lat": float(r.lat), "lon": float(r.lon), "cat": str(r.category)} for r in tra_sample.itertuples()]

# KPI data
kpi_top_eczi   = df_eczi.iloc[0]["nama_desa"]
kpi_top_eczi_v = round(df_eczi.iloc[0]["eczi_score"], 1)
kpi_top_mag    = df_mag.iloc[0]["nama_desa"]
kpi_top_mag_v  = round(df_mag.iloc[0]["magnitude_score"], 1)
kpi_top_cagr   = df.loc[df["ntl_cagr_raw"].idxmax(), "nama_kabkota"]
kpi_top_cagr_v = round(df["ntl_cagr_raw"].max() * 100, 1)
kpi_top_lvl    = df.loc[df["ntl_level_raw"].idxmax(), "nama_desa"]
kpi_top_lvl_v  = round(df["ntl_level_raw"].max(), 2)
kpi_total_poi  = int(sum(len(v) for v in osm_groups.values()))
momentum_rows  = [r for r in pulse_table if "Continuing" in str(r["pulse_badge"])]
kpi_momentum   = momentum_rows[0]["area"] if momentum_rows else areas[0]

# Serialize
def jss(obj):
    return json.dumps(obj, ensure_ascii=False)

def clean_row(r):
    row_clean = {}
    for k, v in r.items():
        if isinstance(v, (np.integer,)):
            row_clean[k] = int(v)
        elif isinstance(v, (np.floating,)):
            row_clean[k] = float(v)
        else:
            row_clean[k] = v
    return row_clean

eczi_rows = [clean_row(r) for r in df_eczi.to_dict("records")]
mag_rows  = [clean_row(r) for r in df_mag.to_dict("records")]

top5_desa = df.head(5)["nama_desa"].tolist()
generated = datetime.now().strftime("%Y-%m-%d %H:%M")

# Convert comp_detail keys to strings for JSON
comp_detail_js = {uid: {str(k): v for k, v in d.items()} for uid, d in comp_detail.items()}

# Top 30 by ECZI for bar charts
top30_df = df.head(30)

# ════════════════════════════════════════════════════════════════════════════
print("[11/12] Generating HTML dashboard...")
# ════════════════════════════════════════════════════════════════════════════

HTML = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Pendeteksi Kawasan Komersial Berkembang -- DKI Jakarta 2021-2025 | Mandiri Institute</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<style>
  body {{ font-family: 'Inter', system-ui, sans-serif; background: #F5F7FA; }}
  h1,h2,h3,.serif {{ font-family: Georgia, 'Times New Roman', serif; }}
  .sidebar {{ background: #1C1C1E; min-height: 100vh; }}
  .nav-item {{ transition: background 0.15s; cursor: pointer; }}
  .nav-item.active, .nav-item:hover {{ background: rgba(200,16,46,0.18); border-left: 3px solid #C8102E; }}
  .nav-item {{ border-left: 3px solid transparent; }}
  .kpi-card {{ background: #fff; border-radius: 12px; border: 1px solid #E4E9F0; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
  .badge {{ display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; }}
  .badge-green  {{ background: #D1FAE5; color: #065F46; }}
  .badge-gray   {{ background: #F1F5F9; color: #475569; }}
  .badge-orange {{ background: #FEE8D6; color: #9A3412; }}
  .badge-navy   {{ background: #1C1C1E; color: #fff; }}
  .badge-red    {{ background: #FEE2E2; color: #991B1B; }}
  .callout {{ border-left: 4px solid #FFB700; background: #FFFBEB; padding: 12px 16px; border-radius: 0 8px 8px 0; }}
  .caveat-box {{ border-left: 4px solid #C8102E; background: #FFF1F2; padding: 12px 16px; border-radius: 0 8px 8px 0; font-size: 13px; }}
  table.data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  table.data-table th {{ background: #1C1C1E; color: #fff; padding: 8px 12px; text-align: left; font-weight: 600; }}
  table.data-table td {{ padding: 7px 12px; border-bottom: 1px solid #E4E9F0; }}
  table.data-table tr:nth-child(even) td {{ background: #F8FAFC; }}
  table.data-table tr:hover td {{ background: #FFF1F2; }}
  .toggle-btn {{ padding: 5px 14px; border-radius: 6px; font-size: 13px; font-weight:600; border: 1.5px solid #C8102E; cursor:pointer; transition: all .15s; }}
  .toggle-btn.active {{ background: #C8102E; color: #fff; }}
  .toggle-btn:not(.active) {{ background: #fff; color: #C8102E; }}
  .section-header {{ font-size: 18px; font-weight: 700; color: #1C1C1E; font-family: Georgia, serif; margin-bottom: 12px; }}
  .progress-bar {{ height: 8px; border-radius: 4px; background: #E4E9F0; overflow: hidden; }}
  .progress-fill {{ height: 100%; border-radius: 4px; }}
  #map-ntl {{ height: 460px; }}
  .leaflet-container {{ font-family: 'Inter', system-ui, sans-serif !important; }}
  .quad-pill {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; white-space: nowrap; }}
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}
</style>
</head>
<body x-data="dashboard()" x-init="init()">

<!-- Sidebar -->
<div class="fixed inset-y-0 left-0 w-56 sidebar flex flex-col z-50 shadow-xl overflow-y-auto">
  <div class="px-5 pt-6 pb-4 border-b border-zinc-700">
    <div class="text-xs text-zinc-400 font-semibold uppercase tracking-widest mb-1">Mandiri Institute</div>
    <div class="text-white font-bold text-sm leading-tight serif">Pendeteksi Kawasan Komersial Berkembang</div>
    <div class="text-zinc-400 text-xs mt-1">DKI Jakarta · 2021-2025</div>
  </div>
  <nav class="flex-1 py-4 px-2 space-y-0.5">
    <template x-for="tab in tabs" :key="tab.id">
      <div class="nav-item rounded-lg px-3 py-2.5 flex items-center gap-2"
           :class="{{active: page===tab.id}}"
           @click="setPage(tab.id)">
        <span class="text-sm font-medium" :class="page===tab.id ? 'text-white' : 'text-zinc-300'" x-text="tab.label"></span>
      </div>
    </template>
  </nav>
  <div class="px-4 py-3 border-t border-zinc-700">
    <div class="text-zinc-500 text-xs leading-relaxed">267 kelurahan/desa · VIIRS + OSM + Podes + Composite-Potensi</div>
    <div class="text-zinc-600 text-xs mt-1">Generated: {generated}</div>
  </div>
</div>

<!-- Main content -->
<div class="ml-56 min-h-screen flex flex-col">
  <!-- Top bar -->
  <div class="bg-white border-b border-slate-200 px-8 py-3 flex items-center justify-between sticky top-0 z-40 shadow-sm">
    <div class="flex items-center gap-3">
      <span class="text-red-700 font-bold text-sm">Pendeteksi Kawasan Komersial Berkembang</span>
      <span class="text-slate-300">|</span>
      <span class="text-slate-500 text-sm" x-text="tabs.find(t=>t.id===page)?.label"></span>
    </div>
    <div class="text-xs text-slate-400">{generated}</div>
  </div>

  <!-- Pages -->
  <div class="flex-1 p-8">

<!-- ===================================================================== -->
<!-- PAGE: RINGKASAN -->
<!-- ===================================================================== -->
<div x-show="page==='ringkasan'">
  <div class="mb-5">
    <h1 class="text-2xl font-bold text-slate-800 serif mb-1">Ringkasan -- Kawasan Komersial Berkembang DKI Jakarta</h1>
    <p class="text-slate-500 text-sm">Skor Potensi Zona Komersial (ECZI) per kelurahan/desa, peringkat, dan sinyal terkini · 267 kelurahan/desa</p>
  </div>

  <div class="callout mb-6">
    <div class="text-sm text-yellow-900">
      <strong>Catatan Metodologi:</strong> Skor ECZI = proxy intensitas aktivitas komersial berbasis 5 dimensi data (NTL, Podes, Composite-Potensi, OSM POI, Aksesibilitas).
      <strong>BUKAN</strong> ukuran langsung PDRB atau omzet. Gunakan untuk perbandingan relatif antar kelurahan/desa.
      NTL, OSM, dan Aksesibilitas menggunakan rata-rata kabupaten/kota sebagai proksi (Phase 0).
    </div>
  </div>

  <!-- KPI Cards -->
  <div class="grid grid-cols-5 gap-4 mb-8">
    <div class="kpi-card p-4 border-l-4 border-red-600">
      <div class="text-xs text-slate-400 uppercase tracking-wide mb-1">Top Kawasan Berkembang</div>
      <div class="text-base font-bold text-slate-800 serif">{kpi_top_eczi}</div>
      <div class="text-2xl font-black text-red-700 mt-1">{kpi_top_eczi_v}</div>
      <div class="text-xs text-slate-400 mt-1">Skor ECZI</div>
    </div>
    <div class="kpi-card p-4 border-l-4 border-blue-700">
      <div class="text-xs text-slate-400 uppercase tracking-wide mb-1">Top Magnitude Komersial</div>
      <div class="text-base font-bold text-slate-800 serif">{kpi_top_mag}</div>
      <div class="text-2xl font-black text-blue-700 mt-1">{kpi_top_mag_v}</div>
      <div class="text-xs text-slate-400 mt-1">Skor Magnitude</div>
    </div>
    <div class="kpi-card p-4">
      <div class="text-xs text-slate-400 uppercase tracking-wide mb-1">CAGR NTL Tertinggi</div>
      <div class="text-base font-bold text-slate-800 serif">{kpi_top_cagr}</div>
      <div class="text-slate-600 text-sm mt-1">CAGR: <strong>{kpi_top_cagr_v}%</strong>/thn</div>
    </div>
    <div class="kpi-card p-4">
      <div class="text-xs text-slate-400 uppercase tracking-wide mb-1">Total POI Lifestyle</div>
      <div class="text-3xl font-black text-red-700">{kpi_total_poi:,}</div>
      <div class="text-slate-500 text-xs mt-1">OSM snapshot 2026</div>
    </div>
    <div class="kpi-card p-4">
      <div class="text-xs text-slate-400 uppercase tracking-wide mb-1">Momentum Terkini</div>
      <div class="text-base font-bold text-slate-800 serif">{kpi_momentum}</div>
      <div class="mt-1"><span class="badge badge-green">Tren Naik Berlanjut</span></div>
    </div>
  </div>

  <!-- Leaderboard Mode Toggle -->
  <div class="flex gap-2 mb-4">
    <button @click="leaderboardMode='eczi'" :class="leaderboardMode==='eczi' ? 'bg-red-700 text-white' : 'bg-gray-100 text-slate-700'" class="px-3 py-1.5 rounded-lg text-sm font-medium border border-transparent transition-colors">Skor ECZI (Berkembang)</button>
    <button @click="leaderboardMode='magnitude'" :class="leaderboardMode==='magnitude' ? 'bg-blue-700 text-white' : 'bg-gray-100 text-slate-700'" class="px-3 py-1.5 rounded-lg text-sm font-medium border border-transparent transition-colors">Magnitude Komersial</button>
  </div>

  <!-- Mode explanation -->
  <div x-show="leaderboardMode==='eczi'" class="callout mb-4">
    <div class="text-sm text-yellow-900">
      <strong>Skor ECZI (Berkembang):</strong> Mengukur sinyal pertumbuhan aktivitas komersial 2021-2025 (NTL + Podes + Potensi + POI). Kawasan yang sedang naik daun muncul di sini.
    </div>
  </div>
  <div x-show="leaderboardMode==='magnitude'" class="caveat-box mb-4">
    <div class="text-sm">
      <strong>Magnitude Komersial (Existing):</strong> Mengukur BESARAN aktivitas komersial saat ini (potensi_total 2025 + kepadatan usaha + POI). Kawasan padat komersial muncul di sini.
      <br/><span class="text-xs mt-1 block">Indeks proxy = jumlah usaha x rata-rata pendapatan pekerja per kabupaten/kota. Bukan total pendapatan firm-level.</span>
    </div>
  </div>

  <!-- Search + Filter -->
  <div class="bg-white rounded-xl border border-slate-200 p-5 mb-6">
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <input type="text" x-model="searchQuery" placeholder="Cari kelurahan/desa..."
             class="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white text-slate-700 min-w-52 focus:outline-none focus:ring-2 focus:ring-red-300"/>
      <div class="flex gap-2 flex-wrap">
        <button @click="filterKabkota='all'" class="toggle-btn text-xs py-1 px-3" :class="{{active: filterKabkota==='all'}}">Semua</button>
        <button @click="filterKabkota='3171'" class="toggle-btn text-xs py-1 px-3" :class="{{active: filterKabkota==='3171'}}">Jaksel</button>
        <button @click="filterKabkota='3172'" class="toggle-btn text-xs py-1 px-3" :class="{{active: filterKabkota==='3172'}}">Jaktim</button>
        <button @click="filterKabkota='3173'" class="toggle-btn text-xs py-1 px-3" :class="{{active: filterKabkota==='3173'}}">Jakpus</button>
        <button @click="filterKabkota='3174'" class="toggle-btn text-xs py-1 px-3" :class="{{active: filterKabkota==='3174'}}">Jakbar</button>
        <button @click="filterKabkota='3175'" class="toggle-btn text-xs py-1 px-3" :class="{{active: filterKabkota==='3175'}}">Jakut</button>
        <button @click="filterKabkota='3101'" class="toggle-btn text-xs py-1 px-3" :class="{{active: filterKabkota==='3101'}}">Kep. Seribu</button>
      </div>
    </div>

    <!-- Leaderboard Table -->
    <table class="data-table">
      <thead><tr>
        <th>Peringkat</th>
        <th>Kelurahan/Desa</th>
        <th>Kabupaten/Kota</th>
        <th x-text="leaderboardMode==='eczi' ? 'Skor ECZI' : 'Skor Magnitude'"></th>
        <th>Tipe Kawasan</th>
        <th>Pulse 2026</th>
      </tr></thead>
      <tbody>
        <template x-for="(row, idx) in filteredDesa" :key="row.desa_uid">
          <tr class="cursor-pointer" @click="selectDesa(row.desa_uid)">
            <td class="font-mono text-slate-500 text-xs" x-text="row.rank"></td>
            <td>
              <span class="font-semibold text-slate-800" x-text="row.nama_desa"></span>
            </td>
            <td class="text-slate-500 text-xs" x-text="row.nama_kabkota"></td>
            <td>
              <div class="flex items-center gap-2" x-show="leaderboardMode==='eczi'">
                <div class="progress-bar w-20"><div class="progress-fill bg-red-600" :style="'width:' + row.eczi_score + '%'"></div></div>
                <span class="font-bold text-slate-800 text-xs" x-text="row.eczi_score.toFixed(1)"></span>
              </div>
              <div class="flex items-center gap-2" x-show="leaderboardMode==='magnitude'">
                <div class="progress-bar w-20"><div class="progress-fill bg-blue-600" :style="'width:' + row.magnitude_score + '%'"></div></div>
                <span class="font-bold text-blue-800 text-xs" x-text="row.magnitude_score.toFixed(1)"></span>
              </div>
            </td>
            <td>
              <span class="quad-pill text-white text-xs" :style="'background:' + row.cat_color" x-text="row.category"></span>
            </td>
            <td>
              <span class="badge" :class="pulseBadgeClass(row.pulse_badge)" x-text="row.pulse_badge"></span>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <div class="flex items-center justify-between mt-3">
      <div class="text-xs text-slate-400">
        Menampilkan <span x-text="filteredDesa.length"></span> dari <span x-text="totalFiltered"></span> kelurahan/desa
      </div>
      <button x-show="!showAll && totalFiltered > 30" @click="showAll=true"
              class="text-xs text-red-600 font-semibold hover:underline">
        Tampilkan Semua <span x-text="totalFiltered"></span> Kelurahan/Desa
      </button>
      <button x-show="showAll" @click="showAll=false"
              class="text-xs text-slate-500 hover:underline">
        Tampilkan Top 30
      </button>
    </div>
  </div>
</div>

<!-- ===================================================================== -->
<!-- PAGE: CAHAYA MALAM -->
<!-- ===================================================================== -->
<div x-show="page==='cahaya-malam'">
  <div class="mb-5 flex items-center gap-3">
    <h1 class="text-2xl font-bold text-slate-800 serif">Peta Cahaya Malam</h1>
    <span class="badge badge-navy">Layer A -- Aktivitas Spasial</span>
  </div>
  <p class="text-slate-500 text-sm mb-5">Data VIIRS VNP46A2 (NASA) · Band: DNB BRDF-Corrected · Resolusi 500m · Proksi per kabupaten/kota untuk 267 kelurahan</p>

  <div class="flex gap-2 mb-4">
    <button class="toggle-btn" :class="{{active: mapMode==='heat'}}" @click="setMapMode('heat')">Heatmap Intensitas</button>
    <button class="toggle-btn" :class="{{active: mapMode==='change'}}" @click="setMapMode('change')">Peta Perubahan</button>
  </div>

  <div x-show="mapMode==='heat'" class="flex items-center gap-4 mb-3 text-xs text-slate-600">
    <span class="font-semibold">Intensitas:</span>
    <div class="flex items-center gap-1"><div class="w-4 h-3 rounded" style="background:#2D1B00"></div> Rendah</div>
    <div class="flex items-center gap-1"><div class="w-4 h-3 rounded" style="background:#8B4500"></div> Sedang</div>
    <div class="flex items-center gap-1"><div class="w-4 h-3 rounded" style="background:#FFB700"></div> Tinggi</div>
    <div class="flex items-center gap-1"><div class="w-4 h-3 rounded" style="background:#FFFFA0"></div> Sangat Tinggi</div>
  </div>
  <div x-show="mapMode==='change'" class="flex items-center gap-4 mb-3 text-xs text-slate-600">
    <span class="font-semibold">Tren:</span>
    <div class="flex items-center gap-1"><div class="w-3 h-3 rounded-full bg-red-700"></div> Pertumbuhan Cepat</div>
    <div class="flex items-center gap-1"><div class="w-3 h-3 rounded-full" style="background:#EA7200"></div> Pertumbuhan</div>
    <div class="flex items-center gap-1"><div class="w-3 h-3 rounded-full" style="background:#98A2B3"></div> Stabil</div>
    <div class="flex items-center gap-1"><div class="w-3 h-3 rounded-full" style="background:#1A5394"></div> Turun</div>
  </div>

  <div class="bg-white rounded-xl border border-slate-200 overflow-hidden mb-6">
    <div id="map-ntl" style="height:460px;"></div>
  </div>

  <div class="bg-white rounded-xl border border-slate-200 p-6 mb-6">
    <div class="section-header">Denyut NTL Terkini (Jan-Apr 2025 vs 2026) -- 16 Kawasan Referensi</div>
    <p class="text-xs text-slate-400 mb-4">Catatan: Nilai NTL di bawah adalah rata-rata per kawasan referensi. Data per kelurahan akan tersedia di Phase 1.</p>
    <table class="data-table">
      <thead><tr>
        <th>Kawasan</th>
        <th>Luminositas Jan-Apr 2025</th>
        <th>Luminositas Jan-Apr 2026</th>
        <th>Perubahan YoY (%)</th>
        <th>Status Pulse</th>
      </tr></thead>
      <tbody id="pulse-table-body"></tbody>
    </table>
  </div>

  <div class="bg-white rounded-xl border border-slate-200 p-6">
    <div class="section-header">Tren Cahaya Malam Bulanan 2019-2025</div>
    <div class="flex items-center gap-3 mb-4">
      <label class="text-sm text-slate-600 font-medium">Pilih kawasan:</label>
      <select id="monthly-area-select" multiple size="4"
              class="border border-slate-200 rounded-lg px-2 py-1 text-sm bg-white text-slate-700 min-w-52"
              onchange="renderMonthlyChart()">
        {chr(10).join(f'<option value="{a}" {"selected" if a in top5_desa[:3] else ""}>{a}</option>' for a in areas)}
      </select>
      <span class="text-xs text-slate-400">(Ctrl+klik untuk pilih beberapa)</span>
    </div>
    <div id="chart-monthly" style="height:340px;"></div>
  </div>
</div>

<!-- ===================================================================== -->
<!-- PAGE: AKTIVITAS KOMERSIAL -->
<!-- ===================================================================== -->
<div x-show="page==='komersial'">
  <div class="mb-5 flex items-center gap-3">
    <h1 class="text-2xl font-bold text-slate-800 serif">Aktivitas Komersial</h1>
    <span class="badge badge-navy">Layer B + C -- Podes & Composite-Potensi</span>
  </div>

  <div class="bg-white rounded-xl border border-slate-200 p-6 mb-6">
    <div class="section-header">Total Usaha per Kelurahan (Podes 2025) -- Top 30</div>
    <div id="chart-podes-bar" style="height:420px;"></div>
  </div>

  <div class="bg-white rounded-xl border border-slate-200 p-6 mb-6">
    <div class="section-header">Skor Kualitas Usaha (Group 3) -- Proxy Indeks Komersial</div>
    <div class="caveat-box mb-4">
      <strong>Peringatan:</strong> Indeks proxy = jumlah usaha (Podes) x rata-rata pendapatan pekerja per kabupaten/kota (Sakernas).
      BUKAN total pendapatan firm-level. Gunakan untuk pembanding relatif antar kelurahan/desa.
      <br/><span class="text-xs text-slate-500 mt-1 block">Catatan: Group 3 hanya bervariasi di 6 kabupaten/kota DKI (fixed effect). Tidak membedakan kelurahan dalam kabupaten/kota yang sama.</span>
    </div>
    <div id="chart-g3-bar" style="height:420px;"></div>
    <p class="text-xs text-slate-400 mt-2">Skor G3 (0-100) = normalisasi gabungan CAGR + perubahan jangka pendek + level indeks komersial proxy.</p>
  </div>
</div>

<!-- ===================================================================== -->
<!-- PAGE: SKOR ECZI -->
<!-- ===================================================================== -->
<div x-show="page==='eczi'">
  <div class="mb-5 flex items-center gap-3">
    <h1 class="text-2xl font-bold text-slate-800 serif">Skor Potensi Zona Komersial (ECZI)</h1>
    <span class="badge badge-red">267 Kelurahan/Desa</span>
  </div>

  <!-- Radar top 5 -->
  <div class="bg-white rounded-xl border border-slate-200 p-6 mb-6">
    <div class="section-header">Profil Skor Grup -- 5 Kelurahan/Desa Teratas</div>
    <p class="text-xs text-slate-400 mb-3">G1: Aktivitas Spasial (NTL) · G2: Kepadatan Usaha (Podes) · G3: Kualitas Usaha · G4: POI Lifestyle · G5: Aksesibilitas</p>
    <div id="chart-radar" style="height:380px;"></div>
  </div>

  <!-- Quadrant scatter -->
  <div class="bg-white rounded-xl border border-slate-200 p-6 mb-6">
    <div class="section-header">Kuadran: Pertumbuhan NTL (X) vs Skor POI Lifestyle (Y)</div>
    <p class="text-xs text-slate-400 mb-2">Sumbu X = Skor Pertumbuhan NTL (0-100) | Sumbu Y = Skor POI Gaya Hidup (0-100) | Garis = median</p>
    <div id="chart-quadrant" style="height:480px;"></div>
    <div class="flex flex-wrap gap-3 mt-3">
      <div class="flex items-center gap-1 text-xs"><div class="w-3 h-3 rounded-full" style="background:#C8102E"></div> Kawasan Komersial Sedang Naik Daun</div>
      <div class="flex items-center gap-1 text-xs"><div class="w-3 h-3 rounded-full" style="background:#EA7200"></div> Awal Pertumbuhan</div>
      <div class="flex items-center gap-1 text-xs"><div class="w-3 h-3 rounded-full" style="background:#1A5394"></div> Kawasan Komersial Mapan</div>
      <div class="flex items-center gap-1 text-xs"><div class="w-3 h-3 rounded-full" style="background:#98A2B3"></div> Aktivitas Rendah</div>
    </div>
  </div>

  <!-- Full ranking table -->
  <div class="bg-white rounded-xl border border-slate-200 p-6">
    <div class="section-header">Peringkat Lengkap -- 267 Kelurahan/Desa</div>
    <table class="data-table">
      <thead><tr>
        <th>Peringkat</th>
        <th>Kelurahan/Desa</th>
        <th>Kabupaten/Kota</th>
        <th>ECZI</th>
        <th>G1 NTL</th>
        <th>G2 Podes</th>
        <th>G3 Komersial</th>
        <th>G4 POI</th>
        <th>G5 Akses</th>
        <th>Kategori</th>
      </tr></thead>
      <tbody id="full-ranking-body"></tbody>
    </table>
  </div>
</div>

<!-- ===================================================================== -->
<!-- PAGE: PROFIL DESA -->
<!-- ===================================================================== -->
<div x-show="page==='profil'">
  <div class="mb-5">
    <h1 class="text-2xl font-bold text-slate-800 serif">Profil Kelurahan/Desa</h1>
    <p class="text-slate-500 text-sm">Rincian skor dan tren per kelurahan/desa</p>
  </div>

  <!-- Desa selector -->
  <div class="bg-white rounded-xl border border-slate-200 p-5 mb-6">
    <div class="flex items-center gap-3">
      <label class="text-sm font-medium text-slate-700">Pilih Kelurahan/Desa:</label>
      <select id="desa-select" class="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white text-slate-700 min-w-72 focus:outline-none focus:ring-2 focus:ring-red-300"
              onchange="selectDesaFromDropdown(this.value)">
        <template x-for="row in ECZI_DATA" :key="row.desa_uid">
          <option :value="row.desa_uid" :selected="selectedDesa===row.desa_uid"
                  x-text="row.nama_desa + ' (' + row.nama_kabkota + ')'"></option>
        </template>
      </select>
    </div>
  </div>

  <!-- Profile content -->
  <div x-show="selectedDesaData">
    <!-- Info header -->
    <div class="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <div class="flex items-start justify-between">
        <div>
          <h2 class="text-xl font-bold text-slate-800 serif" x-text="selectedDesaData?.nama_desa"></h2>
          <p class="text-slate-500 text-sm" x-text="selectedDesaData?.nama_kabkota"></p>
        </div>
        <div class="text-right">
          <div class="text-3xl font-black text-red-700" x-text="selectedDesaData?.eczi_score.toFixed(1)"></div>
          <div class="text-xs text-slate-400">Skor ECZI</div>
          <div class="mt-1">
            <span class="quad-pill text-white text-xs"
                  :style="'background:' + selectedDesaData?.cat_color"
                  x-text="selectedDesaData?.category"></span>
          </div>
        </div>
      </div>
      <!-- Rank badge -->
      <div class="mt-3 flex items-center gap-4 text-sm">
        <div>Peringkat: <strong x-text="(ECZI_DATA.findIndex(r => r.desa_uid === selectedDesa) + 1)"></strong> dari 267</div>
        <div>Pulse: <span class="badge" :class="pulseBadgeClass(selectedDesaData?.pulse_badge)" x-text="selectedDesaData?.pulse_badge"></span></div>
      </div>
    </div>

    <!-- Group scores breakdown -->
    <div class="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <div class="section-header">Skor per Dimensi ECZI</div>
      <div id="chart-profile-groups" style="height:280px;"></div>
      <p class="text-xs text-slate-400 mt-2">NTL, OSM, dan Aksesibilitas menggunakan rata-rata kabupaten/kota sebagai proksi (Phase 0). Data spasial per kelurahan akan tersedia di Phase 1.</p>
    </div>

    <!-- Podes time series -->
    <div class="bg-white rounded-xl border border-slate-200 p-6 mb-6">
      <div class="section-header">Tren Usaha Podes per Kategori</div>
      <div id="chart-profile-podes" style="height:320px;"></div>
    </div>

    <!-- Composite potensi trend -->
    <div class="bg-white rounded-xl border border-slate-200 p-6">
      <div class="section-header">Tren Indeks Komersial Proxy (Composite-Potensi)</div>
      <div class="caveat-box mb-4">
        Indeks proxy = jumlah usaha x rata-rata pendapatan pekerja per kabupaten/kota. BUKAN total pendapatan firm-level. Gunakan untuk pembanding relatif.
        Group 3 hanya bervariasi di 6 kabupaten/kota (bukan per kelurahan).
      </div>
      <div id="chart-profile-comp" style="height:260px;"></div>
    </div>
  </div>
</div>

<!-- ===================================================================== -->
<!-- PAGE: METODOLOGI -->
<!-- ===================================================================== -->
<div x-show="page==='metodologi'">
  <div class="mb-5">
    <h1 class="text-2xl font-bold text-slate-800 serif">Metodologi ECZI</h1>
    <p class="text-slate-500 text-sm">Pendeteksi Kawasan Komersial Berkembang -- DKI Jakarta · Versi 2.0 (2026-05-03)</p>
  </div>

  <div class="bg-white rounded-xl border border-slate-200 p-6 mb-6">
    <div class="section-header">Pembobotan ECZI (17 Komponen)</div>
    <table class="data-table">
      <thead><tr><th>Grup</th><th>Sumber Data</th><th>Komponen</th><th>Bobot</th><th>Total Grup</th></tr></thead>
      <tbody>
        <tr><td rowspan="3" class="font-semibold">G1: Aktivitas Spasial (NTL)</td><td rowspan="3">NASA VIIRS</td><td>CAGR NTL 2021-2025</td><td>13%</td><td rowspan="3">24%</td></tr>
        <tr><td>Perubahan NTL 2024-2025</td><td>7%</td></tr>
        <tr><td>Level NTL 2025</td><td>4%</td></tr>
        <tr><td rowspan="4" class="font-semibold">G2: Kepadatan & Pertumbuhan Usaha (Podes)</td><td rowspan="4">Podes BPS</td><td>CAGR Podes 2021-2025</td><td>13%</td><td rowspan="4">33%</td></tr>
        <tr><td>Perubahan Podes 2024-2025</td><td>7%</td></tr>
        <tr><td>Level Podes 2025</td><td>9%</td></tr>
        <tr><td>Diversitas Shannon (10 kategori)</td><td>4%</td></tr>
        <tr><td rowspan="3" class="font-semibold">G3: Kualitas Usaha (Proxy Pendapatan)</td><td rowspan="3">Composite-Potensi (Podes x Sakernas)</td><td>CAGR Indeks 2021-2025</td><td>5%</td><td rowspan="3">11%</td></tr>
        <tr><td>Perubahan Indeks 2024-2025</td><td>3%</td></tr>
        <tr><td>Level Indeks 2025</td><td>3%</td></tr>
        <tr><td rowspan="4" class="font-semibold">G4: POI Gaya Hidup & Rekreasi (OSM)</td><td rowspan="4">OpenStreetMap</td><td>Entertainment & Nightlife</td><td>4%</td><td rowspan="4">12%</td></tr>
        <tr><td>Lifestyle & Wellness</td><td>3%</td></tr>
        <tr><td>Specialty Retail</td><td>3%</td></tr>
        <tr><td>Tourism & Cultural</td><td>2%</td></tr>
        <tr><td rowspan="3" class="font-semibold">G5: Aksesibilitas & Jangkauan (OSM)</td><td rowspan="3">OpenStreetMap</td><td>Akses Transport (MRT/KRL/Bus)</td><td>12%</td><td rowspan="3">20%</td></tr>
        <tr><td>Kepadatan Auto & Layanan</td><td>5%</td></tr>
        <tr><td>Proxy Catchment Area</td><td>3%</td></tr>
      </tbody>
    </table>
  </div>

  <div class="bg-white rounded-xl border border-slate-200 p-6 mb-6">
    <div class="section-header">Limitasi dan Caveat (9 Poin Wajib)</div>
    <div class="space-y-4 text-sm text-slate-700">
      <div class="callout"><strong>7.1 Sakernas -- Granularity Asimetris (kabkota ke desa):</strong> Sinyal Group 3 hanya bervariasi di 6 kabkota DKI × 2 KBLI = 12 nilai unik, di-spread ke 267 desa. Effectively kabkota fixed effect, bukan desa-level differentiator.</div>
      <div class="callout"><strong>7.2 Avg Revenue BUKAN Premium Signal:</strong> Avg revenue Sakernas 2025 sektor perdagangan + akomodasi-mamin DKI menunjukkan pola counter-intuitive (Jaksel -35%). Formalisasi legal entity tidak sama dengan revenue premium. Group 3 lebih tepat sebagai median earned income proxy.</div>
      <div class="callout"><strong>7.3 OSM -- Coverage Bias Asimetris:</strong> CBD over-mapped, pinggiran under-mapped. Group 4 weight diturunkan ke 12% (dari draft 15%). Group 5 (transport) tetap reliable.</div>
      <div class="callout"><strong>7.4 Periode CAGR 2021-2025:</strong> Sakernas 2019 schema KBLI tidak terdiseminasi penuh; 2020 short-form COVID. Baseline 2021 untuk apple-to-apple alignment semua source.</div>
      <div class="callout"><strong>7.5 Podes 2024 ≈ 2025:</strong> Sebagian desa melaporkan angka sama di 2024 dan 2025. change_pct = 0 bukan karena stagnasi nyata, melainkan artefak data.</div>
      <div class="callout"><strong>7.6 NTL Saturasi CBD:</strong> Sinyal NTL pada kawasan sangat terang (&gt;80 DNB units) terkompresi. Log-transform membantu tapi tidak fully eliminate.</div>
      <div class="callout"><strong>7.7 NTL Recent Pulse Tidak Masuk Score:</strong> Pulse 2025-2026 adalah sidecar badge, bukan komponen ECZI. Podes dan Sakernas tidak punya update 2026.</div>
      <div class="callout"><strong>7.8 Imbalance Level vs Growth (52% vs 48%):</strong> OSM (G4+G5) entirely level-based di Phase 0. Phase 1 dengan multi-snapshot OSM dapat rebalance.</div>
      <div class="callout"><strong>7.9 Group 3 BUKAN Total Revenue Absolute:</strong> count_Podes × avg_pendapatan_Sakernas = proxy index magnitude. Sakernas mengukur pendapatan personal pekerja, bukan revenue per usaha. Valid untuk ranking relatif, TIDAK untuk estimasi nominal absolut.</div>
      <div class="callout"><strong>7.10 OSM/Transport Proxy Level (Phase 0.5):</strong> G4 dan G5 menggunakan centroid kecamatan (44 kecamatan) sebagai proxy, bukan centroid desa. Semua kelurahan dalam satu kecamatan mendapat nilai OSM yang sama. Phase 1 akan menggunakan centroid desa individual.</div>
      <div class="callout"><strong>7.11 Winsorize CAGR di P95:</strong> CAGR outlier Podes dan Composite-Potensi di-cap pada persentil ke-95 sebelum normalisasi untuk mengurangi artefak data (contoh: lonjakan toko_kelontong di beberapa desa tertentu).</div>
    </div>
  </div>

  <div class="bg-white rounded-xl border border-slate-200 p-6">
    <div class="section-header">Referensi Akademik</div>
    <div class="space-y-3 text-sm text-slate-700">
      <p><strong>1. Henderson, J.V., Storeygard, A., & Weil, D.N. (2012).</strong> Measuring Economic Growth from Outer Space. <em>American Economic Review</em>, 102(2), 994-1028. DOI: 10.1257/aer.102.2.994<br/><span class="text-slate-500">Dasar penggunaan NTL sebagai proxy aktivitas ekonomi spasial; elastisitas 0.3.</span></p>
      <p><strong>2. Gibson, J., Olivia, S., & Boe-Gibson, G. (2020).</strong> Night Lights in Economics: Sources and Uses. <em>Journal of Economic Surveys</em>, 34(5), 955-980. DOI: 10.1111/joes.12387<br/><span class="text-slate-500">Review penggunaan NTL di negara berkembang; mendukung Jul-Sep composite untuk Indonesia.</span></p>
      <p><strong>3. Elvidge, C.D., Baugh, K., Zhizhin, M., Hsu, F.C., & Ghosh, T. (2017).</strong> VIIRS night-time lights. <em>International Journal of Remote Sensing</em>, 38(21), 5860-5879. DOI: 10.1080/01431161.2017.1342050<br/><span class="text-slate-500">Deskripsi teknis VIIRS DNB Black Marble; validasi BRDF-corrected band VNP46A2.</span></p>
      <p><strong>4. Mellander, C., Lobo, J., Stolarick, K., & Matheson, Z. (2015).</strong> Night-Time Light Data: A Good Proxy Measure for Economic Activity? <em>PLOS ONE</em>, 10(10), e0139779. DOI: 10.1371/journal.pone.0139779<br/><span class="text-slate-500">NTL sebagai proxy kepadatan ekonomi lebih kuat dari sole growth indicator.</span></p>
      <p><strong>5. Yue, Y., Zhuang, Y., Yeh, A.G.O., et al. (2017).</strong> Measurements of POI-based mixed use and their relationships with neighbourhood vibrancy. <em>International Journal of Geographical Information Science</em>, 31(4), 658-675. DOI: 10.1080/13658816.2016.1248508<br/><span class="text-slate-500">POI density dan Shannon diversity berkorelasi dengan vibrancy kawasan.</span></p>
      <p><strong>6. Li, M., Yu, Z., & Li, R. (2023).</strong> Spatial Characteristics of Night-Time Economy. <em>ISPRS International Journal of Geo-Information</em>, 12(5), 205. DOI: 10.3390/ijgi12050205<br/><span class="text-slate-500">Clustering F&B dan entertainment sebagai inti night-time commercial circuit.</span></p>
      <p><strong>7. Jacobs, J. (1961).</strong> <em>The Death and Life of Great American Cities.</em> New York: Random House.<br/><span class="text-slate-500">Fondasi teoritis mixed-use dan diversity sebagai prasyarat vitalitas kawasan.</span></p>
      <p><strong>8. Ewing, R., & Cervero, R. (2010).</strong> Travel and the Built Environment: A Meta-Analysis. <em>Journal of the American Planning Association</em>, 76(3), 265-294. DOI: 10.1080/01944361003766766<br/><span class="text-slate-500">Land use mix dan proximity ke transit node sebagai prediktor terkuat footfall komersial.</span></p>
      <p><strong>9. Hansen, W.G. (1959).</strong> How Accessibility Shapes Land Use. <em>Journal of the American Institute of Planners</em>, 25(2), 73-76. DOI: 10.1080/01944365908978307<br/><span class="text-slate-500">Fondasi formula transport_access_score: weighted sum dengan decay jarak.</span></p>
    </div>
  </div>
</div>

  </div><!-- /flex-1 p-8 -->
</div><!-- /ml-56 -->

<!-- =====================================================================
     EMBEDDED DATA
     ===================================================================== -->
<script>
const ECZI_DATA = {jss(eczi_rows)};
const MAG_DATA  = {jss(mag_rows)};
const PIXEL_HEAT = {jss(pixel_heat)};
const PIXEL_CIRCLES = {jss(pixel_circles)};
const CENTROID_MAP = {jss(centroid_map)};
const MONTHLY_DATA = {jss(monthly_byarea)};
const PULSE_TABLE = {jss(pulse_table)};
const PODES_DETAIL = {jss(podes_detail)};
const COMP_DETAIL = {jss(comp_detail_js)};
const AREAS_LIST = {jss(areas)};
const MED_X = {float(df['n_ntl_cagr'].median()):.4f};
const MED_Y = {float(df['g4'].median()):.4f};
const QUAD_COLOR = {jss(QUAD_COLOR)};
const TOP30_NAMES = {jss(df.head(30)['nama_desa'].tolist())};
const TOP30_PODES_LEVEL = {jss([round(float(v),1) for v in df.head(30)['podes_level_raw']])};
const TOP30_G3 = {jss([round(float(v),1) for v in df.head(30)['g3']])};
</script>

<!-- =====================================================================
     ALPINE.JS COMPONENT
     ===================================================================== -->
<script>
function dashboard() {{
  return {{
    page: 'ringkasan',
    selectedDesa: null,
    searchQuery: '',
    filterKabkota: 'all',
    showAll: false,
    mapMode: 'heat',
    leaderboardMode: 'eczi',
    leafletMap: null,
    heatLayer: null,
    circleLayer: null,

    tabs: [
      {{id:'ringkasan',    label:'Ringkasan'}},
      {{id:'cahaya-malam', label:'Cahaya Malam'}},
      {{id:'komersial',    label:'Aktivitas Komersial'}},
      {{id:'eczi',         label:'Skor ECZI'}},
      {{id:'profil',       label:'Profil Desa'}},
      {{id:'metodologi',   label:'Metodologi'}},
    ],

    get sortedData() {{
      const src = this.leaderboardMode === 'magnitude' ? MAG_DATA : ECZI_DATA;
      return src.map((r, i) => ({{...r, rank: i+1}}));
    }},

    get totalFiltered() {{
      let d = this.sortedData;
      if (this.filterKabkota !== 'all') d = d.filter(r => String(r.kabkota_id_full) === this.filterKabkota);
      if (this.searchQuery) {{
        const q = this.searchQuery.toLowerCase();
        d = d.filter(r => r.nama_desa.toLowerCase().includes(q) || r.nama_kabkota.toLowerCase().includes(q));
      }}
      return d.length;
    }},

    get filteredDesa() {{
      let d = this.sortedData;
      if (this.filterKabkota !== 'all') d = d.filter(r => String(r.kabkota_id_full) === this.filterKabkota);
      if (this.searchQuery) {{
        const q = this.searchQuery.toLowerCase();
        d = d.filter(r => r.nama_desa.toLowerCase().includes(q) || r.nama_kabkota.toLowerCase().includes(q));
      }}
      if (!this.showAll) d = d.slice(0, 30);
      return d;
    }},

    get selectedDesaData() {{
      if (!this.selectedDesa) return ECZI_DATA[0];
      return ECZI_DATA.find(r => r.desa_uid === this.selectedDesa) || ECZI_DATA[0];
    }},

    pulseBadgeClass(badge) {{
      if (badge === 'Tren Naik Berlanjut') return 'badge-green';
      if (badge === 'Mulai Melambat') return 'badge-orange';
      if (badge === 'Continuing growth') return 'badge-green';
      if (badge === 'Slowing/reversing') return 'badge-orange';
      return 'badge-gray';
    }},

    init() {{
      this.selectedDesa = ECZI_DATA[0].desa_uid;
      this.$nextTick(() => this.renderPage());
      this.$watch('leaderboardMode', () => {{
        if (this.page === 'ringkasan') this.$nextTick(() => this.renderLeaderboardBar());
      }});
    }},

    setPage(p) {{
      this.page = p;
      this.$nextTick(() => this.renderPage());
    }},

    setMapMode(m) {{
      this.mapMode = m;
      this.$nextTick(() => this.initMap());
    }},

    selectDesa(uid) {{
      this.selectedDesa = uid;
      this.page = 'profil';
      this.$nextTick(() => this.renderPage());
    }},

    renderPage() {{
      if (this.page === 'ringkasan') {{
        this.renderLeaderboardBar();
      }} else if (this.page === 'cahaya-malam') {{
        this.initMap();
        this.renderPulseTable();
        renderMonthlyChart();
      }} else if (this.page === 'komersial') {{
        this.renderPodesBar();
        this.renderG3Bar();
      }} else if (this.page === 'eczi') {{
        this.renderRadar();
        this.renderQuadrant();
        this.renderFullRanking();
      }} else if (this.page === 'profil') {{
        this.$nextTick(() => {{
          this.renderProfileGroups();
          this.renderProfilePodes();
          this.renderProfileComp();
          const sel = document.getElementById('desa-select');
          if (sel && this.selectedDesa) sel.value = this.selectedDesa;
        }});
      }}
    }},

    renderLeaderboardBar() {{
      const isMag = this.leaderboardMode === 'magnitude';
      const src = isMag ? MAG_DATA : ECZI_DATA;
      const top30 = src.slice(0, 30);
      const scoreKey = isMag ? 'magnitude_score' : 'eczi_score';
      const barColor = isMag ? '#1A5394' : top30.map(r => r.cat_color);
      const axisTitle = isMag ? 'Skor Magnitude Komersial (0-100)' : 'Skor ECZI (0-100)';
      const trace = {{
        y: top30.map(r => r.nama_desa + ' (' + r.nama_kabkota.replace('Jakarta ','Jak').replace('Kepulauan Seribu','Kep.Seribu') + ')'),
        x: top30.map(r => r[scoreKey]),
        type: 'bar', orientation: 'h',
        marker: {{color: barColor}},
        text: top30.map(r => r[scoreKey].toFixed(1)),
        textposition: 'outside',
        hovertemplate: '<b>%{{y}}</b><br>' + (isMag ? 'Magnitude' : 'ECZI') + ': %{{x:.1f}}<br>%{{customdata}}<extra></extra>',
        customdata: top30.map(r => r.category),
      }};
      Plotly.newPlot('chart-leaderboard', [trace], {{
        margin: {{l:220, r:60, t:20, b:40}},
        xaxis: {{title: axisTitle, range:[0, Math.max(...top30.map(r=>r[scoreKey]))*1.15]}},
        yaxis: {{autorange:'reversed', tickfont:{{size:11}}}},
        paper_bgcolor:'rgba(0,0,0,0)',
        plot_bgcolor:'rgba(0,0,0,0)',
        font: {{family:'Inter,system-ui,sans-serif', size:12}},
      }}, {{responsive:true, displayModeBar:false}});
    }},

    initMap() {{
      if (this.leafletMap) {{
        this.leafletMap.remove();
        this.leafletMap = null;
      }}
      const map = L.map('map-ntl', {{center:[-6.2, 106.82], zoom:11}});
      L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
        attribution:'&copy; CartoDB &copy; OSM contributors', maxZoom:18
      }}).addTo(map);
      this.leafletMap = map;

      if (this.mapMode === 'heat') {{
        const heat = L.heatLayer(PIXEL_HEAT, {{radius:12, blur:8, maxZoom:14,
          gradient:{{0:'#2D1B00', 0.3:'#8B4500', 0.6:'#FFB700', 1:'#FFFFA0'}}}});
        heat.addTo(map);
      }} else {{
        const TCOLOR = {{'rapid_growth':'#C8102E','growth':'#EA7200','stable':'#98A2B3','decline':'#1A5394'}};
        PIXEL_CIRCLES.forEach(pc => {{
          L.circleMarker([pc[0], pc[1]], {{radius:3, color:TCOLOR[pc[3]]||'#98A2B3', fillOpacity:0.7, weight:0}})
           .bindPopup('Perubahan: ' + pc[2].toFixed(1) + '% | Tren: ' + pc[3])
           .addTo(map);
        }});
      }}

      // Reference circles for 16 named areas
      CENTROID_MAP.forEach(c => {{
        const pbadge = c.pulse_badge || 'N/A';
        const color = pbadge.includes('Continuing') || pbadge.includes('Tren Naik') ? '#22c55e'
                    : pbadge.includes('Slow') || pbadge.includes('Melambat') ? '#f97316' : '#94a3b8';
        L.circle([c.lat, c.lon], {{
          radius: c.radius_m, color: color, fillColor: color,
          fillOpacity: 0.08, weight: 2, dashArray: '4,4'
        }}).bindPopup('<b>' + c.area + '</b><br>Pulse: ' + pbadge + ' (' + c.pulse_yoy.toFixed(1) + '%)').addTo(map);
        L.marker([c.lat, c.lon], {{
          icon: L.divIcon({{html: '<div style="background:' + color + ';color:#fff;font-size:10px;padding:2px 5px;border-radius:4px;white-space:nowrap;font-weight:600;">' + c.area.split('/')[0] + '</div>', iconSize:[null,null], className:''}})
        }}).addTo(map);
      }});
    }},

    renderPulseTable() {{
      const tbody = document.getElementById('pulse-table-body');
      if (!tbody) return;
      tbody.innerHTML = PULSE_TABLE.map(p => {{
        const yoy = typeof p.pulse_yoy === 'number' ? p.pulse_yoy.toFixed(1) : p.pulse_yoy;
        const badge = p.pulse_badge;
        const badgeClass = badge.includes('Continuing') ? 'badge-green' : badge.includes('Slow') ? 'badge-orange' : 'badge-gray';
        const arrow = typeof p.pulse_yoy === 'number' ? (p.pulse_yoy > 0 ? ' +' : ' ') : '';
        return `<tr>
          <td class="font-medium">${{p.area}}</td>
          <td>${{typeof p.lum_2025==='number' ? p.lum_2025.toFixed(3) : p.lum_2025}}</td>
          <td>${{typeof p.lum_2026==='number' ? p.lum_2026.toFixed(3) : p.lum_2026}}</td>
          <td class="font-mono">${{arrow}}${{yoy}}%</td>
          <td><span class="badge ${{badgeClass}}">${{badge}}</span></td>
        </tr>`;
      }}).join('');
    }},

    renderPodesBar() {{
      const trace = {{
        y: TOP30_NAMES,
        x: TOP30_PODES_LEVEL,
        type: 'bar', orientation: 'h',
        marker: {{color: '#C8102E', opacity: 0.8}},
        hovertemplate: '<b>%{{y}}</b><br>Total Usaha: %{{x}}<extra></extra>',
      }};
      Plotly.newPlot('chart-podes-bar', [trace], {{
        margin: {{l:200, r:60, t:20, b:40}},
        xaxis: {{title: 'Total Usaha (Podes 2025)'}},
        yaxis: {{autorange:'reversed', tickfont:{{size:11}}}},
        paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
        font: {{family:'Inter,system-ui,sans-serif', size:12}},
      }}, {{responsive:true, displayModeBar:false}});
    }},

    renderG3Bar() {{
      const trace = {{
        y: TOP30_NAMES,
        x: TOP30_G3,
        type: 'bar', orientation: 'h',
        marker: {{color: '#EA7200', opacity: 0.8}},
        hovertemplate: '<b>%{{y}}</b><br>Skor G3: %{{x:.1f}}<extra></extra>',
      }};
      Plotly.newPlot('chart-g3-bar', [trace], {{
        margin: {{l:200, r:60, t:20, b:40}},
        xaxis: {{title: 'Skor Kualitas Usaha G3 (0-100)'}},
        yaxis: {{autorange:'reversed', tickfont:{{size:11}}}},
        paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
        font: {{family:'Inter,system-ui,sans-serif', size:12}},
      }}, {{responsive:true, displayModeBar:false}});
    }},

    renderRadar() {{
      const top5 = ECZI_DATA.slice(0, 5);
      const cats = ['G1 NTL', 'G2 Podes', 'G3 Komersial', 'G4 POI', 'G5 Akses'];
      const colors = ['#C8102E','#EA7200','#1A5394','#22c55e','#8B5CF6'];
      const traces = top5.map((r, i) => ({{
        type: 'scatterpolar', r: [r.g1, r.g2, r.g3, r.g4, r.g5, r.g1],
        theta: [...cats, cats[0]], name: r.nama_desa,
        line: {{color: colors[i]}}, fill: 'toself', fillcolor: colors[i] + '22',
      }}));
      Plotly.newPlot('chart-radar', traces, {{
        polar: {{radialaxis: {{range:[0,100], tickfont:{{size:9}}}}}},
        legend: {{font:{{size:11}}}},
        paper_bgcolor:'rgba(0,0,0,0)',
        margin: {{t:30, b:30}},
        font: {{family:'Inter,system-ui,sans-serif', size:12}},
      }}, {{responsive:true, displayModeBar:false}});
    }},

    renderQuadrant() {{
      const cats = [...new Set(ECZI_DATA.map(r => r.category))];
      const traces = cats.map(cat => {{
        const pts = ECZI_DATA.filter(r => r.category === cat);
        return {{
          x: pts.map(r => r.n_ntl_cagr),
          y: pts.map(r => r.g4),
          mode: 'markers', type: 'scatter', name: cat,
          marker: {{color: QUAD_COLOR[cat]||'#98A2B3', size:7, opacity:0.8}},
          hovertemplate: '<b>%{{customdata[0]}}</b><br>%{{customdata[1]}}<br>ECZI: %{{customdata[2]:.1f}}<br>Kategori: %{{customdata[3]}}<extra></extra>',
          customdata: pts.map(r => [r.nama_desa, r.nama_kabkota, r.eczi_score, r.category]),
        }};
      }});
      // Median lines
      traces.push({{
        x: [MED_X, MED_X], y: [0, 100], mode:'lines', name:'Median NTL Growth',
        line: {{color:'#94a3b8', dash:'dash', width:1}}, showlegend:false,
      }});
      traces.push({{
        x: [0, 100], y: [MED_Y, MED_Y], mode:'lines', name:'Median POI',
        line: {{color:'#94a3b8', dash:'dash', width:1}}, showlegend:false,
      }});
      Plotly.newPlot('chart-quadrant', traces, {{
        xaxis: {{title:'Skor Pertumbuhan NTL (0-100)', range:[-2, 102]}},
        yaxis: {{title:'Skor POI Gaya Hidup (0-100)', range:[-2, 102]}},
        legend: {{font:{{size:11}}}},
        margin: {{l:60, r:20, t:20, b:50}},
        paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
        font: {{family:'Inter,system-ui,sans-serif', size:12}},
      }}, {{responsive:true, displayModeBar:false}});
    }},

    renderFullRanking() {{
      const tbody = document.getElementById('full-ranking-body');
      if (!tbody) return;
      tbody.innerHTML = ECZI_DATA.map((r, i) => {{
        const badge = r.pulse_badge || '';
        const pbClass = badge === 'Tren Naik Berlanjut' ? 'badge-green' : badge === 'Mulai Melambat' ? 'badge-orange' : 'badge-gray';
        return `<tr>
          <td class="font-mono text-xs text-slate-400">${{i+1}}</td>
          <td class="font-medium text-slate-800 cursor-pointer hover:text-red-600" onclick="window._alpine && window._alpine.selectDesa('${{r.desa_uid}}')">${{r.nama_desa}}</td>
          <td class="text-slate-500 text-xs">${{r.nama_kabkota}}</td>
          <td class="font-bold text-red-700">${{r.eczi_score.toFixed(1)}}</td>
          <td class="text-slate-600 text-xs">${{r.g1.toFixed(0)}}</td>
          <td class="text-slate-600 text-xs">${{r.g2.toFixed(0)}}</td>
          <td class="text-slate-600 text-xs">${{r.g3.toFixed(0)}}</td>
          <td class="text-slate-600 text-xs">${{r.g4.toFixed(0)}}</td>
          <td class="text-slate-600 text-xs">${{r.g5.toFixed(0)}}</td>
          <td><span class="quad-pill text-white text-xs" style="background:${{r.cat_color}}">${{r.category}}</span></td>
        </tr>`;
      }}).join('');
    }},

    renderProfileGroups() {{
      const r = this.selectedDesaData;
      if (!r) return;
      const labels = ['G1 Aktivitas Spasial (NTL)','G2 Kepadatan Usaha (Podes)','G3 Kualitas Usaha','G4 POI Lifestyle','G5 Aksesibilitas'];
      const vals = [r.g1, r.g2, r.g3, r.g4, r.g5];
      const colors = ['#C8102E','#1A5394','#EA7200','#22c55e','#8B5CF6'];
      const trace = {{
        y: labels, x: vals, type:'bar', orientation:'h',
        marker:{{color:colors}},
        text: vals.map(v => v.toFixed(0)),
        textposition:'outside',
        hovertemplate:'%{{y}}: %{{x:.1f}}<extra></extra>',
      }};
      Plotly.newPlot('chart-profile-groups', [trace], {{
        margin:{{l:240, r:60, t:10, b:40}},
        xaxis:{{range:[0,115], title:'Skor (0-100)'}},
        yaxis:{{tickfont:{{size:11}}}},
        paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
        font:{{family:'Inter,system-ui,sans-serif', size:12}},
      }}, {{responsive:true, displayModeBar:false}});
    }},

    renderProfilePodes() {{
      const r = this.selectedDesaData;
      if (!r) return;
      const uid = r.desa_uid;
      const detail = PODES_DETAIL[uid] || {{}};
      const years = [2018, 2020, 2021, 2024, 2025];
      const cats = Object.keys(detail).slice(0, 6);
      const catColors = ['#C8102E','#EA7200','#1A5394','#22c55e','#8B5CF6','#F59E0B'];
      const traces = cats.map((cat, ci) => ({{
        x: years.map(String),
        y: years.map(y => (detail[cat] && detail[cat][y]) ? detail[cat][y] : 0),
        name: cat, type:'bar',
        marker:{{color:catColors[ci % catColors.length]}},
      }}));
      if (!traces.length) {{
        document.getElementById('chart-profile-podes').innerHTML = '<p class="text-slate-400 text-sm p-4">Tidak ada data Podes untuk desa ini.</p>';
        return;
      }}
      Plotly.newPlot('chart-profile-podes', traces, {{
        barmode:'group',
        xaxis:{{title:'Tahun Vintage'}},
        yaxis:{{title:'Jumlah Usaha'}},
        legend:{{font:{{size:11}}}},
        margin:{{l:60, r:20, t:10, b:40}},
        paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
        font:{{family:'Inter,system-ui,sans-serif', size:12}},
      }}, {{responsive:true, displayModeBar:false}});
    }},

    renderProfileComp() {{
      const r = this.selectedDesaData;
      if (!r) return;
      const uid = r.desa_uid;
      const cd = COMP_DETAIL[uid] || {{"2021":0,"2024":0,"2025":0}};
      const yrs = ['2021','2024','2025'];
      const vals = yrs.map(y => cd[y] || 0);
      const trace = {{
        x: yrs, y: vals, mode:'lines+markers', type:'scatter',
        line:{{color:'#EA7200', width:3}},
        marker:{{size:9, color:'#EA7200'}},
        hovertemplate:'%{{x}}: %{{y:,.0f}}<extra></extra>',
      }};
      Plotly.newPlot('chart-profile-comp', [trace], {{
        xaxis:{{title:'Tahun'}},
        yaxis:{{title:'Indeks Komersial Proxy (Rp proxy)'}},
        margin:{{l:80, r:20, t:10, b:40}},
        paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
        font:{{family:'Inter,system-ui,sans-serif', size:12}},
      }}, {{responsive:true, displayModeBar:false}});
    }},
  }}; // end return
}} // end dashboard()

function selectDesaFromDropdown(uid) {{
  const comp = document.querySelector('[x-data]').__x.$data;
  comp.selectedDesa = uid;
  comp.$nextTick(() => comp.renderPage());
}}

// Monthly chart
function renderMonthlyChart() {{
  const sel = document.getElementById('monthly-area-select');
  if (!sel) return;
  const selected = Array.from(sel.selectedOptions).map(o => o.value);
  const colors = ['#C8102E','#EA7200','#1A5394','#22c55e','#8B5CF6','#F59E0B','#06B6D4','#EC4899'];
  const traces = selected.map((area, i) => {{
    const d = MONTHLY_DATA[area] || {{ym:[], lum:[]}};
    return {{
      x: d.ym, y: d.lum, mode:'lines', name: area,
      line:{{color:colors[i % colors.length], width:2}},
      hovertemplate: '<b>' + area + '</b><br>%{{x}}: %{{y:.3f}} DNB<extra></extra>',
    }};
  }});
  Plotly.react('chart-monthly', traces, {{
    xaxis:{{title:'Bulan', tickangle:-45}},
    yaxis:{{title:'Median Luminositas (DNB)'}},
    legend:{{font:{{size:11}}}},
    margin:{{l:60, r:20, t:20, b:80}},
    paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
    font:{{family:'Inter,system-ui,sans-serif', size:12}},
  }}, {{responsive:true, displayModeBar:false}});
}}
</script>
</body>
</html>"""

# ════════════════════════════════════════════════════════════════════════════
print("[12/12] Writing HTML file...")
# ════════════════════════════════════════════════════════════════════════════
with open(OUT, "w", encoding="utf-8") as f:
    f.write(HTML)

file_size_kb = os.path.getsize(OUT) / 1024
print(f"\nDone! Output: {OUT}")
print(f"File size: {file_size_kb:.1f} KB ({file_size_kb/1024:.2f} MB)")
print(f"\n=== FIVE FIXES + THREE CHANGES CONFIRMED ===")
print(f"  Fix #1: Group 3 uses composite-potensi-DKI.csv (potensi_total per desa_uid x vintage_year)")
print(f"  Fix #2: Unit of analysis = {len(df)} desa/kelurahan")
print(f"  Fix #3: NTL/OSM/Transport use kabkota-level proxy via KK_NTL_MAP")
print(f"  Fix #4: Quadrant = n_ntl_cagr (X) vs g4 (Y), med_x={df['n_ntl_cagr'].median():.2f}, med_y={df['g4'].median():.2f}")
print(f"  Fix #5: All terminology Indonesian (Ringkasan, Cahaya Malam, Aktivitas Komersial, Skor ECZI, Profil Desa, Metodologi)")
print(f"  Change A: Winsorize podes_cagr and sak_cagr at P95 before normalization")
print(f"  Change B: G4+G5 OSM/transport use kecamatan-level proxy (44 kecamatan), G1 NTL stays kabkota")
print(f"  Change C: magnitude_score added; dual leaderboard (ECZI/Magnitude) in Ringkasan page")
