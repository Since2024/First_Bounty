# FOMO – Gemini-powered Nepali Form Extractor

Minimal MVP that turns batches of Nepali government forms into structured JSON, filled PDFs, and database records. Gemini Vision handles semantic extraction, OCR provides a local fallback, ReportLab renders the output, and both CLI + Streamlit UI share the same pipeline.

## Highlights

- **Gemini Vision 1.5 Flash** for semantic mapping (`app/gemini/extractor.py`).
- **OCR fallback** (Tesseract/OpenCV) whenever Gemini is unavailable.
- **Template-driven normalization** in `app/filler/form_filler.py`.
- **ReportLab + Noto Sans Devanagari** PDF generator with simple style hooks.
- **SQLAlchemy + MySQL/SQLite** persistence via `app/db` (MySQL optional, SQLite default).
- **User Profile System** for saving and reusing extracted data across form submissions.
- **One CLI + Streamlit UI** calling the same core functions.

Repository layout (only the files that remain after cleanup):

```
app/
  gemini/         # Gemini Vision wrapper
  filler/         # Value normalization
  printer/        # PDF generation
  ocr/            # Lightweight OCR fallback
  utils/          # Template helpers + logging
  db/             # SQLAlchemy models + session helpers
  templates/      # JSON templates + reference images
  frontend/       # Streamlit UI
main.py           # CLI entry point
requirements.txt
README.md
```

Run artifacts (JSON/PDF) are written to `./artifacts/` automatically.

## Prerequisites

- Python 3.11+ (tested on 3.13).
- Tesseract with Nepali data: `sudo pacman -S tesseract tesseract-data-nep`.
- MySQL 8+ (or skip and let SQLite handle local testing).
- GOOGLE API access: set `GEMINI_API_KEY`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export GEMINI_API_KEY=xxxxxxxxxxxxxxxx
export MYSQL_HOST=localhost      # optional, SQLite used when unset
export MYSQL_USER=formfill
export MYSQL_PASSWORD=secret
export MYSQL_DB=firstchild
```

The database tables are created automatically the first time you run the CLI/UI.

**Database Selection:**
- If `MYSQL_HOST` (or `DB_HOST`) is set, MySQL will be used.
- If `DATABASE_URL` is set, it takes precedence over other settings.
- Otherwise, SQLite is used as the default (stored in `artifacts/fomo.sqlite3`).

## CLI – Multi-image extraction

```
python main.py extract \
  --images input/sample/id.jpg input/sample/sample_business_tax.png \
  --template business_tax_front.json \
  --output-name demo_business
```

What happens:

1. Every image is passed to Gemini Vision along with the template schema.
2. If Gemini fails, the first image runs through the OCR fallback.
3. Output JSON + filled PDF land in `artifacts/demo_business.(json|pdf)`.
4. A `form_submissions` row stores raw + normalized payload.

List templates at any time:

```
python main.py templates
```

## Streamlit UI

```
streamlit run app/frontend/ui.py
```

Capabilities:

- **User Profile Management:**
  - Enter your email in the sidebar to create/load your profile.
  - Auto-fill forms from saved profile data with one click.
  - Save extracted data to your profile for future use.
  - View your submission statistics.
- Drag/drop multiple images.
- Live preview and Gemini extraction with OCR fallback.
- Review and edit extracted data before PDF generation.
- Generate PDF + save to DB with one click.

## Database Models

The application uses two main database models:

- **`FormSubmission`**: Stores completed form extractions with raw JSON, normalized fields, and generated PDF paths.
- **`UserProfile`**: Stores reusable user data (name, address, contact info, business details) for auto-filling future forms.

Both tables are created automatically on first run.

## Environment Variables

| Name             | Description                                      |
| ---------------- | ------------------------------------------------ |
| `GEMINI_API_KEY` | Required. Google Generative AI key               |
| `GEMINI_MODEL`   | Optional. Defaults to `gemini-1.5-flash`         |
| `DATABASE_URL`   | Optional full SQLAlchemy URL (overrides all other DB settings) |
| `MYSQL_HOST`     | Optional. MySQL hostname (or use `DB_HOST`)      |
| `MYSQL_USER`     | Optional. MySQL username (or use `DB_USER`, defaults to `root`) |
| `MYSQL_PASSWORD` | Optional. MySQL password (or use `DB_PASSWORD`) |
| `MYSQL_DB`       | Optional. MySQL database name (or use `DB_NAME`, defaults to `fomo`) |
| `MYSQL_PORT`     | Optional. MySQL port (or use `DB_PORT`, defaults to `3306`) |
| `SQLITE_PATH`    | Optional path for SQLite database (defaults to `artifacts/fomo.sqlite3`) |
| `LOG_LEVEL`      | INFO by default                                  |

## Tests

A single smoke test (`app/utils/smoke_test.py`) covers the CLI wiring. Run with:

```
pytest app/utils/smoke_test.py
```

## Troubleshooting

- **Missing template background**: add `metadata.image_filename` inside the template JSON and place the referenced image under `app/templates/`.
- **Gemini quota or auth errors**: confirm `GEMINI_API_KEY` and check Google Cloud quotas.
- **ReportLab font download blocked**: manually download `NotoSansDevanagari-Regular.ttf` into `app/printer/fonts/`.
- **MySQL unavailable**: omit the MySQL env vars and SQLite will be used automatically.

## License

MIT (see repository root if provided).
