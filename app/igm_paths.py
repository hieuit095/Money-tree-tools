import os
from pathlib import Path


def igm_root() -> str:
    override = os.environ.get("MONEYTREE_IGM_ROOT", "").strip()
    if override:
        return override
    project_root = Path(__file__).resolve().parents[1]
    return str(project_root / "third_party" / "income-generator")
