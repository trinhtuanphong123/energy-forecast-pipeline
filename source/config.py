# File: src/config.py

import os
from dotenv import load_dotenv

# Tải các biến từ file .env vào môi trường (environment)
load_dotenv()

# Đọc các biến môi trường
AWS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION")
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")

VISUAL_CROSSING_KEY = os.environ.get("VISUAL_CROSSING_API_KEY")
EMAPS_API_TOKEN = os.environ.get("EMAPS_API_KEY")

# Kiểm tra xem các biến quan trọng đã được set chưa
if not all([AWS_KEY, AWS_SECRET, AWS_REGION, S3_BUCKET]):
    raise ValueError("LỖI: Một hoặc nhiều biến môi trường AWS chưa được set. Kiểm tra file .env")