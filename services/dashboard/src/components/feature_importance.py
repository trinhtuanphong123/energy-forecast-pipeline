"""
components/feature_importance.py
🔍 Feature Importance Chart
"""
import streamlit as st
import plotly.graph_objects as go
from typing import Dict
from config import Config

def render_feature_importance(feature_importance: Dict):
    """
    Render feature importance bar chart
    
    Args:
        feature_importance: Dict of {feature: importance}
    """
    
    st.markdown("### 🔍 Feature Importance (Top 10)")
    
    # Get top 10
    top_features = dict(sorted(
        feature_importance.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10])
    
    # Create bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=list(top_features.values()),
        y=list(top_features.keys()),
        orientation='h',
        marker=dict(
            color=list(top_features.values()),
            colorscale='Blues',
            showscale=False
        ),
        text=[f"{v*100:.1f}%" for v in top_features.values()],
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Importance: %{x:.1%}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Top 10 Most Important Features",
        xaxis_title="Importance",
        yaxis_title="Feature",
        height=400,
        template=Config.CHART_THEME,
        showlegend=False,
        xaxis=dict(tickformat='.0%')
    )
    
    st.plotly_chart(fig, use_container_width=True)