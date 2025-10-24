#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import sys
import argparse
from typing import Optional, Tuple

import gspread
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession


PERSON_COL_LABEL = "Une photo de vous neuillesque (pour le jeu)"
FEET_COL_LABEL = "une photo de vos pieds (pour le plaisir)"


def extract_google_drive_id(url: Optional[str]) -> str:
    if not url:
        return ""
    url = str(url)
    if "id=" in url:
        parts = url.split("id=")
        if len(parts) > 1:
            return parts[1].split("&")[0]
    if "/d/" in url:
        parts = url.split("/d/")
        if len(parts) > 1:
            return parts[1].split("/")[0]
    if "open?id=" in url:
        parts = url.split("open?id=")
        if len(parts) > 1:
            return parts[1].split("&")[0]
    return url.strip()


def get_drive_file_name(session: AuthorizedSession, file_id: str, timeout: int = 20) -> str:
    if not file_id:
        return ""
    try:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=name"
        resp = session.get(url, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("name", "") or ""
        else:
            # print debug on stderr but don't fail the process
            print(f"[WARN] Drive API {file_id} -> HTTP {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
            return ""
    except Exception as e:
        print(f"[WARN] Drive API error for {file_id}: {e}", file=sys.stderr)
        return ""


def find_column_indexes(headers: list) -> Tuple[int, int]:
    person_idx = -1
    feet_idx = -1

    def normalize(s: str) -> str:
        return (s or "").strip().lower()

    for idx, h in enumerate(headers):
        h_norm = normalize(h)
        if person_idx == -1 and normalize(PERSON_COL_LABEL) == h_norm:
            person_idx = idx
        if feet_idx == -1 and normalize(FEET_COL_LABEL) == h_norm:
            feet_idx = idx
    return person_idx, feet_idx


def main():
    parser = argparse.ArgumentParser(description="Extract Google Drive photo links and names from a Google Sheet")
    parser.add_argument("--sheet-id", default=os.environ.get("SHEET_ID"), help="Google Sheet ID")
    parser.add_argument("--service-account", default=os.environ.get("SERVICE_ACCOUNT_FILE", "service_account.json"), help="Path to service_account.json")
    parser.add_argument("--worksheet", default=None, help="Worksheet name (default: first sheet)")
    parser.add_argument("--output", default=os.path.join("data", "photos_links.csv"), help="Output CSV path")
    args = parser.parse_args()

    if not args.sheet_id:
        print("ERROR: Missing --sheet-id or SHEET_ID env.", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.service_account):
        print(f"ERROR: Service account file not found: {args.service_account}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Auth scopes: Sheets read + Drive read metadata
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly',
    ]
    creds = service_account.Credentials.from_service_account_file(args.service_account, scopes=scopes)

    # gspread client for Sheets
    client = gspread.authorize(creds)

    # Authorized session for Drive REST calls
    session = AuthorizedSession(creds)

    # Open sheet
    workbook = client.open_by_key(args.sheet_id)
    ws = workbook.worksheet(args.worksheet) if args.worksheet else workbook.sheet1

    values = ws.get_all_values()
    if not values:
        print("ERROR: Empty sheet.", file=sys.stderr)
        sys.exit(2)

    headers = values[0]
    person_idx, feet_idx = find_column_indexes(headers)
    if person_idx == -1 or feet_idx == -1:
        print("ERROR: Required columns not found.", file=sys.stderr)
        print(f"Expected: '{PERSON_COL_LABEL}' and '{FEET_COL_LABEL}'", file=sys.stderr)
        sys.exit(3)

    # Prepare CSV
    out_rows = []
    out_headers = [
        "person_photo_link",
        "person_photo_name",
        "feet_photo_link",
        "feet_photo_name",
    ]

    # Iterate rows
    for row in values[1:]:
        person_link = row[person_idx] if person_idx < len(row) else ""
        feet_link = row[feet_idx] if feet_idx < len(row) else ""

        person_id = extract_google_drive_id(person_link)
        feet_id = extract_google_drive_id(feet_link)

        person_name = get_drive_file_name(session, person_id) if person_id else ""
        feet_name = get_drive_file_name(session, feet_id) if feet_id else ""

        # Skip completely empty rows
        if not (person_link or feet_link):
            continue

        out_rows.append([
            person_link or "",
            person_name or "",
            feet_link or "",
            feet_name or "",
        ])

    # Write output
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(out_headers)
        writer.writerows(out_rows)

    print(f"✓ Wrote {len(out_rows)} rows to {args.output}")


if __name__ == "__main__":
    main()

