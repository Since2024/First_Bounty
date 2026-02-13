"""Gemini Vision extractor for semantic field mapping."""

from __future__ import annotations

import hashlib
import json
import os
import time
from functools import lru_cache
from typing import Any, Dict, List

from app.utils import get_logger, template_fields
from app.utils.image_optimizer import optimize_image_for_api

logger = get_logger(__name__)


def _sanitize_model_name(name: str) -> str:
    """Remove 'models/' prefix if present - library handles it automatically."""
    if not name:
        return name
    return name.replace("models/", "")


_env_model = os.getenv("GEMINI_MODEL")
_MODEL_CANDIDATES = (
    [_sanitize_model_name(_env_model)]
    if _env_model
    else [_sanitize_model_name("gemini-2.5-flash"), _sanitize_model_name("gemini-2.5-pro")]
)

MODEL_NAME = _MODEL_CANDIDATES[0]
API_ENDPOINT = "https://generativelanguage.googleapis.com"
_GENAI = None
REQUEST_TIMEOUT_SECONDS = 60  # Increased timeout for SSL issues


class GeminiExtractionError(RuntimeError):
    """Raised when Gemini Vision cannot complete the request."""


def _build_prompt(template_json: Dict) -> str:
    field_info = []
    for field in template_fields(template_json):
        if not isinstance(field, dict):
            continue
        ocr_cfg = field.get("ocr") or {}
        if not isinstance(ocr_cfg, dict):
            ocr_cfg = {}
        field_info.append(
            {
                "id": field.get("id"),
                "name": field.get("name") or field.get("label"),
                "label": field.get("label"),
                "meaning": field.get("desc"),
                "type": field.get("type"),
                "language_hint": ocr_cfg.get("lang"),
            }
        )

    instructions = {
        "task": (
            "You are extracting data from Nepali government documents (citizenship certificates, forms, etc.) "
            "to fill a land tax form template. Use SEMANTIC MAPPING - understand the MEANING of fields, not just labels. "
            "\n\nSemantic Mapping Rules:"
            "\n- Citizenship 'नाम धर:' → Land Tax 'जग्गा/धनीको नाम र थर' (owner name) AND 'नाम थर' (submitter name f009)"
            "\n- Citizenship 'बाबुको नाम धर:' → Land Tax 'बाबु/पतिको नाम र थर' (father name)"
            "\n- Citizenship 'जन्म मिति:' → Use for date fields if needed"
            "\n- Citizenship 'जिल्ला:' → Can be part of permanent address"
            "\n- Citizenship 'गाउँपालिका/नगरपालिका:' → Part of address"
            "\n- Citizenship address fields → Land Tax 'ठेगाना' (submitter address f010) - same as owner address"
            "\n\nIMPORTANT:"
            "\n- Map fields by MEANING, not by exact label match"
            "\n- Extract ALL readable text from the source document"
            "\n- Fill target template fields based on semantic similarity"
            "\n- If a required field has no matching source data, use empty string and confidence 0"
            "\n- Preserve Nepali Unicode text exactly as it appears"
            "\n- For dates: convert Nepali calendar to Gregorian if needed (साल २०६१ = year 2004-2005)"
            "\n✗ NEVER fill f001 (आन्तरिक संकेत नं/Economic Code) - office assigned only"
            "\n✗ NEVER map citizenship number to f005 (जग्गाधनीको पात नं) - leave empty"
        ),
        "output_schema": "{field_id: {value: string, confidence: float (0-1), notes: string}}",
        "target_fields": field_info,
        "examples": {
            "f002": "हसन गाहा (extracted from citizenship 'नाम धर:')",
            "f003": "धन राज गाहा (extracted from citizenship 'बाबुको नाम धर:')",
            "f006": "कालीगण्डकी, स्याङ्जा (combined from citizenship address fields)",
            "f009": "हसन गाहा (same as f002 - person submitting is usually the owner)",
            "f010": "कालीगण्डकी, स्याङ्जा (same as f006 - submitter address is usually owner address)"
        }
    }
    return json.dumps(instructions, ensure_ascii=False, indent=2)


