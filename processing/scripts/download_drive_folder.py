#!/usr/bin/env python3
"""Recursively download a Google Drive folder via gws CLI."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def gws_list(parent_id: str) -> list[dict]:
    params = json.dumps(
        {
            "q": f"'{parent_id}' in parents",
            "pageSize": 1000,
            "fields": "files(id,name,mimeType,size)",
        }
    )
    r = subprocess.run(
        ["gws", "drive", "files", "list", "--params", params],
        capture_output=True,
        text=True,
    )
    out = r.stdout.split("\n", 1)[1] if r.stdout.startswith("Using") else r.stdout
    data = json.loads(out)
    if "error" in data:
        raise RuntimeError(data["error"])
    return data.get("files", [])


def download_file(file_id: str, dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip (exists): {dest}", flush=True)
        return dest.stat().st_size
    params = json.dumps({"fileId": file_id, "alt": "media"})
    r = subprocess.run(
        ["gws", "drive", "files", "get", "--params", params, "-o", str(dest)],
        capture_output=True,
        text=True,
    )
    out = r.stdout.split("\n", 1)[1] if r.stdout.startswith("Using") else r.stdout
    data = json.loads(out)
    if "error" in data:
        raise RuntimeError(data["error"])
    nbytes = int(data.get("bytes", 0))
    print(f"  saved {nbytes/1e6:.1f} MB -> {dest}", flush=True)
    return nbytes


def download_tree(folder_id: str, dest: Path) -> int:
    total = 0
    for f in gws_list(folder_id):
        name = f["name"]
        if name.startswith("._"):
            continue
        path = dest / name
        if f["mimeType"] == "application/vnd.google-apps.folder":
            print(f"dir  {path}/", flush=True)
            total += download_tree(f["id"], path)
        else:
            print(f"file {path}", flush=True)
            total += download_file(f["id"], path)
    return total


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder_id", help="Google Drive folder ID")
    p.add_argument("dest", type=Path, help="Local destination directory")
    args = p.parse_args()
    args.dest.mkdir(parents=True, exist_ok=True)
    nbytes = download_tree(args.folder_id, args.dest)
    print(f"Done: {nbytes/1e6:.1f} MB total -> {args.dest}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
