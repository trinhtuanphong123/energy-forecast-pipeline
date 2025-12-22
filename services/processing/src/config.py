"""
config.py
⚙️ Configuration Management cho Service Processing
"""
import os
from datetime import datetime, timedelta
from typing import Literal

class Config:
    """Centralized configuration for Processing Service"""
    
    # ============ MODE CONFIGURATION ============
    # BACKFILL: Xử lý tất cả dữ liệu từ 2021 đến nay
    # DAILY: Chỉ xử lý dữ liệu hôm qua
    MODE: Literal["BACKFILL", "DAILY"] = os.getenv("MODE", "DAILY")
    
    # ============ S3 CONFIGURATION ============
    S3_BUCKET = os.getenv("S3_BUCKET", "vietnam-energy-data")
    
    # S3 Paths
    BRONZE_PREFIX = "bronze"
    SILVER_PREFIX = "silver"
    GOLD_PREFIX = "gold"
    
    # ============ DATA SOURCE PATHS ============
    # Weather Bronze path
    WEATHER_BRONZE_PATH = f"{BRONZE_PREFIX}/weather"
    
    # Electricity Bronze paths (5 signals)
    ELECTRICITY_SIGNALS = [
        "carbon_intensity",
        "total_load", 
        "price_day_ahead",
        "electricity_mix",
        "electricity_flows"
    ]
    
    # Silver paths (cleaned data)
    WEATHER_SILVER_PATH = f"{SILVER_PREFIX}/weather"
    ELECTRICITY_SILVER_PATH = f"{SILVER_PREFIX}/electricity"
    
    # Gold path (merged & featured data)
    GOLD_PATH = f"{GOLD_PREFIX}/features"
    
    # ============ DATE RANGE CONFIG ============
    @staticmethod
    def get_date_range():
        """
        Trả về (start_date, end_date) dựa trên MODE
        
        Returns:
            tuple: (start_date_str, end_date_str) format "YYYY-MM-DD"
        """
        if Config.MODE == "BACKFILL":
            # BACKFILL: Từ 2021-01-01 đến hôm qua
            start_date = "2021-01-01"
            end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        else:  # DAILY
            # DAILY: Chỉ xử lý hôm qua
            yesterday = datetime.now() - timedelta(days=1)
            start_date = yesterday.strftime("%Y-%m-%d")
            end_date = start_date
        
        return start_date, end_date
    
    # ============ DATA PROCESSING CONFIG ============
    
    # Timezone conversion (API returns UTC, Vietnam is UTC+7)
    SOURCE_TIMEZONE = "UTC"
    TARGET_TIMEZONE = "Asia/Ho_Chi_Minh"
    
    # Data quality thresholds
    MAX_MISSING_RATIO = 0.3  # 30% missing values threshold
    
    # Outlier detection (Z-score method)
    OUTLIER_ZSCORE_THRESHOLD = 3.5
    
    # ============ FEATURE ENGINEERING CONFIG ============
    
    # Lag features (n giờ trước)
    LAG_HOURS = [1, 2, 3, 6, 12, 24]
    
    # Rolling window features (trung bình n giờ)
    ROLLING_WINDOWS = [3, 6, 12, 24]
    
    # Vietnamese holidays (để tạo holiday feature)
    VIETNAM_HOLIDAYS = [
        # Fixed holidays
        "01-01",  # Tết Dương lịch
        "04-30",  # Ngày Giải phóng
        "05-01",  # Quốc tế Lao động
        "09-02",  # Quốc khánh
        # Note: Tết Nguyên Đán thay đổi mỗi năm - cần lunar calendar library
    ]
    
    # ============ LOGGING CONFIG ============
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # ============ PERFORMANCE CONFIG ============
    
    # Chunk size cho BACKFILL (xử lý từng đợt để tránh OOM)
    BACKFILL_CHUNK_DAYS = 30  # Xử lý 30 ngày mỗi lần
    
    # Parquet compression
    PARQUET_COMPRESSION = "snappy"  # snappy = nhanh, gzip = nén tốt hơn
    
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
║         PROCESSING SERVICE CONFIGURATION                 ║
╚══════════════════════════════════════════════════════════╝

Mode: {Config.MODE}
S3 Bucket: {Config.S3_BUCKET}

Data Sources:
  • Weather Bronze: {Config.WEATHER_BRONZE_PATH}
  • Electricity Bronze: {Config.BRONZE_PREFIX}/electricity/*
  • Weather Silver: {Config.WEATHER_SILVER_PATH}
  • Electricity Silver: {Config.ELECTRICITY_SILVER_PATH}
  • Gold (Features): {Config.GOLD_PATH}

Processing Config:
  • Source Timezone: {Config.SOURCE_TIMEZONE}
  • Target Timezone: {Config.TARGET_TIMEZONE}
  • Max Missing Ratio: {Config.MAX_MISSING_RATIO}
  • Outlier Z-score: {Config.OUTLIER_ZSCORE_THRESHOLD}

Feature Engineering:
  • Lag Hours: {Config.LAG_HOURS}
  • Rolling Windows: {Config.ROLLING_WINDOWS}

Performance:
  • Backfill Chunk: {Config.BACKFILL_CHUNK_DAYS} days
  • Parquet Compression: {Config.PARQUET_COMPRESSION}
        """