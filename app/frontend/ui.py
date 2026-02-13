"""Streamlit UI for FOMO -"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import base64
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List
from datetime import datetime

import streamlit as st

sys.path.append(str(Path(__file__).parent.parent.parent))

from app import data_dir
from app.db import FormSubmission, UserProfile, get_session, init_db
from app.filler import prepare_pdf_fields
from app.services.extraction_service import ExtractionService
from app.services.profile_service import ProfileService
from app.frontend.monitoring import show_monitoring_dashboard
from app.printer import create_filled_pdf
from app.utils import (
    get_logger,
    list_template_files,
    load_template_file,
    template_fields,
    template_image_path,
)
from app.utils.security import hash_password, verify_password, validate_password_strength

# Page config with custom theme
st.set_page_config(
    page_title="FOMO - AI Form Filler",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-color: #6366f1;
        --success-color: #10b981;
        --warning-color: #f59e0b;
        --danger-color: #ef4444;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Beautiful header */
    .main-header {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .main-header h1 {
        color: white;
        font-size: 3rem;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.2rem;
        margin-top: 0.5rem;
    }
    
    /* Step cards */
    .step-card {
        background: #2d2d44;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #6366f1;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .step-number {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 1.2rem;
        margin-right: 1rem;
    }
    
    /* Confidence badges */
    .confidence-high { color: #10b981; font-weight: bold; }
    .confidence-medium { color: #f59e0b; font-weight: bold; }
    .confidence-low { color: #ef4444; font-weight: bold; }
    
    /* Input fields */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e5e7eb;
        transition: all 0.3s;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
        border: none;
        padding: 0.75rem 2rem;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* File uploader */
    .uploadedFile {
        border-radius: 8px;
        border: 2px dashed #6366f1;
        padding: 1rem;
    }
    
    /* Success/Error messages */
    .stSuccess {
        background-color: #d1fae5;
        border-left: 4px solid #10b981;
        border-radius: 8px;
    }
    
    .stError {
        background-color: #fee2e2;
        border-left: 4px solid #ef4444;
        border-radius: 8px;
    }
    
    .stWarning {
        background-color: #fef3c7;
        border-left: 4px solid #f59e0b;
        border-radius: 8px;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #f9fafb 0%, #ffffff 100%);
    }
    
    /* Field sections */
    .field-section {
        background: #f9fafb;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    
    .section-title {
        color: #6366f1;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

init_db()
logger = get_logger(__name__)

if "runs" not in st.session_state:
    st.session_state.runs = []


# Validation functions
def validate_email(email: str) -> tuple[bool, str]:
    """Validate email format - must have @domain.com pattern."""
    if not email or not email.strip():
        return False, "Email cannot be empty"
    
    email = email.strip()
    # Check for @ symbol and domain
    if "@" not in email:
        return False, "Email must contain @ symbol"
    
    parts = email.split("@")
    if len(parts) != 2:
        return False, "Invalid email format"
    
    local, domain = parts
    if not local or not domain:
        return False, "Email must have local and domain parts"
    
    # Check domain has .com, .org, .net, etc.
    if "." not in domain:
        return False, "Email domain must contain a dot (e.g., @gmail.com)"
    
    domain_parts = domain.split(".")
    if len(domain_parts) < 2 or not all(domain_parts):
        return False, "Invalid domain format"
    
    # Basic pattern check
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




def get_logo_base64(logo_path: str) -> str:
    """Load logo image and convert to base64 for embedding."""
    try:
        with open(logo_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        logger.warning(f"Logo not found at {logo_path}")
        return ""


def _template_display_name(path: Path) -> str:
    template = load_template_file(path.name)
    
    # Get base name from template
    if template.get("forms"):
        base_name = template['forms'][0].get('name', path.stem)
    else:
        base_name = template.get('name', path.stem)
    
    # Change display name for business_front.ocr.json to "व्यवसाय कर फारम_back"
    if path.name == "business_front.ocr.json":
        return "व्यवसाय कर फारम back"
    
    return base_name


def _save_to_db(template_name: str, template_file: str, pdf_path: Path, payload: dict, prepared: List[dict]):
    with get_session() as session:
        user_email = st.session_state.get("user_email")
        submission = FormSubmission(
            user_email=user_email,  # Link to user profile
            template_name=template_name,
            template_file=template_file,
            pdf_path=str(pdf_path),
            gemini_json=json.dumps(payload, ensure_ascii=False),
            normalized_fields=json.dumps(prepared, ensure_ascii=False),
        )
        session.add(submission)


def _load_user_extraction_data(session, user_email: str) -> None:
    """Load user's latest extraction data from database and prepare for form filling."""
    try:
        # Get the latest form submission for this user
        latest_submission = session.query(FormSubmission).filter_by(
            user_email=user_email
        ).order_by(FormSubmission.created_at.desc()).first()
        
        if latest_submission:
            # Parse the extraction data from JSON
            extraction_data = json.loads(latest_submission.gemini_json)
            # Store in session state to be loaded into form
            st.session_state.loaded_extraction_data = extraction_data
            st.session_state.loaded_template_file = latest_submission.template_file
            st.session_state.loaded_template_name = latest_submission.template_name
            logger.info(f"Loaded extraction data for user {user_email} from submission {latest_submission.id}")
        else:
            # No previous data, just set flag to load profile data
            st.session_state.profile_ready_to_load = True
            logger.info(f"No previous extraction data found for user {user_email}")
    except Exception as e:
        logger.exception(f"Error loading user extraction data: {e}")
        # Fallback to profile data only
        st.session_state.profile_ready_to_load = True


