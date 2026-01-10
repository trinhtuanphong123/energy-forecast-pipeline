"""
s3_writer.py
💾 Ghi dữ liệu lên S3 với Partitioning theo năm/tháng/ngày/giờ
"""
import json
import logging
import boto3
from datetime import datetime
from typing import Dict, Any, List
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
        signal_name: str = None,
        hour: str = None
    ) -> str:
        """
        Tạo partition path theo format: year=YYYY/month=MM/day=DD/[HH_30.json hoặc data.json]
        
        Args:
            data_source: Nguồn dữ liệu ("weather" hoặc "electricity")
            query_date: Ngày (format: YYYY-MM-DD)
            signal_name: Tên signal (chỉ dành cho electricity)
            hour: Giờ (format: HH) - nếu None thì là file tổng hợp (data.json)
        
        Returns:
            str: Full S3 key path
        
        Example:
            # Hourly file
            bronze/weather/year=2024/month=12/day=20/13_30.json
            
            # Compacted file (data.json)
            bronze/weather/year=2024/month=12/day=20/data.json
            
            # Electricity hourly
            bronze/electricity/carbon_intensity/year=2024/month=12/day=20/13_30.json
        """
        # Parse date
        date_obj = datetime.strptime(query_date, "%Y-%m-%d")
        year = date_obj.year
        month = str(date_obj.month).zfill(2)
        day = str(date_obj.day).zfill(2)
        
        # Determine filename
        if hour is not None:
            # Hourly file: HH_30.json
            filename = f"{hour}_30.json"
        else:
            # Compacted file: data.json
            filename = "data.json"
        
        # Build path
        if data_source == "weather":
            path = f"{self.bronze_prefix}/weather/year={year}/month={month}/day={day}/{filename}"
        elif data_source == "electricity":
            if not signal_name:
                raise ValueError("signal_name is required for electricity data")
            path = f"{self.bronze_prefix}/electricity/{signal_name}/year={year}/month={month}/day={day}/{filename}"
        else:
            raise ValueError(f"Unknown data_source: {data_source}")
        
        return path
    
    def write_json(
        self, 
        data: Dict[str, Any],
        data_source: str,
        query_date: str,
        signal_name: str = None,
        hour: str = None
    ) -> str:
        """
        Ghi dữ liệu JSON lên S3
        
        Args:
            data: Dictionary chứa dữ liệu
            data_source: Nguồn dữ liệu ("weather" hoặc "electricity")
            query_date: Ngày (format: YYYY-MM-DD)
            signal_name: Tên signal (chỉ dành cho electricity)
            hour: Giờ (format: HH) - None nếu là file compacted
        
        Returns:
            str: S3 URI của file đã ghi (s3://bucket/key)
        
        Raises:
            ClientError: Nếu ghi S3 thất bại
        """
        # Generate partition path
        s3_key = self._generate_partition_path(data_source, query_date, signal_name, hour)
        
        # Convert dict to JSON string
        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        
        try:
            logger.info(f"💾 Writing to s3://{self.bucket_name}/{s3_key}")
            
            # Upload to S3
            metadata = {
                'source': data_source,
                'query_date': query_date,
                'ingestion_timestamp': datetime.utcnow().isoformat()
            }
            
            if hour:
                metadata['hour'] = hour
                metadata['file_type'] = 'hourly'
            else:
                metadata['file_type'] = 'compacted'
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_data.encode('utf-8'),
                ContentType='application/json',
                Metadata=metadata
            )
            
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"✅ Successfully written to {s3_uri}")
            
            return s3_uri
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"❌ S3 Write Error [{error_code}]: {error_msg}")
            raise
    
    def write_weather_data(
        self, 
        data: Dict[str, Any], 
        query_date: str,
        hour: str = None
    ) -> str:
        """
        Shorthand method để ghi weather data
        
        Args:
            data: Weather data dictionary
            query_date: Ngày (format: YYYY-MM-DD)
            hour: Giờ (format: HH) - None nếu là file compacted
        
        Returns:
            str: S3 URI
        """
        return self.write_json(
            data=data,
            data_source="weather",
            query_date=query_date,
            hour=hour
        )
    
    def write_electricity_data(
        self, 
        data: Dict[str, Any], 
        signal_name: str,
        query_date: str,
        hour: str = None
    ) -> str:
        """
        Shorthand method để ghi electricity data
        
        Args:
            data: Electricity data dictionary
            signal_name: Tên signal
            query_date: Ngày (format: YYYY-MM-DD)
            hour: Giờ (format: HH) - None nếu là file compacted
        
        Returns:
            str: S3 URI
        """
        return self.write_json(
            data=data,
            data_source="electricity",
            query_date=query_date,
            signal_name=signal_name,
            hour=hour
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
    
    def list_hourly_files(self, data_source: str, query_date: str, signal_name: str = None) -> List[str]:
        """
        List tất cả hourly files trong 1 ngày
        
        Args:
            data_source: "weather" hoặc "electricity"
            query_date: Ngày (format: YYYY-MM-DD)
            signal_name: Tên signal (chỉ cho electricity)
        
        Returns:
            List[str]: List các S3 keys của hourly files (sorted)
        """
        date_obj = datetime.strptime(query_date, "%Y-%m-%d")
        year = date_obj.year
        month = str(date_obj.month).zfill(2)
        day = str(date_obj.day).zfill(2)
        
        if data_source == "weather":
            prefix = f"{self.bronze_prefix}/weather/year={year}/month={month}/day={day}/"
        elif data_source == "electricity":
            if not signal_name:
                raise ValueError("signal_name required for electricity")
            prefix = f"{self.bronze_prefix}/electricity/{signal_name}/year={year}/month={month}/day={day}/"
        else:
            raise ValueError(f"Unknown data_source: {data_source}")
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return []
            
            # Filter only hourly files (XX_30.json pattern)
            hourly_files = [
                obj['Key'] for obj in response['Contents']
                if obj['Key'].endswith('_30.json')
            ]
            
            return sorted(hourly_files)
            
        except ClientError as e:
            logger.error(f"❌ Error listing files: {str(e)}")
            raise
    
    def read_json(self, s3_key: str) -> Dict[str, Any]:
        """
        Đọc JSON file từ S3
        
        Args:
            s3_key: S3 key path
        
        Returns:
            Dict: Parsed JSON data
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
            
        except ClientError as e:
            logger.error(f"❌ Error reading file {s3_key}: {str(e)}")
            raise
    
    def delete_file(self, s3_key: str) -> bool:
        """
        Xóa file trên S3
        
        Args:
            s3_key: S3 key path
        
        Returns:
            bool: True nếu xóa thành công
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"🗑️ Deleted {s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"❌ Error deleting file {s3_key}: {str(e)}")
            raise