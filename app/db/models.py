"""SQLAlchemy models for storing completed runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, String, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(255), nullable=True, index=True)  # Link to user profile
    template_name = Column(String(255), nullable=False)
    template_file = Column(String(255), nullable=False)
    pdf_path = Column(String(500), nullable=False)
    gemini_json = Column(Text, nullable=False)
    normalized_fields = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Add indexes for common queries
    __table_args__ = (
        Index('idx_user_email_created', 'user_email', 'created_at'),
        Index('idx_template_file', 'template_file'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "template_name": self.template_name,
            "template_file": self.template_file,
            "pdf_path": self.pdf_path,
            "created_at": self.created_at.isoformat(),
        }


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Hashed password for authentication

    # Personal Information
    full_name = Column(String(255))
    father_name = Column(String(255))
    grandfather_name = Column(String(255))
    date_of_birth = Column(String(50))

    # Address Information
    permanent_address = Column(String(500))
    temporary_address = Column(String(500))
    district = Column(String(100))
    municipality = Column(String(100))
    ward_number = Column(String(20))

    # Contact Information
    mobile_number = Column(String(20))
    email = Column(String(255))

    # Identification
    citizenship_number = Column(String(50))
    pan_number = Column(String(50))

    # Business Information (optional)
    business_name = Column(String(255))
    business_type = Column(String(255))
    business_registration_number = Column(String(100))

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes already defined via index=True on columns
    # But add compound index for better performance
    __table_args__ = (
        Index('idx_email_updated', 'user_email', 'updated_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_email": self.user_email,
            "full_name": self.full_name,
            "father_name": self.father_name,
            "grandfather_name": self.grandfather_name,
            "date_of_birth": self.date_of_birth,
            "permanent_address": self.permanent_address,
            "temporary_address": self.temporary_address,
            "district": self.district,
            "municipality": self.municipality,
            "ward_number": self.ward_number,
            "mobile_number": self.mobile_number,
            "email": self.email,
            "citizenship_number": self.citizenship_number,
            "pan_number": self.pan_number,
            "business_name": self.business_name,
            "business_type": self.business_type,
            "business_registration_number": self.business_registration_number,
        }


__all__ = ["Base", "FormSubmission", "UserProfile"]

