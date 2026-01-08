"""
etl/weather_cleaner.py
🧹 Weather Data Cleaner - Bronze → Silver (Physical Cleaning)
"""
import logging
import pandas as pd
import pytz
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WeatherCleaner:
    """
    Physical Cleaning: Bronze → Silver
    
    Nhiệm vụ:
    1. Flattening: Duỗi phẳng JSON nested
    2. Type Casting: Ép kiểu dữ liệu chuẩn
    3. Deduplication: Loại bỏ trùng lặp
    4. Column Selection: Chọn cột cần thiết
    """
    
    def __init__(
        self,
        source_tz: str = "UTC",
        target_tz: str = "Asia/Ho_Chi_Minh"
    ):
        self.source_tz = pytz.timezone(source_tz)
        self.target_tz = pytz.timezone(target_tz)
    
    def clean(self, raw_data: Dict[str, Any], query_date: str) -> pd.DataFrame:
        """
        Main cleaning pipeline: Bronze → Silver
        
        Args:
            raw_data: Raw JSON from Bronze
            query_date: Date string (YYYY-MM-DD)
        
        Returns:
            pd.DataFrame: Cleaned Silver data
        """
        logger.info(f"☀️ Cleaning weather data for {query_date}")
        
        # Step 1: Flattening
        df = self._flatten_json(raw_data, query_date)
        logger.info(f"  → Flattened: {len(df)} hourly records")
        
        # Step 2: Type Casting
        df = self._cast_types(df)
        logger.info(f"  → Type cast completed")
        
        # Step 3: Deduplication
        df = self._deduplicate(df)
        logger.info(f"  → Deduplicated: {len(df)} rows")
        
        # Step 4: Column Selection
        df = self._select_columns(df)
        logger.info(f"  → Selected {len(df.columns)} columns")
        
        return df
    
    def _flatten_json(self, raw_data: Dict[str, Any], query_date: str) -> pd.DataFrame:
        """
        Flattening: Duỗi phẳng JSON nested structure
        
        JSON: {"days": [{"hours": [...]}]} → DataFrame phẳng (1 row/hour)
        """
        try:
            days = raw_data.get('days', [])
            if not days:
                raise ValueError("No 'days' field in raw data")
            
            day_data = days[0]
            hours = day_data.get('hours', [])
            
            if not hours:
                raise ValueError("No 'hours' field in day data")
            
            # Convert to DataFrame
            df = pd.DataFrame(hours)
            
            # Create full datetime: date + hour
            df['hour'] = pd.to_datetime(df['datetime'], format='%H:%M:%S').dt.hour
            df['datetime'] = pd.to_datetime(query_date) + pd.to_timedelta(df['hour'], unit='h')
            
            # Drop temporary column
            df = df.drop(['hour'], axis=1, errors='ignore')
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to flatten JSON: {e}")
            raise
    
    def _cast_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Type Casting: Ép kiểu dữ liệu chuẩn
        
        - datetime → datetime64[ns] (UTC+7)
        - temp → float32
        - humidity → float32
        """
        # Datetime: Localize to Vietnam timezone (data đã ở UTC+7)
        df['datetime'] = df['datetime'].dt.tz_localize(self.target_tz)
        df['datetime'] = df['datetime'].dt.tz_localize(None)  # Remove timezone info
        
        # Numeric columns
        numeric_cols = {
            'temp': 'float32',
            'humidity': 'float32',
            'precip': 'float32',
            'windspeed': 'float32',
            'cloudcover': 'float32'
        }
        
        for col, dtype in numeric_cols.items():
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(dtype)
        
        return df
    
    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Deduplication: Loại bỏ dòng trùng lặp
        
        Keep first occurrence, drop duplicates by datetime
        """
        initial_len = len(df)
        df = df.drop_duplicates(subset=['datetime'], keep='first')
        
        removed = initial_len - len(df)
        if removed > 0:
            logger.warning(f"  ⚠️ Removed {removed} duplicate rows")
        
        return df
    
    def _select_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Column Selection: Giữ lại cột cần thiết, vứt bỏ metadata rác
        
        Keep: datetime, temp, humidity, precip, windspeed, cloudcover
        """
        # Rename to standard names
        column_mapping = {
            'temp': 'temperature',
            'precip': 'precipitation',
            'windspeed': 'wind_speed',
            'cloudcover': 'cloud_cover'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Select only needed columns
        required_cols = [
            'datetime', 
            'temperature', 
            'humidity', 
            'precipitation', 
            'wind_speed', 
            'cloud_cover'
        ]
        
        # Keep only existing columns
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols]
        
        return df
    
    def validate_output(self, df: pd.DataFrame) -> bool:
        """Validate cleaned Silver data"""
        if df.empty:
            logger.warning("⚠️ Empty DataFrame")
            return False
        
        # Check required columns
        required_cols = ['datetime', 'temperature']
        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Check datetime type
        if not pd.api.types.is_datetime64_any_dtype(df['datetime']):
            raise ValueError("datetime must be datetime type")
        
        logger.info("✅ Weather Silver validation passed")
        return True