def render_confidence_badge(confidence: float) -> str:
    if confidence >= 0.9:
        return f'<span class="confidence-high">🟢 {confidence:.0%}</span>'
    elif confidence >= 0.7:
        return f'<span class="confidence-medium">🟡 {confidence:.0%}</span>'
    else:
        return f'<span class="confidence-low">🔴 {confidence:.0%}</span>'


# ============== MAIN UI ==============

# Load logo
logo_path = Path(__file__).parent.parent / "templates" / "logo.png"
logo_base64 = get_logo_base64(str(logo_path))

# Animated Header
if logo_base64:
    st.markdown(f"""
    <div class="main-header">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <img src="data:image/png;base64,{logo_base64}" style="height:150px; border-radius: 8px;">
         </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Fallback without logo
    st.markdown("""
    <div class="main-header">
        <h1>🎯 FOMO</h1>
        <p>Fear Of Missing Out - Form Filling</p>
    </div>
    """, unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # Initialize active section
    if "active_sidebar_section" not in st.session_state:
        st.session_state.active_sidebar_section = None
    
    # Two buttons side by side for User Profile and Admin Panel
    col1, col2 = st.columns(2)
    
    with col1:
        user_profile_style = "primary" if st.session_state.active_sidebar_section == "user" else "secondary"
        if st.button("👤 User Profile", use_container_width=True, type=user_profile_style):
            if st.session_state.active_sidebar_section == "user":
                st.session_state.active_sidebar_section = None  # Toggle off
            else:
                st.session_state.active_sidebar_section = "user"
            st.rerun()
    
    with col2:
        admin_panel_style = "primary" if st.session_state.active_sidebar_section == "admin" else "secondary"
        if st.button("🔐 Admin Panel", use_container_width=True, type=admin_panel_style):
            if st.session_state.active_sidebar_section == "admin":
                st.session_state.active_sidebar_section = None  # Toggle off
            else:
                st.session_state.active_sidebar_section = "admin"
            st.rerun()
    
    st.markdown("---")
    
    # User Profile Section (only show when active)
    if st.session_state.active_sidebar_section == "user":
        st.markdown("### 👤 User Profile")
        
        # Check if user is already logged in
        current_email = st.session_state.get("user_email", "")
        is_logged_in = (current_email and st.session_state.get("user_profile"))
        
        if is_logged_in:
            # Already logged in - show profile info and logout
            st.success("✅ Logged in")
            profile = st.session_state.user_profile
            st.markdown("**📋 Saved Data:**")
            if profile.get("full_name"):
                st.caption(f"Name: {profile['full_name']}")
            if profile.get("mobile_number"):
                st.caption(f"Mobile: {profile['mobile_number']}")
            if profile.get("permanent_address"):
                st.caption(f"Address: {profile['permanent_address'][:30]}...")
            
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.user_profile = None
                st.session_state.user_email = None
                st.rerun()
        else:
            # Initialize sub-section state
            if "user_profile_subsection" not in st.session_state:
                st.session_state.user_profile_subsection = None
            
            # Two buttons for Create and Login
            col1, col2 = st.columns(2)
            with col1:
                create_style = "primary" if st.session_state.user_profile_subsection == "create" else "secondary"
                if st.button("➕ Create New", use_container_width=True, type=create_style):
                    if st.session_state.user_profile_subsection == "create":
                        st.session_state.user_profile_subsection = None
                    else:
                        st.session_state.user_profile_subsection = "create"
                    st.rerun()
            
            with col2:
                login_style = "primary" if st.session_state.user_profile_subsection == "login" else "secondary"
                if st.button("🔑 Login", use_container_width=True, type=login_style):
                    if st.session_state.user_profile_subsection == "login":
                        st.session_state.user_profile_subsection = None
                    else:
                        st.session_state.user_profile_subsection = "login"
                    st.rerun()
            
            st.markdown("---")
            
            # Create New Profile Section
            if st.session_state.user_profile_subsection == "create":
                st.markdown("#### ➕ Create New Profile")
                
                create_email = st.text_input(
                    "Your Email",
                    placeholder="user@gmail.com",
                    help="Enter your email (must have @domain.com format)",
                    key="create_email_input"
                )
                
                # Email validation
                create_email_valid = True
                create_email_error = ""
                if create_email:
                    create_email_valid, create_email_error = validate_email(create_email)
                    if not create_email_valid:
                        st.error(f"❌ {create_email_error}")
                
                create_password = st.text_input(
                    "Create Password",
                    type="password",
                    help="Create a password for your new account (min 6 characters)",
                    key="create_password_input"
                )
                
                if st.button("✅ Create Account", use_container_width=True, type="primary"):
                    if not create_email:
                        st.error("❌ Please enter your email")
                    elif not create_email_valid:
                        st.error("❌ Please fix email errors")
                    elif not create_password:
                        st.error("❌ Please enter a password")
                    else:
                        # Validate password strength
                        password_valid, password_error = validate_password_strength(create_password)
                        if not password_valid:
                            st.error(f"❌ {password_error}")
                        else:
                            try:
                                with get_session() as session:
                                    # Create new profile without checking if it exists
                                    new_profile = UserProfile(
                                        user_email=create_email,
                                        password_hash=hash_password(create_password)
                                    )
                                    session.add(new_profile)
                                    session.commit()
                                    # Refresh to get the ID and timestamps
                                    session.refresh(new_profile)
                                    st.session_state.user_profile = new_profile.to_dict()
                                    st.session_state.user_email = create_email
                                    st.success("✅ Account created successfully! You can now extract and save forms.")
                                    st.rerun()
                            except Exception as e:
                                logger.exception(f"Error creating profile: {e}")
                                # Check if it's a unique constraint error
                                if "UNIQUE constraint" in str(e) or "Duplicate entry" in str(e):
                                    st.error("❌ This email is already registered. Please use Login instead.")
                                else:
                                    st.error(f"❌ Error creating account: {str(e)}")
            
            # Login to Existing Profile Section
            if st.session_state.user_profile_subsection == "login":
                st.markdown("#### 🔑 Login to Existing Profile")
                
                login_email = st.text_input(
                    "Your Email",
                    placeholder="user@gmail.com",
                    help="Enter your registered email",
                    key="login_email_input"
                )
                
                # Email validation
                login_email_valid = True
                login_email_error = ""
                if login_email:
                    login_email_valid, login_email_error = validate_email(login_email)
                    if not login_email_valid:
                        st.error(f"❌ {login_email_error}")
                
                login_password = st.text_input(
                    "Password",
                    type="password",
                    help="Enter your password",
                    key="login_password_input"
                )
                
                if st.button("🔓 Login", use_container_width=True, type="primary"):
                    if not login_email:
                        st.error("❌ Please enter your email")
                    elif not login_email_valid:
                        st.error("❌ Please fix email errors")
                    elif not login_password:
                        st.error("❌ Please enter your password")
                    else:
                        try:
                            with get_session() as session:
                                profile = session.query(UserProfile).filter_by(user_email=login_email).first()
                                if not profile:
                                    st.error("❌ Email not found. Please create a new account.")
                                elif not profile.password_hash:
                                    # Old profile without password - set one
                                    st.warning("⚠️ Please set a password for your account")
                                    new_password = st.text_input(
                                        "Set New Password",
                                        type="password",
                                        key="set_password_login"
                                    )
                                    if new_password:
                                        password_valid, password_error = validate_password_strength(new_password)
                                        if not password_valid:
                                            st.error(f"❌ {password_error}")
                                        else:
                                            profile.password_hash = hash_password(new_password)
                                            session.commit()
                                            st.session_state.user_profile = profile.to_dict()
                                            st.session_state.user_email = login_email
                                            # Load latest extraction data
                                            _load_user_extraction_data(session, login_email)
                                            st.success("✅ Password set! Profile loaded.")
                                            st.rerun()
                                elif verify_password(login_password, profile.password_hash):
                                    # Successful login
                                    st.session_state.user_profile = profile.to_dict()
                                    st.session_state.user_email = login_email
                                    # Load latest extraction data from database
                                    _load_user_extraction_data(session, login_email)
                                    st.success("✅ Login successful! Your previous data has been loaded.")
                                    st.rerun()
                                else:
                                    st.error("❌ Incorrect password")
                        except Exception as e:
                            logger.exception(f"Error during login: {e}")
                            st.error(f"❌ Error during login: {str(e)}")
        
        st.markdown("---")
    
    # Admin Panel Section (only show when active)
    if st.session_state.active_sidebar_section == "admin":
        st.markdown("### 🔐 Admin Panel")
        
        # Admin credentials from environment
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        
        # Check if admin is logged in
        is_admin_logged_in = st.session_state.get("admin_logged_in", False)
        
        if is_admin_logged_in:
            st.success("✅ Admin logged in")
            
            # Show monitoring dashboard
            show_monitoring_dashboard()
            
            st.markdown("---")
            if st.button("🚪 Logout Admin", use_container_width=True):
                st.session_state.admin_logged_in = False
                st.rerun()
        else:
            # Admin login form
            admin_user = st.text_input("Admin Username", key="admin_username_input")
            admin_pass = st.text_input("Admin Password", type="password", key="admin_password_input")
            
            if st.button("🔑 Login as Admin", use_container_width=True):
                if admin_user == admin_username and admin_pass == admin_password:
                    st.session_state.admin_logged_in = True
                    st.success("✅ Admin login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid admin credentials")
        
        st.markdown("---")
    
    st.markdown("---")
    
    # API Status
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        st.success(f"✅ Gemini API Connected")
    else:
        st.error("❌ API Key Missing")
    
    st.markdown("---")
    
    # Stats
    st.markdown("### 📊 Statistics")
    st.metric("Forms Processed", len(st.session_state.runs))
    
    if st.session_state.get("user_email"):
        with get_session() as session:
            user_forms = session.query(FormSubmission).filter(
                FormSubmission.gemini_json.like(f'%{st.session_state.user_email}%')
            ).count()
            st.metric("Your Submissions", user_forms)
    
    st.markdown("---")
    
    # Quick Actions
    st.markdown("### 🚀 Quick Actions")
    if st.button("🔄 Clear History", use_container_width=True):
        st.session_state.runs = []
        if "current_extraction" in st.session_state:
            del st.session_state.current_extraction
        st.rerun()
   

# ============== STEP 1: Template Selection ==============
st.markdown("""
<div class="step-card">
    <span class="step-number">1</span>
    <strong style="font-size: 1.2rem;">Select Form Template</strong>
</div>
""", unsafe_allow_html=True)

template_files = list_template_files()
if not template_files:
    st.warning("⚠️ No templates found in app/templates/")
    st.stop()

template_choices = {_template_display_name(path): path for path in template_files}
selected_template_label = st.selectbox(
    "Choose the form you want to fill",
    list(template_choices.keys()),
    label_visibility="collapsed"
)
selected_template_path = template_choices[selected_template_label]
template = load_template_file(selected_template_path.name)

# ============== STEP 2: Upload Documents ==============
st.markdown("""
<div class="step-card">
    <span class="step-number">2</span>
    <strong style="font-size: 1.2rem;">Upload Your Documents</strong>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Drag & drop your documents here",
    type=["jpg", "jpeg", "png", "tif", "tiff"],
    accept_multiple_files=True,
    help="Upload citizenship, passport, or any government document",
    label_visibility="collapsed"
)

