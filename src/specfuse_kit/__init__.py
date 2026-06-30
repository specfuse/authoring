"""Specfuse spec-authoring kit — bootstrap, asset refresh, and generator launcher."""

from importlib.resources import files
from pathlib import Path

__version__ = "0.3.0"


def kit_root() -> Path:
    """Resolve the directory holding the kit's authored content.

    Works in two layouts:
      * installed wheel  -> specfuse_kit/_kit/...
      * editable/repo    -> <repo-root>/  (handbooks/, claude-assets/, ...)
    """
    bundled = Path(str(files("specfuse_kit"))) / "_kit"
    if (bundled / "claude-assets").is_dir():
        return bundled
    # Dev fallback: src/specfuse_kit/__init__.py -> repo root is two parents up.
    repo = Path(__file__).resolve().parents[2]
    if (repo / "claude-assets").is_dir():
        return repo
    raise FileNotFoundError(
        "Cannot locate kit assets (claude-assets/). "
        f"Looked in {bundled} and {repo}."
    )
