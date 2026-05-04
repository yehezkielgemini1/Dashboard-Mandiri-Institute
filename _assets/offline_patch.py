"""
Patch generated dashboard HTML files to use local assets (offline mode).
Replaces CDN URLs with relative paths to ../_assets/ (or ../../_assets/ for thematic).

Run setelah generator masing-masing dashboard:
  python _assets/offline_patch.py
"""
from pathlib import Path
import re

ROOT = Path(__file__).parent.parent  # Dashboard/

DASHBOARDS = [
    (ROOT / "konsumsi-susenas" / "dashboard.html", "../_assets"),
    (ROOT / "kelas-kabkota"    / "dashboard.html",    "../_assets"),
    (ROOT / "peta-potensi-kendaraan" / "dashboard.html", "../_assets"),
    (ROOT / "thematic" / "bbm" / "dashboard.html",              "../../_assets"),
    (ROOT / "index.html",                                            "_assets"),
]

CDN_REPLACE = [
    (r'https://cdn\.plot\.ly/plotly-[\d.]+\.min\.js',                          "{a}/plotly.min.js"),
    (r'https://cdn\.tailwindcss\.com',                                          "{a}/tailwind.min.js"),
    (r'https://cdn\.jsdelivr\.net/npm/alpinejs@[\w.x]+/dist/cdn\.min\.js',     "{a}/alpine.min.js"),
    (r'https://code\.iconify\.design/iconify-icon/[\d.]+/iconify-icon\.min\.js',"{a}/iconify-icon.min.js"),
]

GFONTS_LINK = re.compile(r'<link href="https://fonts\.googleapis\.com/css2[^"]+" rel="stylesheet">')


def patch(html_path: Path, asset_prefix: str) -> int:
    if not html_path.exists():
        print(f"  SKIP (not found): {html_path.relative_to(ROOT)}")
        return 0
    h = html_path.read_text(encoding="utf-8")
    orig_len = len(h)
    # Replace CDN script URLs
    for pat, repl in CDN_REPLACE:
        h = re.sub(pat, repl.format(a=asset_prefix), h)
    # Replace Google Fonts link with local CSS
    h = GFONTS_LINK.sub(f'<link href="{asset_prefix}/fonts/fonts.css" rel="stylesheet">', h)
    # Inject icons.js right after iconify-icon script tag
    icons_inject = f'<script src="{asset_prefix}/icons.js"></script>'
    if icons_inject not in h:
        h = h.replace("iconify-icon.min.js\"></script>", f'iconify-icon.min.js"></script>\n{icons_inject}')
    html_path.write_text(h, encoding="utf-8")
    delta = len(h) - orig_len
    print(f"  OK: {html_path.relative_to(ROOT)} ({delta:+d} bytes)")
    return 1


if __name__ == "__main__":
    print("Offline patch: replace CDN URLs with local _assets paths")
    n = sum(patch(p, a) for p, a in DASHBOARDS)
    print(f"Patched {n} dashboard(s)")
