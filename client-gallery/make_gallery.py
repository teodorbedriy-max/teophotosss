#!/usr/bin/env python3
"""Build a private client gallery (static site) from a folder of photos.

    python3 make_gallery.py ~/Photos/anna-shoot --client "Анна" --date "10.11.2026"

Output: client-gallery/out/<slug>/ — upload that folder to Cloudflare Pages
(drag and drop) or deploy it with `wrangler pages deploy`.

Originals are copied byte for byte (100% quality). Small previews are made
only for viewing in the browser.
Needs Pillow:  pip3 install pillow
"""
import argparse
import datetime as dt
import html
import json
import re
import secrets
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow is missing. Install it with:  pip3 install pillow")

Image.MAX_IMAGE_PIXELS = None
HERE = Path(__file__).resolve().parent
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
MAX_FILE = 25 * 1024 * 1024  # Cloudflare Pages limit per file
PREVIEW, THUMB = 2400, 900

UA = {"а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie", "ж": "zh", "з": "z",
      "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
      "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
      "щ": "shch", "ь": "", "ю": "iu", "я": "ia", "ё": "e", "ы": "y", "э": "e", "ъ": ""}


def slugify(text):
    s = "".join(UA.get(c, c) for c in text.lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:30] or "client"


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024


def save_small(img, dest, size, icc):
    im = img.copy()
    im.thumbnail((size, size), Image.LANCZOS)
    kw = {"quality": 84, "optimize": True, "progressive": True}
    if icc:
        kw["icc_profile"] = icc
    im.save(dest, "JPEG", **kw)


def natural_key(p):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="folder with the edited photos")
    ap.add_argument("--client", required=True, help='client name shown on the page, e.g. "Анна"')
    ap.add_argument("--title", default="", help='optional shoot title, e.g. "Осіння сесія"')
    ap.add_argument("--date", default="", help="date shown on the page (default: today)")
    ap.add_argument("--lang", choices=("uk", "en", "es"), default="uk", help="page language (default uk)")
    ap.add_argument("--cover", default="", help="file name of the cover photo (default: first photo)")
    ap.add_argument("--slug", default="", help="folder / project name (default: client name + random code)")
    ap.add_argument("--out", default=str(HERE / "out"), help="where to put the gallery folder")
    a = ap.parse_args()

    src = Path(a.source).expanduser()
    files = sorted((p for p in src.iterdir() if p.is_file() and p.suffix.lower() in PHOTO_EXT
                    and not p.name.startswith(".")), key=natural_key)
    skipped = [p for p in src.iterdir() if p.is_file() and p.suffix.lower() not in PHOTO_EXT
               and not p.name.startswith(".")]
    too_big = [p for p in files if p.stat().st_size > MAX_FILE]
    files = [p for p in files if p not in too_big]
    if not files:
        sys.exit(f"No photos found in {src}")

    slug = a.slug or f"{slugify(a.client)}-{secrets.token_hex(3)}"
    out = Path(a.out).expanduser() / slug
    if out.exists():
        shutil.rmtree(out)
    for d in ("o", "p", "t"):
        (out / d).mkdir(parents=True)

    items, total = [], 0
    for i, p in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {p.name}", flush=True)
        shutil.copy2(p, out / "o" / p.name)  # untouched original
        with Image.open(p) as im:
            icc = im.info.get("icc_profile")
            im = ImageOps.exif_transpose(im)
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            stem = f"{i:03d}.jpg"
            save_small(im, out / "p" / stem, PREVIEW, icc)
            save_small(im, out / "t" / stem, THUMB, icc)
            w, h = im.size
        size = p.stat().st_size
        total += size
        items.append({"n": p.name, "o": "o/" + quote(p.name), "p": "p/" + stem, "t": "t/" + stem,
                      "w": w, "h": h, "s": size})

    cover = next((it for it in items if it["n"] == a.cover), items[0])
    date = a.date or dt.date.today().strftime("%d.%m.%Y")
    page = (HERE / "template.html").read_text(encoding="utf-8")
    grid = "\n".join(
        f'<a class="tile" href="{it["p"]}" data-i="{k}" style="aspect-ratio:{it["w"]}/{it["h"]}">'
        f'<img src="{it["t"]}" width="{it["w"]}" height="{it["h"]}" loading="lazy" decoding="async" '
        f'alt="{html.escape(it["n"])}"></a>'
        for k, it in enumerate(items))
    data = {"client": a.client, "title": a.title, "date": date, "lang": a.lang, "zip": slug + ".zip",
            "total": total, "items": items}
    repl = {
        "{{LANG}}": a.lang,
        "{{CLIENT}}": html.escape(a.client),
        "{{TITLE}}": html.escape(a.title),
        "{{DATE}}": html.escape(date),
        "{{COUNT}}": str(len(items)),
        "{{TOTAL}}": human(total),
        "{{COVER}}": cover["p"],
        "{{GRID}}": grid,
        "{{DATA}}": json.dumps(data, ensure_ascii=False).replace("</", "<\\/"),
    }
    for k, v in repl.items():
        page = page.replace(k, v)
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    (out / "_headers").write_text(
        "/*\n  X-Robots-Tag: noindex, nofollow\n  Referrer-Policy: no-referrer\n"
        "/o/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/p/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/t/*\n  Cache-Control: public, max-age=31536000, immutable\n")

    print(f"\nDone: {len(items)} photos, {human(total)} of originals")
    print(f"Folder:  {out}")
    print(f"Cloudflare Pages project name:  {slug}")
    for p in too_big:
        print(f"SKIPPED (over 25 MB, Cloudflare Pages limit): {p.name}")
    for p in skipped:
        print(f"SKIPPED (not a photo): {p.name}")


if __name__ == "__main__":
    main()