# Preview uploaded files
if uploaded_files:
    st.markdown("#### 📸 Preview")
    cols = st.columns(min(3, len(uploaded_files)))
    for idx, file in enumerate(uploaded_files):
        with cols[idx % len(cols)]:
            st.image(file, caption=file.name, use_column_width=True)

# ============== STEP 3: Extract Data ==============
if uploaded_files:
    st.markdown("""
    <div class="step-card">
        <span class="step-number">3</span>
        <strong style="font-size: 1.2rem;">Extract Data with AI</strong>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Add force refresh option
        force_refresh = st.checkbox(
            "🔄 Force Fresh Extraction (bypass cache)",
            value=False,
            help="Check this to force a new Gemini extraction even if cached results exist"
        )
        
        if st.button("🚀 Extract with Gemini", use_container_width=True, type="primary"):
            if not api_key:
                st.error("❌ GEMINI_API_KEY not set!")
                st.stop()
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.info("🔄 Processing documents...")
                progress_bar.progress(25)
                
                start_time = time.time()
                
                # Use extraction service with force_refresh option
                extraction, engine, errors = ExtractionService.extract_from_files(
                    uploaded_files,
                    template,
                    force_refresh=force_refresh
                )
                
                elapsed = time.time() - start_time
                
                # Show any warnings
                for error in errors:
                    status_text.warning(f"⚠️ {error}")
                
                progress_bar.progress(100)
                status_text.success(
                    f"✅ Extraction completed in {elapsed:.1f}s using {engine.upper()}"
                )
                time.sleep(1)
                status_text.empty()
                progress_bar.empty()
                
            except Exception as exc:
                status_text.error(f"❌ Extraction failed: {exc}")
                logger.exception("Extraction error")
                st.stop()
            
            # Store extraction
            st.session_state.current_extraction = {
                "engine": engine,
                "files": [file.name for file in uploaded_files],
                "extraction": extraction,
                "template_file": selected_template_path.name,
                "template_name": selected_template_label,
                "template_json": template,
            }
            # Reset auto-load flag for new extraction
            if "profile_auto_loaded" in st.session_state:
                del st.session_state.profile_auto_loaded
            st.rerun()

# ============== STEP 4: Review & Edit ==============
if "current_extraction" in st.session_state:
    st.markdown("""
    <div class="step-card">
        <span class="step-number">4</span>
        <strong style="font-size: 1.2rem;">Review & Edit Extracted Data</strong>
    </div>
    """, unsafe_allow_html=True)
    
    run = st.session_state.current_extraction
    template = run["template_json"]
    extraction = run["extraction"]
    
    # Ensure all template fields exist in extraction (defensive check)
    for field in template_fields(template):
        if field is None or not isinstance(field, dict):
            continue
        fid = field.get("id")
        if fid and fid not in extraction:
            extraction[fid] = {
                "value": "",
                "confidence": 0.0,
                "notes": "",
            }
    
    # Show extraction stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Template", run["template_name"])
    with col2:
        st.metric("🔧 Engine", run["engine"].upper())
    with col3:
        st.metric("📊 Fields Extracted", len(extraction))
    
    # Auto-load data: First try loaded extraction data, then profile data
    profile_auto_loaded = False
    
    # Priority 1: Load previous extraction data if available (from login)
    if "loaded_extraction_data" in st.session_state:
        loaded_data = st.session_state.loaded_extraction_data
        # Merge loaded data into extraction
        for fid, data in loaded_data.items():
            if isinstance(data, dict) and data.get("value"):
                extraction[fid] = {
                    "value": data.get("value", ""),
                    "confidence": data.get("confidence", 1.0),
                    "notes": f"Loaded from previous submission: {data.get('notes', '')}"
                }
        profile_auto_loaded = True
        # Clear the loaded data flag
        del st.session_state.loaded_extraction_data
        st.success("✅ Your previous form data has been loaded into the form fields!")
    
    # Priority 2: Auto-load profile data if available and fields are mostly empty
    elif st.session_state.get("user_profile") and "profile_auto_loaded" not in st.session_state:
        profile = st.session_state.user_profile
        empty_fields = sum(1 for fid, data in extraction.items() if not data.get("value", "").strip())
        total_fields = len(extraction)
        
        # Auto-load if profile is ready to load OR if more than 50% of fields are empty
        if st.session_state.get("profile_ready_to_load", False) or empty_fields > total_fields * 0.5:
            # Map profile data to extraction fields intelligently
            if profile.get("full_name"):
                extraction["f002"] = {
                    "value": profile["full_name"],
                    "confidence": 1.0,
                    "notes": "Auto-loaded from user profile"
                }
                extraction["f009"] = {
                    "value": profile["full_name"],
                    "confidence": 1.0,
                    "notes": "Auto-loaded from user profile"
                }
            
            if profile.get("father_name"):
                extraction["f003"] = {
                    "value": profile["father_name"],
                    "confidence": 1.0,
                    "notes": "Auto-loaded from user profile"
                }
            
            if profile.get("grandfather_name"):
                extraction["f004"] = {
                    "value": profile["grandfather_name"],
                    "confidence": 1.0,
                    "notes": "Auto-loaded from user profile"
                }
            
            if profile.get("permanent_address"):
                extraction["f006"] = {
                    "value": profile["permanent_address"],
                    "confidence": 1.0,
                    "notes": "Auto-loaded from user profile"
                }
                extraction["f010"] = {
                    "value": profile["permanent_address"],
                    "confidence": 1.0,
                    "notes": "Auto-loaded from user profile"
                }
            
            if profile.get("mobile_number"):
                extraction["f007"] = {
                    "value": profile["mobile_number"],
                    "confidence": 1.0,
                    "notes": "Auto-loaded from user profile"
                }
                extraction["f012"] = {
                    "value": profile["mobile_number"],
                    "confidence": 1.0,
                    "notes": "Auto-loaded from user profile"
                }
            
            if profile.get("email"):
                extraction["f008"] = {
                    "value": profile["email"],
                    "confidence": 1.0,
                    "notes": "Auto-loaded from user profile"
                }
            
            if profile.get("business_name") and "business" in run["template_name"].lower():
                extraction["f003"] = {
                    "value": profile["business_name"],
                    "confidence": 1.0,
                    "notes": "Auto-loaded from user profile"
                }
            
            st.session_state.profile_auto_loaded = True
            # Clear the ready to load flag
            if "profile_ready_to_load" in st.session_state:
                del st.session_state.profile_ready_to_load
            profile_auto_loaded = True
    
    if profile_auto_loaded:
        st.success("✅ Your saved profile data has been auto-loaded into the form!")
    
    st.markdown("---")
    
    with st.form(key="edit_form"):
        edited_values: Dict[str, str] = {}
        
        # Load from profile button - more prominent
        if st.session_state.get("user_profile"):
            st.markdown("### 📥 Load Profile Data")
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.form_submit_button("🔄 Load My Saved Data", use_container_width=True, type="secondary"):
                    profile = st.session_state.user_profile
                    
                    # Map profile data to extraction fields
                    if profile.get("full_name"):
                        extraction["f002"] = {
                            "value": profile["full_name"],
                            "confidence": 1.0,
                            "notes": "Loaded from user profile"
                        }
                        extraction["f009"] = {
                            "value": profile["full_name"],
                            "confidence": 1.0,
                            "notes": "Loaded from user profile"
                        }
                    
                    if profile.get("father_name"):
                        extraction["f003"] = {
                            "value": profile["father_name"],
                            "confidence": 1.0,
                            "notes": "Loaded from user profile"
                        }
                    
                    if profile.get("grandfather_name"):
                        extraction["f004"] = {
                            "value": profile["grandfather_name"],
                            "confidence": 1.0,
                            "notes": "Loaded from user profile"
                        }
                    
                    if profile.get("permanent_address"):
                        extraction["f006"] = {
                            "value": profile["permanent_address"],
                            "confidence": 1.0,
                            "notes": "Loaded from user profile"
                        }
                        extraction["f010"] = {
                            "value": profile["permanent_address"],
                            "confidence": 1.0,
                            "notes": "Loaded from user profile"
                        }
                    
                    if profile.get("mobile_number"):
                        extraction["f007"] = {
                            "value": profile["mobile_number"],
                            "confidence": 1.0,
                            "notes": "Loaded from user profile"
                        }
                        extraction["f012"] = {
                            "value": profile["mobile_number"],
                            "confidence": 1.0,
                            "notes": "Loaded from user profile"
                        }
                    
                    if profile.get("email"):
                        extraction["f008"] = {
                            "value": profile["email"],
                            "confidence": 1.0,
                            "notes": "Loaded from user profile"
                        }
                    
                    if profile.get("business_name") and "business" in run["template_name"].lower():
                        extraction["f003"] = {
                            "value": profile["business_name"],
                            "confidence": 1.0,
                            "notes": "Loaded from user profile"
                        }
                    
                    st.session_state.profile_auto_loaded = True
                    st.success("✅ Data loaded from your profile!")
                    st.rerun()
            with col2:
                st.caption("Click to fill all fields with your saved profile data")
        
        st.markdown("---")
        
        # Owner Information Section
        st.markdown("""
        <div class="field-section">
            <div class="section-title">
                <span>👤</span> जग्गाधनी विवरण (Owner Information)
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Get all fields once for distribution
        all_fields_list = [f for f in template_fields(template) if f and isinstance(f, dict) and f.get("id")]
        
        col1, col2 = st.columns(2)
        
        for idx, field in enumerate(all_fields_list):
            fid = field.get("id")
            if not fid:
                continue
            
            field_name = field.get("name", fid)
            field_label = field.get("label", field_name)
            field_desc = field.get("desc", "")
            current_value = extraction.get(fid, {}).get("value", "")
            confidence = extraction.get(fid, {}).get("confidence", 0.0)
            is_required = field.get("validate", {}).get("req", False)
            
            # Build label with confidence badge
            label = f"{field_name}"
            if is_required:
                label += " ⭐"
            
            # Distribute fields evenly between two columns
            mid_point = (len(all_fields_list) + 1) // 2  # +1 to handle odd numbers
            target_col = col1 if idx < mid_point else col2
            
            # Display field in appropriate column
            with target_col:
                if confidence > 0:
                    st.markdown(render_confidence_badge(confidence), unsafe_allow_html=True)
                
                # Handle date fields
                if field.get("type") == "text_date" or field.get("validate", {}).get("type") == "date":
                    edited_value = target_col.date_input(
                        label,
                        value=None,
                        key=f"edit_{fid}",
                        help=field_desc or None,
                    )
                    edited_values[fid] = str(edited_value) if edited_value else current_value
                else:
                    # Check if this is an email or phone field
                    field_type = field.get("type", "").lower()
                    field_validate_type = field.get("validate", {}).get("type", "").lower()
                    field_name_lower = field_name.lower()
                    field_label_lower = field_label.lower()
                    
                    is_email_field = ("email" in field_type or "email" in field_validate_type or 
                                     "email" in field_name_lower or "email" in field_label_lower)
                    is_phone_field = ("phone" in field_type or "phone" in field_validate_type or 
                                     "mobile" in field_name_lower or "mobile" in field_label_lower or
                                     "phone" in field_name_lower or "phone" in field_label_lower)
                    
                    input_value = target_col.text_input(
                        label,
                        value=current_value,
                        key=f"edit_{fid}",
                        help=field_desc or None,
                        placeholder=field_label,
                    )
                    
                    # Validate email field
                    if is_email_field and input_value:
                        email_valid, email_error = validate_email(input_value)
                        if not email_valid:
                            target_col.error(f"❌ {email_error}")
                            # Don't save invalid email - keep current value
                            input_value = current_value
                    
                    # Validate phone field
                    if is_phone_field and input_value:
                        phone_valid, phone_error = validate_phone(input_value)
                        if not phone_valid:
                            target_col.error(f"❌ {phone_error}")
                            # Don't save invalid phone - keep current value
                            input_value = current_value
                    
                    edited_values[fid] = input_value
        
        st.markdown("---")
        
        # Submit buttons
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            submit_btn = st.form_submit_button(
                "💾 Generate PDF",
                use_container_width=True,
                type="primary"
            )
        
        with col2:
            # ADD THIS: Save to profile checkbox
            save_to_profile = st.checkbox(
                "💾 Save data to my profile",
                value=bool(st.session_state.get("user_email")),
                help="Save this data for future form submissions"
            )
        
        with col3:
            cancel_btn = st.form_submit_button(
                "🔄 Extract Again",
                use_container_width=True
            )
        
        if submit_btn:
            # Update extraction
            for fid, value in edited_values.items():
                if value:
                    extraction[fid] = {
                        "value": value,
                        "confidence": extraction.get(fid, {}).get("confidence", 1.0),
                        "notes": extraction.get(fid, {}).get("notes", "") + " [edited]"
                    }
            
            prepared = prepare_pdf_fields(extraction, template)
            
            if not prepared:
                st.error("❌ No fields to save")
                st.stop()
            
            # Generate PDF
            artifacts = data_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"fomo_{timestamp}"
            pdf_path = artifacts / f"{base_name}.pdf"
            json_path = artifacts / f"{base_name}.json"
            
            background = template_image_path(template)
            if not background:
                st.error("❌ Template background missing")
                st.stop()
            
            with st.spinner("🎨 Creating beautiful PDF..."):
                create_filled_pdf(str(background), prepared, str(pdf_path))
                json_path.write_text(json.dumps(extraction, ensure_ascii=False, indent=2), encoding="utf-8")
                _save_to_db(run["template_name"], run["template_file"], pdf_path, extraction, prepared)
            
            # ADD THIS: Save to profile after PDF generation
            if save_to_profile and st.session_state.get("user_email"):
                with get_session() as session:
                    profile = session.query(UserProfile).filter_by(
                        user_email=st.session_state.user_email
                    ).first()
                    
                    if not profile:
                        profile = UserProfile(user_email=st.session_state.user_email)
                        session.add(profile)
                    
                    # Update profile with extracted data (with validation)
                    validation_errors = []
                    for fid, data in edited_values.items():
                        value = data if isinstance(data, str) else str(data)
                        if not value:
                            continue
                        
                        # Map field IDs to profile columns with validation
                        if fid == "f002" and value:  # Owner/person name
                            profile.full_name = value
                        elif fid == "f003" and value:  # Father/Business name
                            if "business" in run["template_name"].lower():
                                profile.business_name = value
                            else:
                                profile.father_name = value
                        elif fid == "f004" and value:  # Grandfather
                            profile.grandfather_name = value
                        elif fid == "f006" and value:  # Address
                            profile.permanent_address = value
                        elif fid == "f007" and value:  # Mobile
                            # Validate phone before saving
                            phone_valid, phone_error = validate_phone(value)
                            if phone_valid:
                                profile.mobile_number = value
                            else:
                                validation_errors.append(f"Phone: {phone_error}")
                        elif fid == "f008" and value:  # Email
                            # Validate email before saving
                            email_valid, email_error = validate_email(value)
                            if email_valid:
                                profile.email = value
                            else:
                                validation_errors.append(f"Email: {email_error}")
                        elif fid == "f009" and value:  # Business type
                            profile.business_type = value
                    
                    if validation_errors:
                        st.warning(f"⚠️ Some data couldn't be saved: {', '.join(validation_errors)}")
                    else:
                        session.commit()
                        st.session_state.user_profile = profile.to_dict()
                        st.success("✅ Profile updated!")
            
            # Store PDF path in session state for download button (outside form)
            st.session_state.generated_pdf_path = str(pdf_path)
            st.session_state.generated_pdf_name = pdf_path.name
            
            # Add to runs history
            st.session_state.runs.insert(
                0,
                {
                    "engine": run["engine"],
                    "files": run["files"],
                    "extraction": extraction,
                    "prepared": prepared,
                    "template_file": run["template_file"],
                    "template_name": run["template_name"],
                    "template_json": template,
                },
            )
            
            del st.session_state.current_extraction
            st.rerun()
        
        if cancel_btn:
            del st.session_state.current_extraction
            st.rerun()

# ============== Admin Panel - User Management ==============
if st.session_state.get("admin_logged_in", False):
    st.markdown("---")
    st.markdown("""
    <div class="step-card">
        <span class="step-number">👑</span>
        <strong style="font-size: 1.2rem;">Admin Panel - User Management</strong>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        with get_session() as session:
            # Get all users
            all_users = session.query(UserProfile).order_by(UserProfile.created_at.desc()).all()
            
            st.metric("Total Users", len(all_users))
            st.markdown("---")
            
            # Search and filter
            col1, col2 = st.columns([3, 1])
            with col1:
                search_query = st.text_input("🔍 Search users (by email or name)", key="admin_search")
            with col2:
                st.write("")  # Spacing
                if st.button("🔄 Refresh", use_container_width=True):
                    # Clear any editing states
                    keys_to_clear = [k for k in st.session_state.keys() if k.startswith(('editing_user_', 'confirm_delete_', 'viewing_user_'))]
                    for k in keys_to_clear:
                        del st.session_state[k]
                    st.rerun()
            
            # Filter users based on search
            filtered_users = all_users
            if search_query:
                search_lower = search_query.lower()
                filtered_users = [
                    u for u in all_users
                    if search_lower in (u.user_email or "").lower() or
                       search_lower in (u.full_name or "").lower()
                ]
            
            st.markdown(f"**Showing {len(filtered_users)} of {len(all_users)} users**")
            st.markdown("---")
            
            # Check if there are users
            if len(filtered_users) == 0:
                st.info("No users found. Create a user account first.")
            else:
                # Display users in cards (NOT expanders to avoid state issues)
                for idx, user in enumerate(filtered_users):
                    # Create a unique container for each user
                    user_container = st.container()
                    
                    with user_container:
                        # User header
                        st.markdown(f"### 👤 {user.user_email}")
                        if user.full_name:
                            st.caption(f"**Name:** {user.full_name}")
                        
                        # Action buttons in a horizontal row for better visibility
                        action_col1, action_col2, action_col3 = st.columns(3)
                        
                        with action_col1:
                            if st.button("👁️ View Details", key=f"view_{user.id}", use_container_width=True):
                                # Toggle viewing state
                                view_key = f"viewing_user_{user.id}"
                                st.session_state[view_key] = not st.session_state.get(view_key, False)
                                st.rerun()
                        
                        with action_col2:
                            if st.button("✏️ Edit User", key=f"edit_{user.id}", use_container_width=True):
                                # Toggle editing state
                                edit_key = f"editing_user_{user.id}"
                                st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                                st.rerun()
                        
                        with action_col3:
                            if st.button("🗑️ Delete User", key=f"delete_{user.id}", use_container_width=True, type="secondary"):
                                # Toggle delete confirmation
                                delete_key = f"confirm_delete_{user.id}"
                                st.session_state[delete_key] = not st.session_state.get(delete_key, False)
                                st.rerun()
                    
                        # View details section
                        if st.session_state.get(f"viewing_user_{user.id}", False):
                            st.markdown("---")
                            st.markdown("**📋 Full User Details:**")
                            
                            details_col1, details_col2 = st.columns(2)
                            
                            with details_col1:
                                st.write(f"**Email:** {user.user_email}")
                                st.write(f"**Full Name:** {user.full_name or 'Not set'}")
                                st.write(f"**Father Name:** {user.father_name or 'Not set'}")
                                st.write(f"**Grandfather Name:** {user.grandfather_name or 'Not set'}")
                                st.write(f"**Mobile:** {user.mobile_number or 'Not set'}")
                                st.write(f"**Contact Email:** {user.email or 'Not set'}")
                            
                            with details_col2:
                                st.write(f"**Address:** {user.permanent_address or 'Not set'}")
                                st.write(f"**District:** {user.district or 'Not set'}")
                                st.write(f"**Municipality:** {user.municipality or 'Not set'}")
                                st.write(f"**Business Name:** {user.business_name or 'Not set'}")
                                st.write(f"**Business Type:** {user.business_type or 'Not set'}")
                            
                            st.write(f"**Created:** {user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else 'N/A'}")
                            st.write(f"**Updated:** {user.updated_at.strftime('%Y-%m-%d %H:%M:%S') if user.updated_at else 'N/A'}")
                            
                            if st.button("❌ Close Details", key=f"close_view_{user.id}"):
                                del st.session_state[f"viewing_user_{user.id}"]
                                st.rerun()
                        
                        # Delete confirmation section
                        if st.session_state.get(f"confirm_delete_{user.id}", False):
                            st.markdown("---")
                            st.warning(f"⚠️ **Confirm Deletion**")
                            st.write(f"Are you sure you want to permanently delete user **{user.user_email}**?")
                            st.write("This action cannot be undone!")
                            
                            col_del1, col_del2 = st.columns(2)
                            
                            with col_del1:
                                if st.button("✅ Yes, Delete Permanently", key=f"confirm_del_{user.id}", use_container_width=True, type="primary"):
                                    try:
                                        # Re-query to ensure we have the right object
                                        user_to_delete = session.query(UserProfile).filter_by(id=user.id).first()
                                        if user_to_delete:
                                            session.delete(user_to_delete)
                                            session.commit()
                                            st.success(f"✅ User {user.user_email} deleted successfully!")
                                            
                                            # Clear state
                                            del st.session_state[f"confirm_delete_{user.id}"]
                                            
                                            # Wait a moment for user to see message
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("User not found")
                                    except Exception as e:
                                        st.error(f"❌ Error deleting user: {e}")
                                        logger.exception("Error deleting user")
                                        session.rollback()
                            
                            with col_del2:
                                if st.button("❌ Cancel", key=f"cancel_del_{user.id}", use_container_width=True):
                                    del st.session_state[f"confirm_delete_{user.id}"]
                                    st.rerun()
                        
                        # Edit form section
                        if st.session_state.get(f"editing_user_{user.id}", False):
                            st.markdown("---")
                            st.markdown("**✏️ Edit User Information:**")
                            
                            with st.form(key=f"edit_user_form_{user.id}"):
                                edit_col1, edit_col2 = st.columns(2)
                                
                                with edit_col1:
                                    updated_email = st.text_input("Email*", value=user.user_email, key=f"edit_email_{user.id}")
                                    updated_name = st.text_input("Full Name", value=user.full_name or "", key=f"edit_name_{user.id}")
                                    updated_father = st.text_input("Father Name", value=user.father_name or "", key=f"edit_father_{user.id}")
                                    updated_grandfather = st.text_input("Grandfather Name", value=user.grandfather_name or "", key=f"edit_grandfather_{user.id}")
                                    updated_mobile = st.text_input("Mobile", value=user.mobile_number or "", key=f"edit_mobile_{user.id}")
                                    updated_contact_email = st.text_input("Contact Email", value=user.email or "", key=f"edit_contact_email_{user.id}")
                                
                                with edit_col2:
                                    updated_address = st.text_area("Permanent Address", value=user.permanent_address or "", key=f"edit_address_{user.id}")
                                    updated_district = st.text_input("District", value=user.district or "", key=f"edit_district_{user.id}")
                                    updated_municipality = st.text_input("Municipality", value=user.municipality or "", key=f"edit_municipality_{user.id}")
                                    updated_ward = st.text_input("Ward Number", value=user.ward_number or "", key=f"edit_ward_{user.id}")
                                    updated_business = st.text_input("Business Name", value=user.business_name or "", key=f"edit_business_{user.id}")
                                    updated_business_type = st.text_input("Business Type", value=user.business_type or "", key=f"edit_business_type_{user.id}")
                                
                                col_submit1, col_submit2 = st.columns(2)
                                
                                with col_submit1:
                                    submitted = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
                                
                                with col_submit2:
                                    cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)
                                
                                if submitted:
                                    validation_errors = []
                                    
                                    # Validate email
                                    if updated_email != user.user_email:
                                        email_valid, email_error = validate_email(updated_email)
                                        if not email_valid:
                                            validation_errors.append(f"Email: {email_error}")
                                    
                                    # Validate mobile if provided
                                    if updated_mobile:
                                        phone_valid, phone_error = validate_phone(updated_mobile)
                                        if not phone_valid:
                                            validation_errors.append(f"Mobile: {phone_error}")
                                    
                                    # Validate contact email if provided
                                    if updated_contact_email:
                                        email_valid, email_error = validate_email(updated_contact_email)
                                        if not email_valid:
                                            validation_errors.append(f"Contact Email: {email_error}")
                                    
                                    if validation_errors:
                                        for error in validation_errors:
                                            st.error(f"❌ {error}")
                                    else:
                                        try:
                                            # Re-query to get fresh object in session
                                            user_to_update = session.query(UserProfile).filter_by(id=user.id).first()
                                            
                                            if user_to_update:
                                                # Update all fields
                                                user_to_update.user_email = updated_email
                                                user_to_update.full_name = updated_name or None
                                                user_to_update.father_name = updated_father or None
                                                user_to_update.grandfather_name = updated_grandfather or None
                                                user_to_update.mobile_number = updated_mobile or None
                                                user_to_update.email = updated_contact_email or None
                                                user_to_update.permanent_address = updated_address or None
                                                user_to_update.district = updated_district or None
                                                user_to_update.municipality = updated_municipality or None
                                                user_to_update.ward_number = updated_ward or None
                                                user_to_update.business_name = updated_business or None
                                                user_to_update.business_type = updated_business_type or None
                                                
                                                session.commit()
                                                st.success("✅ User updated successfully!")
                                                
                                                # Clear editing state
                                                del st.session_state[f"editing_user_{user.id}"]
                                                
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("User not found")
                                        except Exception as e:
                                            st.error(f"❌ Error updating user: {e}")
                                            logger.exception("Error updating user")
                                            session.rollback()
                                
                                if cancelled:
                                    del st.session_state[f"editing_user_{user.id}"]
                                    st.rerun()
                        
                        # Separator between users
                        st.markdown("---")
    
    except Exception as e:
        st.error(f"❌ Error loading admin panel: {e}")
        logger.exception("Error in admin panel")

# ============== Download Generated PDF ==============
# Download button (outside extraction block so it shows after form submission)
if "generated_pdf_path" in st.session_state:
    st.markdown("---")
    st.markdown("""
    <div class="step-card">
        <span class="step-number">✓</span>
        <strong style="font-size: 1.2rem;">PDF Generated Successfully!</strong>
    </div>
    """, unsafe_allow_html=True)
    
    pdf_path = Path(st.session_state.generated_pdf_path)
    if pdf_path.exists():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.download_button(
                "📥 Download PDF",
                data=pdf_path.read_bytes(),
                file_name=st.session_state.generated_pdf_name,
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
        
        st.balloons()
        
        # Clear the generated PDF from session state after showing
        # (Don't clear immediately, let user download first)
        if st.button("✅ Done", use_container_width=True, key="clear_pdf"):
            del st.session_state.generated_pdf_path
            del st.session_state.generated_pdf_name
            st.rerun()

# ============== Recent Extractions ==============
if st.session_state.runs and "current_extraction" not in st.session_state:
    st.markdown("---")
    st.markdown("### 📚 Recent Extractions")
    
    for idx, run in enumerate(st.session_state.runs[:5]):  # Show last 5
        with st.expander(f"🗂️ {run['template_name']} - {run['files'][0]}", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Engine:** {run['engine'].upper()}")
            with col2:
                st.write(f"**Fields:** {len(run['prepared'])}")
            with col3:
                if st.button("🔄 Regenerate", key=f"regen_{idx}"):
                    st.info("Feature coming soon!")
