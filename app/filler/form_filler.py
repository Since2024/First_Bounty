"""Normalize Gemini output for downstream PDF filling."""

from __future__ import annotations

import re
from typing import Dict, List

from app.utils import template_fields

NEPALI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def _normalize_digits(value: str) -> str:
    return value.translate(NEPALI_DIGITS)


def _normalize_date(value: str) -> str:
    clean = _normalize_digits(value).replace(".", "-").replace("/", "-")
    clean = re.sub(r"\s+", "", clean)
    # Accept YYYY-MM-DD or DD-MM-YYYY patterns.
    parts = clean.split("-")
    if len(parts) != 3:
        return value.strip()
    if len(parts[0]) == 4:
        year, month, day = parts
    else:
        day, month, year = parts
    if not (year.isdigit() and month.isdigit() and day.isdigit()):
        return value.strip()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _normalize_phone(value: str) -> str:
    """Normalize phone to exactly 10 digits."""
    digits = re.sub(r"\D", "", _normalize_digits(value))

    # Remove country code if present
    if digits.startswith("977") and len(digits) > 10:
        digits = digits[-10:]

    # Take last 10 digits if longer
    if len(digits) > 10:
        digits = digits[-10:]

    # Only return if exactly 10 digits and valid Nepali format (starts with 9, second digit is 7 or 8)
    if len(digits) == 10 and digits[0] == "9" and digits[1] in ("7", "8"):
        return digits

    # Return original if can't normalize to 10 digits
    return value


def _normalize_email(value: str) -> str:
    """Validate email - must contain @ and domain."""
    value = value.strip().lower()

    # Must have @ and at least one character before and after
    if "@" in value and "." in value:
        parts = value.split("@")
        if len(parts[0]) > 0 and len(parts[1]) > 2 and "." in parts[1]:
            return value

    return value  # Return as-is if format seems okay


def _normalize_default(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_value(field: Dict, value: str) -> str:
    """Normalize field value based on field type."""
    ftype = (field.get("type") or "").lower()

    if not value or not value.strip():
        return ""

    # Email validation
    if "email" in ftype or field.get("validate", {}).get("type") == "email":
        return _normalize_email(value)

    # Phone validation
    if "phone" in ftype or field.get("validate", {}).get("type") == "phone":
        return _normalize_phone(value)

    # Date validation
    if ftype in {"date", "text_date"} or field.get("validate", {}).get("type") == "date":
        return _normalize_date(value)

    # Numbers and box_grid
    if ftype in {"number", "box_grid"} or field.get("validate", {}).get("type") == "number":
        return _normalize_digits(value).replace(" ", "")

    # Default - preserve all text
    return _normalize_default(value)


def prepare_pdf_fields(gemini_output: Dict[str, Dict], template_json: Dict) -> List[Dict]:
    """
    Merge Gemini output with template metadata for PDF generation.

    Returns:
        List of dicts with keys: id, name, value, confidence, bbox_px, page, style
    """
    # Auto-fill submitter fields from owner fields if empty
    # f009 (submitter name) ← f002 (owner name) if f009 is empty
    # f010 (submitter address) ← f006 (owner address) if f010 is empty
    if not gemini_output.get("f009", {}).get("value", "").strip():
        owner_name = gemini_output.get("f002", {}).get("value", "").strip()
        if owner_name:
            gemini_output["f009"] = {
                "value": owner_name,
                "confidence": gemini_output.get("f002", {}).get("confidence", 0.8),
                "notes": f"Auto-filled from owner name (f002): {owner_name}",
            }
    
    if not gemini_output.get("f010", {}).get("value", "").strip():
        owner_address = gemini_output.get("f006", {}).get("value", "").strip()
        if owner_address:
            gemini_output["f010"] = {
                "value": owner_address,
                "confidence": gemini_output.get("f006", {}).get("confidence", 0.8),
                "notes": f"Auto-filled from owner address (f006): {owner_address}",
            }
    
    prepared: List[Dict] = []
    
    for field in template_fields(template_json):
        if field is None or not isinstance(field, dict):
            continue
            
        fid = field.get("id")
        bbox = (field.get("bbox") or {}).get("px")
        if not fid or not bbox or len(bbox) != 4:
            continue

        entry = gemini_output.get(fid, {})
        raw_value = entry.get("value", "")
        normalized = _normalize_value(field, raw_value)
        
        # Skip empty optional fields, but keep empty required fields for visibility
        if normalized == "" and not field.get("validate", {}).get("req"):
            continue

        try:
            confidence = float(entry.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0

        prepared.append(
            {
                "id": fid,
                "name": field.get("name", fid),
                "value": normalized,
                "confidence": max(0.0, min(1.0, confidence)),
                "bbox_px": bbox,
                "page": field.get("page", 1),
                "style": field.get("style", "normal"),
                "type": field.get("type", "text_line"),
                "grid": field.get("grid", {}),
            }
        )
    return prepared


__all__ = ["prepare_pdf_fields"]

