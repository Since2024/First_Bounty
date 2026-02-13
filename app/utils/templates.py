"""Helpers for working with template JSON definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from app import project_root
from app.utils.logger import get_logger

logger = get_logger(__name__)

TEMPLATES_DIR = project_root() / "app" / "templates"


def list_template_files() -> List[Path]:
    """Return sorted JSON template paths."""
    if not TEMPLATES_DIR.exists():
        logger.warning("Template directory %s is missing", TEMPLATES_DIR)
        return []
    return sorted(TEMPLATES_DIR.glob("*.json"))


def load_template_file(template_name: str) -> Dict:
    """
    Load a template JSON by name (relative to templates directory).

    Args:
        template_name: JSON filename or relative path.
    """
    path = resolve_template_asset(template_name)
    if not path.exists():
        raise FileNotFoundError(f"Template '{template_name}' not found at {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_template_asset(filename: str) -> Path:
    """Resolve any asset (image/json) under templates."""
    candidate = Path(filename)
    if candidate.is_absolute():
        return candidate
    return TEMPLATES_DIR / filename


def template_fields(template_data: Dict) -> Iterable[Dict]:
    """Yield field definitions regardless of template nesting."""
    if not template_data:
        return []

    if "fields" in template_data:
        return template_data["fields"]

    forms = template_data.get("forms") or []
    if forms:
        return forms[0].get("fields", [])

    return []


def template_image_path(template_data: Dict) -> Optional[Path]:
    """Return the background image path if declared in metadata."""
    metadata = {}
    if "forms" in template_data and template_data["forms"]:
        metadata = template_data["forms"][0].get("metadata", {})
    elif "metadata" in template_data:
        metadata = template_data["metadata"]

    filename = metadata.get("image_filename")
    if not filename:
        return None

    path = resolve_template_asset(filename)
    return path if path.exists() else None


__all__ = [
    "list_template_files",
    "load_template_file",
    "resolve_template_asset",
    "template_fields",
    "template_image_path",
    "TEMPLATES_DIR",
]

