# File: scripts/3_run_initial_transform.py
# (Cần chạy: pip install polars pyarrow boto3 python-dotenv deltalake pytz)

import polars as pl
import json
import tempfile
import os
import pytz
from datetime import datetime, timedelta
import pandas as pd # Chỉ dùng cho daterange

from source.config import S3_BUCKET
from source.aws_client import s3_client

# --- 1. Cấu hình LAZERS (Các hàm đọc/ghi S3) ---

def read_json_from_s3(s3_key):
    """
    Đọc 1 file JSON duy nhất từ S3 và parse nó.
    """
    try:
        with tempfile.NamedTemporaryFile() as f:
            s3_client.download_file(S3_BUCKET, s3_key, f.name)
            with open(f.name, 'r') as file_data:
                return json.load(file_data)
    except Exception as e:
        print(f"Cảnh báo: Không thể đọc {s3_key}. Lỗi: {e}")
        return None

def write_delta_table(df: pl.DataFrame, s3_path, mode='append'):
    """
    Ghi một Polars DataFrame vào bảng Delta Lake trên S3.
    """
    if df.is_empty():
        return # Không ghi gì nếu df rỗng
        
    # Polars ghi delta lake cần một đường dẫn bắt đầu bằng "s3://"
    full_s3_path = f"s3://{S3_BUCKET}/{s3_path}"
    
    # storage_options được dùng để xác thực với S3
    storage_options = {
        "AWS_REGION": s3_client.meta.region_name,
        "AWS_ACCESS_KEY_ID": s3_client.meta.credentials.access_key,
        "AWS_SECRET_ACCESS_KEY": s3_client.meta.credentials.secret_key
    }
    
    df.write_delta(
        full_s3_path,
        mode=mode,
        storage_options=storage_options,
        overwrite_schema=True # Cho phép schema thay đổi (hữu ích khi mới bắt đầu)
    )

# --- 2. Cấu hình BRONZE -> SILVER (Các hàm Parse & Clean) ---

# Định nghĩa múi giờ
ICT = pytz.timezone("Asia/Ho_Chi_Minh")
UTC = pytz.utc

def clean_common_df(df: pl.DataFrame) -> pl.DataFrame:
    """
    Hàm chuẩn hóa thời gian. Đây là logic quan trọng nhất.
    """
    if df.is_empty():
        return df

    # 1. Chuyển đổi cột 'datetime' (string) sang kiểu datetime (timezone-aware UTC)
    df = df.with_columns(
        pl.col("datetime").str.to_datetime(format="%Y-%m-%dT%H:%M:%SZ", time_zone="UTC").alias("datetime_utc")
    )
    
    # 2. Chuyển đổi sang múi giờ ICT (UTC+7)
    df = df.with_columns(
        pl.col("datetime_utc").dt.convert_time_zone("Asia/Ho_Chi_Minh").alias("datetime_ict")
    )
    
    # 3. Tạo 1 key chuẩn (rounding xuống giờ gần nhất) để JOIN
    df = df.with_columns(
        pl.col("datetime_ict").dt.truncate("1h").alias("hour_ict")
    )
    return df

def parse_weather(data):
    """Parse JSON từ Visual Crossing"""
    hourly_data = data.get("days", [{}])[0].get("hours", [])
    if not hourly_data:
        return pl.DataFrame()
    
    df = pl.DataFrame(hourly_data)
    # datetime là "HH:MM:SS", cần kết hợp với ngày
    date_str = data.get("days", [{}])[0].get("datetime")
    df = df.with_columns(
        # Tạo cột datetime chuẩn UTC (VC API dùng giờ địa phương, nhưng ta giả định nó là UTC)
        (pl.lit(date_str) + "T" + pl.col("datetime") + "Z").alias("datetime")
    )
    return df.select(["datetime", "temp", "humidity", "precip", "windspeed", "cloudcover"])

