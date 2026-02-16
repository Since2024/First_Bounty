import re
import streamlit as st
from app.db import get_session, FormSubmission

def validate_email(email: str) -> tuple[bool, str]:
    """Validate email format."""
    if not email or not email.strip():
        return False, "Email cannot be empty"
    
    email = email.strip()
    if not re.match(r'^[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False, "Invalid email format"
    
    return True, ""

def validate_phone(phone: str) -> tuple[bool, str]:
    """Validate phone number - 10 digits, starts with 9, second digit 7 or 8."""
    if not phone or not phone.strip():
        return False, "Phone number cannot be empty"
    
    # Remove spaces, dashes, and other characters
    phone_clean = re.sub(r'[^\d]', '', phone.strip())
    
    # Check length
    if len(phone_clean) != 10:
        return False, "Phone number must be exactly 10 digits"
    
    # Check first digit is 9
    if phone_clean[0] != '9':
        return False, "Phone number must start with 9"
    
    # Check second digit is 7 or 8
    if phone_clean[1] not in ['7', '8']:
        return False, "Second digit must be 7 or 8"
    
    return True, ""

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength."""
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    return True, ""

def render_confidence_badge(confidence: float) -> str:
    """Render a confidence badge HTML."""
    if confidence >= 0.9:
        return f'<span class="confidence-high">🟢 {confidence:.0%}</span>'
    elif confidence >= 0.7:
        return f'<span class="confidence-medium">🟡 {confidence:.0%}</span>'
    else:
        return f'<span class="confidence-low">🔴 {confidence:.0%}</span>'

def load_user_extraction_data(session, user_email: str) -> None:
    """Load user's latest extraction data from database."""
    import json
    try:
        latest_submission = session.query(FormSubmission).filter_by(
            user_email=user_email
        ).order_by(FormSubmission.created_at.desc()).first()
        
        if latest_submission:
            st.session_state.loaded_extraction_data = json.loads(latest_submission.gemini_json)
            st.session_state.loaded_template_file = latest_submission.template_file
            st.session_state.loaded_template_name = latest_submission.template_name
            # st.toast(f"Loaded previous data for {user_email}")
        else:
            st.session_state.profile_ready_to_load = True
    except Exception as e:
        # st.error(f"Error loading data: {e}")
        st.session_state.profile_ready_to_load = True

def save_to_db(template_name: str, template_file: str, pdf_path: str, payload: dict, prepared: list):
    """Save submission to database."""
    import json
    from pathlib import Path
    
    with get_session() as session:
        user_email = st.session_state.get("user_email")
        submission = FormSubmission(
            user_email=user_email,
            template_name=template_name,
            template_file=template_file,
            pdf_path=str(pdf_path),
            gemini_json=json.dumps(payload, ensure_ascii=False),
            normalized_fields=json.dumps(prepared, ensure_ascii=False),
        )
        session.add(submission)
