"""
Patch language regression di dashboard HTML.
Find-replace 12 item naming yang sudah disepakati tapi rollback berkali-kali.

Run: python patch_language.py
Output: 260503_NASA_emerging-zone-detector.html (overwrite) +
        260503_NASA_emerging-zone-detector.BACKUP.html
"""
import re
import shutil
from pathlib import Path
from datetime import datetime

FP = Path(r"C:/Users/LENOVO/OneDrive - PT Bank Mandiri (Persero) Tbk/Desktop/Mandiri/Mandiri Institute/Dashboard/emerging-zone-jakarta/260503_NASA_emerging-zone-detector.html")
BACKUP = FP.parent / f"{FP.stem}.BACKUP-{datetime.now().strftime('%y%m%d-%H%M')}{FP.suffix}"

# Order matters: LONGEST first untuk avoid partial overlap
# Format: (search, replace, label, max_safe_count)
REPLACEMENTS = [
    # ===== HEADLINES (longest, specific) =====
    ("Wilayah komersial yang sedang menyalakan diri di Jakarta.",
     "Pemetaan kawasan komersial berkembang DKI Jakarta 2021-2025.",
     "Page 1 H2 sub", None),
    ("Wilayah komersial yang sedang menyalakan diri di Jakarta",
     "Pemetaan kawasan komersial berkembang DKI Jakarta 2021-2025",
     "Page 1 H2 sub (no period)", None),

    ("II. Sinyal dari Atas Atap", "II. Tren Luminositas Malam 2021-2025",
     "Page 2 roman heading", None),
    ("Sinyal dari Atas Atap", "Tren Luminositas Malam",
     "Page 2 metaforis residual", None),

    ("Sinyal Awal 2026 per Wilayah", "Tren Terkini (2026) per Wilayah",
     "Page 2 pulse heading", None),
    ("Sinyal Awal 2026", "Tren Terkini (2026)",
     "Pulse heading short", None),

    # ===== KATEGORI 4 ITEM (longest first) =====
    ("Kawasan Komersial Sedang Naik Daun", "Emerging Hotspot",
     "Kategori #1 (full)", None),
    ("Kawasan Komersial Mapan", "Mature Commercial",
     "Kategori #2 (full)", None),

    # Standalone phrases di tooltip/badge text (after full-form replaced)
    ("Naik Daun (tinggi keduanya)", "Emerging Hotspot (tinggi keduanya)",
     "Naik Daun tooltip", None),
    ("Naik Daun", "Emerging Hotspot",
     "Naik Daun standalone", None),

    ("Mapan (kepadatan tinggi, pertumbuhan moderat)",
     "Mature Commercial (kepadatan tinggi, pertumbuhan moderat)",
     "Mapan tooltip", None),

    ("Awal Pertumbuhan (kepadatan rendah)", "Early Growth (kepadatan rendah)",
     "Awal Pertumbuhan tooltip", None),
    ("Awal Pertumbuhan", "Early Growth",
     "Awal Pertumbuhan standalone", None),

    ("Aktivitas Rendah (rendah keduanya)", "Low Activity (rendah keduanya)",
     "Aktivitas Rendah tooltip", None),
    ("Aktivitas Rendah", "Low Activity",
     "Aktivitas Rendah standalone", None),

    # ===== PULSE BADGE 3 ITEM =====
    ("Trend Lanjut Tumbuh", "Pertumbuhan", "Pulse Trend Lanjut Tumbuh", None),
    ("Lanjut Tumbuh", "Pertumbuhan", "Pulse Lanjut Tumbuh standalone", None),
    ("Mulai Melambat", "Perlambatan", "Pulse Mulai Melambat", None),

    # ===== TABEL & MISC =====
    ("Tabel Sortable", "Tabel Lengkap (dapat diurutkan)",
     "Tabel Sortable", None),
    ("Trajectory", "Lintasan", "Trajectory English", None),

    ("Tren 2026", "Tren Terkini (2026)", "Tren 2026 short", None),

    # ===== Page 5 V. Drilldown =====
    ("V. Drilldown", "V. Profil Kawasan dan Kelurahan",
     "Page 5 roman", None),

    # ===== Page 4 IV. Composite Score Detail =====
    ("IV. Composite Score Detail", "IV. Skor Komposit · Dekomposisi Komponen",
     "Page 4 roman", None),
]

# ===== Standalone "Mapan" — careful, only replace in specific contexts =====
# Skip blanket "Mapan" replace because risk of "Sudah Mapan" or other context.
# Manual check after script.

print("="*72)
print(f"Patching: {FP.name}")
print(f"Backup:   {BACKUP.name}")
print("="*72)

# Backup first
shutil.copy2(FP, BACKUP)
print(f"[1] Backup saved: {BACKUP}")

# Read
with open(FP, "r", encoding="utf-8") as f:
    content = f.read()
original_size = len(content)
print(f"[2] Loaded: {original_size:,} chars")

# Apply replacements
print("\n[3] Applying replacements:")
total_replacements = 0
for search, replace, label, expected_max in REPLACEMENTS:
    count = content.count(search)
    if count > 0:
        content = content.replace(search, replace)
        total_replacements += count
        warn = ""
        if expected_max and count > expected_max:
            warn = f" [WARN: count {count} > expected max {expected_max}]"
        print(f"  [{count:>3}x] {label:40s} '{search[:50]}'->'{replace[:50]}'{warn}")
    else:
        print(f"  [  -] {label:40s} not found")

# Audit residual (yang seharusnya 0)
print("\n[4] Residual audit (should all be 0):")
RESIDUAL_CHECKS = [
    "Kawasan Komersial Sedang Naik Daun", "Kawasan Komersial Mapan",
    "Awal Pertumbuhan", "Aktivitas Rendah", "Naik Daun",
    "Trend Lanjut Tumbuh", "Lanjut Tumbuh", "Mulai Melambat",
    "Tabel Sortable", "Trajectory", "Tren 2026",
    "Sinyal Awal 2026", "Sinyal dari Atas Atap", "menyalakan diri",
    "V. Drilldown", "IV. Composite Score Detail",
]
all_clean = True
for kw in RESIDUAL_CHECKS:
    cnt = content.count(kw)
    flag = "OK " if cnt == 0 else "MISS"
    if cnt > 0: all_clean = False
    print(f"  [{flag}] '{kw[:40]}': {cnt}x")

# Audit positive (target keywords harus muncul)
print("\n[5] Target keyword audit (should all be > 0):")
POSITIVE_CHECKS = [
    "Emerging Hotspot", "Mature Commercial", "Early Growth", "Low Activity",
    "Pertumbuhan", "Stabil", "Perlambatan",
    "Luminositas Malam", "Lintasan", "Tabel Lengkap", "Tren Terkini",
]
for kw in POSITIVE_CHECKS:
    cnt = content.count(kw)
    flag = "OK" if cnt > 0 else "FAIL"
    print(f"  [{flag}] '{kw}': {cnt}x")

# Save
with open(FP, "w", encoding="utf-8") as f:
    f.write(content)

new_size = len(content)
print(f"\n[6] Saved: {FP}")
print(f"    Size: {original_size:,} -> {new_size:,} chars (delta {new_size - original_size:+,})")
print(f"    Total replacements: {total_replacements}")

if all_clean:
    print("\n[+] ALL RESIDUAL CHECKS PASS — language fully patched")
else:
    print("\n[!] Some residual found — manual review needed")
