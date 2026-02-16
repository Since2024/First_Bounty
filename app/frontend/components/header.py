import streamlit as st
from pathlib import Path
import base64

def get_logo_base64(logo_path: Path) -> str:
    """Load logo image and convert to base64 for embedding."""
    try:
        with open(logo_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return ""

def render_header(logo_path: Path):
    """Render the main application header with logo."""
    logo_base64 = get_logo_base64(logo_path)
    
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
