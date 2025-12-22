"""
etl/electricity_cleaner.py
⚡ Electricity Data Cleaner - Bronze → Silver
"""
import logging
import pandas as pd
import pytz
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ElectricityCleaner:
    """
    Làm sạch dữ liệu điện từ Bronze layer
    
    Xử lý 5 signals khác nhau:
    1. carbon_intensity
    2. total_load  
    3. price_day_ahead
    4. electricity_mix
    5. electricity_flows
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
        Main cleaning pipeline for electricity data
        
        Args:
            raw_data: Raw JSON from Bronze
            signal_name: Signal name (carbon_intensity, total_load, etc.)
            query_date: Date string (YYYY-MM-DD)
        
        Returns:
            pd.DataFrame: Cleaned data
        """
        logger.info(f"⚡ Cleaning {signal_name} data for {query_date}")
        
        # Step 1: Parse JSON based on signal type
        df = self._parse_json(raw_data, signal_name)
        logger.info(f"  → Parsed {len(df)} records")
        
        # Step 2: Convert timezone
        df = self._convert_timezone(df)
        logger.info(f"  → Converted timezone")
        
        # Step 3: Handle missing values
        df = self._handle_missing_values(df, signal_name)
        logger.info(f"  → Handled missing values")
        
        # Step 4: Add metadata
        df = self._add_metadata(df, signal_name, query_date)
        
        return df
    
    def _parse_json(self, raw_data: Dict[str, Any], signal_name: str) -> pd.DataFrame:
        """
        Parse JSON structure (khác nhau cho mỗi signal)
        
        Common structure:
        {
            "zone": "VN",
            "history": [
                {
                    "datetime": "2024-12-20T00:00:00Z",
                    ...
                }
            ]
        }
        """
        try:
            # Try 'history' field first (most signals use this)
            if 'history' in raw_data:
                data_list = raw_data['history']
            elif 'data' in raw_data:
                data_list = raw_data['data']
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
            logger.error(f"❌ Failed to parse {signal_name}: {e}")
            raise
    
    def _convert_timezone(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert datetime to Vietnam timezone"""
        if df.empty:
            return df
        
        # Localize to UTC (API returns UTC)
        df['datetime'] = df['datetime'].dt.tz_localize('UTC')
        
        # Convert to Vietnam timezone
        df['datetime'] = df['datetime'].dt.tz_convert(self.target_tz)
        
        # Remove timezone info
        df['datetime'] = df['datetime'].dt.tz_localize(None)
        
        return df
    
    def _handle_missing_values(self, df: pd.DataFrame, signal_name: str) -> pd.DataFrame:
        """
        Handle missing values based on signal type
        """
        if df.empty:
            return df
        
        # Identify numeric columns
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        
        for col in numeric_cols:
            missing_count = df[col].isnull().sum()
            if missing_count > 0:
                logger.warning(f"  ⚠️ {col}: {missing_count} missing values")
                
                # Forward fill
                df[col] = df[col].fillna(method='ffill')
                
                # Backward fill for first rows
                df[col] = df[col].fillna(method='bfill')
                
                # If still missing, fill with 0 or median
                if df[col].isnull().any():
                    if 'percentage' in col.lower() or 'ratio' in col.lower():
                        df[col] = df[col].fillna(0)
                    else:
                        df[col] = df[col].fillna(df[col].median())
        
        return df
    
    def _add_metadata(self, df: pd.DataFrame, signal_name: str, query_date: str) -> pd.DataFrame:
        """Add metadata columns"""
        if df.empty:
            return df
        
        df['signal'] = signal_name
        df['source'] = 'electricity_maps'
        df['processed_at'] = datetime.utcnow()
        df['query_date'] = query_date
        
        return df
    
    def merge_signals(self, signal_dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Merge tất cả signals lại với nhau
        
        Args:
            signal_dfs: Dict {signal_name: DataFrame}
        
        Returns:
            pd.DataFrame: Merged data
        """
        logger.info(f"🔗 Merging {len(signal_dfs)} electricity signals")
        
        if not signal_dfs:
            raise ValueError("No signals to merge")
        
        # Filter out empty DataFrames
        valid_dfs = {k: v for k, v in signal_dfs.items() if not v.empty}
        
        if not valid_dfs:
            logger.warning("⚠️ All signal DataFrames are empty")
            return pd.DataFrame()
        
        # Start with first signal
        first_signal = list(valid_dfs.keys())[0]
        merged_df = valid_dfs[first_signal].copy()
        
        # Merge với các signals còn lại
        for signal_name, df in list(valid_dfs.items())[1:]:
            try:
                # Select only datetime and numeric columns
                merge_cols = ['datetime'] + [col for col in df.columns 
                                            if df[col].dtype in ['float64', 'int64']]
                df_to_merge = df[merge_cols]
                
                # Rename columns to avoid conflicts
                rename_dict = {col: f"{signal_name}_{col}" 
                              for col in merge_cols if col != 'datetime'}
                df_to_merge = df_to_merge.rename(columns=rename_dict)
                
                # Merge
                merged_df = merged_df.merge(df_to_merge, on='datetime', how='outer')
                logger.info(f"  → Merged {signal_name}")
                
            except Exception as e:
                logger.error(f"  ❌ Failed to merge {signal_name}: {e}")
                continue
        
        # Sort by datetime
        merged_df = merged_df.sort_values('datetime').reset_index(drop=True)
        
        logger.info(f"✅ Merged result: {len(merged_df)} rows, {len(merged_df.columns)} columns")
        
        return merged_df
    
    def validate_output(self, df: pd.DataFrame) -> bool:
        """Validate cleaned data"""
        if df.empty:
            logger.warning("⚠️ Empty DataFrame")
            return True
        
        # Check datetime column
        if 'datetime' not in df.columns:
            raise ValueError("Missing datetime column")
        
        if not pd.api.types.is_datetime64_any_dtype(df['datetime']):
            raise ValueError("datetime must be datetime type")
        
        logger.info("✅ Data validation passed")
        return True