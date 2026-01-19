"""
app.py
🏁 Main Streamlit Dashboard Application
"""
import streamlit as st
import logging
from datetime import datetime
import sys

# Add src to path
sys.path.insert(0, '/app/src')

from config import Config
from data.loader import DataLoader
from data.processor import DataProcessor
from components.header import render_header
from components.kpi_cards import render_kpi_cards
from components.forecast_chart import render_forecast_chart
from components.performance_chart import render_performance_metrics
from components.feature_importance import render_feature_importance
from components.data_table import render_data_table

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title=Config.APP_TITLE,
    page_icon=Config.APP_ICON,
    layout=Config.PAGE_LAYOUT,
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Remove padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 1.1rem;
        font-weight: 500;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: #262730;
        padding: 8px;
        border-radius: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        font-size: 1.1rem;
        font-weight: 600;
        background-color: transparent;
        border-radius: 4px;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #1f77b4;
    }
    
    /* Charts */
    .js-plotly-plot {
        border-radius: 8px;
    }
    
    /* Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 4px;
        height: 3rem;
        font-weight: 600;
    }
    
    /* Data table */
    .dataframe {
        font-size: 0.9rem;
    }
    
    /* Info boxes */
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application"""
    
    try:
        # Initialize data loader
        loader = DataLoader(
            bucket_name=Config.S3_BUCKET,
            region=Config.AWS_REGION
        )
        
        # Render header
        render_header()
        
        # Create tabs
        tab1, tab2, tab3 = st.tabs([
            "🏠 Forecast",
            "⚙️ Model Performance",
            "🗄️ Data Explorer"
        ])
        
        # ============ TAB 1: FORECAST ============
        with tab1:
            st.markdown("### 📊 Electricity Demand Forecast")
            st.markdown("Real-time forecasting for the next 24 hours with confidence intervals")
            
            # Load data
            with st.spinner("Loading forecast data..."):
                predictions = loader.load_latest_predictions()
                historical = loader.load_historical_data(days=7)
                metadata = loader.load_model_metadata()
            
            if predictions is None:
                st.warning("⚠️ No prediction data available. Please run Training service first.")
                st.info("💡 Training service creates predictions in: `s3://bucket/predictions/latest/`")
                st.stop()
            
            # Display last update time
            if metadata:
                trained_at = metadata.get('training', {}).get('completed_at', 'N/A')
                st.caption(f"📅 Model last trained: {trained_at}")

            # Display last update time
            if predictions:
                generated_at = predictions.get('generated_at')
                if generated_at:
                    from datetime import datetime
                    gen_time = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                    age_minutes = (datetime.now(gen_time.tzinfo) - gen_time).total_seconds() / 60
        
                    if age_minutes < 60:
                        st.success(f"✅ Predictions are fresh (updated {age_minutes:.0f} min ago)")
                    elif age_minutes < 180:
                        st.warning(f"⚠️ Predictions may be stale (updated {age_minutes:.0f} min ago)")
                    else:
                        st.error(f"❌ Predictions are old (updated {age_minutes/60:.1f} hours ago)")
            
            st.markdown("---")
            
            # KPI Cards
            render_kpi_cards(predictions, historical)
            
            st.markdown("---")
            
            # Main forecast chart
            render_forecast_chart(predictions, historical)
            
            st.markdown("---")
            
            # Key drivers
            st.markdown("### 🔍 Key Drivers")
            st.caption("Current weather conditions affecting electricity demand")
            
            if historical is not None and not historical.empty:

                # Derive time features from datetime
                if 'datetime' in historical.columns:
                    historical['is_weekend'] = pd.to_datetime(historical['datetime']).dt.dayofweek.isin([5, 6]).astype(int)
                    historical['hour'] = pd.to_datetime(historical['datetime']).dt.hour

                col1, col2, col3, col4 = st.columns(4)
                
                latest = historical.iloc[-1]
                
                with col1:
                    temp = latest.get('temperature', 0)
                    temp_status = "High 🔥" if temp > 32 else "Normal" if temp > 25 else "Low ❄️"
                    st.metric("🌡️ Temperature", f"{temp:.1f}°C", delta=temp_status)
                
                with col2:
                    hum = latest.get('humidity', 0)
                    hum_status = "High 💧" if hum > 80 else "Normal" if hum > 60 else "Low"
                    st.metric("💧 Humidity", f"{hum:.0f}%", delta=hum_status)
                
                with col3:
                    weekend = latest.get('is_weekend', 0) if 'is_weekend' in latest else 0
                    st.metric("📅 Day Type", "Weekend" if weekend else "Weekday")
                
                with col4:
                    hour = latest.get('hour', 0) if 'hour' in latest else 0
                    st.metric("🕐 Hour", f"{hour:02d}:00")

            else:
                st.info("No historical weather data available")
        
        # ============ TAB 2: MODEL PERFORMANCE ============
        with tab2:
            st.markdown("### ⚙️ Model Performance Metrics")
            st.markdown("Comprehensive model evaluation and feature analysis")
            
            # Load model data
            with st.spinner("Loading model metrics..."):
                metadata = loader.load_model_metadata()
                metrics = loader.load_model_metrics()
            
            if metadata is None or metrics is None:
                st.warning("⚠️ Model metrics not available")
                st.info("💡 Training service creates metrics in: `s3://bucket/models/xgboost/latest/`")
                st.stop()
            
            # Model info
            col1, col2, col3 = st.columns(3)
            
            with col1:
                model_type = metadata.get('model_type', 'N/A').upper()
                st.info(f"**🤖 Model Type:** {model_type}")
            
            with col2:
                version = metadata.get('version', 'N/A')
                st.info(f"**🏷️ Version:** {version}")
            
            with col3:
                trained_at = metadata.get('training', {}).get('completed_at', 'N/A')
                if trained_at != 'N/A':
                    trained_at = trained_at.split('T')[0]  # Just date
                st.info(f"**📅 Last Trained:** {trained_at}")
            
            st.markdown("---")
            
            # Metrics cards
            render_performance_metrics(metrics)
            
            st.markdown("---")
            
            # Training details
            with st.expander("📊 Training Details", expanded=False):
                training_info = metadata.get('training', {})
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Total Samples", f"{training_info.get('total_samples', 0):,}")
                    st.metric("Train Samples", f"{training_info.get('train_samples', 0):,}")
                
                with col2:
                    st.metric("Validation Samples", f"{training_info.get('val_samples', 0):,}")
                    st.metric("Test Samples", f"{training_info.get('test_samples', 0):,}")
                
                duration = training_info.get('duration_seconds', 0)
                st.caption(f"⏱️ Training Duration: {duration:.1f}s")
            
            st.markdown("---")
            
            # Feature importance is stored in metrics.json, not predictions
            feature_importance = metrics.get('feature_importance', {})
            if feature_importance:
                render_feature_importance(feature_importance)
            else:
                st.warning("Feature importance data not available in predictions")
        
        # ============ TAB 3: DATA EXPLORER ============
        with tab3:
            st.markdown("### 🗄️ Data Explorer")
            st.markdown("Browse and download raw feature data")
            
            # Load data
            with st.spinner("Loading data..."):
                data = loader.load_historical_data(days=30)
            
            if data is None or data.empty:
                st.warning("⚠️ No historical data available")
                st.info("💡 Processing service creates data in: `s3://bucket/gold/features/`")
                st.stop()
            
            # Data info
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📊 Total Records", f"{len(data):,}")
            
            with col2:
                if 'datetime' in data.columns:
                    date_range = f"{data['datetime'].min().date()} to {data['datetime'].max().date()}"
                    st.info(f"**📅 Date Range**\n\n{date_range}")
            
            with col3:
                missing = data.isnull().sum().sum()
                missing_pct = (missing / (len(data) * len(data.columns))) * 100
                st.metric("⚠️ Missing Values", f"{missing:,} ({missing_pct:.2f}%)")
            
            st.markdown("---")
            
            # Data table
            render_data_table(data)
    
    except Exception as e:
        st.error(f"💥 Application Error: {str(e)}")
        logger.error(f"Application error: {e}", exc_info=True)
        
        with st.expander("🔍 Error Details"):
            st.code(str(e))
            st.caption("Please check CloudWatch Logs for more details")

if __name__ == "__main__":
    main()