def parse_emaps_generic(data, value_name):
    """Parse JSON chuẩn của E-Maps (Total Load, Carbon, Price)"""
    hourly_data = data.get("data", [])
    if not hourly_data:
        return pl.DataFrame()
        
    df = pl.DataFrame(hourly_data)
    # Đổi tên cột 'value' thành tên có ý nghĩa
    return df.rename({"value": value_name})

def parse_emaps_mix(data):
    """Parse JSON 'electricity_mix' (cấu trúc lồng nhau)"""
    hourly_data = data.get("data", [])
    if not hourly_data:
        return pl.DataFrame()

    # Làm phẳng (flatten) cấu trúc JSON lồng nhau
    normalized_data = []
    for row in hourly_data:
        flat_row = {"datetime": row["datetime"]}
        # Lấy tất cả các nguồn
        for source, mw in row.get("powerConsumptionBreakdown", {}).items():
            flat_row[f"mix_{source}_mw"] = mw
        normalized_data.append(flat_row)
    
    return pl.DataFrame(normalized_data)

def parse_emaps_flows(data):
    """Parse JSON 'electricity_flows' (cấu trúc lồng nhau)"""
    hourly_data = data.get("data", [])
    if not hourly_data:
        return pl.DataFrame()

    normalized_data = []
    for row in hourly_data:
        flat_row = {"datetime": row["datetime"]}
        # Lấy tất cả các luồng trao đổi
        for zone, mw in row.get("exchange", {}).items():
            flat_row[f"flow_{zone}_mw"] = mw
        normalized_data.append(flat_row)
        
    return pl.DataFrame(normalized_data)

# --- 3. LOGIC CHÍNH (Giai đoạn B-S và S-G) ---

def run_bronze_to_silver(start_date_str, end_date_str):
    """
    Lặp qua từng ngày, đọc 6 file JSON từ Bronze,
    biến đổi, và APPEND vào 6 bảng Silver Delta.
    """
    print("--- Bắt đầu Giai đoạn: Bronze -> Silver ---")
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")
    date_range = pd.date_range(start, end, freq='D')
    
    total_days = len(date_range)

    # Ánh xạ (mapping) tên tín hiệu -> hàm parse -> đường dẫn Silver
    SOURCES = {
        "weather": ("visual_crossing", parse_weather),
        "total_load": ("electricity_maps/total_load", lambda d: parse_emaps_generic(d, "total_load_mw")),
        "carbon_intensity": ("electricity_maps/carbon_intensity", lambda d: parse_emaps_generic(d, "carbon_intensity_gco2eq_kwh")),
        "price_day_ahead": ("electricity_maps/price_day_ahead", lambda d: parse_emaps_generic(d, "price_eur_per_mwh")),
        "electricity_mix": ("electricity_maps/electricity_mix", parse_emaps_mix),
        "electricity_flows": ("electricity_maps/electricity_flows", parse_emaps_flows),
    }

    for i, date_obj in enumerate(date_range):
        print(f"--- Đang xử lý ngày: {date_obj.strftime('%Y-%m-%d')} ({i+1}/{total_days}) ---")
        year, month, day = date_obj.strftime("%Y"), date_obj.strftime("%m"), date_obj.strftime("%d")
        
        for signal_name, (bronze_path_prefix, parse_func) in SOURCES.items():
            # 1. Đọc file Bronze JSON
            s3_key = f"bronze/{bronze_path_prefix}/year={year}/month={month}/day={day}/data.json"
            bronze_data = read_json_from_s3(s3_key)
            
            if not bronze_data:
                print(f"Bỏ qua (không có data): {signal_name}")
                continue
            
            # 2. Parse JSON thô -> DataFrame
            df = parse_func(bronze_data)
            
            # 3. Chuẩn hóa thời gian (Rất quan trọng)
            df_clean = clean_common_df(df)
            
            if df_clean.is_empty():
                print(f"Bỏ qua (data rỗng): {signal_name}")
                continue

            # 4. Ghi (Append) vào bảng Silver Delta
            silver_path = f"silver/{signal_name}"
            write_delta_table(df_clean, silver_path, mode='append')
    
    print("--- Hoàn thành Giai đoạn: Bronze -> Silver ---")


