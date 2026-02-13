"""OCR fallback package."""

from .extractor import extract_fields_with_ocr, extract_fields_from_multiple_images, OCRFallbackError

__all__ = ["extract_fields_with_ocr", "extract_fields_from_multiple_images", "OCRFallbackError"]

