"""Quick standalone sanity-check for the Gemini extractor."""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

from app.gemini import GeminiExtractionError, extract_fields_from_images  # noqa: E402
from app.gemini.extractor import MODEL_NAME  # noqa: E402
from app.utils import load_template_file  # noqa: E402

SAMPLE_TEMPLATE = "sampati_tax_page1_front.json"
# 1x1 white JPEG
SAMPLE_IMAGE_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABALDA4MChAODQ4RERATGBcUGBcaHBcYGhkdGh0dHB0d"
    "IC4mICIrKy0xNDQ0HiQ/Okc9PUE+TD84Q0JHSktLPjJCSD7/2wBDAQ0NDhgQEB0RER0+LjouPj4+"
    "Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj7/wAARCAABAAED"
    "ASIAAhEBAxEB/8QAFwABAQEBAAAAAAAAAAAAAAAAAwABBP/EABcBAQEBAQAAAAAAAAAAAAAAAAAB"
    "AwT/2gAMAwEAAhADEAAAAd0H/8QAFhEBAQEAAAAAAAAAAAAAAAAAABES/9oACAEBAAEFAuH/xAAW"
    "EQEBAQAAAAAAAAAAAAAAAAABABH/2gAIAQMBAT8Bw//EABYRAQEBAAAAAAAAAAAAAAAAAAABEf/a"
    "AAgBAgEBPwGr/8QAGhABAAMBAQEAAAAAAAAAAAAAAAERMUEhMf/aAAgBAQAGPwINcmVeY//EABsQ"
    "AAEFAQEAAAAAAAAAAAAAAAABEQISITFB/9oACAEBAAE/IaFRJVjV+ZJ2xuTZP//aAAwDAQACAAMAAA"
    "AAAAAAAAAEEf/EABYRAQEBAAAAAAAAAAAAAAAAAAEQEf/aAAgBAwEBPxCj/8QAFhEBAQEAAAAAAAAA"
    "AAAAAAAAABEB/9oACAECAQE/EH//xAAcEAEBAAMAAwEAAAAAAAAAAAAAAREhMUFhofD/2gAIAQEA"
    "AT8Qtxi0zA4LgdSnLJQO84nhLJGGWs4SyRh//Z"
)


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"[env] GEMINI_API_KEY present: {bool(api_key)}")
    if not api_key:
        print("[error] GEMINI_API_KEY is missing")
        sys.exit(1)

    template = load_template_file(SAMPLE_TEMPLATE)
    image_bytes = base64.b64decode(SAMPLE_IMAGE_B64)

    print(f"[info] Invoking Gemini extractor ({MODEL_NAME})...")
    start = time.perf_counter()
    try:
        extraction = extract_fields_from_images([image_bytes], template)
    except GeminiExtractionError as exc:
        elapsed = time.perf_counter() - start
        print(f"[error] Gemini extraction failed after {elapsed:.2f}s: {exc}")
        sys.exit(2)

    elapsed = time.perf_counter() - start
    print(f"[ok] Extraction succeeded in {elapsed:.2f}s | fields={len(extraction)}")
    print(json.dumps(extraction, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
