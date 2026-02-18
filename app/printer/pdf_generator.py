"""Generate PDFs by overlaying text on template images."""

from __future__ import annotations

import urllib.request
from pathlib import Path
import re
from typing import Dict, List

from PIL import Image
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import uuid

from app.utils import get_logger

logger = get_logger(__name__)

FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT_PATH = FONT_DIR / "NotoSansDevanagari-Regular.ttf"
FONT_URL = (
    "https://github.com/googlefonts/noto-fonts/raw/main/"
    "unhinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf"
)
FONT_NAME = "NotoSansDevanagari"


def _ensure_font():
    if not FONT_PATH.exists():
        FONT_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading Noto Sans Devanagari font")
        urllib.request.urlretrieve(FONT_URL, FONT_PATH)
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def _apply_style(value: str, style) -> str:
    if isinstance(style, str) and style.lower() == "uppercase":
        return value.upper()
    if isinstance(style, dict) and style.get("uppercase"):
        return value.upper()
    return value


def create_filled_pdf(
    template_image: str,
    fields: List[Dict],
    output_path: str,
) -> tuple[str, str]:
    """Create a PDF with fields overlaid on background image.
    
    Returns:
        tuple[str, str]: (output_path, document_uuid)
    """
    
    if not fields:
        raise ValueError("No fields provided for PDF generation")
    
    # Load background
    bg = Image.open(template_image)
    bg_width, bg_height = bg.size
    
    # CRITICAL: Check if we need to scale coordinates
    # Template expects 847x1197, but actual image might be different
    TEMPLATE_WIDTH = 847
    TEMPLATE_HEIGHT = 1197
    
    scale_x = bg_width / TEMPLATE_WIDTH
    scale_y = bg_height / TEMPLATE_HEIGHT
    
    logger.info(f"Creating PDF: {output_path}")
    logger.info(f"Background: {bg_width}x{bg_height}px")
    logger.info(f"Template expects: {TEMPLATE_WIDTH}x{TEMPLATE_HEIGHT}px")
    logger.info(f"Scale factors: x={scale_x:.2f}, y={scale_y:.2f}")
    logger.info(f"Fields to render: {len(fields)}")
    
    # Generate Unique Document ID
    doc_uuid = str(uuid.uuid4())
    logger.info(f"Generated Document UUID: {doc_uuid}")

    # Create PDF with FIXED metadata for determinism
    # ReportLab embeds a creation timestamp DEEP inside the PDF stream.
    # We must patch the internal _doc.info object AFTER canvas creation.
    c = canvas.Canvas(
        output_path, 
        pagesize=(bg_width, bg_height),
        pageCompression=0  # Disable compression for byte-level debugging
    )
    
    # Force metadata to be constant (surface-level setters)
    c.setTitle("FOMO Verified Form")
    c.setAuthor("FOMO AI")
    c.setSubject(f"UUID:{doc_uuid}")  # Embed UUID in Subject field
    c.setKeywords(f"FOMO, Verified, Document, {doc_uuid}")
    
    # CRITICAL: Patch the internal PDF info dictionary to fix the timestamp.
    # ReportLab stores creation/modification dates in c._doc.info as a PDFDate object.
    # We override them with a fixed string in PDF date format: D:YYYYMMDDHHmmSS
    FIXED_PDF_DATE = "D:20250101000000+00'00'"
    try:
        from reportlab.pdfbase.pdfdoc import PDFDate, PDFString
        # The info dict keys are 'CreationDate' and 'ModDate'
        c._doc.info.CreationDate = PDFDate(FIXED_PDF_DATE)
        c._doc.info.ModDate = PDFDate(FIXED_PDF_DATE)
        logger.info("✅ PDF timestamps patched to fixed date for determinism.")
    except Exception as e:
        # Fallback: try direct string assignment
        logger.warning(f"PDFDate patch failed ({e}), trying string fallback.")
        try:
            c._doc.info.CreationDate = FIXED_PDF_DATE
            c._doc.info.ModDate = FIXED_PDF_DATE
        except Exception as e2:
            logger.error(f"Could not patch PDF date: {e2}")


    c.drawImage(template_image, 0, 0, width=bg_width, height=bg_height)
    
    # Register Nepali font
    nep_font_path = Path(__file__).parent / "fonts" / "NotoSansDevanagari-Regular.ttf"
    has_noto = False
    if nep_font_path.exists():
        _ensure_font()
        has_noto = True
        logger.info("Nepali font available: NotoSansDevanagari")
    else:
        logger.warning(f"Nepali font not found at {nep_font_path}, using Helvetica for all text")
    
    # Helper function to detect Devanagari characters
    def _has_devanagari(text: str) -> bool:
        """Check if text contains Devanagari (Nepali) characters."""
        return any('\u0900' <= char <= '\u097F' for char in text)
    
    # Process each field
    for field in fields:
        fid = field.get("id", "unknown")
        value = field.get("value", "")
        bbox_px = field.get("bbox_px")
        field_name = field.get("name", fid)
        field_type = field.get("type", "text_line")

        if not bbox_px or len(bbox_px) != 4:
            logger.warning(f"Field {fid}: Invalid bbox")
            continue

        if not value or not value.strip():
            continue

        # Get template coordinates
        x_template, y_template, w_template, h_template = map(int, bbox_px)

        # SCALE coordinates to actual image size
        x = int(x_template * scale_x)
        y = int(y_template * scale_y)
        w = int(w_template * scale_x)
        h = int(h_template * scale_y)

        # Calculate font size
        font_size = max(14, int(h * 0.70))
        font_size = min(font_size, 48)

        # Convert to PDF coordinates
        pdf_y = bg_height - y - h

        # Set color
        c.setFillColor(colors.black)

        # Handle box_grid fields differently
        if field_type == "box_grid":
            # Box grid always uses Helvetica for digits
            c.setFont('Helvetica', font_size)
            
            # Get grid configuration from field
            grid_config = field.get("grid", {})
            num_boxes = grid_config.get("boxes", 5)

            # Clean value - only digits
            digits = re.sub(r"\D", "", value)

            # Calculate box spacing
            box_width = w / num_boxes

            # Draw each digit in its own box
            for i, digit in enumerate(digits[:num_boxes]):
                digit_x = x + (i * box_width) + (box_width * 0.25)  # Center in box
                text_offset_y = (h - font_size) / 2 + font_size * 0.25
                final_y = pdf_y + text_offset_y

                c.drawString(digit_x, final_y, digit)

            logger.info(f"{fid}: '{value}' → split into {len(digits)} boxes (font=Helvetica)")

        else:
            # Regular text field - choose font based on content
            if has_noto and _has_devanagari(value):
                font_name = FONT_NAME
            else:
                font_name = 'Helvetica'  # Use Helvetica for English/numbers
            
            c.setFont(font_name, font_size)
            
            value = _apply_style(str(value), field.get("style"))
            text_offset_y = (h - font_size) / 2 + font_size * 0.25
            final_y = pdf_y + text_offset_y
            final_x = x + 5

            c.drawString(final_x, final_y, value)

            logger.info(f"{fid}: '{value}' at x={final_x:.1f}, y={final_y:.1f} (font={font_name})")
    
    c.save()
    logger.info(f"✓ PDF saved: {output_path}")
    
    # ============================================================
    # NUCLEAR FALLBACK: Post-save byte-level timestamp scrubbing
    # ============================================================
    # Even with metadata patching, ReportLab may embed the current
    # timestamp in the raw PDF stream as a comment or xref entry.
    # We scrub it out by replacing any D:YYYYMMDD... pattern with a fixed one.
    import re
    try:
        raw = Path(output_path).read_bytes()
        # PDF date format: D:20250118143022+05'45' or D:20250118143022Z
        # Replace ALL occurrences with a fixed date
        scrubbed = re.sub(
            rb"D:\d{14}[Z+\-][0-9']{0,6}",
            b"D:20250101000000+00'00'",
            raw
        )
        if scrubbed != raw:
            Path(output_path).write_bytes(scrubbed)
            logger.info("✅ Post-save: Dynamic timestamps scrubbed from PDF bytes.")
        else:
            logger.info("ℹ️ Post-save: No dynamic timestamps found in PDF bytes.")
    except Exception as e:
        logger.error(f"Post-save scrubbing failed: {e}")
    
    return output_path, doc_uuid


__all__ = ["create_filled_pdf"]

