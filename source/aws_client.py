# File: src/aws_client.py

import boto3
from botocore.exceptions import ClientError # Cần thiết cho hàm check_if_file_exists
from source.config import AWS_KEY, AWS_SECRET, AWS_REGION, S3_BUCKET

# Khởi tạo session với AWS bằng IAM User credentials
session = boto3.Session(
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET,
    region_name=AWS_REGION
)

# Tạo một client S3 từ session
s3_client = session.client("s3")

def upload_file_to_s3(file_path, s3_key):
    """
    Tải một file từ máy local lên S3.
    """
    try:
        s3_client.upload_file(file_path, S3_BUCKET, s3_key)
        # Giảm bớt log, script gọi hàm này sẽ tự in ra
        # print(f"Tải thành công: {file_path} -> s3://{S3_BUCKET}/{s3_key}")
    except Exception as e:
        print(f"LỖI khi tải file {file_path} lên {s3_key}: {e}")

def list_s3_objects(prefix):
    """
    Liệt kê các object trong S3 bucket.
    """
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        return response.get('Contents', [])
    except Exception as e:
        print(f"LỖI khi liệt kê S3: {e}")
        return []

def check_if_file_exists(s3_key):
    """
    Kiểm tra xem file đã tồn tại trên S3 chưa bằng cách gọi head_object.
    Rất nhanh và không tốn chi phí download.
    Trả về True nếu tồn tại, False nếu không.
    """
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        return True
    except ClientError as e:
        # Nếu lỗi là "404 Not Found", file không tồn tại
        if e.response['Error']['Code'] == '404':
            return False
        # Lỗi khác (ví dụ: 403 Forbidden)
        else:
            print(f"LỖI (head_object) khi kiểm tra {s3_key}: {e}")
            return False # Giả định là không tồn tại nếu có lỗi
    except Exception as e:
        print(f"LỖI (check_if_file_exists) khi kiểm tra {s3_key}: {e}")
        return False

