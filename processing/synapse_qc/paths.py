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


# ---------------------------------------------------------------------------
# The analysis repo (`publication_analysis` + `preprocessing`), which supplies
# the published preprocessing code that build_dataset / pair_video reuse.
# ---------------------------------------------------------------------------

_COLLECTION_ROOT = os.path.dirname(REPO)          # .../synapse-data-collection
_PROJECTS = os.path.dirname(_COLLECTION_ROOT)     # its parent

# Checked in order after $SYNAPSE_REPO / paths.synapse_repo. Add new layouts
# here rather than hardcoding a machine-specific path anywhere else.
_SYNAPSE_REPO_CANDIDATES = [
    os.path.join(_PROJECTS, "synapse-analysis"),
    os.path.join(_PROJECTS, "synapse"),
    os.path.join(_COLLECTION_ROOT, "..", "synapse"),
]


def _looks_like_synapse_repo(path):
    return bool(path) and os.path.isdir(os.path.join(path, "publication_analysis"))


def synapse_repo(cfg_value=None, required=False):
    """Absolute path to the analysis repo, or '' if it cannot be found.

    Precedence: ``paths.synapse_repo`` (config/CLI) -> ``$SYNAPSE_REPO`` ->
    the known sibling layouts in :data:`_SYNAPSE_REPO_CANDIDATES`. Nothing is
    hardcoded to one machine; if the repo lives somewhere new, either set
    ``$SYNAPSE_REPO`` or add the layout to that list.
    """
    for cand in (cfg_value, os.environ.get("SYNAPSE_REPO")):
        if _looks_like_synapse_repo(cand):
            return os.path.abspath(cand)
        if cand:  # explicitly pointed somewhere that is not the repo
            raise FileNotFoundError(
                f"synapse_repo={cand!r} does not contain publication_analysis/. "
                f"Point $SYNAPSE_REPO or paths.synapse_repo at the analysis repo.")
    for cand in _SYNAPSE_REPO_CANDIDATES:
        if _looks_like_synapse_repo(cand):
            return os.path.abspath(cand)
    if required:
        raise FileNotFoundError(
            "Could not locate the analysis repo (publication_analysis/). Set "
            "$SYNAPSE_REPO=/path/to/synapse-analysis, or add the layout to "
            "synapse_qc.paths._SYNAPSE_REPO_CANDIDATES. Searched: "
            + ", ".join(_SYNAPSE_REPO_CANDIDATES))
    return ""


def published_workbook(repo=None):
    """The clinical workbook inside the analysis repo (the older state the
    published pkl was built from). Globbed, because the filename is not
    consistent across checkouts -- '02_PC Data.xlsx' on one machine,
    '02_PC Data .xlsx' (note the space) on another."""
    import glob
    repo = repo or synapse_repo()
    if not repo:
        return ""
    hits = sorted(glob.glob(os.path.join(repo, "02_PC*Data*.xls*")))
    return hits[0] if hits else ""


def published_pkl(repo=None):
    """The published synapse_preprocessed.pkl, for pipelines/compare.py."""
    repo = repo or synapse_repo()
    return os.path.join(repo, "processed_data", "synapse_preprocessed.pkl") if repo else ""


def participant_info_tsv(repo=None):
    """The prior hand-graded ratings TSV (see synapse_qc/manual.py)."""
    repo = repo or synapse_repo()
    return os.path.join(repo, "participant_info.tsv") if repo else ""
