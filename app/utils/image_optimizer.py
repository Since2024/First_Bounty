"""Image optimization for faster API calls."""

from PIL import Image
import io
import hashlib
from typing import Tuple


def optimize_image_for_api(
    image_bytes: bytes,
    max_dimension: int = 2048,
    quality: int = 85
) -> Tuple[bytes, dict]:
    """
    Optimize image for Gemini API.
    
    Returns:
        (optimized_bytes, metadata dict with original_size, new_size, hash)
    """
    original_size = len(image_bytes)
    img_hash = hashlib.sha256(image_bytes).hexdigest()[:16]
    
    img = Image.open(io.BytesIO(image_bytes))
    original_format = img.format or 'JPEG'
    
    # Convert RGBA to RGB if needed
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background
    
    # Resize if too large
    if max(img.size) > max_dimension:
        ratio = max_dimension / max(img.size)
        new_size = tuple(int(dim * ratio) for dim in img.size)
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Compress
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    optimized_bytes = output.getvalue()
    
    metadata = {
        'hash': img_hash,
        'original_size': original_size,
        'optimized_size': len(optimized_bytes),
        'compression_ratio': original_size / len(optimized_bytes),
        'dimensions': img.size
    }
    
    return optimized_bytes, metadata

