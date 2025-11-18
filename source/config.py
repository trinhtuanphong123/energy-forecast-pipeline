# File: source/config.py

import os
from dotenv import load_dotenv

# Tải các biến từ file .env vào môi trường
load_dotenv()

# AWS Configuration
AWS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")  # Optional trên EC2
AWS_SECRET = os.environ.get("AWS_SECRET_ACCESS_KEY")  # Optional trên EC2
AWS_REGION = os.environ.get("AWS_REGION")  # Default region
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")

# API Keys (Required)
VISUAL_CROSSING_KEY = os.environ.get("VISUAL_CROSSING_API_KEY")
EMAPS_API_TOKEN = os.environ.get("EMAPS_API_KEY")

# Validation - Chỉ check S3_BUCKET (AWS keys optional vì có thể dùng IAM Role)
if not S3_BUCKET:
    raise ValueError("LỖI: S3_BUCKET_NAME chưa được set trong .env")

if not VISUAL_CROSSING_KEY:
    raise ValueError("LỖI: VISUAL_CROSSING_API_KEY chưa được set trong .env")

if not EMAPS_API_TOKEN:
    raise ValueError("LỖI: EMAPS_API_KEY chưa được set trong .env")

# Info log
print(f"✓ Config loaded: S3 Bucket = {S3_BUCKET}, Region = {AWS_REGION}")
if AWS_KEY:
    print(f"✓ Using AWS credentials from .env")
else:
    print(f"✓ Using IAM Role credentials (EC2)")