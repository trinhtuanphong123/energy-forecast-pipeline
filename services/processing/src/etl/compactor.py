"""
etl/compactor.py
🗜️ Data Compactor - Gộp hourly/daily files
"""
import logging
import pandas as pd
from typing import Dict, Any
from calendar import monthrange
from s3_connector import S3Connector
from config import Config

logger = logging.getLogger(__name__)

class ProcessingCompactor:
    """
    Compactor cho Processing Service
    
    2 loại compaction:
    1. DAILY: Gộp 24 hourly Silver files → 1 daily Silver file
    2. MONTHLY: Gộp N daily Gold files → 1 monthly Gold file (nếu đủ ngày)
    """
    
    def __init__(self, s3_connector: S3Connector):
        """
        Args:
            s3_connector: S3Connector instance
        """
        self.s3 = s3_connector
    
    def compact_daily_silver(self, date: str) -> Dict[str, Any]:
        """
        COMPACTION_DAILY: Gộp 24 hourly Silver files thành 1 daily file
        
        Steps:
        1. List all hourly Silver files (HH_30.parquet) for weather và electricity
        2. Read và concat
        3. Write daily file (day=DD/data.parquet)
        4. Delete hourly files
        
        Args:
            date: Date string (YYYY-MM-DD)
        
        Returns:
            dict: Stats
        """
        logger.info(f"🗜️ Daily Compaction for {date}")
        
        results = {
            "date": date,
            "weather": None,
            "electricity": None
        }
        
        # Compact Weather Silver
        try:
            results["weather"] = self._compact_weather_silver(date)
        except Exception as e:
            logger.error(f"❌ Weather compaction failed: {str(e)}")
            results["weather"] = {"status": "error", "error": str(e)}
        
        # Compact Electricity Silver
        try:
            results["electricity"] = self._compact_electricity_silver(date)
        except Exception as e:
            logger.error(f"❌ Electricity compaction failed: {str(e)}")
            results["electricity"] = {"status": "error", "error": str(e)}
        
        return results
    
    def _compact_weather_silver(self, date: str) -> Dict[str, Any]:
        """Compact Weather Silver: 24 hourly files → 1 daily file"""
        logger.info(f"  ☀️ Compacting Weather Silver for {date}")
        
        # List hourly Silver files (should be HH_30.parquet if we saved them hourly)
        # But based on current code, we write directly to day partition
        # So we need to list all parquet files in the day partition
        
        # Actually, in HOURLY mode, we should save to hour-specific files
        # Let's assume structure: silver/weather/year=YYYY/month=MM/day=DD/HH_30.parquet
        
        date_obj = pd.to_datetime(date)
        year = date_obj.year
        month = str(date_obj.month).zfill(2)
        day = str(date_obj.day).zfill(2)
        
        partition_prefix = f"{Config.WEATHER_SILVER_PATH}/year={year}/month={month}/day={day}/"
        
        # List all files in partition
        try:
            response = self.s3.s3_client.list_objects_v2(
                Bucket=self.s3.bucket_name,
                Prefix=partition_prefix
            )
            
            if 'Contents' not in response:
                logger.warning(f"⚠️ No hourly files found for {date}")
                return {"status": "no_files", "files_processed": 0}
            
            hourly_files = [
                obj['Key'] for obj in response['Contents']
                if obj['Key'].endswith('.parquet') and '_30.parquet' in obj['Key']
            ]
            
            if not hourly_files:
                logger.warning(f"⚠️ No hourly files found (might already be compacted)")
                return {"status": "already_compacted", "files_processed": 0}
            
            logger.info(f"    📁 Found {len(hourly_files)} hourly files")
            
            # Read all hourly files
            dfs = []
            for file_key in hourly_files:
                df = self.s3.read_parquet(file_key)
                dfs.append(df)
            
            # Concatenate
            compacted_df = pd.concat(dfs, ignore_index=True)
            compacted_df = compacted_df.sort_values('datetime').reset_index(drop=True)
            
            # Write daily file
            daily_key = self.s3.get_partition_path(
                Config.WEATHER_SILVER_PATH,
                date,
                "data.parquet"
            )
            
            self.s3.write_parquet(
                compacted_df,
                daily_key,
                compression=Config.PARQUET_COMPRESSION
            )
            
            logger.info(f"    ✅ Compacted {len(hourly_files)} files → {len(compacted_df)} rows")
            
            # Delete hourly files
            deleted_count = 0
            for file_key in hourly_files:
                if self.s3.delete_file(file_key):
                    deleted_count += 1
            
            logger.info(f"    🗑️ Deleted {deleted_count}/{len(hourly_files)} hourly files")
            
            return {
                "status": "success",
                "date": date,
                "files_compacted": len(hourly_files),
                "rows": len(compacted_df),
                "files_deleted": deleted_count
            }
            
        except Exception as e:
            logger.error(f"❌ Weather Silver compaction failed: {str(e)}")
            raise
    
    def _compact_electricity_silver(self, date: str) -> Dict[str, Any]:
        """Compact Electricity Silver: 24 hourly files → 1 daily file"""
        logger.info(f"  ⚡ Compacting Electricity Silver for {date}")
        
        date_obj = pd.to_datetime(date)
        year = date_obj.year
        month = str(date_obj.month).zfill(2)
        day = str(date_obj.day).zfill(2)
        
        partition_prefix = f"{Config.ELECTRICITY_SILVER_PATH}/year={year}/month={month}/day={day}/"
        
        try:
            response = self.s3.s3_client.list_objects_v2(
                Bucket=self.s3.bucket_name,
                Prefix=partition_prefix
            )
            
            if 'Contents' not in response:
                logger.warning(f"⚠️ No hourly files found for {date}")
                return {"status": "no_files", "files_processed": 0}
            
            hourly_files = [
                obj['Key'] for obj in response['Contents']
                if obj['Key'].endswith('.parquet') and '_30.parquet' in obj['Key']
            ]
            
            if not hourly_files:
                logger.warning(f"⚠️ No hourly files found (might already be compacted)")
                return {"status": "already_compacted", "files_processed": 0}
            
            logger.info(f"    📁 Found {len(hourly_files)} hourly files")
            
            # Read all hourly files
            dfs = []
            for file_key in hourly_files:
                df = self.s3.read_parquet(file_key)
                dfs.append(df)
            
            # Concatenate
            compacted_df = pd.concat(dfs, ignore_index=True)
            compacted_df = compacted_df.sort_values('datetime').reset_index(drop=True)
            
            # Write daily file
            daily_key = self.s3.get_partition_path(
                Config.ELECTRICITY_SILVER_PATH,
                date,
                "data.parquet"
            )
            
            self.s3.write_parquet(
                compacted_df,
                daily_key,
                compression=Config.PARQUET_COMPRESSION
            )
            
            logger.info(f"    ✅ Compacted {len(hourly_files)} files → {len(compacted_df)} rows")
            
            # Delete hourly files
            deleted_count = 0
            for file_key in hourly_files:
                if self.s3.delete_file(file_key):
                    deleted_count += 1
            
            logger.info(f"    🗑️ Deleted {deleted_count}/{len(hourly_files)} hourly files")
            
            return {
                "status": "success",
                "date": date,
                "files_compacted": len(hourly_files),
                "rows": len(compacted_df),
                "files_deleted": deleted_count
            }
            
        except Exception as e:
            logger.error(f"❌ Electricity Silver compaction failed: {str(e)}")
            raise


    def compact_hourly_gold(self, date: str) -> Dict[str, Any]:
        """
        Compact hourly Gold files (HH_30.parquet) for a given day
    
        DELETE hourly Gold files after daily file exists.
        (The daily Gold is created by process_silver_to_canonical)
    
        Args:
            date: Date string (YYYY-MM-DD)
    
        Returns:
            dict: Stats
        """
        logger.info(f"🗜️ Compact hourly Gold for {date}")
    
        date_obj = pd.to_datetime(date)
        year = date_obj.year
        month = str(date_obj.month).zfill(2)
        day = str(date_obj.day).zfill(2)
    
        partition_prefix = f"{Config.GOLD_CANONICAL_PATH}/year={year}/month={month}/day={day}/"
    
        try:
            response = self.s3.s3_client.list_objects_v2(
                Bucket=self.s3.bucket_name,
                Prefix=partition_prefix
            )
        
            if 'Contents' not in response:
                return {"status": "no_files", "files_deleted": 0}
        
            # Find hourly files (HH_30.parquet)
            hourly_files = [
                obj['Key'] for obj in response['Contents']
                if '_30.parquet' in obj['Key']
            ]
        
            if not hourly_files:
                return {"status": "no_hourly_files", "files_deleted": 0}
        
            # Check if daily file exists
            daily_key = f"{partition_prefix}data.parquet"
            if not self.s3.check_file_exists(daily_key):
                logger.warning(f"⚠️ Daily Gold file not found, skip deleting hourly files")
                return {"status": "daily_not_found", "files_deleted": 0}
        
            # Delete hourly files (daily file now exists)
            deleted_count = 0
            for file_key in hourly_files:
                if self.s3.delete_file(file_key):
                    deleted_count += 1
        
            logger.info(f"🗑️ Deleted {deleted_count}/{len(hourly_files)} hourly Gold files")
        
            return {
                "status": "success",
                "files_deleted": deleted_count
            }
        
        except Exception as e:
            logger.error(f"❌ Error compacting hourly Gold: {e}")
            return {"status": "error", "error": str(e)}
    
    def compact_monthly_gold(self, year: int, month: int) -> Dict[str, Any]:
        """
        COMPACTION_MONTHLY: Gộp daily Gold files thành 1 monthly file
        
        Chỉ chạy khi tháng đã complete (đủ số ngày)
        
        Steps:
        1. Check tháng đã đủ ngày chưa
        2. List all daily Gold files (day=DD/data.parquet)
        3. Read và concat
        4. Write monthly file (year=YYYY/month=MM/data.parquet)
        5. Delete daily files
        
        Args:
            year: Year
            month: Month
        
        Returns:
            dict: Stats
        """
        logger.info(f"🗜️ Monthly Compaction for {year}-{month:02d}")
        
        # Check if month is complete
        if not Config.is_month_complete(year, month):
            logger.warning(f"⚠️ Month {year}-{month:02d} is not complete yet, skipping")
            return {
                "status": "incomplete",
                "year": year,
                "month": month,
                "message": "Month not complete"
            }
        
        logger.info(f"  ✅ Month {year}-{month:02d} is complete, proceeding...")
        
        # List daily Gold files
        month_str = str(month).zfill(2)
        month_prefix = f"{Config.GOLD_CANONICAL_PATH}/year={year}/month={month_str}/"
        
        try:
            response = self.s3.s3_client.list_objects_v2(
                Bucket=self.s3.bucket_name,
                Prefix=month_prefix
            )
            
            if 'Contents' not in response:
                logger.warning(f"⚠️ No daily files found for {year}-{month:02d}")
                return {"status": "no_files", "files_processed": 0}
            
            # Filter daily files (day=XX/data.parquet)
            daily_files = [
                obj['Key'] for obj in response['Contents']
                if 'day=' in obj['Key'] and obj['Key'].endswith('/data.parquet')
            ]
            
            if not daily_files:
                logger.warning(f"⚠️ No daily files found")
                return {"status": "no_files", "files_processed": 0}
            
            logger.info(f"  📁 Found {len(daily_files)} daily files")
            
            # Expected number of days in month
            _, expected_days = monthrange(year, month)
            
            if len(daily_files) < expected_days:
                logger.warning(f"⚠️ Only {len(daily_files)}/{expected_days} days available")
                return {
                    "status": "incomplete_data",
                    "files_found": len(daily_files),
                    "expected": expected_days
                }
            
            # Read all daily files
            dfs = []
            for file_key in daily_files:
                df = self.s3.read_parquet(file_key)
                dfs.append(df)
            
            # Concatenate
            monthly_df = pd.concat(dfs, ignore_index=True)
            monthly_df = monthly_df.sort_values('datetime').reset_index(drop=True)
            
            # Write monthly file
            monthly_key = self.s3.get_monthly_path(
                Config.GOLD_CANONICAL_PATH,
                year,
                month,
                "data.parquet"
            )
            
            self.s3.write_parquet(
                monthly_df,
                monthly_key,
                compression=Config.PARQUET_COMPRESSION
            )
            
            logger.info(f"  ✅ Compacted {len(daily_files)} days → {len(monthly_df)} rows")
            
            # Delete daily files
            deleted_count = 0
            for file_key in daily_files:
                if self.s3.delete_file(file_key):
                    deleted_count += 1
            
            logger.info(f"  🗑️ Deleted {deleted_count}/{len(daily_files)} daily files")
            
            return {
                "status": "success",
                "year": year,
                "month": month,
                "files_compacted": len(daily_files),
                "rows": len(monthly_df),
                "files_deleted": deleted_count,
                "output": monthly_key
            }
            
        except Exception as e:
            logger.error(f"❌ Monthly Gold compaction failed: {str(e)}")
            raise