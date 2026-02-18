from __future__ import annotations

from urllib.parse import urlencode

import base58

# Constants for Deep Linking
PHANTOM_BASE_URL = "https://phantom.app/ul/v1"

try:  # Optional dependency for wallet encryption helpers
    from nacl.public import Box, PrivateKey, PublicKey
    from nacl.utils import random
except ImportError:  # pragma: no cover
    Box = None
    PrivateKey = None
    PublicKey = None
    random = None


def _require_nacl() -> None:
    if not all([Box, PrivateKey, PublicKey, random]):
        raise RuntimeError("PyNaCl is required for Phantom deep-link encryption features")


def generate_keypair():
    """Generate a new ephemeral keypair for the dApp session."""
    _require_nacl()
    private_key = PrivateKey.generate()
    public_key = private_key.public_key
    return private_key, public_key


def create_connect_url(dapp_public_key: PublicKey, redirect_link: str, app_url: str = "https://fomo-app.com"):
    """Generate the Deep Link URL to connect with Phantom."""
    base58_pubkey = base58.b58encode(dapp_public_key.encode()).decode("utf-8")

    params = {
        "dapp_encryption_public_key": base58_pubkey,
        "cluster": "devnet",
        "app_url": app_url,
        "redirect_link": redirect_link,
    }
    query_string = urlencode(params)
    return f"{PHANTOM_BASE_URL}/connect?{query_string}"


def decrypt_connect_response(phantom_pubkey_str: str, nonce_str: str, data_str: str, dapp_private_key: PrivateKey):
    """Decrypt the payload returned by Phantom after a successful connection."""
    _require_nacl()
    try:
        phantom_public_key = PublicKey(base58.b58decode(phantom_pubkey_str))
        nonce = base58.b58decode(nonce_str)
        encrypted_data = base58.b58decode(data_str)

        box = Box(dapp_private_key, phantom_public_key)
        decrypted_data = box.decrypt(encrypted_data, nonce)
        return decrypted_data
    except Exception as e:
        print(f"Decryption error: {e}")
        return None


def create_sign_transaction_url(
    dapp_private_key: PrivateKey,
    phantom_pubkey_str: str,
    transaction_base64: str,
    session_token: str,
    redirect_link: str,
):
    """Generate the Deep Link URL to sign and send a transaction."""
    _require_nacl()
    phantom_public_key = PublicKey(base58.b58decode(phantom_pubkey_str))
    box = Box(dapp_private_key, phantom_public_key)

    import json

    payload = {
        "session": session_token,
        "transaction": transaction_base64,
    }
    json_payload = json.dumps(payload).encode("utf-8")
    nonce = random(Box.NONCE_SIZE)
    encrypted_payload = box.encrypt(json_payload, nonce)

    params = {
        "dapp_encryption_public_key": base58.b58encode(dapp_private_key.public_key.encode()).decode("utf-8"),
        "nonce": base58.b58encode(nonce).decode("utf-8"),
        "redirect_link": redirect_link,
        "payload": base58.b58encode(encrypted_payload.ciphertext).decode("utf-8"),
    }
    query_string = urlencode(params)
    return f"{PHANTOM_BASE_URL}/signAndSendTransaction?{query_string}"


def create_memo_transaction(
    user_pubkey_str: str,
    memo_text: str,
    recent_blockhash_str: str,
) -> bytes:
    """Create a serialized memo transaction."""
    from solders.hash import Hash
    from solders.instruction import AccountMeta, Instruction
    from solders.message import Message
    from solders.pubkey import Pubkey
    from solders.transaction import Transaction

    memo_program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcQb")
    memo_data = memo_text.encode("utf-8")
    user_pubkey = Pubkey.from_string(user_pubkey_str)

    memo_ix = Instruction(
        program_id=memo_program_id,
        accounts=[AccountMeta(pubkey=user_pubkey, is_signer=True, is_writable=True)],
        data=memo_data,
    )

    if recent_blockhash_str:
        blockhash_bytes = base58.b58decode(recent_blockhash_str)
        recent_blockhash = Hash(blockhash_bytes)
    else:
        recent_blockhash = Hash.default()

    msg = Message.new_with_blockhash([memo_ix], user_pubkey, recent_blockhash)
    txn = Transaction.new_unsigned(msg)
    return bytes(txn)


def normalize_file_hash(file_hash: str) -> str:
    """Normalize SHA-256 hash representation for consistent storage/lookup."""
    return (file_hash or "").strip().lower()


def save_document_proof(file_hash: str, signature: str, wallet_address: str):
    """Save a document proof to the database."""
    from app.db.connection import get_session
    from app.db.models import DocumentProof

    file_hash = normalize_file_hash(file_hash)
    explorer_link = f"https://explorer.solana.com/tx/{signature}?cluster=devnet"

    with get_session() as session:
        existing = session.query(DocumentProof).filter_by(file_hash=file_hash).first()
        if existing:
            return existing.explorer_link

        proof = DocumentProof(
            file_hash=file_hash,
            transaction_signature=signature,
            wallet_address=wallet_address,
            explorer_link=explorer_link,
        )
        session.add(proof)
        session.commit()

    return explorer_link


def lookup_document_proof(file_hash: str):
    """Look up a document proof by hash."""
    from app.db.connection import get_session
    from app.db.models import DocumentProof

    file_hash = normalize_file_hash(file_hash)

    with get_session() as session:
        proof = session.query(DocumentProof).filter_by(file_hash=file_hash).first()
        if proof:
            return proof.to_dict()
    return None


def verify_transaction_on_chain(signature: str) -> bool:
    """Verify that a transaction signature exists on Solana Devnet."""
    try:
        from solana.rpc.api import Client

        client = Client("https://api.devnet.solana.com")
        response = client.get_transaction(signature)
        return response.value is not None
    except Exception as e:
        print(f"Verification error: {e}")
        return False
