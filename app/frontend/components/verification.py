import streamlit as st
import hashlib
from pathlib import Path

def render_verification_page():
    """Render the public document verification page."""
    st.markdown("""
    <div class="step-card">
        <span class="step-number">🔍</span>
        <div>
            <div style="font-weight: 600; font-size: 1.1rem;">Verify Document</div>
            <div class="text-gray text-sm">Check if a document has been verified on Solana</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
    ### How it works
    1. Upload the document you want to verify
    2. We calculate its SHA-256 hash
    3. We check our database for matching proofs
    4. We verify the transaction on Solana Devnet
    """)
    
    st.markdown("---")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Drop your document here",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Upload the exact file you want to verify"
    )
    
    if uploaded_file:
        # Calculate hash
        file_bytes = uploaded_file.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        st.info(f"📄 Document Hash: `{file_hash}`")
        st.caption(f"Comparison: Make sure this hash matches the one shown during generation.\nFile Size: {len(file_bytes)} bytes")
        st.caption(f"First 16 bytes: {file_bytes[:16].hex()}")
        
        if st.button("🔍 Check Verification Status", use_container_width=True, type="primary"):
            from app.solana_utils import lookup_document_proof, verify_transaction_on_chain
            
            with st.spinner("🔎 Searching blockchain records..."):
                proof = lookup_document_proof(file_hash)
            
            if proof:
                st.success("✅ **Document Verified!**")
                
                # Display proof details
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Verification Details**")
                    st.markdown(f"🗓️ **Date**: {proof['created_at'][:10]}")
                    st.markdown(f"👤 **Wallet**: `{proof['wallet_address'][:8]}...{proof['wallet_address'][-8:]}`")
                
                with col2:
                    st.markdown("**Blockchain Proof**")
                    st.markdown(f"[🔗 View on Solana Explorer]({proof['explorer_link']})")
                    
                    # Verify on-chain
                    with st.spinner("Verifying on-chain..."):
                        is_valid = verify_transaction_on_chain(proof['transaction_signature'])
                    
                    if is_valid:
                        st.success("✅ Transaction confirmed on Solana Devnet")
                    else:
                        st.warning("⚠️ Could not verify transaction (network issue or pending)")
                
                # Show full details in expander
                with st.expander("📋 Full Proof Details"):
                    st.json(proof)
            else:
                st.error("❌ **Document Not Found**")
                st.markdown("""
                This document has not been verified through FOMO.
                
                **Possible reasons:**
                - The document was never verified
                - The document has been modified (hash mismatch)
                - The verification was done on a different system
                """)
                
                st.info("💡 **Tip**: Make sure you're uploading the exact same file that was verified.")
