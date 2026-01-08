"""
etl/canonical_merger.py
🔗 Canonical Table Merger - Silver → Gold (Logical Cleaning)
"""
import logging
import pandas as pd
import numpy as np
from typing import Tuple

logger = logging.getLogger(__name__)

class CanonicalMerger:
    """
    Logical Cleaning: Silver → Gold (Canonical Table)
    
    Nhiệm vụ:
    1. Time Alignment: Đồng bộ thời gian
    2. Merging: Join 2 bảng Weather + Electricity
    3. Rename Business: Đặt tên cột theo nghiệp vụ
    4. Imputation: Điền khuyết cơ bản
    5. Outlier Flagging: Đánh dấu bất thường
    
    Output: Canonical Table
    Columns: [datetime, electricity_demand, temperature, humidity, 
              wind_speed, precipitation]
    """
    
    def __init__(self):
        pass
    
    def merge(
        self,
        weather_df: pd.DataFrame,
        electricity_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Main merging pipeline: Silver → Gold (Canonical)
        
        Args:
            weather_df: Weather Silver data
            electricity_df: Electricity Silver data (total_load only)
        
        Returns:
            pd.DataFrame: Canonical Table
        """
        logger.info("🔗 Creating Canonical Table...")
        
        # Step 1: Time Alignment
        weather_df, electricity_df = self._time_alignment(weather_df, electricity_df)
        logger.info(f"  → Time aligned")
        
        # Step 2: Merging (Join)
        df = self._merge_tables(weather_df, electricity_df)
        logger.info(f"  → Merged: {len(df)} rows")
        
        # Step 3: Rename Business
        df = self._rename_business(df)
        logger.info(f"  → Renamed to business names")
        
        # Step 4: Imputation
        df = self._impute_missing(df)
        logger.info(f"  → Imputed missing values")
        
        # Step 5: Outlier Flagging
        df = self._flag_outliers(df)
        logger.info(f"  → Flagged outliers")
        
        # Step 6: Final validation & sorting
        df = self._finalize(df)
        logger.info(f"  → Finalized: {len(df)} rows, {len(df.columns)} columns")
        
        return df
    
    def _time_alignment(
        self,
        weather_df: pd.DataFrame,
        electricity_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Time Alignment: Đồng bộ thời gian
        
        - Đảm bảo cả 2 đều cùng timezone (đã xử lý ở Silver)
        - Resample về cùng tần suất (1 Hour)
        """
        # Ensure datetime type
        weather_df['datetime'] = pd.to_datetime(weather_df['datetime'])
        electricity_df['datetime'] = pd.to_datetime(electricity_df['datetime'])
        
        # Sort by datetime
        weather_df = weather_df.sort_values('datetime').reset_index(drop=True)
        electricity_df = electricity_df.sort_values('datetime').reset_index(drop=True)
        
        # Resample to hourly (if needed)
        # Hiện tại cả 2 đều đã là hourly từ Silver, nên không cần resample
        
        return weather_df, electricity_df
    
    def _merge_tables(
        self,
        weather_df: pd.DataFrame,
        electricity_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merging: Join 2 bảng Weather + Electricity
        
        Join type: INNER JOIN (chỉ giữ rows có đủ cả 2)
        Key: datetime
        """
        # Inner join để đảm bảo có đủ data
        df = pd.merge(
            weather_df,
            electricity_df,
            on='datetime',
            how='inner'
        )
        
        if len(df) == 0:
            logger.warning("⚠️ No overlapping datetime between weather and electricity!")
        
        return df
    
    def _rename_business(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename Business: Đặt tên cột theo nghiệp vụ
        
        - total_load → electricity_demand (Target)
        - Các cột khác giữ nguyên tên nghiệp vụ
        """
        rename_dict = {
            'total_load': 'electricity_demand'
        }
        
        df = df.rename(columns=rename_dict)
        
        return df
    
    def _impute_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Imputation: Điền khuyết cơ bản
        
        - Linear Interpolation cho missing values (nếu gap nhỏ <= 3 hours)
        - Không điền cho gap lớn (> 3 hours)
        """
        numeric_cols = [
            'electricity_demand', 
            'temperature', 
            'humidity', 
            'wind_speed', 
            'precipitation'
        ]
        
        for col in numeric_cols:
            if col not in df.columns:
                continue
            
            # Count missing
            missing_count = df[col].isnull().sum()
            if missing_count == 0:
                continue
            
            logger.info(f"    Imputing {col}: {missing_count} missing values")
            
            # Linear interpolation (limit=3 hours)
            df[col] = df[col].interpolate(
                method='linear',
                limit=3,
                limit_direction='both'
            )
            
            # Fill remaining with forward/backward fill
            df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
        
        return df
    
    def _flag_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Outlier Flagging: Đánh dấu bất thường vật lý
        
        - Temperature > 60°C hoặc < -10°C → Sai cảm biến → Set to NaN
        - Electricity demand < 0 → Impossible → Set to NaN
        - Sau đó impute lại
        """
        # Temperature outliers
        if 'temperature' in df.columns:
            outliers = (df['temperature'] > 60) | (df['temperature'] < -10)
            if outliers.any():
                logger.warning(f"    ⚠️ Temperature outliers: {outliers.sum()} rows")
                df.loc[outliers, 'temperature'] = np.nan
        
        # Electricity demand outliers
        if 'electricity_demand' in df.columns:
            outliers = (df['electricity_demand'] < 0)
            if outliers.any():
                logger.warning(f"    ⚠️ Electricity outliers: {outliers.sum()} rows")
                df.loc[outliers, 'electricity_demand'] = np.nan
        
        # Re-impute after flagging
        df = self._impute_missing(df)
        
        return df
    
    def _finalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Finalize: Sort, select columns, drop remaining NaN
        
        Final columns: [datetime, electricity_demand, temperature, 
                       humidity, wind_speed, precipitation]
        """
        # Select final columns (in order)
        final_cols = [
            'datetime',
            'electricity_demand',
            'temperature',
            'humidity',
            'wind_speed',
            'precipitation'
        ]
        
        # Keep only existing columns
        available_cols = [col for col in final_cols if col in df.columns]
        df = df[available_cols]
        
        # Sort by datetime
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Drop rows with ANY remaining NaN in critical columns
        critical_cols = ['datetime', 'electricity_demand', 'temperature']
        df = df.dropna(subset=critical_cols)
        
        return df
    
    def validate_canonical(self, df: pd.DataFrame) -> bool:
        """Validate Canonical Table"""
        if df.empty:
            logger.warning("⚠️ Empty Canonical Table")
            return False
        
        # Check required columns
        required_cols = ['datetime', 'electricity_demand', 'temperature']
        missing_cols = set(required_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Check no NaN in critical columns
        for col in required_cols:
            if df[col].isnull().any():
                raise ValueError(f"Column {col} still has NaN values!")
        
        # Check datetime is sorted
        if not df['datetime'].is_monotonic_increasing:
            raise ValueError("Datetime not sorted!")
        
        logger.info("✅ Canonical Table validation passed")
        logger.info(f"   Columns: {df.columns.tolist()}")
        logger.info(f"   Shape: {df.shape}")
        logger.info(f"   Date range: {df['datetime'].min()} to {df['datetime'].max()}")
        
        return True