"""
main.py
🏁 Main Entry Point - Processing Service
Điều phối luồng: Bronze → Silver → Gold
"""
import logging
import sys
from datetime import datetime, timedelta
from typing import List

from config import Config
from s3_connector import S3Connector
from etl.weather_cleaner import WeatherCleaner
from etl.electricity_cleaner import ElectricityCleaner
from etl.feature_eng import FeatureEngineer

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
    """
    Xử lý weather data: Bronze → Silver
    
    Returns:
        bool: True if success
    """
    try:
        logger.info(f"☀️ Processing weather data for {date}")
        
        # Read Bronze data
        bronze_key = s3.get_partition_path(
            Config.WEATHER_BRONZE_PATH,
            date,
            "data.json"
        )
        
        if not s3.check_file_exists(bronze_key):
            logger.warning(f"⚠️ Bronze data not found: {bronze_key}")
            return False
        
        raw_data = s3.read_json(bronze_key)
        
        # Clean data
        cleaned_df = cleaner.clean(raw_data, date)
        
        # Validate
        cleaner.validate_output(cleaned_df)
        
        # Write to Silver
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
        
        logger.info(f"✅ Weather Silver: {len(cleaned_df)} rows → {silver_key}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to process weather for {date}: {e}", exc_info=True)
        return False

def process_electricity_bronze_to_silver(
    s3: S3Connector,
    cleaner: ElectricityCleaner,
    date: str
) -> bool:
    """
    Xử lý electricity data: Bronze → Silver
    
    Returns:
        bool: True if success
    """
    try:
        logger.info(f"⚡ Processing electricity data for {date}")

        signal_dfs = {}  # 🔴 PHẢI LÀ DICT

        for signal in Config.ELECTRICITY_SIGNALS:
            bronze_key = s3.get_partition_path(
                f"{Config.ELECTRICITY_BRONZE_PATH}/{signal}",
                date,
                "data.json"
            )

            logger.info(
                f"🔍 Checking electricity bronze: "
                f"s3://{Config.S3_BUCKET}/{bronze_key}"
            )

            if not s3.check_file_exists(bronze_key):
                msg = f"Missing electricity signal [{signal}] for {date}"

                if Config.MODE == "DAILY":
                    logger.error(f"❌ {msg}")
                    # Trong DAILY mode, thiếu signal là vấn đề nghiêm trọng
                    # Nhưng không raise exception ngay, tiếp tục với các signal khác
                else:
                    logger.warning(f"⚠️ {msg}")
                continue

            try:
                raw_data = s3.read_json(bronze_key)

                # 🔥 ENTRY POINT DUY NHẤT
                df = cleaner.clean(raw_data, signal, date)

                if not df.empty:
                    signal_dfs[signal] = df
                    logger.info(f"  ✅ Signal [{signal}]: {len(df)} rows")

            except Exception as e:
                logger.error(
                    f"❌ Failed processing [{signal}] for {date}: {e}",
                    exc_info=True
                )
                if Config.MODE == "DAILY":
                    # Trong DAILY mode, log error nhưng tiếp tục
                    continue
                else:
                    # Trong BACKFILL mode, có thể bỏ qua
                    continue

        logger.info(
            f"📊 Electricity signals processed: "
            f"{len(signal_dfs)}/{len(Config.ELECTRICITY_SIGNALS)}"
        )

        if not signal_dfs:
            logger.warning(f"⚠️ No electricity data for {date}")
            return False

        # Merge signals
        merged_df = cleaner.merge_signals(signal_dfs)
        cleaner.validate_output(merged_df)

        # Write to Silver
        silver_key = s3.get_partition_path(
            Config.ELECTRICITY_SILVER_PATH,
            date,
            "data.parquet"
        )

        s3.write_parquet(
            merged_df,
            silver_key,
            compression=Config.PARQUET_COMPRESSION
        )

        logger.info(f"✅ Electricity Silver: {len(merged_df)} rows → {silver_key}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to process electricity for {date}: {e}", exc_info=True)
        return False


