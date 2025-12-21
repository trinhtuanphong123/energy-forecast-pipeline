"""
s3_writer.py
💾 Ghi dữ liệu lên S3 với Partitioning theo năm/tháng/ngày
"""
import json
import logging
import boto3
from datetime import datetime
from typing import Dict, Any
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class S3Writer:
    """
    Class để ghi dữ liệu JSON lên S3 với Hive-style partitioning
    """
    
    def __init__(self, bucket_name: str, bronze_prefix: str = "bronze"):
        """
        Args:
            bucket_name: Tên S3 bucket
            bronze_prefix: Prefix cho Bronze layer (default: "bronze")
        """
        self.bucket_name = bucket_name
        self.bronze_prefix = bronze_prefix
        self.s3_client = boto3.client('s3')
        
        logger.info(f"📦 Initialized S3Writer for bucket: {bucket_name}")
    
    def _generate_partition_path(
        self, 
        data_source: str,
        query_date: str,
        signal_name: str = None
    ) -> str:
        """
        Tạo partition path theo format: year=YYYY/month=MM/day=DD
        
        Args:
            data_source: Nguồn dữ liệu ("weather" hoặc "electricity")
            query_date: Ngày (format: YYYY-MM-DD)
            signal_name: Tên signal (chỉ dành cho electricity)
        
        Returns:
            str: Full S3 key path
        
        Example:
            bronze/weather/year=2024/month=12/day=20/data.json
            bronze/electricity/carbon_intensity/year=2024/month=12/day=20/data.json
        """
        # Parse date
        date_obj = datetime.strptime(query_date, "%Y-%m-%d")
        year = date_obj.year
        month = str(date_obj.month).zfill(2)
        day = str(date_obj.day).zfill(2)
        
        # Build path
        if data_source == "weather":
            path = f"{self.bronze_prefix}/weather/year={year}/month={month}/day={day}/data.json"
        elif data_source == "electricity":
            if not signal_name:
                raise ValueError("signal_name is required for electricity data")
            path = f"{self.bronze_prefix}/electricity/{signal_name}/year={year}/month={month}/day={day}/data.json"
        else:
            raise ValueError(f"Unknown data_source: {data_source}")
        
        return path
    
    def write_json(
        self, 
        data: Dict[str, Any],
        data_source: str,
        query_date: str,
        signal_name: str = None
    ) -> str:
        """
        Ghi dữ liệu JSON lên S3
        
        Args:
            data: Dictionary chứa dữ liệu
            data_source: Nguồn dữ liệu ("weather" hoặc "electricity")
            query_date: Ngày (format: YYYY-MM-DD)
            signal_name: Tên signal (chỉ dành cho electricity)
        
        Returns:
            str: S3 URI của file đã ghi (s3://bucket/key)
        
        Raises:
            ClientError: Nếu ghi S3 thất bại
        """
        # Generate partition path
        s3_key = self._generate_partition_path(data_source, query_date, signal_name)
        
        # Convert dict to JSON string
        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        
        try:
            logger.info(f"💾 Writing to s3://{self.bucket_name}/{s3_key}")
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_data.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'source': data_source,
                    'query_date': query_date,
                    'ingestion_timestamp': datetime.utcnow().isoformat()
                }
            )
            
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"✅ Successfully written to {s3_uri}")
            
            return s3_uri
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"❌ S3 Write Error [{error_code}]: {error_msg}")
            raise
    
    def write_weather_data(self, data: Dict[str, Any], query_date: str) -> str:
        """
        Shorthand method để ghi weather data
        
        Args:
            data: Weather data dictionary
            query_date: Ngày (format: YYYY-MM-DD)
        
        Returns:
            str: S3 URI
        """
        return self.write_json(
            data=data,
            data_source="weather",
            query_date=query_date
        )
    
    def write_electricity_data(
        self, 
        data: Dict[str, Any], 
        signal_name: str,
        query_date: str
    ) -> str:
        """
        Shorthand method để ghi electricity data
        
        Args:
            data: Electricity data dictionary
            signal_name: Tên signal
            query_date: Ngày (format: YYYY-MM-DD)
        
        Returns:
            str: S3 URI
        """
        return self.write_json(
            data=data,
            data_source="electricity",
            query_date=query_date,
            signal_name=signal_name
        )
    
    def check_file_exists(self, s3_key: str) -> bool:
        """
        Kiểm tra file đã tồn tại trên S3 chưa
        
        Args:
            s3_key: S3 key path
        
        Returns:
            bool: True nếu file tồn tại
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise