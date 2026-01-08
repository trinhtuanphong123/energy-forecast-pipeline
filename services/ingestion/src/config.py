"""
config.py
⚙️ Quản lý tập trung tất cả Config của Service Ingestion
"""
import os
from datetime import datetime, timedelta
from typing import Literal

from datetime import datetime, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7))
now_vn = datetime.now(VN_TZ)


class Config:
    """Centralized configuration management"""
    
    # ============ MODE CONFIGURATION ============
    # Chạy mode nào? BACKFILL (1 lần) hoặc DAILY (hàng ngày)
    @staticmethod
    def get_mode() -> Literal["BACKFILL", "DAILY"]:
        return os.getenv("MODE", "DAILY")

    
    # ============ API KEYS (Secret) ============
    VISUAL_CROSSING_API_KEY = os.getenv("VISUAL_CROSSING_API_KEY")
    ELECTRICITY_MAPS_API_KEY = os.getenv("ELECTRICITY_MAPS_API_KEY")
    
    # ============ S3 CONFIGURATION ============
    S3_BUCKET = os.getenv("S3_BUCKET", "vietnam-energy-data")
    S3_BRONZE_PREFIX = "bronze"  # s3://bucket/bronze/...
    
    # ============ WEATHER API CONFIG ============
    WEATHER_API_HOST = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    WEATHER_LOCATION = "Vietnam"
    WEATHER_ELEMENTS = "datetime,temp,humidity,precip,windspeed,cloudcover"
    
    # ============ ELECTRICITY API CONFIG ============
    ELECTRICITY_API_HOST = "https://api.electricitymaps.com/v3"
    ELECTRICITY_ZONE = "VN"
    ELECTRICITY_GRANULARITY = "hourly"
    
    # Các signal cần lấy từ Electricity Maps
    ELECTRICITY_SIGNALS = [
        "carbon_intensity",
        "total_load",
        "price_day_ahead",
        "electricity_mix",
        "electricity_flows"
    ]
    
    # Mapping signal name -> API endpoint path
    ENDPOINT_MAPPING = {
        "total_load": "total-load",
        "carbon_intensity": "carbon-intensity",
        "price_day_ahead": "price-day-ahead",
        "electricity_mix": "electricity-mix",
        "electricity_flows": "electricity-flows"
    }
    
    # ============ DATE RANGE CONFIG ============
    @staticmethod
    def get_date_range():
        now_vn = datetime.now(timezone(timedelta(hours=7)))

        if Config.get_mode() == "BACKFILL":
            start_date = "2021-10-27"
            end_date = (now_vn - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            yesterday = now_vn - timedelta(days=1)
            start_date = yesterday.strftime("%Y-%m-%d")
            end_date = start_date

        return start_date, end_date
    
    # ============ RETRY CONFIG ============
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    # ============ LOGGING CONFIG ============
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @staticmethod
    def validate():
        """Kiểm tra config có hợp lệ không"""
        errors = []
        
        if not Config.VISUAL_CROSSING_API_KEY:
            errors.append("❌ VISUAL_CROSSING_API_KEY không được set")
        
        if not Config.ELECTRICITY_MAPS_API_KEY:
            errors.append("❌ ELECTRICITY_MAPS_API_KEY không được set")
        
        if not Config.S3_BUCKET:
            errors.append("❌ S3_BUCKET không được set")
        
        if Config.MODE not in ["BACKFILL", "DAILY"]:
            errors.append(f"❌ MODE không hợp lệ: {Config.MODE}. Phải là BACKFILL hoặc DAILY")
        
        if errors:
            raise ValueError("\n".join(errors))
        
        return True