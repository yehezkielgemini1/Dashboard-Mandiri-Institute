"""Package dashboard suite untuk share via WhatsApp / file."""
import shutil, zipfile
from pathlib import Path
from datetime import date

SRC = Path(__file__).parent.parent
DOWNLOADS = Path("C:/Users/LENOVO/Downloads")
today = date.today().strftime("%y%m%d")
folder_name = f"{today}_Mandiri-Institute-Dashboard-Suite"
DEST = DOWNLOADS / folder_name

if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir(parents=True)


def should_copy(p: Path) -> bool:
    s = str(p).replace("\\", "/")
    if "/Old/" in s:
        return False
    if p.name.endswith(".py"):
        return False
    if p.name.endswith(".csv") and "_dim" not in p.name:
        return False
    if p.name == "package_share.py":
        return False
    return True


copied = 0
total = 0
for src_file in SRC.rglob("*"):
    if not src_file.is_file():
        continue
    if not should_copy(src_file):
        continue
    rel = src_file.relative_to(SRC)
    dst = DEST / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_file, dst)
    copied += 1
    total += src_file.stat().st_size

print(f"Copied {copied} files, {total // (1024*1024)} MB to {DEST.name}")

readme = DEST / "README.txt"
readme.write_text(
    f"""MANDIRI INSTITUTE DASHBOARD SUITE
Versi: {today}
Generated: {date.today().isoformat()}

CARA PAKAI:
1. Extract folder ini ke lokasi mana saja (Desktop, Documents, dll)
2. Double-click file index.html
3. Browser akan terbuka, klik card dashboard yang mau dilihat
4. Semua dashboard work offline (no internet needed)

ISI:
- index.html: Portal utama (entry point)
- konsumsi-susenas/: Konsumsi per kapita Susenas (5 exhibit + Compare + Metodologi)
- kelas-kabkota/: Distribusi 8 kelas masyarakat per 514 kab/kota + Inequality (Lorenz/Gini)
- thematic/bbm/: Konsumsi BBM per kelas (Tematik)
- _assets/: Library JS/CSS/font/icon/logo offline (jangan dihapus)

WORKFLOW PPT:
- Tiap chart punya tombol kuning [Export PPT]
- Hasil PNG 1920x1080 ready paste ke slide PowerPoint
- Logo Mandiri Institute + source citation otomatis baked

DATA SOURCE:
- Susenas Maret BPS 2019 sampai 2025
- Klasifikasi kelas wb4 Mandiri Institute (8 kelas)
- Shapefile BPS adm1 (34 prov) + adm2 (522 kab) 2020

KONTAK:
Internal Mandiri Institute, Riset
""",
    encoding="utf-8",
)

# Create ZIP
zip_path = DOWNLOADS / f"{folder_name}.zip"
print("Creating ZIP (compressing, may take 30-60s)...")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for f in DEST.rglob("*"):
        if f.is_file():
            zf.write(f, f.relative_to(DOWNLOADS))

zip_size = zip_path.stat().st_size // (1024 * 1024)
print(f"ZIP created: {zip_path.name} ({zip_size} MB)")
print(f"Folder ready: {DEST}")
print(f"ZIP ready: {zip_path}")
