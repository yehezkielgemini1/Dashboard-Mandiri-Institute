"""Move <link rel="stylesheet" href=".../_shared/tactile-editorial.css"> to AFTER the last </style> before </head>.
Reason: per-file <style> blocks were overriding shared CSS via cascade order.
Fix: shared CSS placed LATER in cascade → shared tokens + canonical components win."""
from pathlib import Path
import re

FILES = [
    "index.html",
    "kelas-kabkota/dashboard.html",
    "konsumsi-susenas/dashboard.html",
    "ketahanan-pangan/ketahanan-pangan-dashboard.html",
    "thematic/bbm/dashboard.html",
    "peta-potensi-kendaraan/dashboard.html",
    "mbg-gap-analysis/dashboard.html",
    "demografi-kesehatan/dashboard.html",
    "umkm-nasional/dashboard.html",
    "aktivitas-ekonomi/regional/dki-jakarta.html",
]

base = Path(".")
for f_rel in FILES:
    fp = base / f_rel
    if not fp.exists():
        print(f"SKIP missing: {f_rel}")
        continue
    text = fp.read_text(encoding="utf-8")
    # Find the <link> for shared tactile-editorial
    link_pat = re.compile(r'^.*<link[^>]*_shared/tactile-editorial\.css[^>]*>\s*\n', re.MULTILINE)
    m = link_pat.search(text)
    if not m:
        print(f"SKIP no shared link: {f_rel}")
        continue
    link_line = m.group(0)
    # Remove link from current position
    text_wo_link = link_pat.sub("", text, count=1)
    # Find </head>
    head_close = text_wo_link.find("</head>")
    if head_close == -1:
        print(f"SKIP no </head>: {f_rel}")
        continue
    # Find LAST </style> before </head>
    last_style_close = text_wo_link.rfind("</style>", 0, head_close)
    if last_style_close == -1:
        # No <style> block at all — just put before </head>
        insert_pos = head_close
    else:
        # Insert after </style> tag (with newline)
        insert_pos = last_style_close + len("</style>")
        # Find newline after </style>
        nl = text_wo_link.find("\n", insert_pos)
        if nl != -1:
            insert_pos = nl + 1
    new_text = text_wo_link[:insert_pos] + link_line + text_wo_link[insert_pos:]
    fp.write_text(new_text, encoding="utf-8")
    print(f"DONE: {f_rel}")
print("\nAll done.")
