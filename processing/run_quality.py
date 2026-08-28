"""Run independent quality analysis over every SYNAPSE participant.

Walks ``data/``, resolves the canonical recording per participant (see
``synapse_qc.inventory``), runs the CEEGrid quality check on the full
recording, and writes (under ``paths.qc_dir`` from ``conf/config.yaml``,
resolved against $SYNAPSE_DATA_BASE — see ``synapse_qc.paths``):

  * ``outputs/qc/quality_results.xlsx``  - Summary + Per-Channel + Legend sheets
  * ``outputs/qc/reports/<PID>.txt``     - per-participant text report

This pass is fully independent of any prior hand rating; the comparison
against ``participant_info.tsv`` is a separate later step.

Usage (from the repo root, with the `brain` conda env active)::

    python run_quality.py
    python run_quality.py --preset strict
    python run_quality.py --only EXP01,CTRL07   # subset, for spot checks

Datestamp the run with ``--date YYYY-MM-DD`` (only used to label the Legend).
"""
import os
import sys
import argparse
import warnings

import numpy as np

# Make the package importable when run as a plain script from the repo root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synapse_qc import qc_core, inventory, excel, paths as qpaths  # noqa: E402

warnings.filterwarnings("ignore")


DIVERGE = 12  # |score_raw - score_filtered| at/above this = materially diverging


def _join(chs):
    return ",".join(chs) if chs else ""


def _scored_device(status, detail):
    """Device of the recording that THIS row scored (from the QC status)."""
    if status in ("ok", "empty_eeg"):
        return "OpenBCI"
    if status == "non_obci_eeg":
        d = detail.lower()
        return "Neurable" if ("neurable" in d or "mw75" in d) else "unknown"
    return ""  # no_eeg_stream / no_xdf


def _devices_present(p, scored_device):
    """All device types this participant has data for, across every session.

    Single-folder participants need no extra I/O (covered by scored_device);
    only multi-session folders (e.g. EXP10 = OpenBCI + Neurable) load siblings.
    """
    devs = set()
    if scored_device and scored_device != "unknown":
        devs.add(scored_device)
    for x in p.all_xdfs:
        if x == p.xdf_path:
            continue
        try:
            devs |= {d for d in qc_core.detect_devices(x) if d != "unknown"}
        except Exception:  # noqa: BLE001
            pass
    return ", ".join(sorted(devs))


def _stream_note(score_raw, score_filt, raw_corr_dominated):
    """Interpret raw-vs-filtered divergence for the operator."""
    if score_filt is None or np.isnan(score_filt):
        return "raw only (no filtered stream)"
    d = score_filt - score_raw
    if abs(d) < DIVERGE:
        return "consistent raw/filtered"
    if d > 0:  # filtered scores better than raw
        if raw_corr_dominated:
            return f"filtered cleaner (+{d:.0f}); raw flagged by common-mode drift (corr)"
        return f"filtered cleaner (+{d:.0f})"
    return f"filtered worse ({d:.0f}); filtered stream degraded"


