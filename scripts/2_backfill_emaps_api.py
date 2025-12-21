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
from source.aws_client import upload_file_to_s3, check_if_file_exists

# 1. --- Cấu hình Backfill ---
START_DATE = "2021-01-01" # Lấy từ 2021
API_HOST = "https://api.electricitymaps.com/v3"
ZONE = "VN"
GRANULARITY = "hourly"

# --- CẤU HÌNH ENDPOINT (QUAN TRỌNG: SỬA TẠI ĐÂY) ---
# Ánh xạ từ tên tham số (--signal) sang phần path của URL API
# Dựa trên mẫu bạn cung cấp và tài liệu chuẩn
ENDPOINT_MAPPING = {
    "total_load": "total-load",
    "carbon_intensity": "carbon-intensity",
    "price_day_ahead": "price-day-ahead",
    "electricity_mix": "electricity-mix", 
    "electricity_flows": "electricity-flows"
}

def get_daily_emaps_data(api_key, signal_name, query_date):
    """
    Gọi API E-Maps để lấy dữ liệu hourly cho 1 ngày cụ thể của 1 tín hiệu.
    """
    # Lấy endpoint từ mapping, nếu không có thì fallback về cách cũ (replace)
    api_path = ENDPOINT_MAPPING.get(signal_name, signal_name.replace('_', '-'))
    
    endpoint = f"{API_HOST}/{api_path}/past-range"
    
    # Debug: In ra URL để kiểm tra nếu lỗi
    # print(f"DEBUG: Calling {endpoint}")

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
        # Nếu lỗi 404 (Not Found) -> Có thể ngày đó không có dữ liệu hoặc sai Endpoint
        if response.status_code == 404:
            print(f"⚠️ Cảnh báo: 404 Not Found cho {signal_name} ({endpoint}) vào ngày {query_date}")
            # Không return None ngay, hãy kiểm tra kỹ hơn nếu cần
            return None
        
        # Nếu lỗi 400 (Bad Request) -> Thường do sai tham số granularity hoặc range quá lớn
        if response.status_code == 400:
             print(f"❌ Lỗi 400 Bad Request: {response.text}")

        print(f"❌ Lỗi HTTP: {http_err}")
        
    except requests.exceptions.RequestException as req_err:
        print(f"❌ Lỗi Request: {req_err}")
    
    return None

# --- Hàm Main để chạy script ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill dữ liệu E-Maps từ API (theo ngày) lên S3 Bronze.")
    parser.add_argument("--signal", required=True, 
                        choices=list(ENDPOINT_MAPPING.keys()), 
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
            print(f"({i+1}/{total_days}) ⏭️ Bỏ qua: {s3_key} (Đã tồn tại)")
            continue

        print(f"({i+1}/{total_days}) ⬇️ Đang lấy {signal} cho ngày: {date_str}...")
        
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
                
            # 6. Tạm dừng 1.5 giây để TÔN TRỌNG API Rate Limit
            time.sleep(1.5)
        else:
            print(f"   (Không có dữ liệu trả về cho ngày này)")
            
    print(f"--- ✅ Hoàn thành Backfill E-Maps cho: {signal} ---")



# python3 scripts/2_backfill_emaps_api.py --signal total_load