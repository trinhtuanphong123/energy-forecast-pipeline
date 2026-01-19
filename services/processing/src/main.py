"""
main.py
🏁 Main Entry Point - Processing Service (Refactored V2)
Pipeline: Bronze → Silver → Gold (Canonical)
Modes: BACKFILL, HOURLY, COMPACTION_DAILY, COMPACTION_MONTHLY
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
from etl.compactor import ProcessingCompactor

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

# ============ BRONZE → SILVER (Physical Cleaning) ============

def process_weather_bronze_to_silver(
    s3: S3Connector,
    cleaner: WeatherCleaner,
    date: str,
    hour: str = None
) -> bool:
    """
    Bronze → Silver: Weather (Physical Cleaning)
    
    Args:
        s3: S3Connector
        cleaner: WeatherCleaner
        date: Date string
        hour: Hour string (optional, for HOURLY mode)
    """
    try:
        logger.info(f"☀️ Processing weather: {date}" + (f" {hour}:00" if hour else ""))
        
        # Read Bronze data (either data.json or HH_30.json)
        if hour is not None:
            # HOURLY mode: Read HH_30.json
            bronze_key = s3.get_partition_path(
                Config.WEATHER_BRONZE_PATH,
                date,
                hour=hour  # Will generate: .../HH_30.json
            )
        else:
            # BACKFILL mode: Read data.json
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
        
        # Write Silver data
        if hour is not None:
            # HOURLY mode: Write to HH_30.parquet
            silver_key = f"{Config.WEATHER_SILVER_PATH}/year={date[:4]}/month={date[5:7]}/day={date[8:10]}/{hour}_30.parquet"
        else:
            # BACKFILL mode: Write to data.parquet
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
        logger.error(f"❌ Failed weather for {date}: {e}", exc_info=True)
        return False

def process_electricity_bronze_to_silver(
    s3: S3Connector,
    cleaner: ElectricityCleaner,
    date: str,
    hour: str = None
) -> bool:
    """
    Bronze → Silver: Electricity (Physical Cleaning - total_load only)
    
    Args:
        s3: S3Connector
        cleaner: ElectricityCleaner
        date: Date string
        hour: Hour string (optional, for HOURLY mode)
    """
    try:
        logger.info(f"⚡ Processing electricity: {date}" + (f" {hour}:00" if hour else ""))
        
        signal = "total_load"
        
        # Read Bronze data
        if hour is not None:
            # HOURLY mode: Read HH_30.json
            bronze_key = s3.get_partition_path(
                f"{Config.ELECTRICITY_BRONZE_PATH}/{signal}",
                date,
                hour=hour
            )
        else:
            # BACKFILL mode: Read data.json
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
        
        # Write Silver data
        if hour is not None:
            # HOURLY mode: Write to HH_30.parquet
            silver_key = f"{Config.ELECTRICITY_SILVER_PATH}/year={date[:4]}/month={date[5:7]}/day={date[8:10]}/{hour}_30.parquet"
        else:
            # BACKFILL mode: Write to data.parquet
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
        
        logger.info(f"✅ Electricity Silver: {len(cleaned_df)} rows → {silver_key}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed electricity for {date}: {e}", exc_info=True)
        return False

# ============ SILVER → GOLD (Canonical Table) ============

def process_silver_to_canonical(
    s3: S3Connector,
    merger: CanonicalMerger,
    date_list: List[str]
) -> bool:
    """
    Silver → Gold: Create Canonical Table (Logical Cleaning)
    
    Reads daily Silver files và creates daily Gold files
    """
    try:
        logger.info(f"🌟 Creating Canonical Table for {len(date_list)} days")
        
        import pandas as pd
        
        for date in date_list:
            logger.info(f"  📅 Processing {date}")
            
            # Read Weather Silver (daily file)
            weather_key = s3.get_partition_path(
                Config.WEATHER_SILVER_PATH,
                date,
                "data.parquet"
            )
            
            if not s3.check_file_exists(weather_key):
                logger.warning(f"    ⚠️ Weather Silver not found for {date}")
                continue
            
            weather_df = s3.read_parquet(weather_key)
            
            # Read Electricity Silver (daily file)
            elec_key = s3.get_partition_path(
                Config.ELECTRICITY_SILVER_PATH,
                date,
                "data.parquet"
            )
            
            if not s3.check_file_exists(elec_key):
                logger.warning(f"    ⚠️ Electricity Silver not found for {date}")
                continue
            
            elec_df = s3.read_parquet(elec_key)
            
            # Create Canonical Table for this day
            canonical_df = merger.merge(weather_df, elec_df)
            merger.validate_canonical(canonical_df)
            
            # Write daily Gold file
            gold_key = s3.get_partition_path(
                Config.GOLD_CANONICAL_PATH,
                date,
                "data.parquet"
            )
            
            s3.write_parquet(
                canonical_df,
                gold_key,
                compression=Config.PARQUET_COMPRESSION
            )
            
            logger.info(f"    ✅ Canonical: {len(canonical_df)} rows → {gold_key}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed Canonical Table: {e}", exc_info=True)
        return False



def process_hourly_silver_to_gold(
    s3: S3Connector,
    merger: CanonicalMerger,
    date: str,
    hour: str
    ) -> bool:
    """
    Create hourly Gold Canonical from hourly Silver files
    
    Args:
    s3: S3Connector
    merger: CanonicalMerger
    date: Date string (YYYY-MM-DD)
    hour: Hour string (HH)
    
    Returns:
        bool: Success status
    """
    try:
        logger.info(f"🌟 Creating hourly Gold: {date} {hour}:00")
        
        # Read Weather Silver (hourly)
        weather_key = f"{Config.WEATHER_SILVER_PATH}/year={date[:4]}/month={date[5:7]}/day={date[8:10]}/{hour}_30.parquet"
        
        if not s3.check_file_exists(weather_key):
            logger.warning(f"⚠️ Weather Silver not found: {weather_key}")
            return False
        
        weather_df = s3.read_parquet(weather_key)
        
        # Read Electricity Silver (hourly)
        elec_key = f"{Config.ELECTRICITY_SILVER_PATH}/year={date[:4]}/month={date[5:7]}/day={date[8:10]}/{hour}_30.parquet"
        
        if not s3.check_file_exists(elec_key):
            logger.warning(f"⚠️ Electricity Silver not found: {elec_key}")
            return False
        
        elec_df = s3.read_parquet(elec_key)
        
        # Create Canonical (merge weather + electricity)
        canonical_df = merger.merge(weather_df, elec_df)
        merger.validate_canonical(canonical_df)
        
        # Write hourly Gold file
        gold_key = f"{Config.GOLD_CANONICAL_PATH}/year={date[:4]}/month={date[5:7]}/day={date[8:10]}/{hour}_30.parquet"
        
        s3.write_parquet(
            canonical_df,
            gold_key,
            compression=Config.PARQUET_COMPRESSION
        )
        
        logger.info(f"✅ Hourly Gold: {len(canonical_df)} rows → {gold_key}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed hourly Gold for {date} {hour}:00: {e}", exc_info=True)
        return False

    

# ============ MODE HANDLERS ============

def run_backfill_mode():
    """
    BACKFILL mode: Xử lý toàn bộ dữ liệu lịch sử
    
    Flow:
    1. Bronze → Silver (all days)
    2. Silver → Gold (all days, daily files)
    3. Compact Gold daily → monthly (for complete months)
    """
    logger.info("=" * 70)
    logger.info("MODE: BACKFILL")
    logger.info("=" * 70)
    
    start_date, end_date = Config.get_processing_target()
    date_list = generate_date_list(start_date, end_date)
    logger.info(f"📅 Processing {len(date_list)} days: {start_date} to {end_date}")
    
    # Initialize components
    s3 = S3Connector(Config.S3_BUCKET)
    weather_cleaner = WeatherCleaner(Config.SOURCE_TIMEZONE, Config.TARGET_TIMEZONE)
    electricity_cleaner = ElectricityCleaner(Config.SOURCE_TIMEZONE, Config.TARGET_TIMEZONE)
    canonical_merger = CanonicalMerger()
    compactor = ProcessingCompactor(s3)
    
    # Step 1: Bronze → Silver
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
    
    # Step 2: Silver → Gold (daily files)
    logger.info("=" * 70)
    logger.info("STEP 2: SILVER → GOLD (Canonical Table - Daily)")
    logger.info("=" * 70)
    
    canonical_success = process_silver_to_canonical(s3, canonical_merger, date_list)
    
    # Step 3: Compact complete months
    logger.info("=" * 70)
    logger.info("STEP 3: COMPACT COMPLETE MONTHS (Gold)")
    logger.info("=" * 70)
    
    # Find all complete months in date range
    import pandas as pd
    dates = pd.to_datetime(date_list)
    months = dates.to_period('M').unique()
    
    for month in months:
        year = month.year
        month_num = month.month
        
        result = compactor.compact_monthly_gold(year, month_num)
        logger.info(f"  {year}-{month_num:02d}: {result['status']}")
    
    return {
        "weather_silver": f"{weather_success}/{len(date_list)}",
        "electricity_silver": f"{electricity_success}/{len(date_list)}",
        "canonical": canonical_success
    }

def run_hourly_mode():
    """
    HOURLY mode: Xử lý dữ liệu giờ vừa thu thập
    
    Flow:
    1. Bronze (HH_30.json) → Silver (HH_30.parquet) for target hour
    2. Create hourly Gold Canonical file
    """
    logger.info("=" * 70)
    logger.info("MODE: HOURLY")
    logger.info("=" * 70)
    
    target_date, target_hour = Config.get_processing_target()
    logger.info(f"🎯 Target: {target_date} {target_hour}:00")
    
    # Initialize components
    s3 = S3Connector(Config.S3_BUCKET)
    weather_cleaner = WeatherCleaner(Config.SOURCE_TIMEZONE, Config.TARGET_TIMEZONE)
    electricity_cleaner = ElectricityCleaner(Config.SOURCE_TIMEZONE, Config.TARGET_TIMEZONE)
    
    # Bronze → Silver (for this hour only)
    logger.info("=" * 70)
    logger.info("STEP: BRONZE → SILVER (Physical Cleaning)")
    logger.info("=" * 70)
    
    weather_success = process_weather_bronze_to_silver(
        s3, weather_cleaner, target_date, target_hour
    )
    
    electricity_success = process_electricity_bronze_to_silver(
        s3, electricity_cleaner, target_date, target_hour
    )
    
    # ============ NEW: CREATE HOURLY GOLD ============
    logger.info("=" * 70)
    logger.info("STEP 2: SILVER → GOLD (Hourly Canonical)")
    logger.info("=" * 70)
   
    canonical_merger = CanonicalMerger()
    gold_success = process_hourly_silver_to_gold(
       s3, canonical_merger, target_date, target_hour
    )
    
    return {
        "weather": weather_success,

        "electricity": electricity_success,
        "gold": gold_success
    }

    

def run_compaction_daily_mode():
    """
    COMPACTION_DAILY mode: Gộp 24 hourly Silver files thành 1 daily file
    
    Flow:
    1. Silver (24x HH_30.parquet) → Silver (1x data.parquet)
    2. Silver → Gold (create daily Canonical file)
    """
    logger.info("=" * 70)
    logger.info("MODE: COMPACTION_DAILY")
    logger.info("=" * 70)
    
    target_date = Config.get_processing_target()[0]
    logger.info(f"🎯 Target: {target_date}")
    
    # Initialize components
    s3 = S3Connector(Config.S3_BUCKET)
    compactor = ProcessingCompactor(s3)
    canonical_merger = CanonicalMerger()
    
    # Step 1: Compact Silver (hourly → daily)
    logger.info("=" * 70)
    logger.info("STEP 1: COMPACT SILVER (Hourly → Daily)")
    logger.info("=" * 70)
    
    results = compactor.compact_daily_silver(target_date)
    
    # Step 2: Create Canonical Table for this day
    logger.info("=" * 70)
    logger.info("STEP 2: CREATE CANONICAL TABLE")
    logger.info("=" * 70)
    
    canonical_success = process_silver_to_canonical(s3, canonical_merger, [target_date])
    
    # Step 3: Delete hourly Gold files (daily now exists)
    logger.info("=" * 70)
    logger.info("STEP 3: CLEANUP HOURLY GOLD FILES")
    logger.info("=" * 70)
    
    gold_cleanup = compactor.compact_hourly_gold(target_date)
    
    return {
        "compaction": results,
        "canonical": canonical_success,
        "gold_cleanup": gold_cleanup
    }

def run_compaction_monthly_mode():
    """
    COMPACTION_MONTHLY mode: Gộp daily Gold files thành 1 monthly file
    
    Flow:
    1. Gold (Nx daily data.parquet) → Gold (1x monthly data.parquet)
    
    Chỉ chạy nếu tháng đã complete
    """
    logger.info("=" * 70)
    logger.info("MODE: COMPACTION_MONTHLY")
    logger.info("=" * 70)
    
    target_year, target_month = Config.get_processing_target()
    logger.info(f"🎯 Target: {target_year}-{target_month:02d}")
    
    # Initialize components
    s3 = S3Connector(Config.S3_BUCKET)
    compactor = ProcessingCompactor(s3)
    
    # Compact monthly
    logger.info("=" * 70)
    logger.info("STEP: COMPACT GOLD (Daily → Monthly)")
    logger.info("=" * 70)
    
    result = compactor.compact_monthly_gold(target_year, target_month)
    
    return result

# ============ MAIN ============

def main():
    """Main orchestrator"""
    try:
        # Print banner
        print(Config.get_summary())
        
        # Validate config
        logger.info("🔍 Validating configuration...")
        Config.validate()
        logger.info("✅ Config OK")
        
        mode = Config.get_mode()
        
        # Route to appropriate mode handler
        if mode == "BACKFILL":
            results = run_backfill_mode()
            logger.info("=" * 70)
            logger.info("🎉 BACKFILL COMPLETED")
            logger.info("=" * 70)
            logger.info(f"Results: {results}")
            
        elif mode == "HOURLY":
            results = run_hourly_mode()
            logger.info("=" * 70)
            logger.info("🎉 HOURLY PROCESSING COMPLETED")
            logger.info("=" * 70)
            logger.info(f"Results: {results}")
            
        elif mode == "COMPACTION_DAILY":
            results = run_compaction_daily_mode()
            logger.info("=" * 70)
            logger.info("🎉 DAILY COMPACTION COMPLETED")
            logger.info("=" * 70)
            logger.info(f"Results: {results}")
            
        elif mode == "COMPACTION_MONTHLY":
            results = run_compaction_monthly_mode()
            logger.info("=" * 70)
            logger.info("🎉 MONTHLY COMPACTION COMPLETED")
            logger.info("=" * 70)
            logger.info(f"Results: {results}")
        
        logger.info("✅ All processing completed successfully")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()