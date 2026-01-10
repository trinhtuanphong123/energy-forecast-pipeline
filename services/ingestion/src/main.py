"""
main.py
🏁 Entry Point của Service Ingestion
Hỗ trợ 3 modes: BACKFILL, HOURLY, COMPACTION
"""
import logging
import sys
from datetime import datetime, timedelta
from typing import List

from config import Config
from s3_writer import S3Writer
from api_clients.weather import WeatherAPIClient
from api_clients.electricity import ElectricityAPIClient
from compactor import DataCompactor

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

def ingest_weather_data_backfill(
    weather_client: WeatherAPIClient,
    s3_writer: S3Writer,
    date_list: List[str]
) -> dict:
    """
    Ingest weather data cho BACKFILL mode (toàn bộ ngày, lưu 1 file)
    
    Args:
        weather_client: Weather API client
        s3_writer: S3 writer instance
        date_list: List các ngày cần lấy
    
    Returns:
        dict: Kết quả thống kê {success: int, failed: int}
    """
    logger.info(f"☀️ Starting weather data ingestion (BACKFILL) for {len(date_list)} days")
    
    stats = {"success": 0, "failed": 0, "skipped": 0}
    
    for idx, date in enumerate(date_list, 1):
        try:
            logger.info(f"📅 [{idx}/{len(date_list)}] Processing {date}")
            
            # Check if file already exists
            s3_key = s3_writer._generate_partition_path("weather", date, hour=None)
            if s3_writer.check_file_exists(s3_key):
                logger.info(f"⏭️ File already exists, skipping...")
                stats["skipped"] += 1
                continue
            
            # Fetch data from API (full day data)
            data = weather_client.fetch_data(date)
            
            # Write to S3 (hour=None -> data.json)
            s3_uri = s3_writer.write_weather_data(data, date, hour=None)
            
            logger.info(f"✅ [{idx}/{len(date_list)}] {date} -> {s3_uri}")
            stats["success"] += 1
            
        except Exception as e:
            logger.error(f"❌ [{idx}/{len(date_list)}] Failed to process {date}: {str(e)}")
            stats["failed"] += 1
    
    logger.info(f"☀️ Weather ingestion (BACKFILL) completed: {stats}")
    return stats

def ingest_weather_data_hourly(
    weather_client: WeatherAPIClient,
    s3_writer: S3Writer,
    target_date: str,
    target_hour: str
) -> dict:
    """
    Ingest weather data cho HOURLY mode (1 giờ, lưu file riêng)
    
    Args:
        weather_client: Weather API client
        s3_writer: S3 writer instance
        target_date: Ngày cần lấy (format: YYYY-MM-DD)
        target_hour: Giờ cần lấy (format: HH)
    
    Returns:
        dict: Kết quả thống kê
    """
    logger.info(f"☀️ Starting weather data ingestion (HOURLY) for {target_date} {target_hour}:00")
    
    stats = {"success": 0, "failed": 0, "skipped": 0}
    
    try:
        # Check if file already exists
        s3_key = s3_writer._generate_partition_path("weather", target_date, hour=target_hour)
        if s3_writer.check_file_exists(s3_key):
            logger.info(f"⏭️ File already exists, skipping...")
            stats["skipped"] = 1
            return stats
        
        # Fetch data from API (full day, will extract 1 hour)
        data = weather_client.fetch_data(target_date)
        
        # Extract only the target hour
        if 'days' in data and len(data['days']) > 0:
            day_data = data['days'][0]
            if 'hours' in day_data:
                # Find the specific hour
                target_hour_data = None
                for hour_data in day_data['hours']:
                    hour_str = hour_data['datetime'].split(':')[0]  # "13:00:00" -> "13"
                    if hour_str == target_hour:
                        target_hour_data = hour_data
                        break
                
                if target_hour_data:
                    # Create single-hour structure
                    hourly_data = {
                        k: v for k, v in data.items() 
                        if k != 'days'
                    }
                    hourly_data['days'] = [{
                        'datetime': target_date,
                        'hours': [target_hour_data]
                    }]
                    
                    # Write to S3 with hour specification
                    s3_uri = s3_writer.write_weather_data(hourly_data, target_date, hour=target_hour)
                    
                    logger.info(f"✅ {target_date} {target_hour}:00 -> {s3_uri}")
                    stats["success"] = 1
                else:
                    logger.error(f"❌ Hour {target_hour} not found in API response")
                    stats["failed"] = 1
            else:
                logger.error(f"❌ No hourly data in API response")
                stats["failed"] = 1
        else:
            logger.error(f"❌ Invalid API response structure")
            stats["failed"] = 1
            
    except Exception as e:
        logger.error(f"❌ Failed to process {target_date} {target_hour}:00: {str(e)}")
        stats["failed"] = 1
    
    logger.info(f"☀️ Weather ingestion (HOURLY) completed: {stats}")
    return stats

