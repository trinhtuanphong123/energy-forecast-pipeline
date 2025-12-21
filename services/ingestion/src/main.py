"""
main.py
🏁 Entry Point của Service Ingestion
Điều phối luồng: API Clients -> S3 Writer
"""
import logging
import sys
from datetime import datetime, timedelta
from typing import List

from config import Config
from s3_writer import S3Writer
from api_clients.weather import WeatherAPIClient
from api_clients.electricity import ElectricityAPIClient

# Setup logging
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def generate_date_list(start_date: str, end_date: str) -> List[str]:
    """
    Tạo list các ngày từ start_date đến end_date
    
    Args:
        start_date: Ngày bắt đầu (format: YYYY-MM-DD)
        end_date: Ngày kết thúc (format: YYYY-MM-DD)
    
    Returns:
        List[str]: List các ngày
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    date_list = []
    current = start
    
    while current <= end:
        date_list.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    return date_list

def ingest_weather_data(
    weather_client: WeatherAPIClient,
    s3_writer: S3Writer,
    date_list: List[str]
) -> dict:
    """
    Ingest weather data cho list các ngày
    
    Args:
        weather_client: Weather API client
        s3_writer: S3 writer instance
        date_list: List các ngày cần lấy
    
    Returns:
        dict: Kết quả thống kê {success: int, failed: int}
    """
    logger.info(f"☀️ Starting weather data ingestion for {len(date_list)} days")
    
    stats = {"success": 0, "failed": 0, "skipped": 0}
    
    for idx, date in enumerate(date_list, 1):
        try:
            logger.info(f"📅 [{idx}/{len(date_list)}] Processing {date}")
            
            # Check if file already exists (skip if in DAILY mode)
            if Config.MODE == "DAILY":
                s3_key = s3_writer._generate_partition_path("weather", date)
                if s3_writer.check_file_exists(s3_key):
                    logger.info(f"⏭️ File already exists, skipping...")
                    stats["skipped"] += 1
                    continue
            
            # Fetch data from API
            data = weather_client.fetch_data(date)
            
            # Write to S3
            s3_uri = s3_writer.write_weather_data(data, date)
            
            logger.info(f"✅ [{idx}/{len(date_list)}] {date} -> {s3_uri}")
            stats["success"] += 1
            
        except Exception as e:
            logger.error(f"❌ [{idx}/{len(date_list)}] Failed to process {date}: {str(e)}")
            stats["failed"] += 1
            
            # Nếu là DAILY mode và fail, raise exception để báo lỗi
            if Config.MODE == "DAILY":
                raise
    
    logger.info(f"☀️ Weather ingestion completed: {stats}")
    return stats

def ingest_electricity_data(
    electricity_client: ElectricityAPIClient,
    s3_writer: S3Writer,
    date_list: List[str],
    signal_list: List[str]
) -> dict:
    """
    Ingest electricity data cho list các ngày và signals
    
    Args:
        electricity_client: Electricity API client
        s3_writer: S3 writer instance
        date_list: List các ngày cần lấy
        signal_list: List các signals cần lấy
    
    Returns:
        dict: Kết quả thống kê {success: int, failed: int}
    """
    logger.info(f"⚡ Starting electricity data ingestion for {len(date_list)} days x {len(signal_list)} signals")
    
    stats = {"success": 0, "failed": 0, "skipped": 0}
    
    for date_idx, date in enumerate(date_list, 1):
        logger.info(f"📅 [{date_idx}/{len(date_list)}] Processing {date}")
        
        for signal_idx, signal in enumerate(signal_list, 1):
            try:
                logger.info(f"  ⚡ [{signal_idx}/{len(signal_list)}] Fetching {signal}")
                
                # Check if file already exists (skip if in DAILY mode)
                if Config.MODE == "DAILY":
                    s3_key = s3_writer._generate_partition_path("electricity", date, signal)
                    if s3_writer.check_file_exists(s3_key):
                        logger.info(f"  ⏭️ File already exists, skipping...")
                        stats["skipped"] += 1
                        continue
                
                # Fetch data from API
                data = electricity_client.fetch_data(date, signal)
                
                # Write to S3
                s3_uri = s3_writer.write_electricity_data(data, signal, date)
                
                logger.info(f"  ✅ {signal} -> {s3_uri}")
                stats["success"] += 1
                
            except Exception as e:
                logger.error(f"  ❌ Failed to process {signal} for {date}: {str(e)}")
                stats["failed"] += 1
                
                # Nếu là DAILY mode và fail, raise exception để báo lỗi
                if Config.MODE == "DAILY":
                    raise
    
    logger.info(f"⚡ Electricity ingestion completed: {stats}")
    return stats

def main():
    """
    Main orchestrator function
    """
    try:
        # Validate config
        logger.info("🔍 Validating configuration...")
        Config.validate()
        logger.info(f"✅ Config OK - Mode: {Config.MODE}")
        
        # Get date range based on MODE
        start_date, end_date = Config.get_date_range()
        date_list = generate_date_list(start_date, end_date)
        logger.info(f"📅 Date range: {start_date} to {end_date} ({len(date_list)} days)")
        
        # Initialize clients
        logger.info("🔧 Initializing API clients...")
        
        weather_client = WeatherAPIClient(
            api_key=Config.VISUAL_CROSSING_API_KEY,
            api_host=Config.WEATHER_API_HOST,
            location=Config.WEATHER_LOCATION,
            elements=Config.WEATHER_ELEMENTS,
            max_retries=Config.MAX_RETRIES
        )
        
        electricity_client = ElectricityAPIClient(
            api_key=Config.ELECTRICITY_MAPS_API_KEY,
            api_host=Config.ELECTRICITY_API_HOST,
            zone=Config.ELECTRICITY_ZONE,
            granularity=Config.ELECTRICITY_GRANULARITY,
            endpoint_mapping=Config.ENDPOINT_MAPPING,
            max_retries=Config.MAX_RETRIES
        )
        
        # Initialize S3 writer
        s3_writer = S3Writer(
            bucket_name=Config.S3_BUCKET,
            bronze_prefix=Config.S3_BRONZE_PREFIX
        )
        
        logger.info("✅ All components initialized")
        
        # ============ INGESTION WORKFLOW ============
        
        # Step 1: Ingest Weather Data
        logger.info("=" * 60)
        logger.info("STEP 1: WEATHER DATA INGESTION")
        logger.info("=" * 60)
        weather_stats = ingest_weather_data(weather_client, s3_writer, date_list)
        
        # Step 2: Ingest Electricity Data
        logger.info("=" * 60)
        logger.info("STEP 2: ELECTRICITY DATA INGESTION")
        logger.info("=" * 60)
        electricity_stats = ingest_electricity_data(
            electricity_client, 
            s3_writer, 
            date_list,
            Config.ELECTRICITY_SIGNALS
        )
        
        # ============ FINAL REPORT ============
        logger.info("=" * 60)
        logger.info("🎉 INGESTION COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Mode: {Config.MODE}")
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info(f"Weather: {weather_stats}")
        logger.info(f"Electricity: {electricity_stats}")
        
        # Check if any failures
        total_failed = weather_stats["failed"] + electricity_stats["failed"]
        if total_failed > 0:
            logger.warning(f"⚠️ {total_failed} tasks failed")
            sys.exit(1)  # Exit với error code
        else:
            logger.info("✅ All tasks completed successfully")
            sys.exit(0)  # Exit success
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()