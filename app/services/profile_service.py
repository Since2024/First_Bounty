"""Profile service - handles user profile operations."""

from typing import Optional, Dict
from sqlalchemy.orm import Session

from app.db import UserProfile
from app.utils.security import hash_password, verify_password
from app.utils import get_logger

logger = get_logger(__name__)


class ProfileService:
    """Handles user profile CRUD operations."""
    
    @staticmethod
    def create_profile(
        session: Session,
        email: str,
        password: str
    ) -> UserProfile:
        """Create new user profile with hashed password."""
        hashed = hash_password(password)
        profile = UserProfile(
            user_email=email,
            password_hash=hashed
        )
        session.add(profile)
        session.flush()  # Get ID without committing
        logger.info("Created profile for %s", email)
        return profile
    
    @staticmethod
    def authenticate(
        session: Session,
        email: str,
        password: str
    ) -> Optional[UserProfile]:
        """Authenticate user and return profile if valid."""
        profile = session.query(UserProfile).filter_by(user_email=email).first()
        
        if not profile:
            logger.warning("Auth failed: user %s not found", email)
            return None
        
        if not profile.password_hash:
            logger.warning("Auth failed: %s has no password set", email)
            return None
        
        if not verify_password(password, profile.password_hash):
            logger.warning("Auth failed: wrong password for %s", email)
            return None
        
        logger.info("Auth successful for %s", email)
        return profile
    
    @staticmethod
    def update_from_extraction(
        session: Session,
        email: str,
        extraction_data: Dict[str, Dict],
        template_name: str
    ) -> UserProfile:
        """Update profile with data from extraction."""
        profile = session.query(UserProfile).filter_by(user_email=email).first()
        
        if not profile:
            raise ValueError(f"Profile not found: {email}")
        
        # Map fields intelligently
        field_mapping = {
            'f002': 'full_name',
            'f003': 'business_name' if 'business' in template_name.lower() else 'father_name',
            'f004': 'grandfather_name',
            'f006': 'permanent_address',
            'f007': 'mobile_number',
            'f008': 'email',
        }
        
        updated_fields = []
        for field_id, profile_attr in field_mapping.items():
            value = extraction_data.get(field_id, {}).get('value', '').strip()
            if value:
                setattr(profile, profile_attr, value)
                updated_fields.append(profile_attr)
        
        logger.info("Updated %d fields for %s", len(updated_fields), email)
        return profile

