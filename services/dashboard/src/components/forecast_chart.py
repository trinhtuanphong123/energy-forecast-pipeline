"""
components/forecast_chart.py
📈 Forecast Chart Component
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
from config import Config

def render_forecast_chart(predictions: Dict, historical: Optional[pd.DataFrame]):
    """
    Render main forecast chart
    
    Args:
        predictions: Predictions data
        historical: Historical dataframe
    """
    
    fig = go.Figure()
    
    # Historical data (last 24h)
    if historical is not None and not historical.empty:
        # Get last 24 hours
        last_24h = historical.tail(24)
        
        # Find target column
        target_col = None
        for col in ['electricity_demand', 'total_load', 'load']:
            if col in last_24h.columns:
                target_col = col
                break
        
        if target_col:
            fig.add_trace(go.Scatter(
                x=last_24h['datetime'],
                y=last_24h[target_col],
                name='Actual',
                mode='lines',
                line=dict(color=Config.COLORS['actual'], width=3),
                hovertemplate='<b>Actual</b><br>%{x}<br>%{y:.1f} MW<extra></extra>'
            ))
    
    # Forecast data
    pred_values = predictions.get('predictions', [])
    timestamps = predictions.get('timestamps', [])
    
    if pred_values and timestamps:
        # Convert timestamps
        timestamps = pd.to_datetime(timestamps)
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=pred_values,
            name='Forecast',
            mode='lines',
            line=dict(color=Config.COLORS['forecast'], width=3, dash='dash'),
            hovertemplate='<b>Forecast</b><br>%{x}<br>%{y:.1f} MW<extra></extra>'
        ))
        
        # Confidence interval
        ci = predictions.get('confidence_intervals', {})
        if ci:
            lower = ci.get('lower', [])
            upper = ci.get('upper', [])
            
            if lower and upper:
                # Upper bound
                fig.add_trace(go.Scatter(
                    x=timestamps,
                    y=upper,
                    mode='lines',
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo='skip'
                ))
                
                # Lower bound with fill
                fig.add_trace(go.Scatter(
                    x=timestamps,
                    y=lower,
                    fill='tonexty',
                    fillcolor=Config.COLORS['confidence'],
                    mode='lines',
                    line=dict(width=0),
                    name='95% Confidence',
                    hoverinfo='skip'
                ))
    
    # Layout
    fig.update_layout(
        title="Electricity Demand - 48 Hours View",
        xaxis_title="Time",
        yaxis_title="Load (MW)",
        height=Config.CHART_HEIGHT,
        template=Config.CHART_THEME,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)