def process_silver_to_gold(
    s3: S3Connector,
    engineer: FeatureEngineer,
    date_list: List[str]
) -> bool:
    """
    Xử lý Silver → Gold (Feature Engineering)
    
    Note: Cần nhiều ngày để tạo lag/rolling features
    """
    try:
        logger.info(f"🌟 Creating Gold features for {len(date_list)} days")
        
        # Read all Silver data (cần nhiều ngày để tạo lag features)
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
                logger.warning(f"⚠️ Failed to read weather Silver for {date}: {e}")
            
            # Read electricity Silver
            try:
                elec_key = s3.get_partition_path(
                Config.ELECTRICITY_SILVER_PATH,
                date,
                "data.parquet"
                )
    
                logger.info(f"🔍 Looking for electricity: {elec_key}")
    
                if s3.check_file_exists(elec_key):
                    elec_df = s3.read_parquet(elec_key)
                    logger.info(f"  ✅ Loaded: {len(elec_df)} rows, {len(elec_df.columns)} cols")
                    logger.info(f"  Columns: {elec_df.columns.tolist()}")
                    electricity_dfs.append(elec_df)
                else:
                    logger.warning(f"  ⚠️ File not found: {elec_key}")
        
            except Exception as e:
                    logger.error(f"⚠️ Failed to read electricity for {date}: {e}", exc_info=True)
        
        if not weather_dfs:
            logger.error("❌ No weather Silver data found")
            return False
        
        # Concatenate all days
        import pandas as pd
        weather_all = pd.concat(weather_dfs, ignore_index=True)
        weather_all = weather_all.sort_values('datetime').reset_index(drop=True)
        
        if electricity_dfs:
            electricity_all = pd.concat(electricity_dfs, ignore_index=True)
            electricity_all = electricity_all.sort_values('datetime').reset_index(drop=True)
        else:
            logger.warning("⚠️ No electricity Silver data, creating empty DataFrame")
            electricity_all = pd.DataFrame({'datetime': weather_all['datetime']})
        
        # Create features
        gold_df = engineer.create_features(weather_all, electricity_all)
        
        # Validate
        engineer.validate_features(gold_df)
        
        # Write Gold data (theo tháng để dễ quản lý)
        # Group by year-month
        gold_df['year_month'] = gold_df['datetime'].dt.to_period('M')
        
        for year_month, group_df in gold_df.groupby('year_month'):
            # Convert Period to string
            ym_str = str(year_month)  # Format: YYYY-MM
            year, month = ym_str.split('-')
            
            gold_key = f"{Config.GOLD_PATH}/year={year}/month={month}/features.parquet"
            
            # Drop temporary column
            group_df = group_df.drop('year_month', axis=1)
            
            s3.write_parquet(
                group_df,
                gold_key,
                compression=Config.PARQUET_COMPRESSION
            )
            
            logger.info(f"✅ Gold features: {len(group_df)} rows → {gold_key}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create Gold features: {e}", exc_info=True)
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
        feature_engineer = FeatureEngineer(
            lag_hours=Config.LAG_HOURS,
            rolling_windows=Config.ROLLING_WINDOWS,
            vietnam_holidays=Config.VIETNAM_HOLIDAYS
        )
        logger.info("✅ Components initialized")
        
        # ============ PROCESSING WORKFLOW ============
        
        # Step 1: Bronze → Silver (Weather)
        logger.info("=" * 70)
        logger.info("STEP 1: WEATHER BRONZE → SILVER")
        logger.info("=" * 70)
        
        weather_success = 0
        weather_failed = 0
        for date in date_list:
            if process_weather_bronze_to_silver(s3, weather_cleaner, date):
                weather_success += 1
            else:
                weather_failed += 1
        
        logger.info(f"Weather Silver: {weather_success} success, {weather_failed} failed")
        
        # Step 2: Bronze → Silver (Electricity)
        logger.info("=" * 70)
        logger.info("STEP 2: ELECTRICITY BRONZE → SILVER")
        logger.info("=" * 70)
        
        electricity_success = 0
        electricity_failed = 0
        for date in date_list:
            if process_electricity_bronze_to_silver(s3, electricity_cleaner, date):
                electricity_success += 1
            else:
                electricity_failed += 1
        
        logger.info(f"Electricity Silver: {electricity_success} success, {electricity_failed} failed")
        
        # Step 3: Silver → Gold (Feature Engineering)
        logger.info("=" * 70)
        logger.info("STEP 3: SILVER → GOLD (FEATURE ENGINEERING)")
        logger.info("=" * 70)
        
        gold_success = process_silver_to_gold(s3, feature_engineer, date_list)
        
        # ============ FINAL REPORT ============
        logger.info("=" * 70)
        logger.info("🎉 PROCESSING COMPLETED")
        logger.info("=" * 70)
        logger.info(f"Mode: {Config.MODE}")
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info(f"Weather Silver: {weather_success}/{len(date_list)}")
        logger.info(f"Electricity Silver: {electricity_success}/{len(date_list)}")
        logger.info(f"Gold Features: {'✅ Success' if gold_success else '❌ Failed'}")
        
        # Check if any failures
        if weather_failed > 0 or electricity_failed > 0 or not gold_success:
            logger.warning(f"⚠️ Some tasks failed")
            if Config.MODE == "DAILY":
                sys.exit(1)  # Fail in DAILY mode
            # In BACKFILL mode, partial success is OK
        
        logger.info("✅ All processing completed successfully")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()