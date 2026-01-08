"""
components/kpi_cards.py
📊 KPI Cards Component
"""
import streamlit as st
import pandas as pd
from typing import Dict, Optional
from config import Config

def render_kpi_cards(predictions: Dict, historical: Optional[pd.DataFrame]):
    """
    Render KPI metric cards
    
    Args:
        predictions: Predictions data
        historical: Historical dataframe
    """
    
    col1, col2, col3 = st.columns(3)
    
    # KPI 1: Current Load
    with col1:
        current_load = 0
        if historical is not None and not historical.empty:
            # Get latest actual value
            target_cols = ['electricity_demand', 'total_load', 'load']
            for col in target_cols:
                if col in historical.columns:
                    current_load = historical[col].iloc[-1]
                    break
        
        st.metric(
            label="⚡ Current Load",
            value=f"{Config.format_number(current_load)} MW",
            delta=None
        )
    
    # KPI 2: Peak Load Tomorrow
    with col2:
        pred_values = predictions.get('predictions', [])
        peak_tomorrow = max(pred_values[:24]) if pred_values else 0
        
        st.metric(
            label="📊 Peak Load Tomorrow",
            value=f"{Config.format_number(peak_tomorrow)} MW",
            delta=None
        )
    
    # KPI 3: 24h Trend
    with col3:
        if len(pred_values) >= 24:
            # Compare avg of next 24h vs current
            next_24h_avg = sum(pred_values[:24]) / 24
            change_pct = ((next_24h_avg - current_load) / current_load * 100) if current_load > 0 else 0
            
            st.metric(
                label="📈 Next 24h Trend",
                value=f"{Config.format_number(next_24h_avg)} MW",
                delta=f"{change_pct:+.1f}%"
            )
        else:
            st.metric(
                label="📈 Next 24h Trend",
                value="N/A",
                delta=None
            )