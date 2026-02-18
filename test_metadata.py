
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfdoc import PDFInfo
from pathlib import Path
import sys

def test_metadata():
    output_path = "test_metadata.pdf"
    c = canvas.Canvas(output_path)
    c.drawString(100, 750, "Hello World")
    
    # Try adding custom metadata
    # The standard way in ReportLab to add custom info is via the SetInfo/info argument
    # or by accessing the implementation details.
    
    # Official way usually maps specific keys.
    # Let's try injecting a custom key.
    
    c.setTitle("Test Title")
    c.setAuthor("Test Author")
    
    # Accessing the internal info object
    c._doc.info.CustomUUID = "12345-67890-UUID"
    
    c.save()
    print(f"Saved {output_path}")
    
    # Read it back to verify
    raw = Path(output_path).read_bytes()
    if b"12345-67890-UUID" in raw:
        print("SUCCESS: Custom UUID found in PDF bytes")
    else:
        print("FAILURE: Custom UUID NOT found in PDF bytes")

if __name__ == "__main__":
    test_metadata()
