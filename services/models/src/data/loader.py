"""
data/loader.py
📥 Load data từ S3 Gold layer
"""
import logging
import pandas as pd
import boto3
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class DataLoader:
    """Load training data từ S3 Gold layer"""
    
    def __init__(self, bucket_name: str, gold_prefix: str = "gold/features"):
        self.bucket_name = bucket_name
        self.gold_prefix = gold_prefix
        self.s3_client = boto3.client('s3')
    
    def load_gold_data(
    self,
    year: int = None,
    month: int = None
    ) -> pd.DataFrame:
        """Load Gold features từ S3"""
        logger.info(f"📥 Loading Gold data from S3...")
    
        # List all parquet files
        if year and month:
            prefix = f"{self.gold_prefix}/year={year}/month={str(month).zfill(2)}/"
        elif year:
            prefix = f"{self.gold_prefix}/year={year}/"
        else:
            prefix = f"{self.gold_prefix}/"
    
        # List objects
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix
      )
    
        if 'Contents' not in response:
            raise ValueError(f"No data found at {prefix}")
    
        # Filter parquet files
        parquet_files = [
        obj['Key'] for obj in response['Contents']
        if obj['Key'].endswith('.parquet')
        ]
    
        logger.info(f"  Found {len(parquet_files)} parquet files")
    
        # Load all files
        dfs = []
        for file_key in parquet_files:
            try:
                # ✅ SỬA: Đọc từ S3 đúng cách với boto3
                import io
                obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
                df = pd.read_parquet(io.BytesIO(obj['Body'].read()))
            
                dfs.append(df)
                logger.debug(f"  ✅ Loaded {file_key}: {len(df)} rows")
            except Exception as e:
                logger.error(f"  ❌ Failed to load {file_key}: {e}")
                continue
    
        if not dfs:
            raise ValueError("No data could be loaded")
    
        # Concatenate all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
    
        # Sort by datetime
        if 'datetime' in combined_df.columns:
            combined_df = combined_df.sort_values('datetime').reset_index(drop=True)
    
        logger.info(f"✅ Loaded {len(combined_df)} total rows")
        logger.info(f"  Columns: {len(combined_df.columns)}")
        if 'datetime' in combined_df.columns:
            logger.info(f"  Date range: {combined_df['datetime'].min()} to {combined_df['datetime'].max()}")
    
        return combined_df
    
    def prepare_train_data(
        self,
        df: pd.DataFrame,
        target_column: str,
        exclude_features: list = None
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features and target từ raw dataframe
        
        Args:
            df: Input dataframe
            target_column: Name of target column
            exclude_features: Features to exclude
        
        Returns:
            X: Features DataFrame
            y: Target Series
        """
        logger.info("🔧 Preparing training data...")
        
        # Check target exists
        if target_column not in df.columns:
            raise ValueError(f"Target column '{target_column}' not found in data")
        
        # Extract target
        y = df[target_column].copy()
        
        # Get feature columns
        exclude = exclude_features or []
        feature_cols = [col for col in df.columns if col not in exclude]
        
        X = df[feature_cols].copy()
        
        logger.info(f"  Features: {len(X.columns)}")
        logger.info(f"  Samples: {len(X)}")
        logger.info(f"  Target: {target_column}")
        
        # Check for missing values
        missing = X.isnull().sum()
        if missing.any():
            logger.warning(f"  ⚠️ Missing values detected:")
            for col, count in missing[missing > 0].items():
                logger.warning(f"    {col}: {count} ({count/len(X)*100:.1f}%)")
        
        return X, y