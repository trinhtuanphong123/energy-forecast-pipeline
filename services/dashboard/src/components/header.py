"""
components/header.py
📋 Header Component
"""
import streamlit as st
from datetime import datetime
from config import Config

def render_header():
    """Render dashboard header"""
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title(Config.APP_TITLE)
        st.caption("Real-time Energy Demand Forecasting System")
    
    with col2:
        # Last update time
        now = datetime.now()
        st.caption(f"🕐 Last Update")
        st.caption(now.strftime("%Y-%m-%d %H:%M:%S"))
    
    st.markdown("---")