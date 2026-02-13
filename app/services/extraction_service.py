"""Extraction service - handles all document processing logic."""

import hashlib
import json
from typing import List, Dict, Tuple
from pathlib import Path
import tempfile

from app.gemini import extract_fields_from_images, GeminiExtractionError
from app.ocr import extract_fields_from_multiple_images, OCRFallbackError
from app.utils import get_logger
from app.utils.cache import get_cached_extraction, set_cached_extraction

logger = get_logger(__name__)


class ExtractionService:
    """Handles document extraction with Gemini + OCR fallback."""
    
    @staticmethod
    def extract_from_files(
        uploaded_files: List,
        template: Dict,
        force_refresh: bool = False
    ) -> Tuple[Dict[str, Dict], str, List[str]]:
        """
        Extract fields from uploaded files with caching support.
        
        Args:
            uploaded_files: List of uploaded file objects
            template: Template definition
            force_refresh: If True, bypass cache and force fresh extraction
        
        Returns:
            (extraction_dict, engine_used, error_messages)
        """
        errors = []
        
        # Compute hashes
        images_bytes = [file.getvalue() for file in uploaded_files]
        image_hashes = [
            hashlib.sha256(img).hexdigest()[:16]
            for img in images_bytes
        ]
        template_hash = hashlib.sha256(
            json.dumps(template, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        if force_refresh:
            logger.info("Force refresh: bypassing cache")
        else:
            # Check for cached Gemini results first (prefer Gemini over OCR)
            cached_gemini = get_cached_extraction(image_hashes, template_hash, engine_filter="gemini")
            if cached_gemini:
                logger.info("Using cached Gemini extraction")
                return cached_gemini, "cached_gemini", []
        
        # Try Gemini first (always attempt fresh Gemini if no cached Gemini found)
        
        try:
            logger.info("Starting Gemini extraction...")
            extraction = extract_fields_from_images(images_bytes, template)
            
            # Cache successful Gemini extraction
            set_cached_extraction(image_hashes, template_hash, extraction, engine="gemini")
            
            return extraction, "gemini", []
            
        except GeminiExtractionError as exc:
            error_msg = f"Gemini failed: {str(exc)}"
            logger.warning(error_msg)
            errors.append(error_msg)
            
            # Log the full error details for debugging
            logger.error("Gemini extraction error details: %s", exc, exc_info=True)
            
            # Fallback to OCR - check for cached OCR only if not forcing refresh
            if not force_refresh:
                cached_ocr = get_cached_extraction(image_hashes, template_hash, engine_filter="ocr")
                if cached_ocr:
                    logger.info("Using cached OCR extraction (Gemini failed, using previous OCR result)")
                    return cached_ocr, "cached_ocr", errors
            
            try:
                logger.info("Falling back to OCR...")
                temp_paths = []
                
                for idx, file in enumerate(uploaded_files):
                    tmp = tempfile.NamedTemporaryFile(
                        suffix=f"_{idx}.jpg",
                        delete=False
                    )
                    tmp.write(file.getvalue())
                    tmp.flush()
                    temp_paths.append(tmp.name)
                
                extraction = extract_fields_from_multiple_images(temp_paths, template)
                
                # Cache OCR extraction (but mark it as OCR so we can retry Gemini later)
                set_cached_extraction(image_hashes, template_hash, extraction, engine="ocr")
                
                # Cleanup
                for path in temp_paths:
                    Path(path).unlink(missing_ok=True)
                
                return extraction, "ocr", errors
                
            except OCRFallbackError as ocr_exc:
                error_msg = f"OCR failed: {str(ocr_exc)}"
                logger.error(error_msg)
                errors.append(error_msg)
                raise RuntimeError(f"All extraction methods failed: {'; '.join(errors)}")

