"""Streamlit UI for FOMO -"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.db import init_db
from app.utils import get_logger
from app.frontend.components.header import render_header
from app.frontend.components.sidebar import render_sidebar
from app.frontend.components.steps import (
    render_step_template_selection,
    render_step_upload,
    render_step_extraction,
    render_step_review
)

from app.frontend.components.admin import render_admin_dashboard

# Page config
st.set_page_config(
    page_title="FOMO - AI Form Filler",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    css_path = Path(__file__).parent / "styles.css"
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()
init_db()
logger = get_logger(__name__)

if "runs" not in st.session_state:
    st.session_state.runs = []

# ============== MAIN UI ==============

# 1. Header
logo_path = Path(__file__).parent.parent / "templates" / "logo.png"
render_header(logo_path)

# 2. Sidebar
render_sidebar()

# 3. Main Content Area
if st.session_state.get("admin_logged_in"):
    render_admin_dashboard()
else:
    # Step 1: Template
    template_path, template_data = render_step_template_selection()

    if template_path:
        # Step 2: Upload
        uploaded_files = render_step_upload()
        
        # Step 3: Extract
        if uploaded_files:
            render_step_extraction(uploaded_files, template_data, template_path, template_path.stem)
            
            # Step 4: Review
            render_step_review()
