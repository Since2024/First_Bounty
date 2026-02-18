"""Simple OCR fallback that honors template bounding boxes."""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pytesseract
from pytesseract import TesseractError, TesseractNotFoundError
from PIL import Image

from app.utils import get_logger, template_fields

logger = get_logger(__name__)

try:
    import cv2  # type: ignore
except ImportError:  # pragma: no cover - depends on system libs
    cv2 = None
    logger.warning("OpenCV unavailable; OCR fallback will use PIL-only preprocessing.")

AVAILABLE_LANGS: List[str] = []
try:
    AVAILABLE_LANGS = pytesseract.get_languages(config="")
except (pytesseract.TesseractError, TesseractNotFoundError):
    logger.warning("Unable to list Tesseract languages; defaulting to eng.")

VALID_LANG_FALLBACK = "eng"


def validate_lang(lang_code: str | None) -> str:
    """Return a Tesseract language string that exists on this system."""
    if not lang_code:
        lang_code = "nep+eng"

    if not AVAILABLE_LANGS:
        return VALID_LANG_FALLBACK

    parts = [segment.strip() for segment in lang_code.split("+") if segment.strip()]
    valid_parts = [segment for segment in parts if segment in AVAILABLE_LANGS]
    if valid_parts:
        return "+".join(valid_parts)

    logger.warning("Lang '%s' not available. Using '%s'.", lang_code, VALID_LANG_FALLBACK)
    return VALID_LANG_FALLBACK

class OCRFallbackError(RuntimeError):
    """Raised when OCR fallback fails."""


def _preprocess(region):
    if cv2 is None:
        # PIL fallback for environments without libGL/OpenCV runtime.
        pil_image = Image.fromarray(region)
        gray = pil_image.convert("L")
        arr = np.array(gray)
        # Basic binary threshold to boost OCR contrast.
        return np.where(arr > 170, 255, 0).astype(np.uint8)

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        29,
        5,
    )


def _extract_region_text(region, lang: str, psm: int) -> str:
    pil_image = Image.fromarray(region)
    config = f"--psm {psm} --oem 3"
    try:
        result = pytesseract.image_to_string(pil_image, lang=lang, config=config)
    except (TesseractError, TesseractNotFoundError) as exc:
        raise OCRFallbackError(str(exc)) from exc
    return result.strip()


def extract_fields_with_ocr(image_path: str, template_json: Dict) -> Dict[str, Dict]:
    """Fallback extraction relying on local Tesseract."""
    logger.warning("Running OCR fallback for %s", image_path)
    if cv2 is None:
        pil_image = Image.open(image_path).convert("RGB")
        image = np.array(pil_image)
    else:
        image = cv2.imread(image_path)
    if image is None:
        raise OCRFallbackError(f"Cannot read image: {image_path}")

    extracted: Dict[str, Dict] = {}
    for field in template_fields(template_json):
        if field is None or not isinstance(field, dict):
            continue
        fid = field.get("id")
        bbox = (field.get("bbox") or {}).get("px")
        if not fid or not bbox or len(bbox) != 4:
            continue

        x, y, w, h = map(int, bbox)
        region = image[y : y + h, x : x + w]
        if region.size == 0:
            continue

        ocr_config = field.get("ocr", {})
        if not isinstance(ocr_config, dict):
            ocr_config = {}

        lang = validate_lang(ocr_config.get("lang", "nep+eng"))
        psm = ocr_config.get("psm", 7)

        preprocessed = _preprocess(region)
        text = _extract_region_text(preprocessed, lang, psm)

        confidence = 0.8 if text else 0.0
        extracted[fid] = {
            "value": text,
            "confidence": confidence,
            "notes": "ocr_fallback",
        }

    if not extracted:
        raise OCRFallbackError("OCR fallback produced no fields")

    logger.info("OCR fallback extracted %d fields", len(extracted))
    return extracted


def extract_fields_from_multiple_images(
    image_paths: List[str],
    template_json: Dict
) -> Dict[str, Dict]:
    """
    Process ALL images with OCR and merge results.
    
    Strategy:
    - Extract from each image independently
    - Merge by taking highest-confidence value for each field
    - Track which image contributed each field
    """
    logger.warning("Running OCR fallback on %d images", len(image_paths))
    
    all_extractions = []
    for idx, img_path in enumerate(image_paths):
        try:
            logger.info("OCR processing image %d/%d: %s", idx + 1, len(image_paths), img_path)
            extraction = extract_fields_with_ocr(img_path, template_json)
            # Tag with source image
            for field_data in extraction.values():
                field_data['source_image'] = idx + 1
            all_extractions.append(extraction)
        except OCRFallbackError as e:
            logger.warning("OCR failed on image %d: %s", idx + 1, e)
            continue
    
    if not all_extractions:
        raise OCRFallbackError("OCR failed on all images")
    
    # Merge results - take highest confidence for each field
    merged: Dict[str, Dict] = {}
    for extraction in all_extractions:
        for fid, data in extraction.items():
            if fid not in merged:
                merged[fid] = data
            else:
                # Keep higher confidence value
                if data.get('confidence', 0) > merged[fid].get('confidence', 0):
                    old_conf = merged[fid].get('confidence', 0)
                    merged[fid] = data
                    logger.debug(
                        "Field %s: replaced (conf %.2f → %.2f)",
                        fid, old_conf, data.get('confidence', 0)
                    )
    
    logger.info("OCR merged %d fields from %d images", len(merged), len(all_extractions))
    return merged


__all__ = ["extract_fields_with_ocr", "extract_fields_from_multiple_images", "OCRFallbackError"]