def ingest_electricity_data_backfill(
    electricity_client: ElectricityAPIClient,
    s3_writer: S3Writer,
    date_list: List[str],
    signal_list: List[str]
) -> dict:
    """
    Ingest electricity data cho BACKFILL mode
    
    Args:
        electricity_client: Electricity API client
        s3_writer: S3 writer instance
        date_list: List các ngày cần lấy
        signal_list: List các signals cần lấy
    
    Returns:
        dict: Kết quả thống kê
    """
    logger.info(f"⚡ Starting electricity data ingestion (BACKFILL) for {len(date_list)} days x {len(signal_list)} signals")
    
    stats = {"success": 0, "failed": 0, "skipped": 0}
    
    for date_idx, date in enumerate(date_list, 1):
        logger.info(f"📅 [{date_idx}/{len(date_list)}] Processing {date}")
        
        for signal_idx, signal in enumerate(signal_list, 1):
            try:
                logger.info(f"  ⚡ [{signal_idx}/{len(signal_list)}] Fetching {signal}")
                
                # Check if file already exists
                s3_key = s3_writer._generate_partition_path("electricity", date, signal, hour=None)
                if s3_writer.check_file_exists(s3_key):
                    logger.info(f"  ⏭️ File already exists, skipping...")
                    stats["skipped"] += 1
                    continue
                
                # Fetch data from API
                data = electricity_client.fetch_data(date, signal)
                
                # Write to S3
                s3_uri = s3_writer.write_electricity_data(data, signal, date, hour=None)
                
                logger.info(f"  ✅ {signal} -> {s3_uri}")
                stats["success"] += 1
                
            except Exception as e:
                logger.error(f"  ❌ Failed to process {signal} for {date}: {str(e)}")
                stats["failed"] += 1
    
    logger.info(f"⚡ Electricity ingestion (BACKFILL) completed: {stats}")
    return stats

def ingest_electricity_data_hourly(
    electricity_client: ElectricityAPIClient,
    s3_writer: S3Writer,
    target_date: str,
    target_hour: str,
    signal_list: List[str]
) -> dict:
    """
    Ingest electricity data cho HOURLY mode
    
    Args:
        electricity_client: Electricity API client
        s3_writer: S3 writer instance
        target_date: Ngày cần lấy
        target_hour: Giờ cần lấy
        signal_list: List các signals
    
    Returns:
        dict: Kết quả thống kê
    """
    logger.info(f"⚡ Starting electricity data ingestion (HOURLY) for {target_date} {target_hour}:00")
    
    stats = {"success": 0, "failed": 0, "skipped": 0}
    
    for signal_idx, signal in enumerate(signal_list, 1):
        try:
            logger.info(f"  ⚡ [{signal_idx}/{len(signal_list)}] Fetching {signal}")
            
            # Check if file already exists
            s3_key = s3_writer._generate_partition_path("electricity", target_date, signal, hour=target_hour)
            if s3_writer.check_file_exists(s3_key):
                logger.info(f"  ⏭️ File already exists, skipping...")
                stats["skipped"] += 1
                continue
            
            # Fetch data from API (full day)
            data = electricity_client.fetch_data(target_date, signal)
            
            # Extract only target hour
            if 'history' in data:
                target_hour_data = None
                for record in data['history']:
                    datetime_str = record['datetime']  # "2024-01-11T13:00:00Z"
                    hour_str = datetime_str.split('T')[1].split(':')[0]
                    if hour_str == target_hour:
                        target_hour_data = record
                        break
                
                if target_hour_data:
                    # Create single-hour structure
                    hourly_data = {
                        k: v for k, v in data.items() 
                        if k not in ['history', '_metadata']
                    }
                    hourly_data['history'] = [target_hour_data]
                    hourly_data['_metadata'] = {
                        "signal": signal,
                        "query_date": target_date,
                        "hour": target_hour,
                        "zone": Config.ELECTRICITY_ZONE
                    }
                    
                    # Write to S3
                    s3_uri = s3_writer.write_electricity_data(hourly_data, signal, target_date, hour=target_hour)
                    
                    logger.info(f"  ✅ {signal} -> {s3_uri}")
                    stats["success"] += 1
                else:
                    logger.error(f"  ❌ Hour {target_hour} not found for {signal}")
                    stats["failed"] += 1
            else:
                logger.error(f"  ❌ No history data for {signal}")
                stats["failed"] += 1
                
        except Exception as e:
            logger.error(f"  ❌ Failed to process {signal}: {str(e)}")
            stats["failed"] += 1
    
    logger.info(f"⚡ Electricity ingestion (HOURLY) completed: {stats}")
    return stats

def run_backfill_mode():
    """
    Chạy BACKFILL mode: Lấy toàn bộ dữ liệu lịch sử
    """
    logger.info("=" * 60)
    logger.info("MODE: BACKFILL")
    logger.info("=" * 60)
    
    # Get date range
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
    
    s3_writer = S3Writer(
        bucket_name=Config.S3_BUCKET,
        bronze_prefix=Config.S3_BRONZE_PREFIX
    )
    
    # Ingest data
    logger.info("=" * 60)
    logger.info("STEP 1: WEATHER DATA INGESTION")
    logger.info("=" * 60)
    weather_stats = ingest_weather_data_backfill(weather_client, s3_writer, date_list)
    
    logger.info("=" * 60)
    logger.info("STEP 2: ELECTRICITY DATA INGESTION")
    logger.info("=" * 60)
    electricity_stats = ingest_electricity_data_backfill(
        electricity_client, 
        s3_writer, 
        date_list,
        Config.ELECTRICITY_SIGNALS
    )
    
    return weather_stats, electricity_stats

