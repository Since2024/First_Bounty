"""Simple file-based cache for extraction results."""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from app import data_dir
from app.utils import get_logger

logger = get_logger(__name__)

CACHE_DIR = data_dir() / ".cache"
CACHE_TTL_HOURS = 24


def _get_cache_key(image_hashes: List[str], template_hash: str) -> str:
    """Generate cache key from image and template hashes."""
    combined = "".join(sorted(image_hashes)) + template_hash
    return hashlib.sha256(combined.encode()).hexdigest()


def get_cached_extraction(
    image_hashes: List[str],
    template_hash: str,
    engine_filter: Optional[str] = None
) -> Optional[Dict]:
    """
    Retrieve cached extraction if available and fresh.
    
    Args:
        image_hashes: List of image hash strings
        template_hash: Template hash string
        engine_filter: If provided, only return cache if it matches this engine ('gemini' or 'ocr')
    
    Returns:
        Cached extraction dict or None
    """
    cache_key = _get_cache_key(image_hashes, template_hash)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        # Check TTL
        cached_at = datetime.fromisoformat(data['cached_at'])
        age = datetime.now() - cached_at
        
        if age > timedelta(hours=CACHE_TTL_HOURS):
            logger.debug("Cache expired for key %s (age: %s)", cache_key[:16], age)
            cache_file.unlink()
            return None
        
        # Filter by engine if specified
        cached_engine = data.get('engine', 'unknown')
        if engine_filter and cached_engine != engine_filter:
            logger.debug(
                "Cache engine mismatch: cached=%s, requested=%s (skipping cache)",
                cached_engine,
                engine_filter
            )
            return None
        
        logger.info("Cache hit for key %s (engine: %s)", cache_key[:16], cached_engine)
        return data['extraction']
        
    except Exception as e:
        logger.warning("Error reading cache: %s", e)
        cache_file.unlink(missing_ok=True)
        return None


def set_cached_extraction(
    image_hashes: List[str],
    template_hash: str,
    extraction: Dict,
    engine: str = "unknown"
) -> None:
    """
    Store extraction result in cache.
    
    Args:
        image_hashes: List of image hash strings
        template_hash: Template hash string
        extraction: Extraction result dict
        engine: Engine used ('gemini', 'ocr', etc.)
    """
    cache_key = _get_cache_key(image_hashes, template_hash)
    CACHE_DIR.mkdir(exist_ok=True, parents=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    try:
        data = {
            'cached_at': datetime.now().isoformat(),
            'extraction': extraction,
            'image_hashes': image_hashes,
            'template_hash': template_hash,
            'engine': engine,
        }
        
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info("Cached extraction for key %s (engine: %s)", cache_key[:16], engine)
        
    except Exception as e:
        logger.warning("Error writing cache: %s", e)


def clear_cache() -> int:
    """Clear all cached extractions. Returns number of files deleted."""
    if not CACHE_DIR.exists():
        return 0
    
    count = 0
    for cache_file in CACHE_DIR.glob("*.json"):
        try:
            cache_file.unlink()
            count += 1
        except Exception as e:
            logger.warning("Error deleting cache file %s: %s", cache_file, e)
    
    logger.info("Cleared %d cache files", count)
    return count

