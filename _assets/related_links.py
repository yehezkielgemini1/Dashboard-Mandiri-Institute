"""
Inject "Dashboard Terkait" cross-link section to footer of each dashboard.
Run setelah generator + offline_patch:
  python _assets/related_links.py
"""
from pathlib import Path
import re

ROOT = Path(__file__).parent.parent

# Manifest: id, label, kategori, icon, path relatif dari root
ALL_DASHBOARDS = [
    {"id": "konsumsi-susenas", "label": "Konsumsi per Kapita", "kategori": "Riset Reguler",
     "icon": "mdi:cart-outline", "path": "konsumsi-susenas/dashboard.html",
     "blurb": "Pengeluaran konsumsi RT, makanan vs non-makanan, rincian 316 komoditi."},
    {"id": "kelas-kabkota", "label": "Distribusi Kelas Masyarakat", "kategori": "Riset Reguler",
     "icon": "mdi:account-group-outline", "path": "kelas-kabkota/dashboard.html",
     "blurb": "Distribusi 8 kelas masyarakat di 514 kab/kota, plus kurva Lorenz & koefisien Gini."},
    {"id": "peta-potensi-kendaraan", "label": "Potensi Pasar Kredit Kendaraan", "kategori": "Research Initiative",
     "icon": "mdi:car-multiple", "path": "peta-potensi-kendaraan/dashboard.html",
     "blurb": "Skor komposit 13 indeks untuk memetakan kabkot prioritas kredit kendaraan."},
    {"id": "bbm", "label": "Konsumsi BBM per Kelas", "kategori": "Isu Tematik",
     "icon": "mdi:gas-station-outline", "path": "thematic/bbm/dashboard.html",
     "blurb": "Komposisi 5 jenis BBM per kelas masyarakat. Era subsidi Premium vs penghapusan 2022."},
]

# Per dashboard: relative depth ke root + dashboard ID nya sendiri
DASHBOARD_FILES = [
    {"file": "konsumsi-susenas/dashboard.html", "self_id": "konsumsi-susenas", "depth": "../"},
    {"file": "kelas-kabkota/dashboard.html",    "self_id": "kelas-kabkota",    "depth": "../"},
    {"file": "peta-potensi-kendaraan/dashboard.html", "self_id": "peta-potensi-kendaraan", "depth": "../"},
    {"file": "thematic/bbm/dashboard.html",     "self_id": "bbm",              "depth": "../../"},
]

MARKER_START = "<!-- RELATED-LINKS-START -->"
MARKER_END = "<!-- RELATED-LINKS-END -->"


def build_related_html(self_id: str, depth: str) -> str:
    """Build cross-link section HTML untuk dashboard tertentu."""
    others = [d for d in ALL_DASHBOARDS if d["id"] != self_id]
    cards = []
    for d in others:
        href = depth + d["path"]
        cards.append(f"""
        <a href="{href}" class="related-card">
          <div class="related-icon"><iconify-icon icon="{d['icon']}"></iconify-icon></div>
          <div class="related-body">
            <div class="related-tag">{d['kategori']}</div>
            <div class="related-title">{d['label']}</div>
            <div class="related-blurb">{d['blurb']}</div>
          </div>
          <iconify-icon icon="mdi:arrow-right" class="related-arrow"></iconify-icon>
        </a>""")
    return f"""{MARKER_START}
<style>
  .related-section {{ border-top: 1px solid var(--rule); margin-top: 64px; padding-top: 40px; padding-bottom: 32px; }}
  .related-section .related-eyebrow {{ font-size: 11px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: var(--navy); }}
  .related-section h3 {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 24px; font-weight: 600; color: var(--ink); margin-top: 6px; margin-bottom: 24px; }}
  .related-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
  .related-card {{ display: flex; align-items: flex-start; gap: 16px; padding: 18px; border: 1px solid var(--rule); background: white; text-decoration: none; color: var(--ink); transition: all 0.15s; }}
  .related-card:hover {{ border-color: var(--navy); box-shadow: 0 4px 16px rgba(5,28,44,0.08); transform: translateY(-2px); }}
  .related-icon {{ width: 40px; height: 40px; background: var(--mist); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
  .related-icon iconify-icon {{ font-size: 22px; color: var(--navy); }}
  .related-body {{ flex: 1; min-width: 0; }}
  .related-tag {{ font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }}
  .related-title {{ font-family: 'Source Serif 4', Georgia, serif; font-size: 15px; font-weight: 600; line-height: 1.25; margin-top: 4px; }}
  .related-blurb {{ font-size: 12px; color: var(--muted); line-height: 1.45; margin-top: 6px; }}
  .related-arrow {{ font-size: 18px; color: var(--navy); flex-shrink: 0; }}
</style>
<div class="with-sidebar">
<section class="related-section max-w-[1280px] mx-auto px-8">
  <div class="related-eyebrow">Lihat Juga</div>
  <h3>Dashboard terkait</h3>
  <div class="related-grid">{''.join(cards)}
  </div>
</section>
</div>
{MARKER_END}"""


def inject(file_path: Path, self_id: str, depth: str) -> None:
    if not file_path.exists():
        print(f"  SKIP: {file_path} not found")
        return
    h = file_path.read_text(encoding="utf-8")
    block = build_related_html(self_id, depth)
    if MARKER_START in h:
        # Replace existing block
        h = re.sub(re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END), block, h, count=1, flags=re.DOTALL)
    else:
        # Insert before </body>
        h = h.replace("</body>", block + "\n</body>", 1)
    file_path.write_text(h, encoding="utf-8")
    print(f"  OK: {file_path.relative_to(ROOT)}")


if __name__ == "__main__":
    print("Inject 'Dashboard Terkait' cross-link section to all dashboards")
    for d in DASHBOARD_FILES:
        inject(ROOT / d["file"], d["self_id"], d["depth"])
    print("Done.")
