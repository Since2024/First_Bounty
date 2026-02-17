import os
import streamlit as st
from app.db import UserProfile, get_session
from app.utils.security import hash_password, verify_password
from app.frontend.utils import validate_email, validate_password_strength, load_user_extraction_data
from app.frontend.monitoring import show_monitoring_dashboard

def render_sidebar():
    with st.sidebar:
        st.markdown("### Menu")
        
        if "active_sidebar_section" not in st.session_state:
            st.session_state.active_sidebar_section = None
            
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("👤 Profile", use_container_width=True, 
                        type="primary" if st.session_state.active_sidebar_section == "user" else "secondary"):
                st.session_state.active_sidebar_section = "user" if st.session_state.active_sidebar_section != "user" else None
                st.rerun()
        
        with col2:
            if st.button("🔍 Verify", use_container_width=True,
                        type="primary" if st.session_state.active_sidebar_section == "verify" else "secondary"):
                st.session_state.active_sidebar_section = "verify" if st.session_state.active_sidebar_section != "verify" else None
                st.rerun()
        
        with col3:
            if st.button("🔐 Admin", use_container_width=True,
                        type="primary" if st.session_state.active_sidebar_section == "admin" else "secondary"):
                st.session_state.active_sidebar_section = "admin" if st.session_state.active_sidebar_section != "admin" else None
                st.rerun()
                
        st.markdown("---")
        
        if st.session_state.active_sidebar_section == "user":
            _render_user_profile()
            
        elif st.session_state.active_sidebar_section == "admin":
            _render_admin_panel()
            
        _render_system_status()

def _render_user_profile():
    st.markdown("### 👤 User Profile")
    
    if st.session_state.get("user_email") and st.session_state.get("user_profile"):
        st.success(f"Logged in as {st.session_state.user_email}")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user_profile = None
            st.session_state.user_email = None
            st.rerun()
    else:
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", use_container_width=True):
                _handle_login(email, password)
                
        with tab2:
            new_email = st.text_input("Email", key="reg_email")
            new_pass = st.text_input("Password", type="password", key="reg_pass")
            if st.button("Create Account", use_container_width=True):
                _handle_registration(new_email, new_pass)

def _handle_login(email, password):
    if not email or not password:
        st.error("Please fill all fields")
        return

    with get_session() as session:
        profile = session.query(UserProfile).filter_by(user_email=email).first()
        if profile and verify_password(password, profile.password_hash):
            st.session_state.user_profile = profile.to_dict()
            st.session_state.user_email = email
            load_user_extraction_data(session, email)
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid credentials")

def _handle_registration(email, password):
    valid, msg = validate_email(email)
    if not valid:
        st.error(msg)
        return
        
    valid, msg = validate_password_strength(password)
    # allow weak passwords for demo/dev if needed, or enforce stricter
    if not valid: 
        st.warning(msg) # just warning for now
        
    try:
        with get_session() as session:
            new_profile = UserProfile(
                user_email=email,
                password_hash=hash_password(password)
            )
            session.add(new_profile)
            session.commit()
            st.success("Account created! Please login.")
    except Exception as e:
        st.error(f"Error: {e}")

def _render_admin_panel():
    st.markdown("### 🔐 Admin Panel")
    
    if st.session_state.get("admin_logged_in"):
        if st.button("Logout Admin"):
            st.session_state.admin_logged_in = False
            st.rerun()
        show_monitoring_dashboard()
    else:
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("Login Admin"):
            if user == os.getenv("ADMIN_USERNAME", "admin") and pwd == os.getenv("ADMIN_PASSWORD", "admin123"):
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Invalid admin credentials")

def _render_system_status():
    st.markdown("---")
    st.caption("System Status")
    if os.getenv("GEMINI_API_KEY"):
        st.markdown("🟢 Gemini API: Connected")
    else:
        st.markdown("🔴 Gemini API: Disconnected")
