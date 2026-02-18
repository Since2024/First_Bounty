"""One-time migration system - runs only once per migration."""

from pathlib import Path
from sqlalchemy import text
from app.utils import get_logger

logger = get_logger(__name__)

MIGRATIONS_COMPLETED_FILE = Path("artifacts/.migrations_completed")


def mark_migration_complete(migration_name: str):
    """Mark a migration as completed."""
    MIGRATIONS_COMPLETED_FILE.parent.mkdir(exist_ok=True, parents=True)
    with open(MIGRATIONS_COMPLETED_FILE, 'a') as f:
        f.write(f"{migration_name}\n")


def is_migration_complete(migration_name: str) -> bool:
    """Check if migration was already run."""
    if not MIGRATIONS_COMPLETED_FILE.exists():
        return False
    
    with open(MIGRATIONS_COMPLETED_FILE, 'r') as f:
        completed = f.read().splitlines()
    
    return migration_name in completed


def run_migrations(engine, database_url: str):
    """Run all pending migrations once."""
    
    # Migration 1: Add password_hash to user_profiles
    migration_name = "add_password_hash_column"
    if not is_migration_complete(migration_name):
        logger.info("Running migration: %s", migration_name)
        try:
            with engine.connect() as conn:
                if database_url.startswith("sqlite"):
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_profiles'"
                    ))
                    if result.fetchone():
                        result = conn.execute(text("PRAGMA table_info(user_profiles)"))
                        columns = [row[1] for row in result.fetchall()]
                        if "password_hash" not in columns:
                            conn.execute(text("ALTER TABLE user_profiles ADD COLUMN password_hash VARCHAR(255)"))
                            conn.commit()
                            logger.info("✓ Added password_hash column")
                else:
                    # MySQL
                    result = conn.execute(text(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_NAME = 'user_profiles' AND COLUMN_NAME = 'password_hash'"
                    ))
                    if not result.fetchone():
                        conn.execute(text("ALTER TABLE user_profiles ADD COLUMN password_hash VARCHAR(255)"))
                        conn.commit()
                        logger.info("✓ Added password_hash column")
            
            mark_migration_complete(migration_name)
        except Exception as e:
            logger.error("Migration failed: %s", e)
            raise
    
    # Migration 2: Add user_email to form_submissions
    migration_name = "add_user_email_to_submissions"
    if not is_migration_complete(migration_name):
        logger.info("Running migration: %s", migration_name)
        try:
            with engine.connect() as conn:
                if database_url.startswith("sqlite"):
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='form_submissions'"
                    ))
                    if result.fetchone():
                        result = conn.execute(text("PRAGMA table_info(form_submissions)"))
                        columns = [row[1] for row in result.fetchall()]
                        if "user_email" not in columns:
                            conn.execute(text("ALTER TABLE form_submissions ADD COLUMN user_email VARCHAR(255)"))
                            conn.commit()
                            logger.info("✓ Added user_email column")
                else:
                    # MySQL
                    result = conn.execute(text(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_NAME = 'form_submissions' AND COLUMN_NAME = 'user_email'"
                    ))
                    if not result.fetchone():
                        conn.execute(text("ALTER TABLE form_submissions ADD COLUMN user_email VARCHAR(255)"))
                        conn.commit()
                        logger.info("✓ Added user_email column")
            
            mark_migration_complete(migration_name)
        except Exception as e:
            logger.error("Migration failed: %s", e)
            raise

    # Migration 3: Add document_uuid to document_proofs
    migration_name = "add_document_uuid_column"
    if not is_migration_complete(migration_name):
        logger.info("Running migration: %s", migration_name)
        try:
            with engine.connect() as conn:
                if database_url.startswith("sqlite"):
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='document_proofs'"
                    ))
                    if result.fetchone():
                        result = conn.execute(text("PRAGMA table_info(document_proofs)"))
                        columns = [row[1] for row in result.fetchall()]
                        if "document_uuid" not in columns:
                            conn.execute(text("ALTER TABLE document_proofs ADD COLUMN document_uuid VARCHAR(36)"))
                            conn.commit()
                            logger.info("✓ Added document_uuid column")
                else:
                    # MySQL
                    result = conn.execute(text(
                        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_NAME = 'document_proofs' AND COLUMN_NAME = 'document_uuid'"
                    ))
                    if not result.fetchone():
                        conn.execute(text("ALTER TABLE document_proofs ADD COLUMN document_uuid VARCHAR(36)"))
                        conn.commit()
                        logger.info("✓ Added document_uuid column")
            
            mark_migration_complete(migration_name)
        except Exception as e:
            logger.error("Migration failed: %s", e)
            raise

