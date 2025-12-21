# File: source/config.py

import os
import json
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load biến môi trường từ .env
load_dotenv()

# ============================================
# AWS Configuration
# ============================================
AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-2")  # ← SỬA REGION NÀY!
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")

# AWS credentials (IAM Role tự động handle)
AWS_KEY = None
AWS_SECRET = None


# ============================================
# Load API Keys từ AWS Secrets Manager
# ============================================
def get_secret():
    """
    Load API keys từ AWS Secrets Manager
    Dựa trên code mẫu từ AWS Console
    """
    secret_name = "vietnam-energy/api-keys"  # ← SỬA TÊN SECRET NÀY NẾU KHÁC!
    region_name = AWS_REGION
    
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        print(f"✓ Loaded API keys from Secrets Manager (Region: {region_name})")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"⚠️ Cannot load from Secrets Manager: {error_code}")
        
        if error_code == 'ResourceNotFoundException':
            print(f"⚠️ Secret '{secret_name}' not found in region {region_name}")
        elif error_code == 'AccessDeniedException':
            print(f"⚠️ EC2 IAM Role doesn't have permission to read Secrets Manager")
        
        print(f"⚠️ Falling back to .env file")
        # Fallback to .env
        return {
            "visual_crossing": os.environ.get("VISUAL_CROSSING_API_KEY"),
            "emaps": os.environ.get("EMAPS_API_KEY")
        }
    
    # Parse secret JSON string
    secret_string = get_secret_value_response['SecretString']
    secret_dict = json.loads(secret_string)
    
    return secret_dict


# ============================================
# Load secrets and assign to variables
# ============================================
secrets = get_secret()


VISUAL_CROSSING_KEY = secrets.get("visual_crossing")  
EMAPS_API_TOKEN = secrets.get("emaps")  


# ============================================
# Validation
# ============================================
if not S3_BUCKET:
    raise ValueError("❌ S3_BUCKET_NAME not set in .env")

if not VISUAL_CROSSING_KEY:
    raise ValueError("❌ Visual Crossing API key not found in Secrets Manager or .env")

if not EMAPS_API_TOKEN:
    raise ValueError("❌ Electricity Maps API key not found in Secrets Manager or .env")


# ============================================
# Info logging
# ============================================
print(f"✓ Config loaded successfully")
print(f"  - S3 Bucket: {S3_BUCKET}")
print(f"  - Region: {AWS_REGION}")
print(f"  - Visual Crossing Key: {VISUAL_CROSSING_KEY[:10]}... ({len(VISUAL_CROSSING_KEY)} chars)")
print(f"  - Electricity Maps Key: {EMAPS_API_TOKEN[:10]}... ({len(EMAPS_API_TOKEN)} chars)")
print(f"✓ Using IAM Role for AWS authentication")