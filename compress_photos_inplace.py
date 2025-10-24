#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import io
import argparse
import tempfile
import multiprocessing as mp
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from PIL import Image, ImageOps
from PIL import ImageFile as _PIL_ImageFile

# Allow loading truncated/corrupted images
_PIL_ImageFile.LOAD_TRUNCATED_IMAGES = True

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG", ".WEBP"}


@dataclass
class CompressOptions:
    root: str
    max_size: int = 1280
    quality: int = 82
    workers: int = max(1, mp.cpu_count() // 2)
    exts: Tuple[str, ...] = tuple(sorted(SUPPORTED_EXTS))


def iter_image_files(root: str, exts: Tuple[str, ...]) -> Iterable[str]:
    exts_lower = tuple(e.lower() for e in exts)
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            _, ext = os.path.splitext(name)
            if ext.lower() in exts_lower:
                yield os.path.join(dirpath, name)


def _get_mode_for_path(path: str) -> int:
    try:
        return os.stat(path).st_mode
    except Exception:
        return 0o644


def _open_image_robust(path: str) -> Image.Image:
    """Try to open image; fallback to reading bytes for robustness."""
    try:
        return Image.open(path)
    except Exception:
        try:
            with open(path, 'rb') as f:
                data = f.read()
            return Image.open(io.BytesIO(data))
        except Exception:
            raise


def compress_one(path: str, max_size: int, quality: int) -> Tuple[str, int, int, str]:
    """Compress a single image in-place using a temp file.
    Returns (path, old_size, new_size, status)
    status: "ok" | "skipped" | "error"
    """
    try:
        old_size = os.path.getsize(path)
        with _open_image_robust(path) as im:
            # Normalize orientation
            try:
                im = ImageOps.exif_transpose(im)
            except Exception:
                pass

            # Resize if larger than max_size (keeping aspect ratio)
            if max(im.size) > max_size:
                im.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Choose params per format
            ext = os.path.splitext(path)[1].lower()

            save_kwargs = {}

            if ext in (".jpg", ".jpeg", ".jpg".upper(), ".jpeg".upper()):
                # Ensure RGB for JPEG
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                save_kwargs.update(dict(format="JPEG", quality=quality, optimize=True, progressive=True, subsampling="keep"))
            elif ext in (".webp", ".webp".upper()):
                # WebP lossy with given quality
                save_kwargs.update(dict(format="WEBP", quality=quality, method=6))
                if im.mode not in ("RGB", "L", "RGBA", "LA"):
                    im = im.convert("RGB")
            elif ext in (".png", ".png".upper()):
                # PNG: optimize and compress
                if im.mode not in ("RGB", "RGBA", "L"):
                    try:
                        im = im.convert("RGB")
                    except Exception:
                        pass
                save_kwargs.update(dict(format="PNG", optimize=True, compress_level=9))
            else:
                # Unsupported? skip
                return (path, old_size, old_size, "skipped")

            # Write to temp then replace
            dirpath = os.path.dirname(path)
            mode = _get_mode_for_path(path)
            with tempfile.NamedTemporaryFile(prefix=".tmp_", suffix=ext, dir=dirpath, delete=False) as tmp:
                tmp_path = tmp.name
            try:
                im.save(tmp_path, **save_kwargs)
                new_size = os.path.getsize(tmp_path)
                if new_size > old_size and max(im.size) <= max_size:
                    os.remove(tmp_path)
                    return (path, old_size, old_size, "skipped")
                os.replace(tmp_path, path)
                try:
                    os.chmod(path, mode)
                except Exception:
                    pass
                return (path, old_size, new_size, "ok")
            except Exception:
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass
                return (path, old_size, old_size, "error")
    except Exception:
        return (path, 0, 0, "error")


def _worker(args):
    return compress_one(*args)


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024.0:
            return f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}TB"


def main():
    parser = argparse.ArgumentParser(description="Compress all images in a folder in-place (replaces originals)")
    parser.add_argument("root", help="Root folder to scan recursively")
    parser.add_argument("--max-size", type=int, default=1280, help="Max image dimension (px), default 1280")
    parser.add_argument("--quality", type=int, default=82, help="JPEG/WEBP quality (1-95), default 82")
    parser.add_argument("--workers", type=int, default=max(1, mp.cpu_count() // 2), help="Parallel workers, default ~half cores")
    parser.add_argument("--exts", default=",".join(sorted(SUPPORTED_EXTS)), help="Comma-separated extensions to include")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"ERROR: Not a directory: {root}", file=sys.stderr)
        sys.exit(1)

    exts = tuple(s.strip().lower() if s.strip().startswith('.') else f".{s.strip().lower()}" for s in args.exts.split(',') if s.strip())

    files = list(iter_image_files(root, exts))
    if not files:
        print("No image files found.")
        return

    print(f"Found {len(files)} images. Compressing with {args.workers} workers...")
    jobs = [(p, args.max_size, args.quality) for p in files]

    total_old, total_new = 0, 0
    ok = skipped = errors = 0

    with mp.Pool(processes=args.workers) as pool:
        for (path, old, new, status) in pool.imap_unordered(_worker, jobs, chunksize=4):
            if status == "ok":
                ok += 1
                total_old += old
                total_new += new
                saved = old - new
                print(f"[OK] {os.path.relpath(path, root)}  {human_size(old)} -> {human_size(new)}  (-{human_size(saved)})")
            elif status == "skipped":
                skipped += 1
                print(f"[SKIP] {os.path.relpath(path, root)}")
            else:
                errors += 1
                print(f"[ERR] {os.path.relpath(path, root)}")

    if total_old > 0:
        ratio = 100.0 * (total_old - total_new) / total_old
    else:
        ratio = 0.0
    print("\nSummary:")
    print(f"  Processed: {ok}  Skipped: {skipped}  Errors: {errors}")
    print(f"  Size: {human_size(total_old)} -> {human_size(total_new)}  (saved {human_size(total_old - total_new)} = {ratio:.1f}%)")


if __name__ == "__main__":
    main()
