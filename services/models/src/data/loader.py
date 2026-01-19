"""
data/loader.py
📥 Load data từ S3 Gold Canonical Layer
"""
import logging
import pandas as pd
import boto3
import io
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class DataLoader:
    """Load training data từ S3 Gold Canonical layer"""
    
    def __init__(self, bucket_name: str, canonical_prefix: str = "gold/canonical"):
        self.bucket_name = bucket_name
        self.canonical_prefix = canonical_prefix
        self.s3_client = boto3.client('s3')
    
    def load_canonical_data(
        self,
        year: int = None,
        month: int = None
    ) -> pd.DataFrame:
        """
        Load Gold Canonical data từ S3
        
        Args:
            year: Filter by year (optional)
            month: Filter by month (optional)
        
        Returns:
            pd.DataFrame: Combined canonical data
        """
        logger.info(f"📥 Loading Gold Canonical data from S3...")
        
        # Construct prefix
        if year and month:
            prefix = f"{self.canonical_prefix}/year={year}/month={str(month).zfill(2)}/"
        elif year:
            prefix = f"{self.canonical_prefix}/year={year}/"
        else:
            prefix = f"{self.canonical_prefix}/"
        
        # List all parquet files
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            raise ValueError(f"No data found at {prefix}")
        
        parquet_files = [
            obj['Key'] for obj in response['Contents']
            if obj['Key'].endswith('/data.parquet')
        ]
        
        logger.info(f"  Found {len(parquet_files)} parquet files")
        
        # Load all files
        dfs = []
        for file_key in parquet_files:
            try:
                obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
                df = pd.read_parquet(io.BytesIO(obj['Body'].read()))
                dfs.append(df)
                logger.debug(f"  ✅ Loaded {file_key}: {len(df)} rows")
            except Exception as e:
                logger.error(f"  ❌ Failed to load {file_key}: {e}")
                continue
        
        if not dfs:
            raise ValueError("No data could be loaded")
        
        # Combine
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Sort by datetime
        if 'datetime' in combined_df.columns:
            combined_df = combined_df.sort_values('datetime').reset_index(drop=True)
        
        logger.info(f"✅ Loaded {len(combined_df)} total rows")
        logger.info(f"  Columns: {len(combined_df.columns)}")
        
        if 'datetime' in combined_df.columns:
            logger.info(
                f"  Date range: {combined_df['datetime'].min()} to "
                f"{combined_df['datetime'].max()}"
            )
        
        return combined_df
    
    def prepare_train_data(
        self,
        df: pd.DataFrame,
        target_column: str,
        exclude_features: list = None
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DatetimeIndex]:
        """
        Prepare X, y, timestamps từ canonical data
        
        Args:
            df: Input canonical DataFrame
            target_column: Target column name
            exclude_features: Columns to exclude from features
        
        Returns:
            X: Features DataFrame
            y: Target Series
            timestamps: DatetimeIndex for time series
        """
        logger.info("🔧 Preparing training data from Canonical...")
        
        # Validate target
        if target_column not in df.columns:
            available = df.columns.tolist()
            raise ValueError(
                f"Target '{target_column}' not found. Available: {available[:10]}..."
            )
        
        # Extract target
        y = df[target_column].copy()
        
        # Get timestamps
        if 'datetime' in df.columns:
            timestamps = pd.to_datetime(df['datetime'])
        else:
            logger.warning("⚠️ No 'datetime' column found, using index")
            timestamps = pd.DatetimeIndex(range(len(df)))
        
        # Exclude features
        exclude = exclude_features or []
        feature_cols = [col for col in df.columns if col not in exclude]
        
        X = df[feature_cols].copy()
        
        logger.info(f"  Features: {len(X.columns)}")
        logger.info(f"  Samples: {len(X)}")
        logger.info(f"  Target: {target_column} (mean={y.mean():.2f}, std={y.std():.2f})")
        
        # Check missing values
        missing = X.isnull().sum()
        if missing.any():
            logger.warning(f"  ⚠️ Missing values detected:")
            for col, count in missing[missing > 0].items():
                pct = count / len(X) * 100
                logger.warning(f"    {col}: {count} ({pct:.1f}%)")
        
        # Check target missing
        target_missing = y.isnull().sum()
        if target_missing > 0:
            logger.warning(f"  ⚠️ Target missing: {target_missing} rows")
            # Drop rows with missing target
            mask = ~y.isnull()
            X = X[mask]
            y = y[mask]
            timestamps = timestamps[mask]
            logger.info(f"  Dropped missing target, remaining: {len(X)} rows")
        
        return X, y, timestamps
    
    def get_data_info(self, df: pd.DataFrame) -> dict:
        """
        Get summary info về canonical data
        
        Args:
            df: Canonical DataFrame
        
        Returns:
            dict: Summary statistics
        """
        info = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024**2,
            'column_types': df.dtypes.value_counts().to_dict(),
            'missing_values': df.isnull().sum().sum(),
        }
        
        if 'datetime' in df.columns:
            info['date_range'] = {
                'start': str(df['datetime'].min()),
                'end': str(df['datetime'].max()),
                'days': (df['datetime'].max() - df['datetime'].min()).days
            }
        
        return info

    
    def load_recent_hourly_gold(
        self,
        end_date: str,
        end_hour: str,
        hours: int = 168
        ) -> pd.DataFrame:
        """
        Load recent N hours of Gold data (including hourly files)
    
        This supports both:
        - Daily compacted files (data.parquet)
        - Hourly files (HH_30.parquet)
    
        Args:
            end_date: End date (YYYY-MM-DD)
            end_hour: End hour (HH)
            hours: Number of hours to load
    
        Returns:
            pd.DataFrame: Combined historical data
        """
        logger.info(f"📥 Loading {hours} hours of Gold data until {end_date} {end_hour}:00")
    
        from datetime import datetime, timedelta
    
        end_datetime = datetime.strptime(f"{end_date} {end_hour}", "%Y-%m-%d %H")
        start_datetime = end_datetime - timedelta(hours=hours)
    
        dfs = []
        current = start_datetime
    
        while current <= end_datetime:
            date_str = current.strftime("%Y-%m-%d")
            hour_str = current.strftime("%H")
            year = current.year
            month = str(current.month).zfill(2)
            day = str(current.day).zfill(2)
        
            # Try hourly file first
            hourly_key = f"{self.canonical_prefix}/year={year}/month={month}/day={day}/{hour_str}_30.parquet"
        
            # Try daily file as fallback
            daily_key = f"{self.canonical_prefix}/year={year}/month={month}/day={day}/data.parquet"
        
            try:
                # Check hourly file
                self.s3_client.head_object(Bucket=self.bucket_name, Key=hourly_key)
                obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=hourly_key)
                df = pd.read_parquet(io.BytesIO(obj['Body'].read()))
                dfs.append(df)
                current += timedelta(hours=1)
                continue
            except:
                pass
        
            try:
                # Fall back to daily file (only once per day)
                if hour_str == "00":  # Only load daily file once
                    self.s3_client.head_object(Bucket=self.bucket_name, Key=daily_key)
                    obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=daily_key)
                    df = pd.read_parquet(io.BytesIO(obj['Body'].read()))
                    dfs.append(df)
            except:
                pass
        
            current += timedelta(hours=1)
    
        if not dfs:
            raise ValueError(f"No Gold data found for last {hours} hours")
    
        combined = pd.concat(dfs, ignore_index=True)
    
        # De-duplicate and sort
        if 'datetime' in combined.columns:
            combined['datetime'] = pd.to_datetime(combined['datetime'])
            combined = combined.drop_duplicates(subset=['datetime'])
            combined = combined.sort_values('datetime').reset_index(drop=True)
        
        # Filter to exact time range
        combined = combined[
            (combined['datetime'] >= start_datetime) & 
            (combined['datetime'] <= end_datetime)
        ]
    
        logger.info(f"✅ Loaded {len(combined)} rows")
    
        return combined