def analyse_one(p, preset, method="robust"):
    """Run QC for one resolved participant. Returns (summary_row, channel_rows, report_text).

    The RAW stream (obci_eeg1) is the headline QC; the FILTERED stream
    (obci_eeg2) is scored as a cross-check / convergence validation.
    """
    base = {
        "participant": p.pid,
        "group": p.group,
        "sub_id": p.sub_id,
        "session": p.sub_dir,
        "old_only": p.old_only,
        "neurable": p.is_neurable,
        "has_responses": bool(p.responses_csv),
        "has_video": bool(p.video),
        "n_pdfs": len(p.pdfs),
        "resolve_note": p.note,
    }

    def _append_note(extra):
        base["resolve_note"] = "; ".join(x for x in (base["resolve_note"], extra) if x)

    if not p.xdf_path:
        base.update({"qc_status": "no_xdf", "has_eeg": False, "quality_score": np.nan,
                     "device": "", "devices_present": ""})
        base["auto_grade"] = excel.auto_grade(np.nan, "no_xdf")
        return base, [], None

    # Locate raw + filtered OpenBCI streams (handles empty / non-OpenBCI cases).
    try:
        raw_stream, filt_stream, status, detail = qc_core.select_obci_streams(p.xdf_path)
    except Exception as e:  # noqa: BLE001
        base.update({"qc_status": f"load_error:{type(e).__name__}", "has_eeg": False,
                     "quality_score": np.nan})
        base["auto_grade"] = excel.auto_grade(np.nan, "error")
        _append_note(str(e))
        return base, [], None

    # Device of the scored recording + every device this participant has.
    base["device"] = _scored_device(status, detail)
    base["devices_present"] = _devices_present(p, base["device"])

    if status != "ok":
        has_eeg = status in {"empty_eeg", "non_obci_eeg"}
        base.update({"qc_status": status, "has_eeg": has_eeg, "quality_score": np.nan})
        base["auto_grade"] = excel.auto_grade(np.nan, status)
        _append_note(detail)
        return base, [], None

    try:
        raw = qc_core.create_raw(raw_stream, neurable=p.is_neurable)
        qc = qc_core.quality_check(raw, preset=preset, method=method, verbose=False)
    except Exception as e:  # noqa: BLE001
        base.update({"qc_status": f"qc_error:{type(e).__name__}", "has_eeg": True,
                     "quality_score": np.nan})
        base["auto_grade"] = excel.auto_grade(np.nan, "error")
        _append_note(str(e))
        return base, [], None

    # Cross-check / convergence: QC the filtered stream the same way. With the
    # robust (filter-first) method this should agree with the raw score.
    score_filt = np.nan
    nbad_filt = np.nan
    if filt_stream is not None:
        try:
            qf = qc_core.quality_check(qc_core.create_raw(filt_stream, neurable=p.is_neurable),
                                       preset=preset, method=method, verbose=False)
            score_filt = round(qf["quality_score"], 1)
            nbad_filt = len(qf["bads_combined"])
        except Exception:  # noqa: BLE001
            pass

    ch_names = qc["ch_names"]
    snr = np.asarray(qc["snr_estimate"], dtype=float)
    mean_corr = np.asarray(qc["mean_corr"], dtype=float)
    corr_bad_frac = np.asarray(qc.get("corr_bad_frac", []), dtype=float)
    # "corr-dominated" = the correlation criterion flagged more channels than the
    # flat + dead criteria combined (signature of removable common-mode drift).
    raw_corr_dominated = len(qc["bads_corr"]) > (len(qc["bads_flat"]) + len(qc["bads_variance"]))

    base.update({
        "qc_status": "ok",
        "has_eeg": True,
        "n_channels": len(ch_names),
        "duration_s": round(qc["duration_total"], 1),
        "sfreq": round(raw.info["sfreq"], 1),
        "quality_score": round(qc["quality_score"], 1),
        "n_bad": len(qc["bads_combined"]),
        "n_flat": len(qc["bads_flat"]),
        "n_var": len(qc["bads_variance"]),
        "n_noisy": len(qc.get("bads_noisy", [])),
        "n_corr": len(qc["bads_corr"]),
        "n_highcorr": len(qc.get("bads_highcorr", [])),
        "bad_channels": _join(sorted(qc["bads_combined"])),
        "flat_channels": _join(sorted(qc["bads_flat"])),
        "dead_channels": _join(sorted(qc["bads_variance"])),
        "noisy_channels": _join(sorted(qc.get("bads_noisy", []))),
        "corr_channels": _join(sorted(qc["bads_corr"])),
        "highcorr_channels": _join(sorted(qc.get("bads_highcorr", []))),
        "ear_asymmetry": round(qc["ear_asymmetry"], 4) if qc["ear_asymmetry"] is not None else np.nan,
        "mean_snr": round(float(np.mean(snr)), 1),
        "min_snr": round(float(np.min(snr)), 1),
        "mean_corr": round(float(np.nanmean(mean_corr)), 3),
        "max_corr_bad_frac": (round(float(np.nanmax(corr_bad_frac)), 3)
                              if corr_bad_frac.size else np.nan),
        "n_corr_windows": qc.get("n_corr_windows", 0),
        "method": qc.get("method", method),
        "has_filtered": filt_stream is not None,
        "score_filtered": score_filt,
        "n_bad_filtered": nbad_filt,
        "stream_note": _stream_note(qc["quality_score"], score_filt, raw_corr_dominated),
    })
    base["auto_grade"] = excel.auto_grade(qc["quality_score"], "ok")

    # Per-channel long rows (RAW / canonical stream).
    flat = set(qc["bads_flat"])
    dead = set(qc["bads_variance"])
    noisy = set(qc.get("bads_noisy", []))
    corr = set(qc["bads_corr"])
    highcorr = set(qc.get("bads_highcorr", []))
    ch_rows = []
    for i, ch in enumerate(ch_names):
        flags = []
        if ch in flat:
            flags.append("flat")
        if ch in dead:
            flags.append("dead")
        if ch in noisy:
            flags.append("noisy")
        if ch in corr:
            flags.append("lowcorr")
        if ch in highcorr:
            flags.append("bridge?")
        ch_rows.append({
            "participant": p.pid,
            "group": p.group,
            "channel": ch,
            "status": "BAD" if ch in qc["bads_combined"] else "OK",
            "flagged_by": "+".join(flags),
            "variance": float(qc["variances"][i]),
            "sd_uv": round(float(qc["ch_sd_uv"][i]), 4),
            "mean_corr": round(float(mean_corr[i]), 3) if not np.isnan(mean_corr[i]) else np.nan,
            "corr_bad_frac": (round(float(corr_bad_frac[i]), 3)
                              if i < corr_bad_frac.size else np.nan),
            "snr": round(float(snr[i]), 1),
        })

    report = qc_core.generate_quality_report(qc, ch_names=ch_names)
    return base, ch_rows, report