def run_silver_to_gold():
    """
    Đọc 6 bảng Silver Delta, JOIN, và ghi 1 bảng Gold ĐÃ PHÂN VÙNG.
    """
    print("--- Bắt đầu Giai đoạn: Silver -> Gold ---")
    
    storage_options = {
        "AWS_REGION": s3_client.meta.region_name,
        "AWS_ACCESS_KEY_ID": s3_client.meta.credentials.access_key,
        "AWS_SECRET_ACCESS_KEY": s3_client.meta.credentials.secret_key
    }

    def s3_path(table_name):
        return f"s3://{S3_BUCKET}/silver/{table_name}"

    try:
        print("Quét (scanning) 6 bảng Silver Delta...")
        df_weather = pl.scan_delta(s3_path("weather"), storage_options=storage_options)
        df_load = pl.scan_delta(s3_path("total_load"), storage_options=storage_options)
        df_carbon = pl.scan_delta(s3_path("carbon_intensity"), storage_options=storage_options)
        df_price = pl.scan_delta(s3_path("price_day_ahead"), storage_options=storage_options)
        df_mix = pl.scan_delta(s3_path("electricity_mix"), storage_options=storage_options)
        df_flows = pl.scan_delta(s3_path("electricity_flows"), storage_options=storage_options)
        
    except Exception as e:
        print(f"LỖI: Không thể đọc bảng Silver. Bạn đã chạy Bronze->Silver chưa? Lỗi: {e}")
        return

    print("Thực hiện JOIN 6 bảng...")
    gold_df = df_weather.join(df_load, on="hour_ict", how="left") \
                        .join(df_carbon, on="hour_ict", how="left") \
                        .join(df_price, on="hour_ict", how="left") \
                        .join(df_mix, on="hour_ict", how="left") \
                        .join(df_flows, on="hour_ict", how="left")
    
    print("Tạo đặc trưng (features) thời gian...")
    gold_df = gold_df.with_columns([
        pl.col("hour_ict").dt.hour().alias("hour_of_day"),
        pl.col("hour_ict").dt.day_of_week().alias("day_of_week"),
        pl.col("hour_ict").dt.day_of_year().alias("day_of_year"),
        pl.col("hour_ict").dt.month().alias("month"),
        pl.col("hour_ict").dt.year().alias("year") # <-- QUAN TRỌNG: Thêm cột 'year' và 'month'
    ])
    
    print("Thu thập (collecting) dữ liệu và ghi vào S3 Gold (việc này có thể mất vài phút)...")
    
    # Đây là lúc Polars thực sự chạy (tốn RAM)
    final_df = gold_df.collect()
    
    # ĐỊA CHỈ SỬA ĐỔI QUAN TRỌNG:
    gold_s3_path = f"s3://{S3_BUCKET}/gold/hourly_features_joined/"
    
    print(f"Bắt đầu ghi {len(final_df)} dòng vào: {gold_s3_path}")
    
    final_df.write_delta(
        gold_s3_path,
        mode="overwrite", # Ghi đè toàn bộ bảng Gold
        partition_by=["year", "month"], # <-- ĐÂY LÀ GIẢI PHÁP
        storage_options=storage_options,
        overwrite_schema=True
    )
    
    print(f"--- Hoàn thành Giai đoạn: Silver -> Gold ---")
    print(f"Bảng Gold ĐÃ PHÂN VÙNG được lưu tại: {gold_s3_path}")
    print(f"Tổng số dòng: {len(final_df)}")


  

# --- 4. HÀM CHẠY CHÍNH ---
if __name__ == "__main__":
    # 1. Chạy Bronze -> Silver
    # (Xóa các bảng Silver cũ nếu muốn chạy lại từ đầu - CẨN THẬN!)
    run_bronze_to_silver(
        start_date_str="2021-01-01", # Khớp với Script 2
        end_date_str=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    )
    
    # 2. Chạy Silver -> Gold
    run_silver_to_gold()