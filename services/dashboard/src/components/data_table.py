"""
components/data_table.py
📋 Data Explorer Table
"""
import streamlit as st
import pandas as pd
from config import Config

def render_data_table(data: pd.DataFrame):
    """
    Render paginated data table
    
    Args:
        data: DataFrame to display
    """
    
    # Search/filter
    st.markdown("### 🔍 Filter Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Date range filter
        if 'datetime' in data.columns:
            min_date = data['datetime'].min().date()
            max_date = data['datetime'].max().date()
            
            date_range = st.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start, end = date_range
                data = data[
                    (data['datetime'].dt.date >= start) &
                    (data['datetime'].dt.date <= end)
                ]
    
    with col2:
        # Column selection
        selected_cols = st.multiselect(
            "Select Columns",
            options=data.columns.tolist(),
            default=data.columns[:5].tolist()
        )
        
        if selected_cols:
            data = data[selected_cols]
    
    st.markdown("---")
    
    # Pagination
    page_size = Config.ROWS_PER_PAGE
    total_pages = (len(data) - 1) // page_size + 1
    
    page = st.number_input(
        f"Page (1-{total_pages})",
        min_value=1,
        max_value=total_pages,
        value=1
    )
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # Display table
    st.dataframe(
        data.iloc[start_idx:end_idx],
        use_container_width=True
    )
    
    st.caption(f"Showing {start_idx + 1}-{min(end_idx, len(data))} of {len(data)} rows")
    
    # Download button
    st.markdown("---")
    
    csv = data.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"energy_data_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )