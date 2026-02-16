import os
import time
import streamlit as st
from app.db import get_session, UserProfile
from app.utils import get_logger
from app.frontend.utils import validate_email, validate_phone

logger = get_logger(__name__)

def render_admin_dashboard():
    """Render the main admin dashboard."""
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
