"""
etl/feature_eng.py
⚙️ Feature Engineering - Silver → Gold
Tạo features cho ML model
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Tạo features từ Silver data
    
    Features categories:
    1. Time-based features (hour, day_of_week, month, etc.)
    2. Lag features (giá trị n giờ trước)
    3. Rolling features (trung bình n giờ)
    4. Cyclical features (sin/cos encoding cho time)
    5. Holiday features
    6. Weather interaction features
    """
    
    def __init__(
        self,
        lag_hours: List[int] = [1, 2, 3, 6, 12, 24],
        rolling_windows: List[int] = [3, 6, 12, 24],
        vietnam_holidays: List[str] = None
    ):
        """
        Args:
            lag_hours: List số giờ lag cần tạo
            rolling_windows: List window sizes cho rolling mean
            vietnam_holidays: List các ngày lễ Vietnam (MM-DD format)
        """
        self.lag_hours = lag_hours
        self.rolling_windows = rolling_windows
        self.vietnam_holidays = vietnam_holidays or [
            "01-01", "04-30", "05-01", "09-02"
        ]
    
    def create_features(
        self,
        weather_df: pd.DataFrame,
        electricity_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Main feature engineering pipeline
        
        Args:
            weather_df: Cleaned weather data (Silver)
            electricity_df: Cleaned electricity data (Silver)
        
        Returns:
            pd.DataFrame: Feature table (Gold)
        """
        logger.info("⚙️ Starting feature engineering...")
        
        # Step 1: Merge weather + electricity
        df = self._merge_datasets(weather_df, electricity_df)
        logger.info(f"  → Merged datasets: {len(df)} rows")

        # ✅ THÊM: Tạo target column từ electricity data
        df = self._create_target_column(df)
        logger.info(f"  → Created target column")
        
        # Step 2: Time-based features
        df = self._create_time_features(df)
        logger.info(f"  → Created time features")
        
        # Step 3: Lag features
        df = self._create_lag_features(df)
        logger.info(f"  → Created lag features")
        
        # Step 4: Rolling features
        df = self._create_rolling_features(df)
        logger.info(f"  → Created rolling features")
        
        # Step 5: Cyclical encoding
        df = self._create_cyclical_features(df)
        logger.info(f"  → Created cyclical features")
        
        # Step 6: Holiday features
        df = self._create_holiday_features(df)
        logger.info(f"  → Created holiday features")
        
        # Step 7: Interaction features
        df = self._create_interaction_features(df)
        logger.info(f"  → Created interaction features")
        
        # Step 8: Drop rows with NaN (từ lag/rolling)
        initial_len = len(df)
        df = df.dropna()
        dropped = initial_len - len(df)
        if dropped > 0:
            logger.info(f"  → Dropped {dropped} rows with NaN")
        
        logger.info(f"✅ Feature engineering complete: {len(df)} rows, {len(df.columns)} features")
        
        return df
    
    def _merge_datasets(
        self,
        weather_df: pd.DataFrame,
        electricity_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Merge weather và electricity data"""
        logger.info("🔗 Merging weather and electricity data")
    
        # Ensure datetime columns
        weather_df['datetime'] = pd.to_datetime(weather_df['datetime'])
        electricity_df['datetime'] = pd.to_datetime(electricity_df['datetime'])

        logger.info(f"📊 Weather columns: {weather_df.columns.tolist()}")
        logger.info(f"📊 Electricity columns: {electricity_df.columns.tolist()}")
    
        # Merge on datetime (outer join để giữ tất cả timestamps)
        merged = weather_df.merge(
        electricity_df,
        on='datetime',
        how='outer',
        suffixes=('_weather', '_electricity')
        )
    
        # Sort by datetime
        merged = merged.sort_values('datetime').reset_index(drop=True)
    
        # ✅ THÊM: Forward fill weather data (vì weather có 1 row/day, electricity có 24 rows/day)
        weather_cols = [col for col in merged.columns if 'weather' in col or col in ['temperature', 'humidity', 'wind_speed', 'precipitation', 'cloud_cover']]
    
        logger.info(f"🔧 Forward filling weather columns: {weather_cols}")
        for col in weather_cols:
            if col in merged.columns:
                merged[col] = merged[col].fillna(method='ffill')
                merged[col] = merged[col].fillna(method='bfill')  # Backup for first rows
    
        logger.info(f"📊 Merged columns ({len(merged.columns)}): {merged.columns.tolist()}")

        numeric_cols = merged.select_dtypes(include=['float64', 'int64']).columns
        elec_numeric = [col for col in numeric_cols if 'temperature' not in col.lower() 
                and 'humidity' not in col.lower() and 'wind' not in col.lower()]
        logger.info(f"📊 Electricity numeric columns: {elec_numeric[:10]}")
    
        return merged
    
    def _create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo time-based features
        """
        df['hour'] = df['datetime'].dt.hour
        df['day_of_week'] = df['datetime'].dt.dayofweek  # 0=Monday
        df['day_of_month'] = df['datetime'].dt.day
        df['month'] = df['datetime'].dt.month
        df['quarter'] = df['datetime'].dt.quarter
        df['year'] = df['datetime'].dt.year
        
        # Is weekend
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        
        # Part of day
        df['part_of_day'] = pd.cut(
            df['hour'],
            bins=[0, 6, 12, 18, 24],
            labels=['night', 'morning', 'afternoon', 'evening'],
            include_lowest=True
        )
        
        return df
    
    def _create_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo lag features (giá trị n giờ trước)
        
        Ví dụ: temperature_lag_1 = temperature của 1 giờ trước
        """
        # Columns cần tạo lag
        lag_columns = [
            'temperature', 'humidity', 'wind_speed',
            # Có thể add thêm electricity columns nếu có
        ]
        
        # Filter ra các columns thực sự tồn tại
        lag_columns = [col for col in lag_columns if col in df.columns]
        
        for col in lag_columns:
            for lag in self.lag_hours:
                df[f'{col}_lag_{lag}'] = df[col].shift(lag)
        
        return df
    
    def _create_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo rolling mean features (trung bình n giờ)
        
        Ví dụ: temperature_rolling_mean_3 = trung bình temperature 3 giờ qua
        """
        rolling_columns = [
            'temperature', 'humidity', 'wind_speed', 'precipitation'
        ]
        
        rolling_columns = [col for col in rolling_columns if col in df.columns]
        
        for col in rolling_columns:
            for window in self.rolling_windows:
                df[f'{col}_rolling_mean_{window}'] = df[col].rolling(
                    window=window,
                    min_periods=1
                ).mean()
                
                df[f'{col}_rolling_std_{window}'] = df[col].rolling(
                    window=window,
                    min_periods=1
                ).std()
        
        return df
    
    def _create_cyclical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cyclical encoding cho time features
        
        Ví dụ: hour 23 và hour 0 rất gần nhau, nhưng về số thì xa
        → Encode bằng sin/cos để model hiểu được tính chu kỳ
        """
        # Hour (24-hour cycle)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # Day of week (7-day cycle)
        df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        # Month (12-month cycle)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        
        return df
    
    def _create_holiday_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo holiday features
        """
        # Create date string (MM-DD)
        df['date_str'] = df['datetime'].dt.strftime('%m-%d')
        
        # Is holiday
        df['is_holiday'] = df['date_str'].isin(self.vietnam_holidays).astype(int)
        
        # Drop temporary column
        df = df.drop('date_str', axis=1)
        
        return df
    
    def _create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo interaction features (kết hợp nhiều features)
        
        Ví dụ: temp_humidity = temperature * humidity
        """
        if 'temperature' in df.columns and 'humidity' in df.columns:
            # Heat index (cảm giác nóng)
            df['heat_index'] = df['temperature'] * (df['humidity'] / 100)
        
        if 'wind_speed' in df.columns and 'temperature' in df.columns:
            # Wind chill (cảm giác lạnh do gió)
            df['wind_chill'] = df['temperature'] - (df['wind_speed'] * 0.5)
        
        if 'precipitation' in df.columns and 'humidity' in df.columns:
            # Rain probability indicator
            df['rain_indicator'] = ((df['precipitation'] > 0) & (df['humidity'] > 80)).astype(int)
        
        return df
    
    def get_feature_importance_groups(self) -> dict:
        """
        Nhóm features theo category để dễ phân tích feature importance
        
        Returns:
            dict: {category: [feature_names]}
        """
        return {
            'time': [
                'hour', 'day_of_week', 'day_of_month', 'month', 'quarter',
                'is_weekend', 'is_holiday', 'hour_sin', 'hour_cos',
                'day_of_week_sin', 'day_of_week_cos', 'month_sin', 'month_cos'
            ],
            'weather_raw': [
                'temperature', 'humidity', 'precipitation', 'wind_speed', 'cloud_cover'
            ],
            'weather_lag': [
                f'{col}_lag_{lag}'
                for col in ['temperature', 'humidity', 'wind_speed']
                for lag in self.lag_hours
            ],
            'weather_rolling': [
                f'{col}_rolling_{stat}_{window}'
                for col in ['temperature', 'humidity', 'wind_speed', 'precipitation']
                for stat in ['mean', 'std']
                for window in self.rolling_windows
            ],
            'interaction': [
                'heat_index', 'wind_chill', 'rain_indicator'
            ]
        }
    
    def validate_features(self, df: pd.DataFrame) -> bool:
        """
        Validate feature table
        """
        # Check for infinite values
        inf_cols = df.columns[df.isin([np.inf, -np.inf]).any()].tolist()
        if inf_cols:
            logger.warning(f"⚠️ Infinite values in: {inf_cols}")
            # Replace inf with NaN
            df[inf_cols] = df[inf_cols].replace([np.inf, -np.inf], np.nan)
        
        # Check for high percentage of NaN
        null_ratio = df.isnull().sum() / len(df)
        high_null = null_ratio[null_ratio > 0.5].index.tolist()
        if high_null:
            logger.warning(f"⚠️ High null ratio (>50%) in: {high_null}")
        
        # Check datetime is sorted
        if not df['datetime'].is_monotonic_increasing:
            logger.warning("⚠️ Datetime not sorted, sorting...")
            df = df.sort_values('datetime').reset_index(drop=True)
        
        logger.info("✅ Feature validation passed")
        return True
    



    def _create_target_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo target column từ electricity signals đã merge
        """
        logger.info("🎯 Creating target column...")
    
        # ✅ Tìm columns liên quan đến total load/demand
        # Sau khi merge_signals, columns sẽ có format: {signal_name}_{original_column}
    
        possible_patterns = [
        'total_load',           # Từ signal total_load
        'powerConsumption',     # Từ API Electricity Maps
        'consumption',
        'load',
        'demand'
        ]
    
        # Tìm column phù hợp
        target_col = None
        for pattern in possible_patterns:
            matching_cols = [col for col in df.columns if pattern.lower() in col.lower()]
        
            if matching_cols:
                # Ưu tiên column có 'total' hoặc số lớn nhất
                for col in matching_cols:
                    # Bỏ qua các column metadata
                    if any(skip in col.lower() for skip in ['signal', 'source', 'processed', 'query']):
                        continue
                
                    # Kiểm tra là numeric
                    if df[col].dtype in ['float64', 'int64']:
                        target_col = col
                        break
        
            if target_col:
                break
    
        if target_col:
            df['electricity_demand'] = df[target_col]
            logger.info(f"  ✅ Created target 'electricity_demand' from '{target_col}'")
        else:
            # Fallback: Dùng column numeric đầu tiên từ electricity
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        
            # Loại bỏ weather columns
            weather_keywords = ['temperature', 'humidity', 'wind', 'precipitation', 'cloud', 'pressure']
            electricity_cols = [
                col for col in numeric_cols 
                if not any(keyword in col.lower() for keyword in weather_keywords)
                and not any(skip in col.lower() for skip in ['signal', 'source', 'processed', 'query', 'hour', 'day', 'month', 'year'])
            ]
        
            if electricity_cols:
                target_col = electricity_cols[0]
                df['electricity_demand'] = df[target_col]
                logger.info(f"  ⚠️ Using fallback target '{target_col}'")
            else:
                logger.error("❌ Cannot find suitable target column!")
                logger.error(f"Available columns: {df.columns.tolist()}")
                raise ValueError("No suitable electricity demand column found")
    
        # Validate target
        if df['electricity_demand'].isnull().all():
            raise ValueError("Target column is all NaN!")
    
        null_ratio = df['electricity_demand'].isnull().sum() / len(df)
        if null_ratio > 0.5:
            logger.warning(f"⚠️ Target has {null_ratio*100:.1f}% missing values")
    
        return df