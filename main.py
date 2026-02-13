#!/usr/bin/env python3
"""CLI entry point for the FirstChild minimal MVP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Sequence

from app import data_dir
from app.db import FormSubmission, get_session, init_db
from app.filler import prepare_pdf_fields
from app.gemini import GeminiExtractionError, extract_fields_from_images
from app.ocr import OCRFallbackError, extract_fields_with_ocr
from app.printer import create_filled_pdf
from app.utils import (
    get_logger,
    list_template_files,
    load_template_file,
    template_image_path,
)

logger = get_logger(__name__)

init_db()


def _read_image_bytes(paths: Sequence[Path]) -> List[bytes]:
    return [path.read_bytes() for path in paths]


def _run_pipeline(image_paths: Sequence[Path], template: dict) -> tuple[dict, str]:
    images = _read_image_bytes(image_paths)
    try:
        data = extract_fields_from_images(images, template)
        return data, "gemini"
    except GeminiExtractionError as exc:
        logger.error("Gemini extraction failed: %s", exc)
        try:
            data = extract_fields_with_ocr(str(image_paths[0]), template)
            return data, "ocr"
        except OCRFallbackError as fallback_exc:
            raise RuntimeError("Both Gemini and OCR extraction failed") from fallback_exc


def cmd_list_templates(_args: argparse.Namespace) -> int:
    files = list_template_files()
    if not files:
        print("No templates found in app/templates")
        return 1
    for path in files:
        print(path.name)
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    template = load_template_file(args.template)
    image_paths = [Path(p) for p in args.images]
    for path in image_paths:
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

    extraction, engine = _run_pipeline(image_paths, template)
    pdf_fields = prepare_pdf_fields(extraction, template)
    if not pdf_fields:
        raise RuntimeError("No fields available for PDF output")

    template_img = template_image_path(template)
    background = template_img or image_paths[0]

    artifacts = data_dir()
    base_name = args.output_name or f"{Path(args.template).stem}_{image_paths[0].stem}"
    pdf_path = artifacts / f"{base_name}.pdf"
    json_path = artifacts / f"{base_name}.json"

    create_filled_pdf(str(background), pdf_fields, str(pdf_path))
    json_path.write_text(
        json.dumps(extraction, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if template.get("forms"):
        template_name = template["forms"][0].get("name", Path(args.template).stem)
    else:
        template_name = template.get("name", Path(args.template).stem)

    with get_session() as session:
        submission = FormSubmission(
            template_name=template_name,
            template_file=Path(args.template).name,
            pdf_path=str(pdf_path),
            gemini_json=json.dumps(extraction, ensure_ascii=False),
            normalized_fields=json.dumps(pdf_fields, ensure_ascii=False),
        )
        session.add(submission)

    print("Extraction complete 🎉")
    print(f"Engine     : {engine}")
    print(f"JSON output: {json_path}")
    print(f"PDF output : {pdf_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FirstChild extraction CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    extract = sub.add_parser("extract", help="Run Gemini extraction on images")
    extract.add_argument(
        "--images",
        nargs="+",
        required=True,
        help="Paths to input images (multi-page supported)",
    )
    extract.add_argument(
        "--template",
        required=True,
        help="Template JSON filename inside app/templates",
    )
    extract.add_argument(
        "--output-name",
        help="Base filename for generated JSON/PDF (defaults to template+image stem)",
    )
    extract.set_defaults(func=cmd_extract)

    templates = sub.add_parser("templates", help="List available templates")
    templates.set_defaults(func=cmd_list_templates)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
