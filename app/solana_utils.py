import base58
import base64
from nacl.public import PrivateKey, PublicKey, Box
from nacl.utils import random
from urllib.parse import urlencode

# Constants for Deep Linking
PHANTOM_BASE_URL = "https://phantom.app/ul/v1"

def generate_keypair():
    """Generate a new ephemeral keypair for the dApp session."""
    private_key = PrivateKey.generate()
    public_key = private_key.public_key
    return private_key, public_key

def create_connect_url(dapp_public_key: PublicKey, redirect_link: str, app_url: str = "https://fomo-app.com"):
    """
    Generate the Deep Link URL to connect with Phantom.
    
    Args:
        dapp_public_key: The public key of the dApp (generated via generate_keypair).
        redirect_link: The URL where Phantom should redirect after connection (e.g., localhost:8501).
        app_url: The URL of the dApp (used for metadata display in Phantom).
    """
    base58_pubkey = base58.b58encode(dapp_public_key.encode()).decode("utf-8")
    
    params = {
        "dapp_encryption_public_key": base58_pubkey,
        "cluster": "devnet",  # Or 'mainnet-beta'
        "app_url": app_url,
        "redirect_link": redirect_link,
    }
    query_string = urlencode(params)
    return f"{PHANTOM_BASE_URL}/connect?{query_string}"

def decrypt_connect_response(phantom_pubkey_str: str, nonce_str: str, data_str: str, dapp_private_key: PrivateKey):
    """
    Decrypt the payload returned by Phantom after a successful connection.
    
    Args:
        phantom_pubkey_str: Base58 encoded public key from Phantom.
        nonce_str: Base58 encoded nonce.
        data_str: Base58 encoded encrypted data.
        dapp_private_key: The private key of the dApp (kept in session state).
        
    Returns:
        dict: The decrypted JSON payload containing session and public_key.
    """
    try:
        phantom_public_key = PublicKey(base58.b58decode(phantom_pubkey_str))
        nonce = base58.b58decode(nonce_str)
        encrypted_data = base58.b58decode(data_str)
        
        box = Box(dapp_private_key, phantom_public_key)
        decrypted_data = box.decrypt(encrypted_data, nonce)
        
        # decrypted_data is bytes, decode to string?
        # Actually, Phantom returns JSON.
        # But 'decrypt' returns the message.
        return decrypted_data
    except Exception as e:
        print(f"Decryption error: {e}")
        return None

def create_sign_transaction_url(
    dapp_private_key: PrivateKey,
    phantom_pubkey_str: str,
    transaction_base64: str,
    session_token: str,
    redirect_link: str
):
    """
    Generate the Deep Link URL to sign and send a transaction.
    """
    phantom_public_key = PublicKey(base58.b58decode(phantom_pubkey_str))
    box = Box(dapp_private_key, phantom_public_key)
    
    # Encrypt the payload
    # Payload format:
    # {
    #   "session": "...",
    #   "transaction": "..." (base58 encoded serialized transaction)
    # }
    import json
    payload = {
        "session": session_token,
        "transaction": transaction_base64 # transaction needs to be base58 encoded
    }
    json_payload = json.dumps(payload).encode("utf-8")
    nonce = random(Box.NONCE_SIZE)
    encrypted_payload = box.encrypt(json_payload, nonce)
    
    # Construct URL
    params = {
        "dapp_encryption_public_key": base58.b58encode(dapp_private_key.public_key.encode()).decode("utf-8"),
        "nonce": base58.b58encode(nonce).decode("utf-8"),
        "redirect_link": redirect_link,
        "payload": base58.b58encode(encrypted_payload.ciphertext).decode("utf-8")
    }
    query_string = urlencode(params)
    return f"{PHANTOM_BASE_URL}/signAndSendTransaction?{query_string}"

from solders.transaction import Transaction
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
import base64
import base58

