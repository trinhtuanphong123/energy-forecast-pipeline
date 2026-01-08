"""
config.py
⚙️ Configuration Management cho Service Processing (Refactored)
"""
import os
from datetime import datetime, timedelta
from typing import Literal

class Config:
    """Centralized configuration for Processing Service"""
    
    # ============ MODE CONFIGURATION ============
    MODE: Literal["BACKFILL", "DAILY"] = os.getenv("MODE", "DAILY")
    
    # ============ S3 CONFIGURATION ============
    S3_BUCKET = os.getenv("S3_BUCKET", "vietnam-energy-data")
    
    # S3 Paths
    BRONZE_PREFIX = "bronze"
    SILVER_PREFIX = "silver"
    GOLD_PREFIX = "gold"
    
    # ============ DATA SOURCE PATHS ============
    # Weather paths
    WEATHER_BRONZE_PATH = f"{BRONZE_PREFIX}/weather"
    WEATHER_SILVER_PATH = f"{SILVER_PREFIX}/weather"
    
    # Electricity paths (chỉ quan tâm total_load)
    ELECTRICITY_BRONZE_PATH = f"{BRONZE_PREFIX}/electricity"
    ELECTRICITY_SILVER_PATH = f"{SILVER_PREFIX}/electricity"
    
    # Chỉ xử lý total_load signal (bỏ qua các signal khác)
    ELECTRICITY_SIGNALS = ["total_load"]
    
    # Gold path (Canonical Table)
    GOLD_CANONICAL_PATH = f"{GOLD_PREFIX}/canonical"
    
    # ============ DATE RANGE CONFIG ============
    @staticmethod
    def get_date_range():
        """
        Trả về (start_date, end_date) dựa trên MODE
        
        Returns:
            tuple: (start_date_str, end_date_str) format "YYYY-MM-DD"
        """
        if Config.MODE == "BACKFILL":
            start_date = "2021-10-27"  # First date with data
            end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        else:  # DAILY
            yesterday = datetime.now() - timedelta(days=1)
            start_date = yesterday.strftime("%Y-%m-%d")
            end_date = start_date
        
        return start_date, end_date
    
    # ============ DATA PROCESSING CONFIG ============
    
    # Timezone conversion
    SOURCE_TIMEZONE = "UTC"
    TARGET_TIMEZONE = "Asia/Ho_Chi_Minh"
    
    # ============ LOGGING CONFIG ============
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # ============ PERFORMANCE CONFIG ============
    
    # Parquet compression
    PARQUET_COMPRESSION = "snappy"
    
    @staticmethod
    def validate():
        """Kiểm tra config có hợp lệ không"""
        errors = []
        
        if not Config.S3_BUCKET:
            errors.append("❌ S3_BUCKET không được set")
        
        if Config.MODE not in ["BACKFILL", "DAILY"]:
            errors.append(f"❌ MODE không hợp lệ: {Config.MODE}")
        
        if errors:
            raise ValueError("\n".join(errors))
        
        return True
    
    @staticmethod
    def get_summary():
        """In ra summary của config"""
        return f"""
╔══════════════════════════════════════════════════════════╗
║         PROCESSING SERVICE (REFACTORED)                  ║
╚══════════════════════════════════════════════════════════╝

Mode: {Config.MODE}
S3 Bucket: {Config.S3_BUCKET}

Pipeline:
  Bronze → Silver (Physical Cleaning)
    • Weather: {Config.WEATHER_BRONZE_PATH} → {Config.WEATHER_SILVER_PATH}
    • Electricity: {Config.ELECTRICITY_BRONZE_PATH}/total_load → {Config.ELECTRICITY_SILVER_PATH}
  
  Silver → Gold (Logical Cleaning)
    • Canonical Table: {Config.GOLD_CANONICAL_PATH}
    • Columns: [datetime, electricity_demand, temperature, humidity, wind_speed, precipitation]

Processing Config:
  • Timezone: {Config.SOURCE_TIMEZONE} → {Config.TARGET_TIMEZONE}
  • Parquet Compression: {Config.PARQUET_COMPRESSION}
        """