import streamlit as st
import hashlib

from app.solana_utils import lookup_document_proof, check_verification_status, VerificationStatus, normalize_file_hash


def _display_proof(proof, method_label=""):
    """Display proof details after successful lookup."""
    
    # 1. Determine Status
    with st.spinner("Verifying on-chain..."):
        status = check_verification_status(proof)

    # 2. Display Status Header
    if status == VerificationStatus.VERIFIED_ON_CHAIN:
        st.success(f"✅ **Verified On-Chain!** {method_label}")
    elif status == VerificationStatus.VERIFIED_DB_PRUNED:
        st.warning(f"⚠️ **Verified from Registry (Pruned from Chain)** {method_label}")
        st.info("The transaction was valid when created, but the Solana Devnet history has been pruned. The local registry confirms its existence.")
    else:
        st.error(f"❌ **Transaction Not Found** {method_label}")
        return

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Verification Details**")
        st.markdown(f"🗓️ **Date**: {proof['created_at'][:10]}")
        st.markdown(f"👤 **Wallet**: `{proof['wallet_address'][:8]}...{proof['wallet_address'][-8:]}`")
        if proof.get('file_hash'):
            st.markdown(f"🔒 **Hash**: `{proof['file_hash'][:16]}...`")

    with col2:
        st.markdown("**Blockchain Proof**")
        st.markdown(f"[🔗 View on Solana Explorer]({proof['explorer_link']})")

        if status == VerificationStatus.VERIFIED_ON_CHAIN:
             st.success("✅ Confirmed on Solana Devnet")
        elif status == VerificationStatus.VERIFIED_DB_PRUNED:
             st.caption("ℹ️ Transaction too old for Devnet Explorer")

    with st.expander("📋 Full Proof Details"):
        st.json(proof)


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

    # ====== METHOD 1: VERIFICATION CODE (Primary - Most Reliable) ======
    st.markdown("### 🔑 Verify by Code")
    st.caption("Paste the Verification Code shown on the document's Success page.")
    
    verification_code = st.text_input(
        "Verification Code",
        placeholder="e.g. 6098b70c-fd54-409c-8658-a007782d0f61",
        help="This is the UUID shown after document generation. Copy it from the Success page.",
        label_visibility="collapsed",
    )

    if verification_code.strip() and st.button("🔍 Verify by Code", use_container_width=True, type="primary"):
        with st.spinner("🔎 Searching records..."):
            proof = lookup_document_proof(document_uuid=verification_code.strip())
        
        if proof:
            _display_proof(proof, "(Matched by Verification Code)")
        else:
            st.error("❌ **No record found** for this verification code.")
            st.caption("Double-check the code and try again.")

    st.markdown("---")

    # ====== METHOD 2: FILE HASH (Secondary) ======
    with st.expander("📄 Verify by File Upload or Hash (Advanced)"):
        st.caption("Upload the original file or paste its SHA-256 hash.")
        
        manual_hash = st.text_input(
            "Paste a SHA-256 hash",
            placeholder="64 hex characters",
        )

        uploaded_file = st.file_uploader(
            "Or upload the document",
            type=["pdf", "png", "jpg", "jpeg"],
            help="Upload the exact same file that was originally verified."
        )

        file_hash = None

        if uploaded_file:
            file_bytes = uploaded_file.read()
            file_hash = normalize_file_hash(hashlib.sha256(file_bytes).hexdigest())
            st.info(f"📄 Computed Hash: `{file_hash}`")
            st.caption(f"File Size: {len(file_bytes)} bytes")

        if manual_hash.strip():
            normalized_manual = normalize_file_hash(manual_hash.strip())
            if len(normalized_manual) == 64 and all(ch in "0123456789abcdef" for ch in normalized_manual):
                file_hash = normalized_manual
                st.caption(f"Using manual hash: `{normalized_manual}`")
            else:
                st.warning("Hash must be a 64-character hexadecimal string.")

        if file_hash and st.button("🔍 Verify by Hash", use_container_width=True):
            with st.spinner("🔎 Searching records..."):
                proof = lookup_document_proof(file_hash=file_hash)

            if proof:
                _display_proof(proof, "(Exact Hash Match)")
            else:
                st.error("❌ **Document Not Found**")
                st.markdown("""
                **Common reasons:**
                - The file was modified after download (browsers often change PDF bytes)
                - Use the **Verification Code** method above instead — it's more reliable
                """)
