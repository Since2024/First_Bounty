"""Tests for extraction service."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from app.services.extraction_service import ExtractionService
from app.utils import load_template_file


@pytest.fixture(autouse=True)
def _clear_cache_each_test():
    from app.utils.cache import clear_cache
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def sample_template():
    """Load a sample template for testing."""
    try:
        return load_template_file("sampati_tax_page1_front.json")
    except Exception:
        # Fallback to a minimal template if file doesn't exist
        return {
            "fields": [
                {"id": "f001", "name": "Test Field", "type": "text"}
            ]
        }


@pytest.fixture
def mock_image_file():
    """Create a mock image file object."""
    mock_file = Mock()
    mock_file.getvalue.return_value = b"fake_image_data"
    mock_file.name = "test_image.jpg"
    return mock_file


@pytest.fixture
def sample_images(mock_image_file):
    """Return list of mock image files."""
    return [mock_image_file, mock_image_file]


def test_extraction_caching(sample_images, sample_template):
    """Test that caching works correctly."""
    # Clear cache first
    from app.utils.cache import clear_cache
    clear_cache()
    
    # First extraction - should hit API
    with patch('app.services.extraction_service.extract_fields_from_images') as mock_extract:
        mock_extract.return_value = {"f001": {"value": "test", "confidence": 0.9}}
        
        result1, engine1, _ = ExtractionService.extract_from_files(
            sample_images,
            sample_template
        )
        
        assert engine1 in ["gemini", "ocr"]  # Should not be cached
        assert mock_extract.called
    
    # Second extraction should use cache
    result2, engine2, _ = ExtractionService.extract_from_files(
        sample_images,
        sample_template
    )
    
    assert engine2 == "cached"
    assert result1 == result2


def test_extraction_with_gemini_success(sample_images, sample_template):
    """Test successful Gemini extraction."""
    with patch('app.services.extraction_service.extract_fields_from_images') as mock_extract:
        expected_result = {"f001": {"value": "test", "confidence": 0.9}}
        mock_extract.return_value = expected_result
        
        result, engine, errors = ExtractionService.extract_from_files(
            sample_images,
            sample_template
        )
        
        assert engine == "gemini"
        assert result == expected_result
        assert errors == []
        assert mock_extract.called


def test_extraction_with_gemini_fallback_to_ocr(sample_images, sample_template):
    """Test Gemini failure falls back to OCR."""
    from app.gemini import GeminiExtractionError
    
    with patch('app.services.extraction_service.extract_fields_from_images') as mock_gemini:
        with patch('app.services.extraction_service.extract_fields_from_multiple_images') as mock_ocr:
            mock_gemini.side_effect = GeminiExtractionError("Gemini failed")
            mock_ocr.return_value = {"f001": {"value": "ocr_result", "confidence": 0.8}}
            
            result, engine, errors = ExtractionService.extract_from_files(
                sample_images,
                sample_template
            )
            
            assert engine == "ocr"
            assert result == {"f001": {"value": "ocr_result", "confidence": 0.8}}
            assert len(errors) > 0
            assert "Gemini failed" in errors[0]


def test_extraction_all_methods_fail(sample_images, sample_template):
    """Test that exception is raised when all methods fail."""
    from app.gemini import GeminiExtractionError
    from app.ocr import OCRFallbackError
    
    with patch('app.services.extraction_service.extract_fields_from_images') as mock_gemini:
        with patch('app.services.extraction_service.extract_fields_from_multiple_images') as mock_ocr:
            mock_gemini.side_effect = GeminiExtractionError("Gemini failed")
            mock_ocr.side_effect = OCRFallbackError("OCR failed")
            
            with pytest.raises(RuntimeError) as exc_info:
                ExtractionService.extract_from_files(
                    sample_images,
                    sample_template
                )
            
            assert "All extraction methods failed" in str(exc_info.value)