def main():
    ap = argparse.ArgumentParser(description="Independent SYNAPSE EEG quality analysis.")
    ap.add_argument("--preset", default="default", choices=["default", "strict", "lenient"])
    ap.add_argument("--method", default="robust", choices=["robust", "legacy"],
                    help="robust = filter-first (default); legacy = original unfiltered metric")
    ap.add_argument("--only", default="", help="comma list of PIDs to restrict to")
    ap.add_argument("--date", default="", help="label the run date in the Legend")
    ap.add_argument("--data-root", default=None,
                    help="raw recordings dir (default: $SYNAPSE_DATA_ROOT / "
                         "$SYNAPSE_DATA_BASE/data / <repo>/data)")
    args = ap.parse_args()

    # Output location comes from conf/config.yaml (paths.qc_dir) -- change it
    # there, not here.
    out_dir = qpaths.output_paths()["qc"]
    report_dir = os.path.join(out_dir, "reports")
    xlsx_path = os.path.join(out_dir, "quality_results.xlsx")
    os.makedirs(report_dir, exist_ok=True)
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    participants = inventory.discover(data_root=args.data_root)
    if only:
        participants = [p for p in participants if p.pid in only]

    summary_rows, channel_rows = [], []
    print(f"Analysing {len(participants)} participants (preset={args.preset}, method={args.method})\n")
    print(f"{'PID':8} {'grade':10} {'score':>6} {'bad':>4}  status / note")
    print("-" * 72)
    for p in participants:
        row, ch_rows, report = analyse_one(p, args.preset, method=args.method)
        summary_rows.append(row)
        channel_rows.extend(ch_rows)
        if report:
            with open(os.path.join(report_dir, f"{p.pid}.txt"), "w") as f:
                f.write(report)
        score = row.get("quality_score")
        score_s = f"{score:.0f}" if isinstance(score, (int, float)) and not np.isnan(score) else "-"
        print(f"{p.pid:8} {row.get('auto_grade',''):10} {score_s:>6} "
              f"{str(row.get('n_bad','-')):>4}  {row['qc_status']}"
              + (f" | {row['resolve_note']}" if row['resolve_note'] else ""))

    run_meta = {
        "generated": args.date or "(undated)",
        "preset": args.preset,
        "method": args.method,
        "window": "full recording (no event cropping)",
        "n": len(summary_rows),
        "config": qc_core.CEEGRID_QUALITY_PRESETS.get(args.preset, {}),
    }
    excel.write_workbook(summary_rows, channel_rows, xlsx_path, run_meta=run_meta)

    n_ok = sum(1 for r in summary_rows if r["qc_status"] == "ok")
    n_no_eeg = sum(1 for r in summary_rows if r["qc_status"].startswith("no_eeg"))
    print("\n" + "=" * 72)
    print(f"Wrote {xlsx_path}")
    print(f"  {len(summary_rows)} participants | {n_ok} with EEG analysed | "
          f"{n_no_eeg} no EEG stream")
    print(f"  per-participant reports in {report_dir}/")


if __name__ == "__main__":
    main()
