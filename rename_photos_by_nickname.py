#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import csv
import argparse
import unicodedata
from typing import Optional, Tuple, List

from PIL import Image, ImageOps, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESPONSES_CSV_DEFAULT = None
FORMULAIRE_CSV_DEFAULT = None
PHOTOS_LINKS_CSV_DEFAULT = os.path.join(DATA_DIR, "photos_links.csv")

# auto-detect responses csv
for fname in os.listdir(DATA_DIR):
    if fname.endswith(".csv") and ("Réponses au formulaire" in fname or fname == "formulaire.csv"):
        # préférer formulaire.csv si présent
        path = os.path.join(DATA_DIR, fname)
        if fname == "formulaire.csv":
            FORMULAIRE_CSV_DEFAULT = path
            break
        RESPONSES_CSV_DEFAULT = path
if FORMULAIRE_CSV_DEFAULT is None and RESPONSES_CSV_DEFAULT is not None:
    FORMULAIRE_CSV_DEFAULT = RESPONSES_CSV_DEFAULT

# find File responses root
FILE_RESPONSES_DIR = None
# Schéma final: data/images/{tetes,pieds}
FILE_RESPONSES_DIR = os.path.join(DATA_DIR, "images")
os.makedirs(os.path.join(FILE_RESPONSES_DIR, "tetes"), exist_ok=True)
os.makedirs(os.path.join(FILE_RESPONSES_DIR, "pieds"), exist_ok=True)


def norm(s: str) -> str:
    try:
        return unicodedata.normalize("NFKC", s or "").strip().casefold()
    except Exception:
        return (s or "").strip().lower()


def sanitize_basename(nickname: str) -> str:
    # Keep readable, replace spaces with underscores, remove slashes and control chars
    s = unicodedata.normalize("NFKC", nickname or "").strip()
    s = s.replace("/", "-").replace("\\", "-")
    s = "_".join(s.split())
    # Optional: limit length
    return s[:200]


def find_subdirs() -> Tuple[Optional[str], Optional[str]]:
    if not FILE_RESPONSES_DIR:
        return None, None
    neuillesque = None
    pieds = None
    for sub in os.listdir(FILE_RESPONSES_DIR):
        p = os.path.join(FILE_RESPONSES_DIR, sub)
        if not os.path.isdir(p):
            continue
        low = sub.lower()
        if neuillesque is None and ("tetes" in low or "tête" in low or "neuillesque" in low or "jeu" in low):
            neuillesque = p
        if pieds is None and ("pieds" in low or "pied" in low):
            pieds = p
    return neuillesque, pieds


def find_best_match(subdir: str, nickname: str) -> Optional[str]:
    if not subdir:
        return None
    target = norm(nickname)
    best = None
    try:
        for fname in os.listdir(subdir):
            fb = os.path.splitext(fname)[0]
            if target and target in norm(fb):
                best = os.path.join(subdir, fname)
                break
    except Exception:
        return None
    return best


def find_by_exact_name(subdir: str, filename: str) -> Optional[str]:
    """Find a file by exact name (case-insensitive). If not found, try basename-only match."""
    if not subdir or not filename:
        return None
    target_full = filename.casefold()
    target_base = os.path.splitext(filename)[0].casefold()
    try:
        for fname in os.listdir(subdir):
            if fname.casefold() == target_full:
                return os.path.join(subdir, fname)
        for fname in os.listdir(subdir):
            if os.path.splitext(fname)[0].casefold() == target_base:
                return os.path.join(subdir, fname)
    except Exception:
        return None
    return None


def convert_to_jpeg(src_path: str, dest_path: str) -> bool:
    try:
        with Image.open(src_path) as im:
            try:
                im = ImageOps.exif_transpose(im)
            except Exception:
                pass
            if im.mode in ("RGBA", "LA"):
                background = Image.new("RGB", im.size, (255, 255, 255))
                background.paste(im, mask=im.split()[-1])
                im = background
            elif im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            im.save(dest_path, format="JPEG", quality=85, optimize=True, progressive=True)
        return True
    except Exception as e:
        print(f"[ERROR] Convert {src_path} -> {dest_path}: {e}")
        return False


