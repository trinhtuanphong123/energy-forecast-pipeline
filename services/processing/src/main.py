"""
main.py
🏁 Main Entry Point - Processing Service (Refactored)
Pipeline: Bronze → Silver → Gold (Canonical)
"""
import logging
import sys
from datetime import datetime, timedelta
from typing import List

from config import Config
from s3_connector import S3Connector
from etl.weather_cleaner import WeatherCleaner
from etl.electricity_cleaner import ElectricityCleaner
from etl.canonical_merger import CanonicalMerger

# Setup logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def generate_date_list(start_date: str, end_date: str) -> List[str]:
    """Tạo list các ngày cần xử lý"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    date_list = []
    current = start
    while current <= end:
        date_list.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    return date_list

def process_weather_bronze_to_silver(
    s3: S3Connector,
    cleaner: WeatherCleaner,
    date: str
) -> bool:
    """Bronze → Silver: Weather (Physical Cleaning)"""
    try:
        logger.info(f"☀️ Processing weather: {date}")
        
        bronze_key = s3.get_partition_path(
            Config.WEATHER_BRONZE_PATH,
            date,
            "data.json"
        )
        
        if not s3.check_file_exists(bronze_key):
            logger.warning(f"⚠️ Bronze not found: {bronze_key}")
            return False
        
        raw_data = s3.read_json(bronze_key)
        cleaned_df = cleaner.clean(raw_data, date)
        cleaner.validate_output(cleaned_df)
        
        silver_key = s3.get_partition_path(
            Config.WEATHER_SILVER_PATH,
            date,
            "data.parquet"
        )
        
        s3.write_parquet(
            cleaned_df,
            silver_key,
            compression=Config.PARQUET_COMPRESSION
        )
        
        logger.info(f"✅ Weather Silver: {len(cleaned_df)} rows")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed weather for {date}: {e}", exc_info=True)
        return False

def process_electricity_bronze_to_silver(
    s3: S3Connector,
    cleaner: ElectricityCleaner,
    date: str
) -> bool:
    """Bronze → Silver: Electricity (Physical Cleaning - total_load only)"""
    try:
        logger.info(f"⚡ Processing electricity: {date}")
        
        # Chỉ xử lý total_load
        signal = "total_load"
        bronze_key = s3.get_partition_path(
            f"{Config.ELECTRICITY_BRONZE_PATH}/{signal}",
            date,
            "data.json"
        )
        
        if not s3.check_file_exists(bronze_key):
            logger.warning(f"⚠️ Bronze not found: {bronze_key}")
            return False
        
        raw_data = s3.read_json(bronze_key)
        cleaned_df = cleaner.clean(raw_data, signal, date)
        
        if cleaned_df.empty:
            logger.warning(f"⚠️ Empty electricity data for {date}")
            return False
        
        cleaner.validate_output(cleaned_df)
        
        silver_key = s3.get_partition_path(
            Config.ELECTRICITY_SILVER_PATH,
            date,
            "data.parquet"
        )
        
        s3.write_parquet(
            cleaned_df,
            silver_key,
            compression=Config.PARQUET_COMPRESSION
        )
        
        logger.info(f"✅ Electricity Silver: {len(cleaned_df)} rows")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed electricity for {date}: {e}", exc_info=True)
        return False

def process_silver_to_canonical(
    s3: S3Connector,
    merger: CanonicalMerger,
    date_list: List[str]
) -> bool:
    """Silver → Gold: Create Canonical Table (Logical Cleaning)"""
    try:
        logger.info(f"🌟 Creating Canonical Table for {len(date_list)} days")
        
        # Read all Silver data
        weather_dfs = []
        electricity_dfs = []
        
        for date in date_list:
            # Read weather Silver
            try:
                weather_key = s3.get_partition_path(
                    Config.WEATHER_SILVER_PATH,
                    date,
                    "data.parquet"
                )
                if s3.check_file_exists(weather_key):
                    weather_df = s3.read_parquet(weather_key)
                    weather_dfs.append(weather_df)
            except Exception as e:
                logger.warning(f"⚠️ Failed weather Silver for {date}: {e}")
            
            # Read electricity Silver
            try:
                elec_key = s3.get_partition_path(
                    Config.ELECTRICITY_SILVER_PATH,
                    date,
                    "data.parquet"
                )
                if s3.check_file_exists(elec_key):
                    elec_df = s3.read_parquet(elec_key)
                    electricity_dfs.append(elec_df)
            except Exception as e:
                logger.warning(f"⚠️ Failed electricity Silver for {date}: {e}")
        
        if not weather_dfs or not electricity_dfs:
            logger.error("❌ No Silver data found")
            return False
        
        # Concatenate all days
        import pandas as pd
        weather_all = pd.concat(weather_dfs, ignore_index=True)
        electricity_all = pd.concat(electricity_dfs, ignore_index=True)
        
        # Create Canonical Table
        canonical_df = merger.merge(weather_all, electricity_all)
        merger.validate_canonical(canonical_df)
        
        # Write Canonical Table (theo tháng)
        canonical_df['year_month'] = canonical_df['datetime'].dt.to_period('M')
        
        for year_month, group_df in canonical_df.groupby('year_month'):
            ym_str = str(year_month)
            year, month = ym_str.split('-')
            
            canonical_key = f"{Config.GOLD_CANONICAL_PATH}/year={year}/month={month}/data.parquet"
            
            group_df = group_df.drop('year_month', axis=1)
            
            s3.write_parquet(
                group_df,
                canonical_key,
                compression=Config.PARQUET_COMPRESSION
            )
            
            logger.info(f"✅ Canonical Table: {len(group_df)} rows → {canonical_key}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed Canonical Table: {e}", exc_info=True)
        return False

def main():
    """Main orchestrator"""
    try:
        # Print banner
        print(Config.get_summary())
        
        # Validate config
        logger.info("🔍 Validating configuration...")
        Config.validate()
        logger.info("✅ Config OK")
        
        # Get date range
        start_date, end_date = Config.get_date_range()
        date_list = generate_date_list(start_date, end_date)
        logger.info(f"📅 Processing {len(date_list)} days: {start_date} to {end_date}")
        
        # Initialize components
        logger.info("🔧 Initializing components...")
        s3 = S3Connector(Config.S3_BUCKET)
        weather_cleaner = WeatherCleaner(
            source_tz=Config.SOURCE_TIMEZONE,
            target_tz=Config.TARGET_TIMEZONE
        )
        electricity_cleaner = ElectricityCleaner(
            source_tz=Config.SOURCE_TIMEZONE,
            target_tz=Config.TARGET_TIMEZONE
        )
        canonical_merger = CanonicalMerger()
        logger.info("✅ Components initialized")
        
        # ============ STEP 1: BRONZE → SILVER ============
        logger.info("=" * 70)
        logger.info("STEP 1: BRONZE → SILVER (Physical Cleaning)")
        logger.info("=" * 70)
        
        weather_success = 0
        electricity_success = 0
        
        for date in date_list:
            if process_weather_bronze_to_silver(s3, weather_cleaner, date):
                weather_success += 1
            
            if process_electricity_bronze_to_silver(s3, electricity_cleaner, date):
                electricity_success += 1
        
        logger.info(f"Weather Silver: {weather_success}/{len(date_list)}")
        logger.info(f"Electricity Silver: {electricity_success}/{len(date_list)}")
        
        # ============ STEP 2: SILVER → GOLD ============
        logger.info("=" * 70)
        logger.info("STEP 2: SILVER → GOLD (Canonical Table)")
        logger.info("=" * 70)
        
        canonical_success = process_silver_to_canonical(s3, canonical_merger, date_list)
        
        # ============ FINAL REPORT ============
        logger.info("=" * 70)
        logger.info("🎉 PROCESSING COMPLETED")
        logger.info("=" * 70)
        logger.info(f"Mode: {Config.MODE}")
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info(f"Weather Silver: {weather_success}/{len(date_list)}")
        logger.info(f"Electricity Silver: {electricity_success}/{len(date_list)}")
        logger.info(f"Canonical Table: {'✅ Success' if canonical_success else '❌ Failed'}")
        
        if not canonical_success:
            logger.error("❌ Failed to create Canonical Table")
            sys.exit(1)
        
        logger.info("✅ All processing completed successfully")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()