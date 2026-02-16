import time
import json
from pathlib import Path
from datetime import datetime
import streamlit as st
from app import data_dir
from app.db import get_session, UserProfile
from app.utils import list_template_files, load_template_file, template_fields, template_image_path, get_logger
from app.services.extraction_service import ExtractionService
from app.frontend.utils import render_confidence_badge, validate_email, validate_phone, save_to_db
from app.filler import prepare_pdf_fields
from app.printer import create_filled_pdf

logger = get_logger(__name__)

def render_step_template_selection():
    st.markdown("""
    <div class="step-card">
        <span class="step-number">1</span>
        <div>
            <div style="font-weight: 600; font-size: 1.1rem;">Select Form Template</div>
            <div class="text-gray text-sm">Choose the type of document you want to process</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    template_files = list_template_files()
    if not template_files:
        st.warning("No templates found.")
        return None, None

    # Helper to get display name
    def _get_name(path):
        t = load_template_file(path.name)
        if t.get("forms"):
            return t['forms'][0].get('name', path.stem)
        return t.get('name', path.stem)

    choices = {_get_name(p): p for p in template_files}
    selected_name = st.selectbox("Template", list(choices.keys()), label_visibility="collapsed")
    return choices[selected_name], load_template_file(choices[selected_name].name)

def render_step_upload():
    st.markdown("""
    <div class="step-card">
        <span class="step-number">2</span>
        <div>
            <div style="font-weight: 600; font-size: 1.1rem;">Upload Documents</div>
            <div class="text-gray text-sm">Upload images or PDFs of your documents</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    return st.file_uploader(
        "Upload files", 
        type=["jpg", "jpeg", "png", "pdf", "tiff"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

def render_step_extraction(uploaded_files, template, template_path, template_name):
    if not uploaded_files:
        return

    st.markdown("""
    <div class="step-card">
        <span class="step-number">3</span>
        <div>
            <div style="font-weight: 600; font-size: 1.1rem;">AI Extraction</div>
            <div class="text-gray text-sm">Extract data using Google Gemini models</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        force = st.checkbox("Force Refresh", help="Ignore cached results")
    
    with col2:
        if st.button("🚀 Start Extraction", use_container_width=True, type="primary"):
            _run_extraction(uploaded_files, template, force, template_path, template_name)

def _run_extraction(files, template, force, template_path, template_name):
    progress = st.progress(0)
    status = st.empty()
    
    try:
        status.info("Processing...")
        progress.progress(20)
        
        extraction, engine, errors = ExtractionService.extract_from_files(
            files, template, force_refresh=force
        )
        
        progress.progress(100)
        status.success("Done!")
        time.sleep(1)
        
        st.session_state.current_extraction = {
            "engine": engine,
            "files": [f.name for f in files],
            "extraction": extraction,
            "template_file": template_path.name,
            "template_name": template_name,
            "template_json": template
        }
        st.rerun()
            
    except Exception as e:
        status.error(f"Failed: {e}")

def render_step_review():
    if "current_extraction" not in st.session_state:
        return

    st.markdown("""
    <div class="step-card">
        <span class="step-number">4</span>
        <div>
            <div style="font-weight: 600; font-size: 1.1rem;">Review Data</div>
            <div class="text-gray text-sm">Verify and edit extracted information</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    run = st.session_state.current_extraction
    template = run["template_json"]
    extraction = run["extraction"]
    
    # Ensure all fields exist
    for field in template_fields(template):
        if field is None or not isinstance(field, dict):
            continue
        fid = field.get("id")
        if fid and fid not in extraction:
            extraction[fid] = {"value": "", "confidence": 0.0, "notes": ""}

    # Show extraction stats
    c1, c2, c3 = st.columns(3)
    c1.metric("Template", run["template_name"])
    c2.metric("Engine", run["engine"].upper())
    c3.metric("Fields", len(extraction))
    
    # Handle Data Loading Logic
    _handle_data_loading(extraction, run)
    
    st.divider()
    
    # Form Rendering
    with st.form(key="edit_form"):
        edited_values = _render_form_fields(template, extraction)
        
        st.markdown("---")
        
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            submit = st.form_submit_button("💾 Generate PDF", use_container_width=True, type="primary")
        with c2:
            save_profile = st.checkbox("Save to profile", value=bool(st.session_state.get("user_email")))
        with c3:
            cancel = st.form_submit_button("Cancel", use_container_width=True)

        if submit:
            _handle_submission(edited_values, extraction, template, run, save_profile)

        if cancel:
            del st.session_state.current_extraction
            st.rerun()

    # Success / Download Section (outside form)
    if "generated_pdf_path" in st.session_state:
        _render_download_section()

def _handle_data_loading(extraction, run):
    profile_auto_loaded = False
    
    # 1. Load from previous extraction (login)
    if "loaded_extraction_data" in st.session_state:
        loaded = st.session_state.loaded_extraction_data
        for fid, data in loaded.items():
            if isinstance(data, dict) and data.get("value"):
                extraction[fid] = {
                    "value": data.get("value", ""),
                    "confidence": data.get("confidence", 1.0),
                    "notes": f"Loaded from previous: {data.get('notes', '')}"
                }
        del st.session_state.loaded_extraction_data
        st.success("✅ Previous form data loaded!")
        profile_auto_loaded = True
    
    # 2. Auto-load profile if fields are empty
    elif st.session_state.get("user_profile") and "profile_auto_loaded" not in st.session_state:
        profile = st.session_state.user_profile
        empty_count = sum(1 for _, d in extraction.items() if not d.get("value", "").strip())
        
        if st.session_state.get("profile_ready_to_load", False) or empty_count > len(extraction) * 0.5:
            _map_profile_to_extraction(profile, extraction, run["template_name"])
            st.session_state.profile_auto_loaded = True
            if "profile_ready_to_load" in st.session_state:
                del st.session_state.profile_ready_to_load
            profile_auto_loaded = True
            st.success("✅ Profile data auto-loaded!")

    # Manual Load Button
    if st.session_state.get("user_profile"):
        if st.button("🔄 Reload Profile Data"):
             _map_profile_to_extraction(st.session_state.user_profile, extraction, run["template_name"])
             st.rerun()

def _map_profile_to_extraction(profile, extraction, template_name):
    mappings = {
        "f002": profile.get("full_name"),
        "f009": profile.get("full_name"), # Witness usually same
        "f003": profile.get("father_name") if "business" not in template_name.lower() else profile.get("business_name"),
        "f004": profile.get("grandfather_name"),
        "f006": profile.get("permanent_address"),
        "f010": profile.get("permanent_address"),
        "f007": profile.get("mobile_number"),
        "f012": profile.get("mobile_number"),
        "f008": profile.get("email"),
    }
    
    for fid, value in mappings.items():
        if value:
            extraction[fid] = {
                "value": value,
                "confidence": 1.0, 
                "notes": "Loaded from profile"
            }

def _render_form_fields(template, extraction):
    edited_values = {}
    
    st.markdown("### Form Details")
    all_fields = [f for f in template_fields(template) if f and isinstance(f, dict) and f.get("id")]
    
    col1, col2 = st.columns(2)
    for idx, field in enumerate(all_fields):
        fid = field.get("id")
        if not fid: continue
        
        target_col = col1 if idx % 2 == 0 else col2
        
        with target_col:
            current = extraction.get(fid, {})
            val = current.get("value", "")
            conf = current.get("confidence", 0.0)
            
            if conf > 0:
                st.markdown(render_confidence_badge(conf), unsafe_allow_html=True)
            
            label = field.get("label", field.get("name", fid))
            if field.get("validate", {}).get("req"):
                label += " *"
            
            # Basic validation check for UI feedback
            is_email = "email" in label.lower()
            is_phone = "phone" in label.lower() or "mobile" in label.lower()
            
            new_val = st.text_input(label, value=val, key=f"edit_{fid}")
            
            if new_val:
                if is_email:
                    valid, msg = validate_email(new_val)
                    if not valid: st.error(msg)
                if is_phone:
                    valid, msg = validate_phone(new_val)
                    if not valid: st.error(msg)
            
            edited_values[fid] = new_val
            
    return edited_values

def _handle_submission(edited_values, extraction, template, run, save_profile):
    # Update extraction with edited values
    for fid, val in edited_values.items():
        if val:
            extraction[fid] = {
                "value": val,
                "confidence": extraction.get(fid, {}).get("confidence", 1.0),
                "notes": "Edited"
            }
            
    prepared = prepare_pdf_fields(extraction, template)
    if not prepared:
        st.error("No data to save")
        return

    # PDF Generation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"fomo_{timestamp}"
    artifacts = data_dir()
    pdf_path = artifacts / f"{base_name}.pdf"
    
    bg = template_image_path(template)
    if not bg:
        st.error("Template background missing")
        return
        
    try:
        with st.spinner("Generating PDF..."):
            create_filled_pdf(str(bg), prepared, str(pdf_path))
            save_to_db(run["template_name"], run["template_file"], str(pdf_path), extraction, prepared)
            
            if save_profile and st.session_state.get("user_email"):
                _update_user_profile(edited_values, run["template_name"])
            
            st.session_state.generated_pdf_path = str(pdf_path)
            st.session_state.generated_pdf_name = pdf_path.name
            
            # Update history
            st.session_state.runs.insert(0, {
                **run,
                "prepared": prepared,
                "timestamp": timestamp
            })
            
            del st.session_state.current_extraction
            st.rerun()
            
    except Exception as e:
        st.error(f"Error: {e}")
        logger.exception("Submission failed")

def _update_user_profile(values, template_name):
    with get_session() as session:
        profile = session.query(UserProfile).filter_by(
            user_email=st.session_state.user_email
        ).first()
        
        if not profile:
            profile = UserProfile(user_email=st.session_state.user_email)
            session.add(profile)
            
        # Update fields logic (simplified mapping)
        if values.get("f002"): profile.full_name = values["f002"]
        if values.get("f006"): profile.permanent_address = values["f006"]
        if values.get("f007"): profile.mobile_number = values["f007"]
        if values.get("f008"): profile.email = values["f008"]
        
        session.commit()
        st.session_state.user_profile = profile.to_dict()

def _render_download_section():
    st.markdown("""
    <div class="step-card">
        <span class="step-number">✓</span>
        <div>
            <div style="font-weight: 600; font-size: 1.1rem;">Success!</div>
            <div class="text-gray text-sm">Your document is ready</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    path = Path(st.session_state.generated_pdf_path)
    if path.exists():
        c1, c2 = st.columns([1, 1])
        with c1:
            st.download_button(
                "📥 Download PDF",
                data=path.read_bytes(),
                file_name=st.session_state.generated_pdf_name,
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
        with c2:
            if st.button("Start New Form", use_container_width=True):
                del st.session_state.generated_pdf_path
                st.rerun()