def unique_path(path: str) -> str:
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        cand = f"{base}_{i}{ext}"
        if not os.path.exists(cand):
            return cand
        i += 1


def already_ok(src_path: str, expected_base: str, is_feet: bool) -> bool:
    """Return True if the source filename already matches the expected final name.
    expected: [nickname].jpg or [nickname]_pieds.jpg (case-insensitive).
    """
    src_name = os.path.basename(src_path).lower()
    expected = (f"{expected_base}_pieds.jpg" if is_feet else f"{expected_base}.jpg").lower()
    return src_name == expected


def process(responses_csv: str, dry_run: bool = False, verbose: bool = False, report_path: Optional[str] = None,
            photos_links_csv: Optional[str] = None) -> None:
    neuillesque_dir, pieds_dir = find_subdirs()
    if not neuillesque_dir and not pieds_dir:
        print("ERROR: Subfolders not found under File responses.")
        return

    # Load formulaire
    with open(responses_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows: List[dict] = list(reader)

    # Load photos_links mapping (link -> filename)
    link_to_name = {}
    plc = photos_links_csv or PHOTOS_LINKS_CSV_DEFAULT
    if plc and os.path.exists(plc):
        try:
            with open(plc, encoding="utf-8") as pf:
                pr = csv.DictReader(pf)
                for r in pr:
                    pl = (r.get("person_photo_link") or "").strip()
                    pn = (r.get("person_photo_name") or "").strip()
                    if pl and pn:
                        link_to_name[pl] = pn
                    fl = (r.get("feet_photo_link") or "").strip()
                    fn = (r.get("feet_photo_name") or "").strip()
                    if fl and fn:
                        link_to_name[fl] = fn
        except Exception as e:
            if verbose:
                print(f"[WARN] Cannot read photos_links.csv: {e}")

    total = 0
    renamed = 0
    skipped = 0
    reasons = {}
    events = []

    def add_event(nick: str, kind: str, action: str, src: Optional[str], dest: Optional[str], reason: Optional[str] = None):
        if reason:
            reasons[reason] = reasons.get(reason, 0) + 1
        if verbose:
            tag = "RENAMED" if action == "renamed" else ("SKIP" if action == "skipped" else action.upper())
            print(f"[{tag}] {kind:6} {nick} | src={src or '-'} -> dest={dest or '-'} | reason={reason or ''}")
        events.append({
            "nickname": nick,
            "type": kind,
            "action": action,
            "src": src or "",
            "dest": dest or "",
            "reason": reason or "",
        })

    for row in rows:
        nickname = (row.get("Surnom (le VRAI, pour pouvoir vous identifier)") or "").strip()
        if not nickname:
            continue
        base = sanitize_basename(nickname)

        # Person photo
        # Determine expected source by mapping first
        link_person = (row.get("Une photo de vous neuillesque (pour le jeu)") or "").strip()
        mapped_person_name = link_to_name.get(link_person, "")
        src_person = None
        if mapped_person_name:
            src_person = find_by_exact_name(neuillesque_dir, mapped_person_name)
        if not src_person:
            # fallback to nickname heuristic
            src_person = find_best_match(neuillesque_dir, nickname)
        if src_person:
            # Skip if already in expected final name
            if already_ok(src_person, base, is_feet=False):
                skipped += 1
                expected = os.path.join(neuillesque_dir, f"{base}.jpg") if neuillesque_dir else None
                add_event(nickname, "person", "skipped", src_person, expected, "already_ok")
            else:
                dest = os.path.join(neuillesque_dir, f"{base}.jpg")
                # If a correct file already exists, skip renaming this one
                if os.path.exists(dest):
                    skipped += 1
                    add_event(nickname, "person", "skipped", src_person, dest, "dest_exists")
                else:
                    dest = unique_path(dest)
                    if dry_run:
                        add_event(nickname, "person", "dry_run", src_person, dest, None)
                    else:
                        if convert_to_jpeg(src_person, dest):
                            try:
                                os.remove(src_person)
                            except Exception:
                                pass
                            renamed += 1
                            add_event(nickname, "person", "renamed", src_person, dest, None)
                        else:
                            skipped += 1
                            add_event(nickname, "person", "skipped", src_person, dest, "convert_failed")
        else:
            skipped += 1
            expected = os.path.join(neuillesque_dir, f"{base}.jpg") if neuillesque_dir else None
            add_event(nickname, "person", "skipped", None, expected, "not_found")

        # Feet photo
        link_feet = (row.get("une photo de vos pieds (pour le plaisir)") or "").strip()
        mapped_feet_name = link_to_name.get(link_feet, "")
        src_feet = None
        if mapped_feet_name:
            src_feet = find_by_exact_name(pieds_dir, mapped_feet_name)
        if not src_feet:
            src_feet = find_best_match(pieds_dir, nickname)
        if src_feet:
            if already_ok(src_feet, base, is_feet=True):
                skipped += 1
                expected = os.path.join(pieds_dir, f"{base}_pieds.jpg") if pieds_dir else None
                add_event(nickname, "feet", "skipped", src_feet, expected, "already_ok")
            else:
                dest = os.path.join(pieds_dir, f"{base}_pieds.jpg")
                if os.path.exists(dest):
                    skipped += 1
                    add_event(nickname, "feet", "skipped", src_feet, dest, "dest_exists")
                else:
                    dest = unique_path(dest)
                    if dry_run:
                        add_event(nickname, "feet", "dry_run", src_feet, dest, None)
                    else:
                        if convert_to_jpeg(src_feet, dest):
                            try:
                                os.remove(src_feet)
                            except Exception:
                                pass
                            renamed += 1
                            add_event(nickname, "feet", "renamed", src_feet, dest, None)
                        else:
                            skipped += 1
                            add_event(nickname, "feet", "skipped", src_feet, dest, "convert_failed")
        else:
            skipped += 1
            expected = os.path.join(pieds_dir, f"{base}_pieds.jpg") if pieds_dir else None
            add_event(nickname, "feet", "skipped", None, expected, "not_found")

        total += 1

    print(f"Processed rows: {total}  Renamed: {renamed}  Skipped: {skipped}")
    if reasons:
        print("Skip reasons:")
        for k,v in sorted(reasons.items(), key=lambda x: (-x[1], x[0])):
            print(f"  - {k}: {v}")

    if report_path:
        import json
        try:
            with open(report_path, "w", encoding="utf-8") as rf:
                rf.write(json.dumps({
                    "summary": {"processed": total, "renamed": renamed, "skipped": skipped, "reasons": reasons},
                    "events": events,
                }, ensure_ascii=False, indent=2))
            print(f"Report written to {report_path}")
        except Exception as e:
            print(f"[WARN] Cannot write report: {e}")


def main():
    parser = argparse.ArgumentParser(description="Rename photos by nickname to [nickname].jpg and [nickname]_pieds.jpg")
    parser.add_argument("--responses", default=FORMULAIRE_CSV_DEFAULT, help="Path to formulaire CSV")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying files")
    parser.add_argument("--verbose", action="store_true", help="Verbose per-file logs")
    parser.add_argument("--report", default=None, help="Write a JSON report to this path")
    parser.add_argument("--links", default=PHOTOS_LINKS_CSV_DEFAULT, help="Path to photos_links.csv")
    args = parser.parse_args()

    if not args.responses or not os.path.exists(args.responses):
        print("ERROR: responses CSV not found. Use --responses to specify path.", file=sys.stderr)
        sys.exit(1)

    process(args.responses, dry_run=args.dry_run, verbose=args.verbose, report_path=args.report, photos_links_csv=args.links)


if __name__ == "__main__":
    main()
