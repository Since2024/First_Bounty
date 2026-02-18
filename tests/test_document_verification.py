"""Tests for document proof verification helpers."""

import hashlib

from app.db.connection import get_session
from app.db.models import DocumentProof
from app.solana_utils import lookup_document_proof, save_document_proof


def test_document_proof_lookup_normalizes_hash():
    # Use deterministic payload to derive a realistic SHA-256 hash.
    payload = b"fomo-verification-test-payload"
    canonical_hash = hashlib.sha256(payload).hexdigest()
    mixed_hash = f"  {canonical_hash.upper()}  "

    signature = "test_signature_1234567890"
    wallet = "wallet_ABCDEF123456"

    # Ensure clean state for this specific hash.
    with get_session() as session:
        session.query(DocumentProof).filter_by(file_hash=canonical_hash).delete()

    try:
        save_document_proof(mixed_hash, signature, wallet)
        proof = lookup_document_proof(mixed_hash)

        assert proof is not None
        assert proof["file_hash"] == canonical_hash
        assert proof["transaction_signature"] == signature
        assert proof["wallet_address"] == wallet
    finally:
        with get_session() as session:
            session.query(DocumentProof).filter_by(file_hash=canonical_hash).delete()
