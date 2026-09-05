#!/usr/bin/env python3
"""Copy subject folders from 01_Experimental/01_Control into PC/Phone subfolders.

NB those are folder names on GOOGLE DRIVE, not local paths -- and they are the
OLD, PARTIAL staging area, superseded by `PC/` (see docs/data_sync.md). Kept for
the folder ids it records; prefer scripts/sync_study_data.py for pulling data.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

EXP_SOURCE = "1fuedMYQX93jnIVU9OM09gJuyULW44i4G"
CTRL_SOURCE = "1p3GulCfl4TJOAnLBkY1nN1D3k1g-Yiu_"
PC_EXP_DEST = "1PwPZVgItqGQjYsvIexCHKgGeSN6kESvW"
PC_CTRL_DEST = "1sMmxBa92rbywM6AkUTEIvVIq8S0XY2-a"
PHONE_EXP_DEST = "15k5Z3CNDnVc8WkhcBvM-5EZKmTwm02GU"
PHONE_CTRL_DEST = "16c1z_3nAOcoILOSTsxeVoz1rbj3Zoenk"

LOG_PATH = Path(__file__).resolve().parents[1] / "outputs" / "runs" / "copy_subjects_to_pc_phone.log"


def gws(*args: str) -> dict:
    r = subprocess.run(["gws", *args], capture_output=True, text=True, check=False)
    out = r.stdout
    if out.startswith("Using keyring"):
        out = "\n".join(out.splitlines()[1:])
    if not out.strip():
        raise RuntimeError(f"gws empty output: {r.stderr}")
    data = json.loads(out)
    if "error" in data:
        raise RuntimeError(str(data["error"]))
    return data


def list_children(folder_id: str) -> list[dict]:
    params = json.dumps(
        {
            "q": f"'{folder_id}' in parents",
            "pageSize": 1000,
            "fields": "files(id,name,mimeType,capabilities)",
        }
    )
    return gws("drive", "files", "list", "--params", params).get("files", [])


def existing_names(parent_id: str) -> set[str]:
    return {f["name"] for f in list_children(parent_id)}


def has_xdf(folder_id: str, cache: dict[str, bool] | None = None) -> bool:
    if cache is None:
        cache = {}
    if folder_id in cache:
        return cache[folder_id]
    queue = [folder_id]
    while queue:
        fid = queue.pop(0)
        for f in list_children(fid):
            if f.get("name", "").lower().endswith(".xdf"):
                cache[folder_id] = True
                return True
            if f.get("mimeType") == "application/vnd.google-apps.folder":
                queue.append(f["id"])
    cache[folder_id] = False
    return False


def create_folder(name: str, parent_id: str) -> str:
    body = json.dumps(
        {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
    )
    return gws("drive", "files", "create", "--json", body)["id"]


def copy_file(file_id: str, name: str, parent_id: str) -> None:
    params = json.dumps({"fileId": file_id})
    body = json.dumps({"name": name, "parents": [parent_id]})
    gws("drive", "files", "copy", "--params", params, "--json", body)


def copy_tree(source_id: str, dest_parent_id: str, name: str) -> str:
    dest_id = create_folder(name, dest_parent_id)
    for ch in list_children(source_id):
        if ch["mimeType"] == "application/vnd.google-apps.folder":
            copy_tree(ch["id"], dest_id, ch["name"])
        elif (ch.get("capabilities") or {}).get("canCopy", True):
            copy_file(ch["id"], ch["name"], dest_id)
        else:
            log(f"    SKIP (no copy perm): {name}/{ch['name']}")
    return dest_id


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def process_cohort(source_id: str, pc_dest: str, phone_dest: str, label: str) -> dict:
    cache: dict[str, bool] = {}
    pc_names = existing_names(pc_dest)
    phone_names = existing_names(phone_dest)
    subjects = [
        f
        for f in list_children(source_id)
        if f["mimeType"] == "application/vnd.google-apps.folder"
    ]
    subjects.sort(key=lambda x: x["name"])

    stats = {"copied_pc": [], "copied_phone": [], "skipped": [], "failed": []}
    for s in subjects:
        name = s["name"]
        is_pc = has_xdf(s["id"], cache)
        dest = pc_dest if is_pc else phone_dest
        dest_label = "PC" if is_pc else "Phone"
        dest_names = pc_names if is_pc else phone_names

        if name in dest_names:
            log(f"{label} {name}: skip (already in {dest_label})")
            stats["skipped"].append(name)
            continue

        log(f"{label} {name}: copying to {dest_label}...")
        t0 = time.time()
        try:
            copy_tree(s["id"], dest, name)
            elapsed = time.time() - t0
            log(f"{label} {name}: done ({elapsed:.1f}s)")
            stats[f"copied_{dest_label.lower()}"].append(name)
            dest_names.add(name)
        except Exception as exc:  # noqa: BLE001
            log(f"{label} {name}: FAILED — {exc}")
            stats["failed"].append({"name": name, "error": str(exc)})

    return stats


def main() -> int:
    LOG_PATH.write_text("", encoding="utf-8")
    log("Starting subject copy job")
    exp_stats = process_cohort(EXP_SOURCE, PC_EXP_DEST, PHONE_EXP_DEST, "EXP")
    ctrl_stats = process_cohort(CTRL_SOURCE, PC_CTRL_DEST, PHONE_CTRL_DEST, "CTRL")
    summary = {"experimental": exp_stats, "control": ctrl_stats}
    log("SUMMARY: " + json.dumps(summary))
    return 1 if summary["experimental"]["failed"] or summary["control"]["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
