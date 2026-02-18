import streamlit as st
import hashlib

from app.solana_utils import lookup_document_proof, verify_transaction_on_chain, normalize_file_hash


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

    manual_hash = st.text_input(
        "Or paste a SHA-256 hash (optional)",
        placeholder="64 hex characters",
        help="Use this if verification fails for uploaded file and you want to test a known hash directly.",
    )

    # File uploader
    uploaded_file = st.file_uploader(
        "Drop your document here",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Upload the exact same file bytes that were originally verified"
    )

    file_hash = None
    file_bytes = b""

    if uploaded_file:
        # Calculate hash
        file_bytes = uploaded_file.read()
        file_hash = normalize_file_hash(hashlib.sha256(file_bytes).hexdigest())

        # --- DEVELOPER DEBUG PANEL ---
        with st.expander("🛠️ Developer Debug Tools (Upload)"):
             st.markdown(f"**SHA256 Hash:** `{file_hash}`")
             st.markdown(f"**First 32 Bytes:** `{file_bytes[:32].hex()}`")
             st.info("ℹ️ If these don't match the 'Success' page exactly, the file bytes changed.")

        st.info(f"📄 Document Hash: `{file_hash}`")
        if len(file_bytes) > 0:
             st.caption(f"File Size: {len(file_bytes)} bytes")

    if manual_hash.strip():
        normalized_manual = normalize_file_hash(manual_hash)
        if len(normalized_manual) == 64 and all(ch in "0123456789abcdef" for ch in normalized_manual):
            st.caption(f"Using manually supplied hash: `{normalized_manual}`")
            file_hash = normalized_manual
        else:
            st.warning("Manual hash must be a 64-character hexadecimal SHA-256 string.")

    if file_hash and st.button("🔍 Check Verification Status", use_container_width=True, type="primary"):
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
            This document hash has not been verified through FOMO.

            **Common reasons:**
            - The file was changed after download (renaming is fine; editing/re-saving is not)
            - A browser viewer re-saved/re-printed the PDF, changing bytes
            - The verification record is in another database/environment
            """)

            st.info("💡 Tip: Use the **Direct Download** button from Success page, then verify that exact file.")