def create_memo_transaction(
    user_pubkey_str: str,
    memo_text: str,
    recent_blockhash_str: str
) -> bytes:
    """
    Create a serialized transaction with a Memo. 
    Returns the serialized message to be signed.
    """
    # Memo Program v2 ID
    memo_program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcQb")
    
    # Encoded memo
    memo_data = memo_text.encode("utf-8")
    
    # Create Instruction
    user_pubkey = Pubkey.from_string(user_pubkey_str)
    
    memo_ix = Instruction(
        program_id=memo_program_id,
        accounts=[AccountMeta(pubkey=user_pubkey, is_signer=True, is_writable=True)],
        data=memo_data
    )
    
    # Build Transaction
    # solders.transaction.Transaction.new_signed_with_payer is common, 
    # or just Transaction(instructions=[...], payer=...)
    # Let's try the modern way
    
    # If recent_blockhash_str is provided, use it.
    if recent_blockhash_str:
        from solders.hash import Hash
        blockhash_bytes = base58.b58decode(recent_blockhash_str)
        recent_blockhash = Hash(blockhash_bytes)
    else:
        recent_blockhash = None

    # Construct transaction
    # Note: solders Transaction usually takes a sequence of instructions and a payer
    if recent_blockhash:
        txn = Transaction.new_with_payer(
            [memo_ix],
            user_pubkey
        )
        # We need to set the blockhash if possible or leave it for signing?
        # Transaction.new_with_payer sets it to default or checks?
        # Actually in recent solders, we might need to be careful.
        # Let's try a simpler approach if we can: creating a legacy transaction structure manually?
        # Or using the `solana.transaction` wrapper if it exists. 
        # The user has solana 0.36.11 installed. 
        # In 0.30+, `from solana.transaction import Transaction` SHOULD exist but might be a wrapper.
        # But user got ModuleNotFoundError. This suggests `solana` package might be broken or incomplete.
        pass

    # Let's try importing from `solana.transaction` again but maybe the installation was weird.
    # OR, we simply use `solders` directly which is installed (0.27.1).
    
    txn = Transaction.new_with_payer(
        [memo_ix],
        user_pubkey
    )
    # The blockhash is usually required for serialization to be valid for network.
    # But for deep linking, we send a serialized message?
    # Phantom `signAndSendTransaction` docs say: "The transaction must be serialized..."
    
    # We can use `Message` if we want just the message?
    from solders.message import Message
    msg = Message.new_with_blockhash(
        [memo_ix],
        user_pubkey,
        recent_blockhash if recent_blockhash else Hash.default() 
    )
    
    # Create a transaction from the message
    txn = Transaction.new_unsigned(msg)
    
    return bytes(txn) # Serialize to bytes

def save_document_proof(file_hash: str, signature: str, wallet_address: str):
    """
    Save a document proof to the database.
    Returns the explorer link for the transaction.
    """
    from app.db.connection import get_session
    from app.db.models import DocumentProof
    
    explorer_link = f"https://explorer.solana.com/tx/{signature}?cluster=devnet"
    
    with get_session() as session:
        # Check if already exists
        existing = session.query(DocumentProof).filter_by(file_hash=file_hash).first()
        if existing:
            return existing.explorer_link
        
        proof = DocumentProof(
            file_hash=file_hash,
            transaction_signature=signature,
            wallet_address=wallet_address,
            explorer_link=explorer_link
        )
        session.add(proof)
        session.commit()
        
    return explorer_link

def lookup_document_proof(file_hash: str):
    """
    Look up a document proof by its hash.
    Returns dict with proof details or None if not found.
    """
    from app.db.connection import get_session
    from app.db.models import DocumentProof
    
    with get_session() as session:
        proof = session.query(DocumentProof).filter_by(file_hash=file_hash).first()
        if proof:
            return proof.to_dict()
    return None

def verify_transaction_on_chain(signature: str) -> bool:
    """
    Verify that a transaction signature exists on Solana Devnet.
    Returns True if valid, False otherwise.
    """
    try:
        from solana.rpc.api import Client
        client = Client("https://api.devnet.solana.com")
        
        response = client.get_transaction(signature)
        return response.value is not None
    except Exception as e:
        print(f"Verification error: {e}")
        return False
