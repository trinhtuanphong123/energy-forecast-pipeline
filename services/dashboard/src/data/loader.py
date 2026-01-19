"""
data/loader.py
📥 Data Loader với Streamlit Caching
"""
import logging
import json
import pandas as pd
import boto3
import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DataLoader:
    """
    Load data từ S3 với Streamlit caching
    """
    
    def __init__(self, bucket_name: str, region: str = "ap-southeast-2"):
        self.bucket_name = bucket_name
        self.region = region
    
    @staticmethod
    @st.cache_resource
    def get_s3_client(region: str):
        """Get S3 client (cached)"""
        return boto3.client('s3', region_name=region)
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def load_latest_predictions(_self) -> Optional[Dict]:
        """
        Load latest predictions from S3
        
        Returns:
            Dict: Predictions data
        """
        try:
            s3_client = _self.get_s3_client(_self.region)
            
            # Try to load from predictions/latest/
            key = "predictions/latest/predictions.json"
            
            logger.info(f"Loading predictions from s3://{_self.bucket_name}/{key}")
            
            response = s3_client.get_object(
                Bucket=_self.bucket_name,
                Key=key
            )
            
            data = json.loads(response['Body'].read().decode('utf-8'))
            
            logger.info(f"✅ Loaded {len(data.get('predictions', []))} predictions")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to load predictions: {e}")
            return None
    
    @st.cache_data(ttl=300)
    def load_model_metadata(_self, model_type: str = "xgboost") -> Optional[Dict]:
        """
        Load model metadata from S3
        
        Args:
            model_type: Model type (xgboost, lstm, etc.)
        
        Returns:
            Dict: Model metadata
        """
        try:
            s3_client = _self.get_s3_client(_self.region)
            
            key = f"models/{model_type}/latest/metadata.json"
            
            logger.info(f"Loading metadata from s3://{_self.bucket_name}/{key}")
            
            response = s3_client.get_object(
                Bucket=_self.bucket_name,
                Key=key
            )
            
            metadata = json.loads(response['Body'].read().decode('utf-8'))
            
            logger.info(f"✅ Loaded model metadata: {metadata.get('version')}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to load metadata: {e}")
            return None
    
    @st.cache_data(ttl=300)
    def load_model_metrics(_self, model_type: str = "xgboost") -> Optional[Dict]:
        """
        Load model metrics from S3
        
        Args:
            model_type: Model type
        
        Returns:
            Dict: Model metrics
        """
        try:
            s3_client = _self.get_s3_client(_self.region)
            
            key = f"models/{model_type}/latest/metrics.json"
            
            response = s3_client.get_object(
                Bucket=_self.bucket_name,
                Key=key
            )
            
            metrics = json.loads(response['Body'].read().decode('utf-8'))
            
            logger.info(f"✅ Loaded model metrics")
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to load metrics: {e}")
            return None
    
    @st.cache_data(ttl=600)  # Cache for 10 minutes
    def load_historical_data(
        _self,
        days: int = 30
    ) -> Optional[pd.DataFrame]:
        """
        Load historical data from S3 Gold layer
        
        Args:
            days: Number of days to load
        
        Returns:
            pd.DataFrame: Historical data
        """
        try:
            logger.info(f"Loading {days} days of historical data...")
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # List parquet files
            s3_client = _self.get_s3_client(_self.region)
            
            prefix = "gold/canonical/"
            
            # List all files in Gold layer
            response = s3_client.list_objects_v2(
                Bucket=_self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                logger.warning("No Gold data found")
                return None
            
            # Filter parquet files
            parquet_keys = [
                obj['Key'] for obj in response['Contents']
                if obj['Key'].endswith('/data.parquet')
            ]
            
            # Load latest file (for demo)
            # In production, filter by date range
            if not parquet_keys:
                return None
            
            # Load first parquet file
            latest_key = sorted(parquet_keys)[-1]
            
            s3_uri = f"s3://{_self.bucket_name}/{latest_key}"
            
            logger.info(f"Loading from {s3_uri}")
            
            df = pd.read_parquet(s3_uri)
            
            # Convert datetime
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
            
            # Filter by date range
            df = df[df['datetime'] >= start_date]
            
            logger.info(f"✅ Loaded {len(df)} rows")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to load historical data: {e}")
            return None
    
    def get_latest_actual_load(_self, df: pd.DataFrame) -> Optional[float]:
        """
        Get latest actual load value
        
        Args:
            df: Historical dataframe
        
        Returns:
            float: Latest load value
        """
        if df is None or df.empty:
            return None
        
        # Assume there's a target column
        # You may need to adjust based on actual column name
        target_cols = ['electricity_demand', 'total_load', 'load']
        
        for col in target_cols:
            if col in df.columns:
                return df[col].iloc[-1]
        
        return None

    @st.cache_data(ttl=300)
    def load_latest_predictions(_self) -> Optional[Dict]:
        """Load latest predictions with new format support"""
        try:
            s3_client = _self.get_s3_client(_self.region)
            key = "predictions/latest/predictions.json"
            
            response = s3_client.get_object(Bucket=_self.bucket_name, Key=key)
            data = json.loads(response['Body'].read().decode('utf-8'))
            
            # Handle new single-prediction format from Models PREDICT mode
            if 'predicted_value' in data:
                # Convert to array format for compatibility
                return {
                    'predictions': [{
                        'datetime': data.get('prediction_for'),
                        'predicted': data.get('predicted_value'),
                        'confidence_lower': data.get('confidence_lower'),
                        'confidence_upper': data.get('confidence_upper')
                    }],
                    'model_type': data.get('model_type'),
                    'generated_at': data.get('generated_at'),
                    'based_on_data_until': data.get('based_on_data_until')
                }
            
            # Legacy format: return as-is
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to load predictions: {e}")
            return None