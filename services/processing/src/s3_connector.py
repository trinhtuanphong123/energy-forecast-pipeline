"""
s3_connector.py
🔌 S3 Connector - Đọc JSON (Bronze) và Ghi Parquet (Silver/Gold)
"""
import json
import logging
import boto3
import pandas as pd
from io import BytesIO
from datetime import datetime
from typing import List, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class S3Connector:
    """
    Class để đọc và ghi dữ liệu từ/lên S3
    Hỗ trợ:
    - Đọc JSON (Bronze layer)
    - Ghi Parquet (Silver/Gold layer)
    - List files với partition
    """
    
    def __init__(self, bucket_name: str):
        """
        Args:
            bucket_name: Tên S3 bucket
        """
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
        self.s3_resource = boto3.resource('s3')
        self.bucket = self.s3_resource.Bucket(bucket_name)
        
        logger.info(f"📦 Initialized S3Connector for bucket: {bucket_name}")
    
    def read_json(self, s3_key: str) -> dict:
        """
        Đọc JSON file từ S3
        
        Args:
            s3_key: S3 key path
        
        Returns:
            dict: JSON data
        """
        try:
            logger.debug(f"📖 Reading JSON: s3://{self.bucket_name}/{s3_key}")
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            data = json.loads(response['Body'].read().decode('utf-8'))
            return data
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.error(f"❌ File not found: {s3_key}")
                raise FileNotFoundError(f"S3 key not found: {s3_key}")
            else:
                logger.error(f"❌ S3 Error [{error_code}]: {e}")
                raise
    
    def write_parquet(
        self,
        df: pd.DataFrame,
        s3_key: str,
        compression: str = "snappy"
    ) -> str:
        """
        Ghi DataFrame lên S3 dưới dạng Parquet
        
        Args:
            df: Pandas DataFrame
            s3_key: S3 key path
            compression: Compression method (snappy, gzip)
        
        Returns:
            str: S3 URI
        """
        try:
            logger.debug(f"💾 Writing Parquet: s3://{self.bucket_name}/{s3_key}")
            
            # Convert DataFrame to Parquet in memory
            parquet_buffer = BytesIO()
            df.to_parquet(
                parquet_buffer,
                engine='pyarrow',
                compression=compression,
                index=False
            )
            
            # Upload to S3
            parquet_buffer.seek(0)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=parquet_buffer.getvalue(),
                ContentType='application/octet-stream',
                Metadata={
                    'format': 'parquet',
                    'compression': compression,
                    'rows': str(len(df)),
                    'columns': str(len(df.columns)),
                    'written_at': datetime.utcnow().isoformat()
                }
            )
            
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"✅ Written {len(df)} rows to {s3_uri}")
            
            return s3_uri
            
        except Exception as e:
            logger.error(f"❌ Failed to write Parquet: {e}")
            raise
    
    def read_parquet(self, s3_key: str) -> pd.DataFrame:
        """
        Đọc Parquet file từ S3
        
        Args:
            s3_key: S3 key path
        
        Returns:
            pd.DataFrame: Data
        """
        try:
            logger.debug(f"📖 Reading Parquet: s3://{self.bucket_name}/{s3_key}")
            
            # Read directly from S3
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            df = pd.read_parquet(s3_uri)
            
            logger.info(f"✅ Read {len(df)} rows from {s3_uri}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Failed to read Parquet: {e}")
            raise
    
    def list_partitions(
        self,
        prefix: str,
        start_date: str,
        end_date: str
    ) -> List[str]:
        """
        List tất cả partitions trong khoảng thời gian
        
        Args:
            prefix: S3 prefix (ví dụ: "bronze/weather")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            List[str]: List các S3 keys
        """
        logger.info(f"🔍 Listing partitions: {prefix} from {start_date} to {end_date}")
        
        # Generate date range
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        keys = []
        for date in date_range:
            year = date.year
            month = str(date.month).zfill(2)
            day = str(date.day).zfill(2)
            
            # Construct partition path
            partition_prefix = f"{prefix}/year={year}/month={month}/day={day}/"
            
            # List objects in this partition
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=partition_prefix
                )
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        keys.append(obj['Key'])
            except ClientError as e:
                logger.warning(f"⚠️ No data for {date.strftime('%Y-%m-%d')}: {e}")
                continue
        
        logger.info(f"✅ Found {len(keys)} files")
        return keys
    
    def check_file_exists(self, s3_key: str) -> bool:
        """
        Kiểm tra file có tồn tại không
        
        Args:
            s3_key: S3 key path
        
        Returns:
            bool: True if exists
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def get_partition_path(
        self,
        prefix: str,
        date: str,
        filename: str = "data.parquet"
    ) -> str:
        """
        Generate partition path theo Hive style
        
        Args:
            prefix: S3 prefix (ví dụ: "silver/weather")
            date: Date string (YYYY-MM-DD)
            filename: Tên file
        
        Returns:
            str: Full S3 key
        """
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        year = date_obj.year
        month = str(date_obj.month).zfill(2)
        day = str(date_obj.day).zfill(2)
        
        return f"{prefix}/year={year}/month={month}/day={day}/{filename}"
    
    def delete_partition(self, prefix: str, date: str):
        """
        Xóa toàn bộ partition của 1 ngày (để reprocess)
        
        Args:
            prefix: S3 prefix
            date: Date string (YYYY-MM-DD)
        """
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        year = date_obj.year
        month = str(date_obj.month).zfill(2)
        day = str(date_obj.day).zfill(2)
        
        partition_prefix = f"{prefix}/year={year}/month={month}/day={day}/"
        
        logger.info(f"🗑️ Deleting partition: {partition_prefix}")
        
        # List and delete all objects in partition
        objects_to_delete = []
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=partition_prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})
        
        if objects_to_delete:
            self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': objects_to_delete}
            )
            logger.info(f"✅ Deleted {len(objects_to_delete)} objects")
        else:
            logger.info(f"ℹ️ No objects to delete")