"""Inject uniform CSS override to all 6 dashboards: hide sidebar + dark/cb toggles, keep topnav only."""
from pathlib import Path

ROOT = Path(__file__).parent.parent

DASHBOARDS = [
    'konsumsi-susenas/dashboard.html',
    'kelas-kabkota/dashboard.html',
    'thematic/bbm/dashboard.html',
    'ketahanan-pangan/ketahanan-pangan-dashboard.html',
    'peta-potensi-kendaraan/dashboard.html',
    'emerging-zone-jakarta/260503_NASA_emerging-zone-detector.html',
]

OVERRIDE_BLOCK = """
<!-- UNIFORM v2 OVERRIDE 2026-05-05: hide sidebar entirely, keep topnav as the only nav -->
<style id="uniform-v2-override">
  /* Hide entire sidebar (incl. nav items, dark mode toggle, color blind toggle, palette tag) */
  .sidebar, aside.sidebar { display: none !important; }
  .mobile-toggle { display: none !important; }
  /* Remove sidebar offset so main content uses full width */
  .with-sidebar { margin-left: 0 !important; }
  /* Push folio/filter sticky bars below topnav (topnav height ~64px) */
  .folio { top: 64px !important; }
  .filter-bar { top: 96px !important; }
</style>
"""

OVERRIDE_MARKER = 'id="uniform-v2-override"'

for rel in DASHBOARDS:
    fp = ROOT / rel
    if not fp.exists():
        print(f'[SKIP] not found: {fp}')
        continue
    txt = fp.read_text(encoding='utf-8')
    if OVERRIDE_MARKER in txt:
        print(f'[SKIP-already-applied] {rel}')
        continue
    # Inject right before </head>
    if '</head>' not in txt:
        print(f'[ERR no </head>] {rel}')
        continue
    new_txt = txt.replace('</head>', OVERRIDE_BLOCK + '\n</head>', 1)
    fp.write_text(new_txt, encoding='utf-8')
    print(f'[OK] {rel}')

print('Done.')
