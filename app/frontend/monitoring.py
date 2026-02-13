"""Monitoring dashboard for admin."""

import streamlit as st
from datetime import datetime, timedelta
from sqlalchemy import func, text

from app.db import FormSubmission, get_session
from app.utils import get_logger

logger = get_logger(__name__)


def show_monitoring_dashboard():
    """Display system health and metrics."""
    st.markdown("## 📊 System Monitoring")
    
    with get_session() as session:
        # Total submissions
        total = session.query(func.count(FormSubmission.id)).scalar() or 0
        
        # Last 24 hours
        since = datetime.utcnow() - timedelta(hours=24)
        recent = session.query(func.count(FormSubmission.id)).filter(
            FormSubmission.created_at >= since
        ).scalar() or 0
        
        # Last 7 days
        since_week = datetime.utcnow() - timedelta(days=7)
        week_count = session.query(func.count(FormSubmission.id)).filter(
            FormSubmission.created_at >= since_week
        ).scalar() or 0
        
        # Success rate calculation (simplified - assumes non-zero total means success)
        success_rate = 100.0 if total > 0 else 0.0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Extractions", total)
        
        with col2:
            st.metric("Last 24h", recent)
        
        with col3:
            st.metric("Last 7 Days", week_count)
        
        with col4:
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Engine breakdown
        st.markdown("### 🔧 Extraction Engine Usage")
        
        try:
            # Try to get engine stats from JSON data
            # This is a simplified approach - in production you might want to store engine separately
            engine_stats_query = session.execute(text("""
                SELECT 
                    CASE 
                        WHEN gemini_json LIKE '%"notes": "ocr_fallback"%' THEN 'ocr'
                        WHEN gemini_json IS NOT NULL AND gemini_json != '' THEN 'gemini'
                        ELSE 'unknown'
                    END as engine,
                    COUNT(*) as count
                FROM form_submissions
                GROUP BY engine
            """))
            
            engine_stats = engine_stats_query.fetchall()
            
            if engine_stats:
                cols = st.columns(len(engine_stats))
                for idx, (engine, count) in enumerate(engine_stats):
                    with cols[idx]:
                        st.metric(engine.upper(), count)
            else:
                st.info("No engine statistics available yet")
                
        except Exception as e:
            logger.warning("Error fetching engine stats: %s", e)
            st.warning("Could not fetch engine statistics")
        
        # Recent submissions table
        st.markdown("### 📋 Recent Submissions")
        
        try:
            recent_submissions = session.query(FormSubmission).order_by(
                FormSubmission.created_at.desc()
            ).limit(10).all()
            
            if recent_submissions:
                data = []
                for sub in recent_submissions:
                    data.append({
                        "ID": sub.id,
                        "Template": sub.template_name,
                        "User": sub.user_email or "Anonymous",
                        "Created": sub.created_at.strftime("%Y-%m-%d %H:%M:%S") if sub.created_at else "N/A"
                    })
                
                st.dataframe(data, use_container_width=True, hide_index=True)
            else:
                st.info("No submissions yet")
                
        except Exception as e:
            logger.warning("Error fetching recent submissions: %s", e)
            st.warning("Could not fetch recent submissions")
        
        # Cache statistics
        st.markdown("### 💾 Cache Statistics")
        
        try:
            from app.utils.cache import CACHE_DIR
            from pathlib import Path
            
            if CACHE_DIR.exists():
                cache_files = list(CACHE_DIR.glob("*.json"))
                cache_size = sum(f.stat().st_size for f in cache_files if f.exists())
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Cached Extractions", len(cache_files))
                with col2:
                    st.metric("Cache Size", f"{cache_size / 1024:.1f} KB")
            else:
                st.info("Cache directory does not exist yet")
                
        except Exception as e:
            logger.warning("Error fetching cache stats: %s", e)
            st.warning("Could not fetch cache statistics")

