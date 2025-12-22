"""
etl/weather_cleaner.py
🧹 Weather Data Cleaner - Bronze → Silver
"""
import logging
import pandas as pd
import pytz
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WeatherCleaner:
    """
    Làm sạch dữ liệu thời tiết từ Bronze layer
    
    Nhiệm vụ:
    1. Parse JSON structure thành DataFrame
    2. Convert timezone UTC → UTC+7
    3. Handle missing values
    4. Remove outliers
    5. Standardize column names
    """
    
    def __init__(
        self,
        source_tz: str = "UTC",
        target_tz: str = "Asia/Ho_Chi_Minh",
        outlier_zscore: float = 3.5
    ):
        """
        Args:
            source_tz: Source timezone (API default)
            target_tz: Target timezone (Vietnam)
            outlier_zscore: Z-score threshold for outlier detection
        """
        self.source_tz = pytz.timezone(source_tz)
        self.target_tz = pytz.timezone(target_tz)
        self.outlier_zscore = outlier_zscore
    
    def clean(self, raw_data: Dict[str, Any], query_date: str) -> pd.DataFrame:
        """
        Main cleaning pipeline
        
        Args:
            raw_data: Raw JSON data from Bronze
            query_date: Date string (YYYY-MM-DD)
        
        Returns:
            pd.DataFrame: Cleaned data
        """
        logger.info(f"🧹 Cleaning weather data for {query_date}")
        
        # Step 1: Parse JSON to DataFrame
        df = self._parse_json(raw_data, query_date)
        logger.info(f"  → Parsed {len(df)} hourly records")
        
        # Step 2: Convert timezone
        df = self._convert_timezone(df)
        logger.info(f"  → Converted timezone to {self.target_tz}")
        
        # Step 3: Handle missing values
        df = self._handle_missing_values(df)
        logger.info(f"  → Handled missing values")
        
        # Step 4: Remove outliers
        df = self._remove_outliers(df)
        logger.info(f"  → Removed outliers (kept {len(df)} records)")
        
        # Step 5: Standardize columns
        df = self._standardize_columns(df)
        logger.info(f"  → Standardized column names")
        
        # Step 6: Add metadata
        df = self._add_metadata(df, query_date)
        
        return df
    
    def _parse_json(self, raw_data: Dict[str, Any], query_date: str) -> pd.DataFrame:
        """
        Parse Visual Crossing JSON structure
        
        JSON structure:
        {
            "days": [
                {
                    "datetime": "2024-12-20",
                    "hours": [
                        {
                            "datetime": "00:00:00",
                            "temp": 24.0,
                            "humidity": 78.0,
                            ...
                        }
                    ]
                }
            ]
        }
        """
        try:
            # Extract hourly data
            days = raw_data.get('days', [])
            if not days:
                raise ValueError("No 'days' field in raw data")
            
            # Get first day (should only have 1 day per file)
            day_data = days[0]
            hours = day_data.get('hours', [])
            
            if not hours:
                raise ValueError("No 'hours' field in day data")
            
            # Convert to DataFrame
            df = pd.DataFrame(hours)
            
            # Add date column
            df['date'] = query_date
            
            # Create full datetime
            df['datetime_str'] = df['date'] + ' ' + df['datetime']
            df['datetime'] = pd.to_datetime(df['datetime_str'])
            
            # Drop temporary columns
            df = df.drop(['datetime_str'], axis=1)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to parse JSON: {e}")
            raise
    
    def _convert_timezone(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert datetime from UTC to Vietnam timezone (UTC+7)
        """
        # Localize to source timezone
        df['datetime'] = df['datetime'].dt.tz_localize(self.source_tz)
        
        # Convert to target timezone
        df['datetime'] = df['datetime'].dt.tz_convert(self.target_tz)
        
        # Remove timezone info (keep only naive datetime)
        df['datetime'] = df['datetime'].dt.tz_localize(None)
        
        return df
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Handle missing values:
        - Forward fill cho numerical columns (use last valid value)
        - Drop rows nếu quá nhiều missing
        """
        numeric_cols = ['temp', 'humidity', 'precip', 'windspeed', 'cloudcover']
        
        # Check missing ratio
        missing_ratio = df[numeric_cols].isnull().sum() / len(df)
        
        for col in numeric_cols:
            if missing_ratio[col] > 0:
                logger.warning(f"  ⚠️ {col}: {missing_ratio[col]:.1%} missing")
                
                # Forward fill (use last valid value)
                df[col] = df[col].fillna(method='ffill')
                
                # Backward fill for first rows
                df[col] = df[col].fillna(method='bfill')
                
                # If still missing, fill with median
                if df[col].isnull().any():
                    median_value = df[col].median()
                    df[col] = df[col].fillna(median_value)
                    logger.warning(f"  → Filled remaining with median: {median_value}")
        
        return df
    
    def _remove_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove outliers using Z-score method
        
        Reasonable ranges for Vietnam:
        - temp: 15-40°C
        - humidity: 30-100%
        - windspeed: 0-50 km/h
        - cloudcover: 0-100%
        """
        # Define reasonable ranges
        ranges = {
            'temp': (15, 40),
            'humidity': (30, 100),
            'windspeed': (0, 50),
            'cloudcover': (0, 100),
            'precip': (0, 100)  # mm/h
        }
        
        initial_len = len(df)
        
        # Remove obvious outliers (outside reasonable range)
        for col, (min_val, max_val) in ranges.items():
            if col in df.columns:
                outliers = (df[col] < min_val) | (df[col] > max_val)
                if outliers.any():
                    logger.warning(f"  ⚠️ Removing {outliers.sum()} outliers in {col}")
                    df = df[~outliers]
        
        removed = initial_len - len(df)
        if removed > 0:
            logger.info(f"  → Removed {removed} outlier records")
        
        return df
    
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename columns cho consistent
        """
        column_mapping = {
            'temp': 'temperature',
            'humidity': 'humidity',
            'precip': 'precipitation',
            'windspeed': 'wind_speed',
            'cloudcover': 'cloud_cover'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Select only needed columns
        required_cols = ['datetime', 'temperature', 'humidity', 'precipitation', 
                        'wind_speed', 'cloud_cover']
        
        df = df[required_cols]
        
        return df
    
    def _add_metadata(self, df: pd.DataFrame, query_date: str) -> pd.DataFrame:
        """
        Add metadata columns
        """
        df['source'] = 'visual_crossing'
        df['processed_at'] = datetime.utcnow()
        df['query_date'] = query_date
        
        return df
    
    def validate_output(self, df: pd.DataFrame) -> bool:
        """
        Validate cleaned data
        
        Returns:
            bool: True if valid
        """
        # Check required columns
        required_cols = ['datetime', 'temperature', 'humidity', 'precipitation',
                        'wind_speed', 'cloud_cover']
        
        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Check for any remaining nulls
        null_counts = df[required_cols].isnull().sum()
        if null_counts.any():
            logger.warning(f"⚠️ Still have nulls: {null_counts[null_counts > 0]}")
        
        # Check data types
        if not pd.api.types.is_datetime64_any_dtype(df['datetime']):
            raise ValueError("datetime column must be datetime type")
        
        logger.info("✅ Data validation passed")
        return True