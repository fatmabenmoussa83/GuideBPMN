"""Central paths and settings for the guideline-accumulation pipeline.

Everything is repository-relative so the package runs from any checkout.
"""
from pathlib import Path
import os
import sys

PIPELINE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_ROOT.parent


def portable_path(path) -> str:
    """A path as saved in the run files: relative to the repository when inside it."""
    try:
        return Path(path).resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def resolve_path(saved) -> Path:
    """The inverse of portable_path: a saved path, relative paths from the repository."""
    p = Path(saved)
    return p if p.is_absolute() else REPO_ROOT / p

# Shared components (single sources of truth).
DATASET_PATH = REPO_ROOT / "bpmn_generator_catalogue" / "dataset.json"
XSD_DIR = REPO_ROOT / "xsd"
SIM_EVAL_DIR = REPO_ROOT / "similarity_evaluator"
DOCUMENTATION_GUIDELINES = REPO_ROOT / "guidelines" / "bpmn_documentation_guidelines.json"
# The learned catalogue. GUIDEBPMN_CATALOGUE gives another file (relative to the
# repository or absolute), so that two learning runs (two APIs, two models) never
# write into the same catalogue: .\start_webapi.ps1 -Port 9000 -Catalogue guidelines\haiku\learned_guidelines.json
_CATALOGUE = os.environ.get("GUIDEBPMN_CATALOGUE", "").strip()
DEFAULT_LEARNED_GUIDELINES = REPO_ROOT / "guidelines" / "learned_guidelines.json"
LEARNED_GUIDELINES = ((Path(_CATALOGUE) if Path(_CATALOGUE).is_absolute() else REPO_ROOT / _CATALOGUE)
                      if _CATALOGUE else DEFAULT_LEARNED_GUIDELINES)
# Without GUIDEBPMN_CATALOGUE, every run uses the catalogue of its generator model:
# guidelines/learned/<model>/agents/learned_guidelines.json (guideline_store.catalogue_for_model)
LEARNED_BY_MODEL = REPO_ROOT / "guidelines" / "learned"
RUNS_DIR = PIPELINE_ROOT / "runs"

# Cross-validation and promotion.
N_FOLDS = 5
PROMOTION_MIN_SUPPORT = 2        # a candidate must fire on >= 2 other examples

def add_shared_paths():
    """Make the root validator and the similarity evaluator importable.

    """
    for p in (REPO_ROOT, SIM_EVAL_DIR):
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)
