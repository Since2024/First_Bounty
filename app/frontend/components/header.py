import streamlit as st
from pathlib import Path
import base64
from app.solana_utils import generate_keypair, create_connect_url, decrypt_connect_response
import json

def get_logo_base64(logo_path: Path) -> str:
    """Load logo image and convert to base64 for embedding."""
    try:
        with open(logo_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return ""

def _handle_phantom_callback():
    """Check for Phantom Deep Link callback parameters."""
    params = st.query_params
    
    if "phantom_encryption_public_key" in params and "nonce" in params and "data" in params:
        try:
            # We must have a dapp_keypair in session from before the redirect
            if "dapp_keypair" in st.session_state:
                dapp_private_key = st.session_state.dapp_keypair[0]
                
                decrypted_json = decrypt_connect_response(
                    params["phantom_encryption_public_key"],
                    params["nonce"],
                    params["data"],
                    dapp_private_key
                )
                
                if decrypted_json:
                    session_data = json.loads(decrypted_json.decode("utf-8"))
                    st.session_state.phantom_wallet = session_data["public_key"]
                    st.session_state.phantom_session = session_data["session"]
                    st.session_state.phantom_encryption_key = params["phantom_encryption_public_key"]
                    
                    st.toast(f"Connected to Phantom! 👻", icon="✅")
            
            # Clear params to clean URL
            st.query_params.clear()
            # st.rerun() # Rerun might loop if params aren't cleared effectively, but .clear() handles it.
            
        except Exception as e:
            st.error(f"Failed to connect wallet: {e}")

def render_header(logo_path: Path):
    """Render the main application header with logo and wallet connection."""
    
    # 1. Initialize Keypair if needed
    if "dapp_keypair" not in st.session_state:
        st.session_state.dapp_keypair = generate_keypair()

    # 2. Handle Callback (if returning from Phantom)
    _handle_phantom_callback()

    logo_base64 = get_logo_base64(logo_path)
    
    # 3. Create Header Layout
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if logo_base64:
            st.markdown(f"""
            <div class="main-header">
                <img src="data:image/png;base64,{logo_base64}" style="height: 80px; width: auto; border-radius: 8px;">
                <div>
                    <h1>FOMO</h1>
                    <p>Fear Of Missing Out - AI Form Filler</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="main-header">
                <div>
                    <h1>🎯 FOMO</h1>
                    <p>Fear Of Missing Out - AI Form Filler</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        # Wallet Button
        if "phantom_wallet" in st.session_state:
            wallet = st.session_state.phantom_wallet
            short_wallet = f"{wallet[:4]}...{wallet[-4:]}"
            st.markdown(f"""
            <div style="background: rgba(99, 102, 241, 0.1); padding: 0.5rem; border-radius: 8px; text-align: center; border: 1px solid var(--primary-color);">
                <div style="font-size: 0.8rem; color: var(--text-secondary);">Connected Wallet</div>
                <div style="font-weight: 600; color: var(--primary-color);">🟣 Phantom ({short_wallet})</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Disconnect", key="disconnect_wallet", use_container_width=True):
                del st.session_state["phantom_wallet"]
                del st.session_state["phantom_session"]
                st.rerun()
        else:
            # Generate Deep Link
            _, public_key = st.session_state.dapp_keypair
            redirect_url = "http://localhost:8501" 
            connect_url = create_connect_url(public_key, redirect_url)
            
            st.markdown("**Connect Your Wallet**")
            
            # Option 1: Deep Link (for mobile)
            st.link_button("🟣 Connect Phantom (Mobile)", connect_url, use_container_width=True)
            
            st.markdown("---")
            st.caption("**Using browser extension?** Enter your wallet address manually:")
            
            # Option 2: Manual input (for browser extensions)
            manual_wallet = st.text_input(
                "Phantom Wallet Address",
                placeholder="e.g., 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
                help="Copy your wallet address from Phantom extension (44 characters)"
            )
            
            if st.button("✅ Connect Manually", use_container_width=True, type="secondary"):
                if not manual_wallet:
                    st.error("Please enter your wallet address")
                elif len(manual_wallet) < 32 or len(manual_wallet) > 44:
                    st.error("Invalid wallet address length. Should be 32-44 characters.")
                else:
                    # Validate it's a valid base58 Solana address
                    try:
                        from solders.pubkey import Pubkey
                        Pubkey.from_string(manual_wallet)  # This will throw if invalid
                        
                        st.session_state.phantom_wallet = manual_wallet
                        st.session_state.phantom_session = "manual_session"
                        st.session_state.phantom_encryption_key = "manual_key"
                        st.success(f"✅ Connected! Wallet: {manual_wallet[:4]}...{manual_wallet[-4:]}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Invalid Solana wallet address. Please check and try again.")
                        st.caption("Make sure you copied the full address from Phantom")
