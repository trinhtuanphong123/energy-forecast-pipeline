# File: scripts/2_backfill_emaps_api.py
# (Cần chạy: pip install requests boto3 python-dotenv pandas)

import requests
import json
import time
import tempfile
import os
import argparse
from datetime import datetime, timedelta
import pandas as pd

# Import config và S3 client
from source.config import EMAPS_API_TOKEN, S3_BUCKET
from source.aws_client import upload_file_to_s3, check_if_file_exists # (Bạn phải thêm hàm check_if_file_exists vào aws_client.py)

# 1. --- Cấu hình Backfill ---
START_DATE = "2021-01-01" # Lấy từ 2021
API_HOST = "https://api.electricitymaps.com/v3"
ZONE = "VN"
GRANULARITY = "hourly" # QUAN TRỌNG: Lấy theo giờ để khớp với thời tiết


def get_daily_emaps_data(api_key, signal_name, query_date):
    """
    Gọi API E-Maps để lấy dữ liệu hourly cho 1 ngày cụ thể của 1 tín hiệu.
    """
    # Endpoint thay đổi dựa trên signal_name
    # Ví dụ: total-load, carbon-intensity, v.v.
    endpoint = f"{API_HOST}/{signal_name.replace('_', '-')}/past-range"
    
    # Định nghĩa start và end cho đúng 24h của ngày đó
    start_time = f"{query_date}T00:00:00Z"
    end_time = f"{query_date}T23:59:59Z"

    headers = {
        "auth-token": api_key
    }
    params = {
        "zone": ZONE,
        "start": start_time,
        "end": end_time,
        "temporalGranularity": GRANULARITY
    }
    
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status() # Báo lỗi nếu 4xx, 5xx
        return response.json()
        
    except requests.exceptions.HTTPError as http_err:
        # Nếu lỗi 404 (Not Found), có thể ngày đó không có data -> Bỏ qua
        if response.status_code == 404:
            print(f"Cảnh báo: 404 - Không tìm thấy dữ liệu cho {signal_name} vào ngày {query_date}")
            return None
        print(f"Lỗi HTTP: {http_err} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"Lỗi Request: {req_err}")
    
    return None

# --- Hàm Main để chạy script ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill dữ liệu E-Maps từ API (theo ngày) lên S3 Bronze.")
    parser.add_argument("--signal", required=True, 
                        choices=["total_load", "carbon_intensity", "price_day_ahead", "electricity_flows", "electricity_mix"], 
                        help="Tên tín hiệu (ví dụ: total_load, carbon_intensity)")
    
    args = parser.parse_args()
    signal = args.signal
    
    print(f"--- Bắt đầu Giai đoạn 1: Backfill E-Maps (API) cho: {signal} ---")
    
    if not EMAPS_API_TOKEN:
        raise ValueError("LỖI: EMAPS_API_TOKEN chưa được set trong .env")

    # Tạo dải ngày (date range) từ START_DATE đến hôm qua
    start = datetime.strptime(START_DATE, "%Y-%m-%d")
    end = datetime.now() - timedelta(days=1)
    date_range = pd.date_range(start, end, freq='D')
    
    total_days = len(date_range)
    print(f"Sẽ xử lý {total_days} ngày (từ {START_DATE} đến {end.strftime('%Y-%m-%d')}).")
    
    for i, date_obj in enumerate(date_range):
        date_str = date_obj.strftime("%Y-%m-%d")
        year = date_obj.strftime("%Y")
        month = date_obj.strftime("%m")
        day = date_obj.strftime("%d")
        
        # 1. Định nghĩa S3 key
        s3_key = f"bronze/electricity_maps/{signal}/year={year}/month={month}/day={day}/data.json"
        
        # 2. Kiểm tra nếu file đã tồn tại -> Bỏ qua
        if check_if_file_exists(s3_key):
            print(f"({i+1}/{total_days}) Bỏ qua: {s3_key} (Đã tồn tại)")
            continue

        print(f"({i+1}/{total_days}) Đang lấy {signal} cho ngày: {date_str}...")
        
        # 3. Gọi API
        data = get_daily_emaps_data(EMAPS_API_TOKEN, signal, date_str)
        
        if data:
            # 4. Lưu file JSON vào file tạm
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                json.dump(data, f)
                temp_file_path = f.name
            
            # 5. Tải file tạm lên S3
            try:
                upload_file_to_s3(temp_file_path, s3_key)
            finally:
                os.remove(temp_file_path)
                
            # 6. Tạm dừng 2 giây để TÔN TRỌNG API Rate Limit
            # (Bạn không muốn bị ban)
            time.sleep(2) 
            
    print(f"--- Hoàn thành Backfill E-Maps cho: {signal} ---")