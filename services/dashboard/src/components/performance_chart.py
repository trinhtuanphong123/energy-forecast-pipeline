"""
components/performance_chart.py
📊 Model Performance Metrics
"""
import streamlit as st
from typing import Dict
from config import Config

def render_performance_metrics(metrics: Dict):
    """
    Render performance metric cards
    
    Args:
        metrics: Model metrics dict
    """
    
    col1, col2, col3 = st.columns(3)
    
    # MAPE
    with col1:
        mape = metrics.get('mape', metrics.get('val_mape', 0))
        color = Config.get_metric_color('mape', mape)
        status = Config.get_metric_status('mape', mape)
        
        st.metric(
            label="📉 MAPE (7 Days)",
            value=f"{mape:.2f}%",
            delta=None,
            help="Mean Absolute Percentage Error - Lower is better"
        )
        st.caption(status)
    
    # RMSE
    with col2:
        rmse = metrics.get('rmse', metrics.get('val_rmse', 0))
        color = Config.get_metric_color('rmse', rmse)
        status = Config.get_metric_status('rmse', rmse)
        
        st.metric(
            label="📏 RMSE",
            value=f"{Config.format_number(rmse)} MW",
            delta=None,
            help="Root Mean Square Error"
        )
        st.caption(status)
    
    # R²
    with col3:
        r2 = metrics.get('r2', 0)
        color = Config.get_metric_color('r2', r2)
        status = Config.get_metric_status('r2', r2)
        
        st.metric(
            label="📈 R² Score",
            value=f"{r2:.3f}",
            delta=None,
            help="R-squared - Higher is better"
        )
        st.caption(status)