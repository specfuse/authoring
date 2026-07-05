"""Specfuse authoring kit — bootstrap, asset refresh, and generator launcher."""

from importlib.resources import files
from pathlib import Path

__version__ = "0.3.3"


def kit_root() -> Path:
    """Resolve the directory holding the kit's authored content.

    Works in two layouts:
      * installed wheel  -> specfuse/authoring/_kit/...
      * editable/repo    -> <repo-root>/  (handbooks/, samples/, ...)
    """
    bundled = Path(str(files("specfuse.authoring"))) / "_kit"
    if (bundled / "handbooks").is_dir():
        return bundled
    # Dev fallback: specfuse/authoring/__init__.py -> repo root is two parents up.
    repo = Path(__file__).resolve().parents[2]
    if (repo / "handbooks").is_dir():
        return repo
    raise FileNotFoundError(
        "Cannot locate kit content (handbooks/). "
        f"Looked in {bundled} and {repo}."
    )
