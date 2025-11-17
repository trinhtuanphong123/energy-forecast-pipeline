# File: scripts/1_backfill_weather_api.py


import requests
import json
import time
import tempfile
import os
from datetime import datetime, timedelta
import pandas as pd

# Import config và S3 client đã định nghĩa
from source.config import VISUAL_CROSSING_KEY, S3_BUCKET, AWS_REGION
from source.aws_client import upload_file_to_s3, s3_client

# 1. --- Cấu hình Backfill ---
LOCATION = "Vietnam"
START_DATE = "2021-01-01" # Lấy 5 năm dữ liệu
API_HOST = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

# Các trường dữ liệu cần thiết (KHÔNG "chọn hết")
# temp = nhiệt độ, humidity = độ ẩm, precip = lượng mưa, 
# windspeed = tốc độ gió, cloudcover = độ che phủ mây
ELEMENTS = "datetime,temp,humidity,precip,windspeed,cloudcover"


def get_daily_weather_data(api_key, query_date):
    """
    Gọi API Visual Crossing để lấy dữ liệu hourly cho 1 ngày cụ thể.
    """
    params = {
        "unitGroup": "metric",        # Dùng độ C, km/h
        "include": "hours",           # Rất quan trọng: Lấy dữ liệu theo giờ
        "location": LOCATION,
        "key": api_key,
        "contentType": "json",
        "elements": ELEMENTS,
        "datetime": query_date       # Query cho 1 ngày cụ thể
    }
    
    try:
        response = requests.get(API_HOST, params=params)
        # Tự động báo lỗi nếu API trả về 4xx hoặc 5xx
        response.raise_for_status() 
        return response.json()
        
    except requests.exceptions.HTTPError as http_err:
        print(f"Lỗi HTTP: {http_err} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"Lỗi Request: {req_err}")
    
    return None

def check_if_file_exists(s3_key):
    """
    Kiểm tra xem file đã tồn tại trên S3 Bronze chưa để tránh chạy lại.
    """
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        return True
    except Exception as e:
        return False

# --- Hàm Main để chạy script ---
if __name__ == "__main__":
    print("--- Bắt đầu Giai đoạn 1: Backfill Dữ liệu Thời tiết ---")
    
    if not VISUAL_CROSSING_KEY:
        raise ValueError("LỖI: VISUAL_CROSSING_API_KEY chưa được set trong .env")

    # Tạo dải ngày (date range) từ START_DATE đến hôm qua
    start = datetime.strptime(START_DATE, "%Y-%m-%d")
    end = datetime.now() - timedelta(days=1) # Dữ liệu đến hôm qua
    
    date_range = pd.date_range(start, end, freq='D')
    
    total_days = len(date_range)
    print(f"Sẽ xử lý {total_days} ngày (từ {START_DATE} đến {end.strftime('%Y-%m-%d')}).")
    
    for i, date_obj in enumerate(date_range):
        date_str = date_obj.strftime("%Y-%m-%d")
        year = date_obj.strftime("%Y")
        month = date_obj.strftime("%m")
        day = date_obj.strftime("%d")
        
        # 1. Định nghĩa đường dẫn file S3 (S3 Key)
        s3_key = f"bronze/visual_crossing/year={year}/month={month}/day={day}/data.json"
        
        # 2. Kiểm tra nếu file đã tồn tại -> Bỏ qua
        if check_if_file_exists(s3_key):
            print(f"({i+1}/{total_days}) Bỏ qua: {s3_key} (Đã tồn tại)")
            continue

        print(f"({i+1}/{total_days}) Đang lấy dữ liệu: {date_str}...")
        
        # 3. Gọi API
        data = get_daily_weather_data(VISUAL_CROSSING_KEY, date_str)
        
        if data:
            # 4. Lưu file JSON vào file tạm (temp file)
            # tempfile.NamedTemporaryFile sẽ tự động xóa file sau khi dùng
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                json.dump(data, f)
                temp_file_path = f.name
            
            # 5. Tải file tạm lên S3 bằng client đã định nghĩa
            try:
                upload_file_to_s3(temp_file_path, s3_key)
            finally:
                # Xóa file tạm đi
                os.remove(temp_file_path)
                
            # 6. Tạm dừng 1 giây để tránh API bị quá tải (Rate Limit)
            time.sleep(1) 
            
    print("--- Hoàn thành Backfill Dữ liệu Thời tiết ---")