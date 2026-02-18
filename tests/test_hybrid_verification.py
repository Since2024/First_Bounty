
import os
import sys
import uuid
import pytest
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.getcwd())

from app.solana_utils import (
    save_document_proof,
    lookup_document_proof,
    check_verification_status,
    VerificationStatus,
    verify_transaction_on_chain
)
from app.db.connection import init_db, get_session
from app.db.models import DocumentProof

# Initialize DB for tests (uses SQLite by default)
init_db()

def test_hybrid_verification_flow():
    print("\n--- Starting Hybrid Verification Test ---")
    
    # 1. Setup Test Data
    test_hash = "test_hash_" + str(uuid.uuid4().hex)
    test_sig = "test_sig_" + str(uuid.uuid4().hex)
    test_wallet = "test_wallet_123"
    test_uuid = str(uuid.uuid4())
    
    print(f"Test Data: Hash={test_hash}, Sig={test_sig}")

    # 2. Save Proof (Simulate "Manual Mode" / Pruned Tx)
    # This saves to DB but obviously won't exist on Solana Devnet
    link = save_document_proof(test_hash, test_sig, test_wallet, test_uuid)
    print(f"Saved proof. Link: {link}")

    # 3. Lookup Proof
    proof = lookup_document_proof(file_hash=test_hash)
    assert proof is not None
    assert proof['file_hash'] == test_hash
    assert proof['transaction_signature'] == test_sig
    print("Lookup successful.")

    # 4. Verify Status - Expect VERIFIED_DB_PRUNED
    # We mock verify_transaction_on_chain to be sure (though it would fail anyway)
    with patch('app.solana_utils.verify_transaction_on_chain', return_value=False):
        status = check_verification_status(proof)
        print(f"Status (Mocked False): {status}")
        assert status == VerificationStatus.VERIFIED_DB_PRUNED

    # 5. Verify Status - Expect VERIFIED_ON_CHAIN
    # Simulate that it magically appeared on chain
    with patch('app.solana_utils.verify_transaction_on_chain', return_value=True):
        status = check_verification_status(proof)
        print(f"Status (Mocked True): {status}")
        assert status == VerificationStatus.VERIFIED_ON_CHAIN

    # 6. Verify Status - Expect NOT_FOUND
    # Test with empty proof
    status = check_verification_status(None)
    assert status == VerificationStatus.NOT_FOUND
    print("Empty proof handled correctly.")

    print("\n✅ hybrid_verification_flow logic verified!")

if __name__ == "__main__":
    try:
        test_hybrid_verification_flow()
    except AssertionError as e:
        print(f"❌ Test Failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
