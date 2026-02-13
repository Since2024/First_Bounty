"""Core package for the FirstChild minimal MVP."""

from importlib import resources
from pathlib import Path


def project_root() -> Path:
    """Return repository root (one level up from this package)."""
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """Directory for runtime artifacts (created on demand)."""
    root = project_root() / "artifacts"
    root.mkdir(exist_ok=True, parents=True)
    return root


__all__ = ["project_root", "data_dir", "resources"]