def run_hourly_mode():
    """
    Chạy HOURLY mode: Lấy dữ liệu của giờ trước
    """
    logger.info("=" * 60)
    logger.info("MODE: HOURLY")
    logger.info("=" * 60)
    
    # Get target datetime
    target_date, target_hour = Config.get_target_datetime()
    logger.info(f"🎯 Target: {target_date} {target_hour}:00")
    
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
    
    s3_writer = S3Writer(
        bucket_name=Config.S3_BUCKET,
        bronze_prefix=Config.S3_BRONZE_PREFIX
    )
    
    # Ingest data
    logger.info("=" * 60)
    logger.info("STEP 1: WEATHER DATA INGESTION")
    logger.info("=" * 60)
    weather_stats = ingest_weather_data_hourly(
        weather_client, 
        s3_writer, 
        target_date, 
        target_hour
    )
    
    logger.info("=" * 60)
    logger.info("STEP 2: ELECTRICITY DATA INGESTION")
    logger.info("=" * 60)
    electricity_stats = ingest_electricity_data_hourly(
        electricity_client,
        s3_writer,
        target_date,
        target_hour,
        Config.ELECTRICITY_SIGNALS
    )
    
    return weather_stats, electricity_stats

def run_compaction_mode():
    """
    Chạy COMPACTION mode: Gộp hourly files của ngày hôm qua
    """
    logger.info("=" * 60)
    logger.info("MODE: COMPACTION")
    logger.info("=" * 60)
    
    # Get yesterday's date
    start_date, end_date = Config.get_date_range()
    logger.info(f"🎯 Compacting data for: {start_date}")
    
    # Initialize S3 writer and compactor
    s3_writer = S3Writer(
        bucket_name=Config.S3_BUCKET,
        bronze_prefix=Config.S3_BRONZE_PREFIX
    )
    
    compactor = DataCompactor(s3_writer)
    
    # Run compaction
    results = compactor.compact_all(start_date)
    
    # Check results
    success = True
    if results['weather']['status'] != 'success':
        logger.error(f"❌ Weather compaction failed")
        success = False
    
    for signal, result in results['electricity'].items():
        if result['status'] != 'success':
            logger.error(f"❌ {signal} compaction failed")
            success = False
    
    if success:
        logger.info("✅ All compactions completed successfully")
    
    return results

def main():
    """
    Main orchestrator function
    """
    try:
        # Validate config
        logger.info("🔍 Validating configuration...")
        Config.validate()
        
        mode = Config.get_mode()
        logger.info(f"✅ Config OK - Mode: {mode}")
        
        # Route to appropriate mode handler
        if mode == "BACKFILL":
            weather_stats, electricity_stats = run_backfill_mode()
            
            # Final report
            logger.info("=" * 60)
            logger.info("🎉 BACKFILL COMPLETED")
            logger.info("=" * 60)
            logger.info(f"Weather: {weather_stats}")
            logger.info(f"Electricity: {electricity_stats}")
            
            total_failed = weather_stats["failed"] + electricity_stats["failed"]
            if total_failed > 0:
                logger.warning(f"⚠️ {total_failed} tasks failed")
                sys.exit(1)
            else:
                logger.info("✅ All tasks completed successfully")
                sys.exit(0)
        
        elif mode == "HOURLY":
            weather_stats, electricity_stats = run_hourly_mode()
            
            # Final report
            logger.info("=" * 60)
            logger.info("🎉 HOURLY INGESTION COMPLETED")
            logger.info("=" * 60)
            logger.info(f"Weather: {weather_stats}")
            logger.info(f"Electricity: {electricity_stats}")
            
            total_failed = weather_stats["failed"] + electricity_stats["failed"]
            if total_failed > 0:
                logger.warning(f"⚠️ {total_failed} tasks failed")
                sys.exit(1)
            else:
                logger.info("✅ All tasks completed successfully")
                sys.exit(0)
        
        elif mode == "COMPACTION":
            results = run_compaction_mode()
            
            # Final report
            logger.info("=" * 60)
            logger.info("🎉 COMPACTION COMPLETED")
            logger.info("=" * 60)
            logger.info(f"Results: {results}")
            
            # Check for failures
            has_error = False
            if results['weather']['status'] != 'success':
                has_error = True
            for signal, result in results['electricity'].items():
                if result['status'] != 'success':
                    has_error = True
            
            if has_error:
                logger.warning("⚠️ Some compactions failed")
                sys.exit(1)
            else:
                logger.info("✅ All compactions completed successfully")
                sys.exit(0)
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()