"""
etl/electricity_cleaner.py
⚡ Electricity Data Cleaner - Bronze → Silver (Physical Cleaning)
"""
import logging
import pandas as pd
import pytz
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ElectricityCleaner:
    """
    Physical Cleaning: Bronze → Silver
    
    Nhiệm vụ:
    1. Flattening: Duỗi phẳng JSON
    2. Type Casting: Ép kiểu dữ liệu chuẩn
    3. Deduplication: Loại bỏ trùng lặp
    4. Column Selection: Chọn cột cần thiết (chỉ giữ total_load)
    """
    
    def __init__(
        self,
        source_tz: str = "UTC",
        target_tz: str = "Asia/Ho_Chi_Minh"
    ):
        self.source_tz = pytz.timezone(source_tz)
        self.target_tz = pytz.timezone(target_tz)
    
    def clean(
        self,
        raw_data: Dict[str, Any],
        signal_name: str,
        query_date: str
    ) -> pd.DataFrame:
        """
        Main cleaning pipeline: Bronze → Silver
        
        Args:
            raw_data: Raw JSON from Bronze
            signal_name: Signal name (carbon_intensity, total_load, etc.)
            query_date: Date string (YYYY-MM-DD)
        
        Returns:
            pd.DataFrame: Cleaned Silver data
        """
        logger.info(f"⚡ Cleaning {signal_name} data for {query_date}")
        
        # Step 1: Flattening
        df = self._flatten_json(raw_data, signal_name)
        logger.info(f"  → Flattened: {len(df)} records")
        
        # Step 2: Type Casting
        df = self._cast_types(df)
        logger.info(f"  → Type cast completed")
        
        # Step 3: Deduplication
        df = self._deduplicate(df)
        logger.info(f"  → Deduplicated: {len(df)} rows")
        
        # Step 4: Column Selection (chỉ giữ total_load)
        if signal_name == 'total_load':
            df = self._select_columns(df, signal_name)
            logger.info(f"  → Selected {len(df.columns)} columns")
        else:
            # Các signal khác không cần thiết cho Canonical Table
            logger.info(f"  ⏭️ Skipping {signal_name} (not needed for Canonical Table)")
            return pd.DataFrame()  # Return empty
        
        return df
    
    def _flatten_json(self, raw_data: Dict[str, Any], signal_name: str) -> pd.DataFrame:
        """
        Flattening: Duỗi phẳng JSON structure
        
        {"data": [...]} → DataFrame phẳng
        """
        try:
            # Try 'data' field first (total_load uses this)
            if 'data' in raw_data:
                data_list = raw_data['data']
            elif 'history' in raw_data:
                data_list = raw_data['history']
            else:
                raise ValueError(f"Unknown data structure for {signal_name}")
            
            if not data_list:
                logger.warning(f"⚠️ Empty data list for {signal_name}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(data_list)
            
            # Parse datetime
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
            else:
                raise ValueError("No datetime field in data")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to flatten {signal_name}: {e}")
            raise
    
    def _cast_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Type Casting: Ép kiểu dữ liệu chuẩn
        
        - datetime → datetime64[ns] (UTC+7)
        - value (MW) → float32
        """
        if df.empty:
            return df
        
        # Datetime: Convert UTC → UTC+7
        if df['datetime'].dt.tz is None:
            df['datetime'] = df['datetime'].dt.tz_localize('UTC')
        else:
            df['datetime'] = df['datetime'].dt.tz_convert('UTC')
        
        df['datetime'] = df['datetime'].dt.tz_convert(self.target_tz)
        df['datetime'] = df['datetime'].dt.tz_localize(None)
        
        # Numeric: value column
        if 'value' in df.columns:
            df['value'] = pd.to_numeric(df['value'], errors='coerce').astype('float32')
        
        return df
    
    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Deduplication: Loại bỏ dòng trùng lặp
        
        Keep first occurrence, drop duplicates by datetime
        """
        if df.empty:
            return df
        
        initial_len = len(df)
        df = df.drop_duplicates(subset=['datetime'], keep='first')
        
        removed = initial_len - len(df)
        if removed > 0:
            logger.warning(f"  ⚠️ Removed {removed} duplicate rows")
        
        return df
    
    def _select_columns(self, df: pd.DataFrame, signal_name: str) -> pd.DataFrame:
        """
        Column Selection: Chỉ giữ datetime và value
        
        Rename 'value' → 'total_load' (business name)
        """
        if df.empty:
            return df
        
        # Select only needed columns
        required_cols = ['datetime', 'value']
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols]
        
        # Rename to business name
        if 'value' in df.columns:
            df = df.rename(columns={'value': 'total_load'})
        
        return df
    
    def validate_output(self, df: pd.DataFrame) -> bool:
        """Validate cleaned Silver data"""
        if df.empty:
            logger.warning("⚠️ Empty DataFrame")
            return True
        
        # Check datetime column
        if 'datetime' not in df.columns:
            raise ValueError("Missing datetime column")
        
        if not pd.api.types.is_datetime64_any_dtype(df['datetime']):
            raise ValueError("datetime must be datetime type")
        
        logger.info("✅ Electricity Silver validation passed")
        return True