"""Single source of truth for where generated outputs live.

Every output location is defined ONCE, in ``conf/config.yaml`` under ``paths:``
(``qc_dir``, ``output_dir``, ...). The Hydra pipelines read them from their own
cfg; the plain scripts (``run_quality.py``, ``spotcheck.py``) load the same YAML
through :func:`output_paths` -- so relocating any output is a one-line config
change, never a code change.

Base-dir precedence (mirrors the Hydra pipelines):
``paths.root`` (config/CLI) -> ``$SYNAPSE_DATA_BASE`` -> the repo dir (with a
loud warning, so a forgotten env var can't silently grow a second outputs tree).
"""
import os
import subprocess

from omegaconf import OmegaConf

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG = os.path.join(REPO, "conf", "config.yaml")


def resolve_base(cfg_root=None, warn=True):
    """Base dir holding the ``outputs/`` (and usually ``data/``) trees."""
    base = cfg_root or os.environ.get("SYNAPSE_DATA_BASE")
    if base:
        return base
    if warn:
        print(f"[paths] WARNING: $SYNAPSE_DATA_BASE is not set and paths.root was "
              f"not given -- outputs will go under the repo ({REPO}/outputs). "
              f"Point SYNAPSE_DATA_BASE at the data tree "
              f"(e.g. /data1/anarghya/synapse-data) to write there instead.")
    return REPO


def output_paths(cfg_root=None, warn=True):
    """Resolved output dirs for the non-Hydra entry points, straight from
    ``conf/config.yaml``. Returns ``{"base", "qc", "epochs"}``."""
    cfg = OmegaConf.load(_CONFIG)
    base = resolve_base(cfg_root or cfg.paths.get("root"), warn=warn)
    return {
        "base": base,
        "qc": os.path.join(base, cfg.paths.qc_dir),
        "epochs": os.path.join(base, cfg.paths.output_dir),
    }


def git_sha():
    """Short commit id of this checkout (``-dirty`` when uncommitted changes
    exist), recorded in every output manifest; '' if git is unavailable."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True,
            stderr=subprocess.DEVNULL).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=REPO, text=True,
            stderr=subprocess.DEVNULL).strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:  # noqa: BLE001
        return ""
