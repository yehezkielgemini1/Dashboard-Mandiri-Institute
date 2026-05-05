"""Auto-crop white frames + split 2-photo composites for dashboard tiles."""
from PIL import Image
import numpy as np
from pathlib import Path

HERE = Path(__file__).parent
WHITE_THRESH = 245  # pixels with all RGB > this = treated as white frame


def is_white_row(row):
    """Row is white if mean per-pixel min channel value > threshold."""
    # row shape: (W, 3) RGB
    return np.min(row, axis=1).mean() > WHITE_THRESH


def is_white_col(col):
    return np.min(col, axis=1).mean() > WHITE_THRESH


def crop_white_frame(img):
    """Auto-crop solid white frame around image."""
    arr = np.array(img.convert('RGB'))
    H, W, _ = arr.shape

    # Top
    top = 0
    while top < H and is_white_row(arr[top]):
        top += 1
    # Bottom
    bot = H - 1
    while bot > top and is_white_row(arr[bot]):
        bot -= 1
    # Left
    left = 0
    while left < W and is_white_col(arr[:, left]):
        left += 1
    # Right
    right = W - 1
    while right > left and is_white_col(arr[:, right]):
        right -= 1

    return img.crop((left, top, right + 1, bot + 1))


def split_two_photos(img, which='top'):
    """For composites with 2 photos stacked vertically + white gap in middle.
    Returns top or bottom photo only (white frames also removed)."""
    arr = np.array(img.convert('RGB'))
    H, W, _ = arr.shape

    # Compute "whiteness" per row
    white_rows = np.array([is_white_row(arr[r]) for r in range(H)])

    # Find runs of white rows; the largest mid-image white run = gap between photos
    runs = []
    i = 0
    while i < H:
        if white_rows[i]:
            j = i
            while j < H and white_rows[j]:
                j += 1
            runs.append((i, j))  # white run [i, j)
            i = j
        else:
            i += 1

    # Filter runs that are NOT at the very top/bottom (those are outer frame)
    # The mid-gap should be a substantial run roughly between H*0.3 and H*0.7
    mid_runs = [(s, e) for (s, e) in runs if s > H * 0.15 and e < H * 0.85]
    if not mid_runs:
        # Fallback: pick longest run not touching edge
        mid_runs = [(s, e) for (s, e) in runs if s > 0 and e < H]
    if not mid_runs:
        # No gap found — just return a half
        if which == 'top':
            return crop_white_frame(img.crop((0, 0, W, H // 2)))
        return crop_white_frame(img.crop((0, H // 2, W, H)))

    # Largest gap
    gap = max(mid_runs, key=lambda r: r[1] - r[0])
    if which == 'top':
        sub = img.crop((0, 0, W, gap[0]))
    else:
        sub = img.crop((0, gap[1], W, H))
    return crop_white_frame(sub)


def main():
    jobs = [
        ('Demographic & Consumption 2025.png', 'crop',  'demographic-consumption-clean.jpg'),
        ('Dashboard kelas masyarakat.png',     'crop',  'kelas-masyarakat-clean.jpg'),
        ('Dashboard BBM.png',                  'top',   'bbm-clean.jpg'),
        ('Dashboard kendaraan.png',            'bot',   'kendaraan-clean.jpg'),
    ]
    for src_name, mode, out_name in jobs:
        src = HERE / src_name
        if not src.exists():
            print(f'[SKIP] not found: {src}')
            continue
        img = Image.open(src)
        if mode == 'crop':
            out = crop_white_frame(img)
        elif mode == 'top':
            out = split_two_photos(img, 'top')
        else:
            out = split_two_photos(img, 'bottom')
        # Save as JPEG (smaller, faster page load) at high quality
        out.convert('RGB').save(HERE / out_name, 'JPEG', quality=88, optimize=True)
        print(f'[OK] {src_name} ({img.size[0]}x{img.size[1]}) -> {out_name} ({out.size[0]}x{out.size[1]})')


if __name__ == '__main__':
    main()