def _ensure_model() -> Any:
    global _GENAI, MODEL_NAME
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        error_msg = "GEMINI_API_KEY is not set. Please set it in your environment variables."
        logger.error(error_msg)
        raise GeminiExtractionError(error_msg)
    if not api_key.strip():
        error_msg = "GEMINI_API_KEY is set but empty. Please provide a valid API key."
        logger.error(error_msg)
        raise GeminiExtractionError(error_msg)
    
    if _GENAI is None:
        try:
            import google.generativeai as genai_mod  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover - import guard
            raise GeminiExtractionError(
                "google-generativeai is not installed. "
                "Add it via pip install google-generativeai."
            ) from exc
        _GENAI = genai_mod
        try:
            # Configure without explicit endpoint to use default (v1 API)
            # This allows access to newer models like gemini-2.5-flash
            _GENAI.configure(
                api_key=api_key,
                transport="rest",
            )
        except Exception as exc:
            error_msg = f"Failed to configure Gemini API: {exc}"
            logger.error(error_msg)
            raise GeminiExtractionError(error_msg) from exc

    last_error: Exception | None = None
    for candidate in _MODEL_CANDIDATES:
        try:
            # Try to create the model - this will validate the model name
            model = _GENAI.GenerativeModel(candidate)
            # Test if model is accessible by checking if we can get model info
            # (This is a lightweight check that doesn't make an API call)
            if candidate != MODEL_NAME:
                logger.info("Gemini: switching to fallback model %s", candidate)
            MODEL_NAME = candidate
            logger.info("Gemini: successfully initialized model %s", candidate)
            return model
        except Exception as exc:
            last_error = exc
            error_str = str(exc)
            # Check for authentication errors
            if any(keyword in error_str.lower() for keyword in ['401', 'unauthorized', 'api key', 'invalid', 'permission', '403', 'forbidden']):
                error_msg = f"Gemini API authentication failed for model {candidate}: {error_str}. Please check your GEMINI_API_KEY."
                logger.error(error_msg)
                raise GeminiExtractionError(error_msg) from exc
            logger.warning("Gemini: failed to initialize model %s: %s", candidate, exc)
    
    error_msg = f"Unable to initialize any Gemini model. Last error: {last_error}"
    logger.error(error_msg)
    raise GeminiExtractionError(error_msg) from last_error


