"""
config.py
⚙️ Configuration Management cho Service Processing (Refactored v2)
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Literal
from calendar import monthrange

VN_TZ = timezone(timedelta(hours=7))

class Config:
    """Centralized configuration for Processing Service"""
    
    # ============ MODE CONFIGURATION ============
    @staticmethod
    def get_mode() -> Literal["BACKFILL", "HOURLY", "COMPACTION_DAILY", "COMPACTION_MONTHLY"]:
        mode = os.getenv("MODE", "HOURLY")
        valid_modes = ["BACKFILL", "HOURLY", "COMPACTION_DAILY", "COMPACTION_MONTHLY"]
        if mode not in valid_modes:
            raise ValueError(f"Invalid MODE: {mode}. Must be one of {valid_modes}")
        return mode
    
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
    
    # Chỉ xử lý total_load signal
    ELECTRICITY_SIGNALS = ["total_load"]
    
    # Gold path (Canonical Table)
    GOLD_CANONICAL_PATH = f"{GOLD_PREFIX}/canonical"
    
    # ============ DATE/TIME RANGE CONFIG ============
    @staticmethod
    def get_processing_target():
        """
        Trả về target cần xử lý dựa trên MODE
        
        Returns:
            - BACKFILL: (start_date, end_date)
            - HOURLY: (date, hour)
            - COMPACTION_DAILY: (date,)
            - COMPACTION_MONTHLY: (year, month)
        """
        now_vn = datetime.now(VN_TZ)
        mode = Config.get_mode()
        
        if mode == "BACKFILL":
            # Xử lý toàn bộ lịch sử
            start_date = "2021-10-27"
            end_date = (now_vn - timedelta(days=1)).strftime("%Y-%m-%d")
            return start_date, end_date
            
        elif mode == "HOURLY":
            # Xử lý giờ vừa thu thập (giờ trước)
            current_hour = now_vn.replace(minute=0, second=0, microsecond=0)
            target_hour = current_hour - timedelta(hours=1)
            return target_hour.strftime("%Y-%m-%d"), target_hour.strftime("%H")
            
        elif mode == "COMPACTION_DAILY":
            # Gộp dữ liệu ngày hôm qua
            yesterday = now_vn - timedelta(days=1)
            return (yesterday.strftime("%Y-%m-%d"),)
            
        elif mode == "COMPACTION_MONTHLY":
            # Gộp dữ liệu tháng trước (nếu đủ ngày)
            first_of_month = now_vn.replace(day=1)
            last_month = first_of_month - timedelta(days=1)
            return last_month.year, last_month.month
    
    @staticmethod
    def is_month_complete(year: int, month: int) -> bool:
        """
        Kiểm tra tháng đã đủ ngày chưa
        
        Args:
            year: Năm
            month: Tháng
        
        Returns:
            bool: True nếu đã đủ ngày trong tháng
        """
        now_vn = datetime.now(VN_TZ)
        
        # Tháng hiện tại chưa bao giờ complete
        if year == now_vn.year and month == now_vn.month:
            return False
        
        # Tháng trong tương lai không hợp lệ
        target_date = datetime(year, month, 1)
        if target_date > now_vn:
            return False
        
        # Tháng trong quá khứ: Check xem có đủ số ngày không
        _, days_in_month = monthrange(year, month)
        
        # Nếu tháng đã qua thì mặc định là complete
        last_day_of_month = datetime(year, month, days_in_month)
        return last_day_of_month < now_vn
    
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
        
        mode = Config.get_mode()
        # Mode đã được validate trong get_mode()
        
        if errors:
            raise ValueError("\n".join(errors))
        
        return True
    
    @staticmethod
    def get_summary():
        """In ra summary của config"""
        mode = Config.get_mode()
        target = Config.get_processing_target()
        
        if mode == "BACKFILL":
            target_str = f"Date range: {target[0]} to {target[1]}"
        elif mode == "HOURLY":
            target_str = f"Date: {target[0]}, Hour: {target[1]}:00"
        elif mode == "COMPACTION_DAILY":
            target_str = f"Date: {target[0]}"
        elif mode == "COMPACTION_MONTHLY":
            target_str = f"Year: {target[0]}, Month: {target[1]}"
        else:
            target_str = str(target)
        
        return f"""
╔══════════════════════════════════════════════════════════╗
║         PROCESSING SERVICE (REFACTORED V2)               ║
╚══════════════════════════════════════════════════════════╝

Mode: {mode}
Target: {target_str}
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