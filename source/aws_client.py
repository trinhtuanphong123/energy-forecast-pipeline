# File: source/aws_client.py

import boto3
from botocore.exceptions import ClientError
from source.config import AWS_KEY, AWS_SECRET, AWS_REGION, S3_BUCKET

# Khởi tạo S3 client
# Nếu có AWS_KEY và AWS_SECRET trong .env → dùng chúng
# Nếu không → boto3 tự động dùng IAM Role (trên EC2)
if AWS_KEY and AWS_SECRET:
    print("Initializing S3 client with explicit credentials...")
    session = boto3.Session(
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
        region_name=AWS_REGION
    )
    s3_client = session.client("s3")
else:
    print("Initializing S3 client with IAM Role...")
    s3_client = boto3.client("s3", region_name=AWS_REGION)

def upload_file_to_s3(file_path, s3_key):
    """
    Tải một file từ máy local lên S3.
    """
    try:
        s3_client.upload_file(file_path, S3_BUCKET, s3_key)
        print(f"✓ Uploaded: {s3_key}")
    except Exception as e:
        print(f"✗ LỖI khi tải file {file_path} lên {s3_key}: {e}")
        raise

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
    Kiểm tra xem file đã tồn tại trên S3 chưa.
    Trả về True nếu tồn tại, False nếu không.
    """
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            print(f"LỖI khi kiểm tra {s3_key}: {e}")
            return False
    except Exception as e:
        print(f"LỖI không xác định khi kiểm tra {s3_key}: {e}")
        return False