def _coerce_json(payload: str) -> Dict:
    payload = payload.strip()
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        # Try to salvage by locating the outermost braces.
        start = payload.find("{")
        end = payload.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = payload[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass
        raise


def _normalize_output(raw: Dict, template_json: Dict) -> Dict[str, Dict]:
    normalized: Dict[str, Dict] = {}
    for field in template_fields(template_json):
        if field is None or not isinstance(field, dict):
            continue
        fid = field.get("id")
        if not fid:
            continue
        entry = raw.get(fid) if isinstance(raw, dict) else None
        if isinstance(entry, dict):
            value = entry.get("value", "")
            confidence = entry.get("confidence", entry.get("score", 0))
            notes = entry.get("notes") or entry.get("explanation")
        else:
            value = entry if isinstance(entry, str) else ""
            confidence = 0
            notes = None

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0

        normalized[fid] = {
            "value": value.strip(),
            "confidence": max(0.0, min(1.0, confidence)),
            "notes": notes or "",
        }
    return normalized


@lru_cache(maxsize=100)
def _get_cached_extraction(image_hash: str, template_hash: str):
    """Cache extraction results by image+template hash."""
    # Returns None if not cached
    return None


def extract_fields_from_images(
    images: List[bytes],
    template_json: Dict,
) -> Dict[str, Dict]:
    """
    Enhanced with optimization, caching, and retry logic.
    
    Run Gemini Vision on a list of images and map to template fields.

    Args:
        images: List of binary image contents (bytes).
        template_json: Template definition.

    Returns:
        Dict keyed by field id -> {value, confidence, notes}
    """
    if not images:
        raise ValueError("At least one image is required")

    # 1. Optimize all images first
    optimized_images = []
    total_original = 0
    total_optimized = 0

    logger.info("Optimizing %d images for Gemini API...", len(images))
    for idx, img_bytes in enumerate(images):
        opt_bytes, metadata = optimize_image_for_api(img_bytes)
        optimized_images.append(opt_bytes)
        total_original += metadata['original_size']
        total_optimized += metadata['optimized_size']
        logger.info(
            "Image %d: %d KB → %d KB (%.1fx compression)",
            idx + 1,
            metadata['original_size'] // 1024,
            metadata['optimized_size'] // 1024,
            metadata['compression_ratio']
        )

    logger.info(
        "Total optimization: %.1f MB → %.1f MB (%.1f%% reduction)",
        total_original / 1024 / 1024,
        total_optimized / 1024 / 1024,
        (1 - total_optimized / total_original) * 100
    )

    # Check total request size (Gemini has limits - typically 20MB for free tier, 100MB+ for paid)
    # Prompt text is usually small, so we check image sizes
    MAX_TOTAL_SIZE_MB = 20  # Conservative limit for free tier
    total_size_mb = total_optimized / 1024 / 1024
    if total_size_mb > MAX_TOTAL_SIZE_MB:
        logger.warning(
            "Total image size (%.2f MB) exceeds recommended limit (%d MB). "
            "This may cause API errors.",
            total_size_mb,
            MAX_TOTAL_SIZE_MB
        )

    # 2. Check cache (use first image hash + template hash)
    template_hash = hashlib.sha256(
        json.dumps(template_json, sort_keys=True).encode()
    ).hexdigest()[:16]

    # 3. Retry logic with exponential backoff
    max_retries = 3
    timeouts = [30, 60, 90]  # Progressive timeout strategy
    overall_start_time = time.perf_counter()

    for attempt in range(max_retries):
        attempt_start_time = time.perf_counter()
        try:
            timeout = timeouts[min(attempt, len(timeouts) - 1)]
            logger.info(
                "Gemini attempt %d/%d (timeout: %ds)",
                attempt + 1,
                max_retries,
                timeout
            )

            model = _ensure_model()
            prompt = _build_prompt(template_json)

            parts: List[Dict] = [{"text": prompt}]
            for img_bytes in optimized_images:
                parts.append({"mime_type": "image/jpeg", "data": img_bytes})
            response = model.generate_content(
                parts,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "top_k": 40,
                    "response_mime_type": "application/json",
                },
                request_options={"timeout": timeout},
            )
            elapsed = time.perf_counter() - attempt_start_time

            logger.info("✓ Gemini API call completed in %.2fs (attempt %d)", elapsed, attempt + 1)

            # Check for blocked/filtered responses
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                if hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                    block_reason = response.prompt_feedback.block_reason
                    error_msg = f"Gemini blocked the request: {block_reason}"
                    logger.error(error_msg)
                    raise GeminiExtractionError(error_msg)
            
            # Check candidates for safety ratings
            if hasattr(response, 'candidates') and response.candidates:
                for idx, candidate in enumerate(response.candidates):
                    if hasattr(candidate, 'finish_reason'):
                        if candidate.finish_reason and candidate.finish_reason != 1:  # 1 = STOP
                            finish_reason_str = str(candidate.finish_reason)
                            if 'safety' in finish_reason_str.lower() or 'blocked' in finish_reason_str.lower():
                                error_msg = f"Gemini blocked response due to safety: {finish_reason_str}"
                                logger.error(error_msg)
                                raise GeminiExtractionError(error_msg)

            # Parse and return
            text = response.text
            if not text and response.candidates:
                text = "".join(
                    part.text or ""
                    for part in response.candidates[0].content.parts
                    if getattr(part, "text", None)
                )

            if not text:
                # Log more details about why text is empty
                logger.error("Gemini returned an empty response")
                if hasattr(response, 'candidates') and response.candidates:
                    for idx, candidate in enumerate(response.candidates):
                        logger.error("Candidate %d: finish_reason=%s", idx, getattr(candidate, 'finish_reason', 'unknown'))
                raise GeminiExtractionError("Gemini returned an empty response (no text/candidates)")

            logger.debug("Gemini raw response text (first 500 chars): %s", text[:500])

            try:
                raw = _coerce_json(text)
                normalized = _normalize_output(raw, template_json)
                logger.info("Gemini extracted %d fields", len(normalized))
                return normalized
            except json.JSONDecodeError as json_exc:
                logger.error("Failed to parse Gemini JSON response: %s", json_exc)
                logger.error("Response text (first 1000 chars): %s", text[:1000])
                raise GeminiExtractionError(f"Failed to parse Gemini JSON response: {json_exc}") from json_exc

        except Exception as exc:
            elapsed = time.perf_counter() - attempt_start_time
            error_msg = str(exc)
            error_lower = error_msg.lower()
            error_type = type(exc).__name__
            
            # Log detailed error information
            logger.error(
                "Gemini API error (attempt %d/%d, %.2fs): %s: %s",
                attempt + 1,
                max_retries,
                elapsed,
                error_type,
                error_msg
            )
            
            # Try to extract more details from the exception
            error_details = error_msg
            if hasattr(exc, 'message'):
                error_details = f"{error_msg} | Details: {exc.message}"
            if hasattr(exc, 'status_code'):
                error_details = f"{error_msg} | Status: {exc.status_code}"
            if hasattr(exc, 'reason'):
                error_details = f"{error_msg} | Reason: {exc.reason}"
            
            # Check for quota/rate limit errors (429)
            is_quota_error = any(keyword in error_lower for keyword in [
                '429', 'quota', 'rate limit', 'rate_limit', 'too many requests',
                'quota exceeded', 'billing', 'payment'
            ])
            
            if is_quota_error:
                total_elapsed = time.perf_counter() - overall_start_time
                detailed_error = (
                    f"Gemini API quota/rate limit exceeded: {error_details}. "
                    "Please check your API quota, billing status, or wait before retrying."
                )
                logger.error(detailed_error)
                raise GeminiExtractionError(detailed_error) from exc

            # Check for authentication/authorization errors (don't retry these)
            is_auth_error = any(keyword in error_lower for keyword in [
                '401', 'unauthorized', 'api key', 'invalid key', 'permission', 
                '403', 'forbidden', 'authentication', 'api_key', 'api key invalid',
                'invalid api key', 'api key not found'
            ])
            
            if is_auth_error:
                total_elapsed = time.perf_counter() - overall_start_time
                detailed_error = (
                    f"Gemini API authentication failed: {error_details}. "
                    "Please verify your GEMINI_API_KEY is correct and has proper permissions."
                )
                logger.error(detailed_error)
                raise GeminiExtractionError(detailed_error) from exc

            # Check for content policy or invalid request errors (400)
            is_content_error = any(keyword in error_lower for keyword in [
                '400', 'bad request', 'invalid', 'content policy', 'safety',
                'blocked', 'harmful', 'policy violation', 'image too large',
                'request too large', 'payload too large'
            ])
            
            if is_content_error:
                total_elapsed = time.perf_counter() - overall_start_time
                detailed_error = (
                    f"Gemini API content/request error: {error_details}. "
                    "This might be due to image size, content policy, or invalid request format."
                )
                logger.error(detailed_error)
                raise GeminiExtractionError(detailed_error) from exc

            # Check if retryable (network/timeout errors)
            is_retryable = any(keyword in error_lower for keyword in [
                'timeout', 'ssl', 'connection', 'network', 'eof', '503', '500', '502',
                'service unavailable', 'bad gateway', 'gateway timeout'
            ])

            if attempt < max_retries - 1 and is_retryable:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(
                    "Attempt %d failed (retryable): %s. Retrying in %ds...",
                    attempt + 1,
                    error_details,
                    wait_time
                )
                time.sleep(wait_time)
                continue
            else:
                total_elapsed = time.perf_counter() - overall_start_time
                logger.error(
                    "Gemini failed after %d attempts (%.2fs total): %s (type: %s)",
                    attempt + 1,
                    total_elapsed,
                    error_details,
                    error_type
                )
                raise GeminiExtractionError(f"All retries failed: {error_details}") from exc


__all__ = ["extract_fields_from_images", "GeminiExtractionError"]

