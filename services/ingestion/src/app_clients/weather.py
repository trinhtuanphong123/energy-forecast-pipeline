"""
api_clients/weather.py
☀️ Client để lấy dữ liệu thời tiết từ Visual Crossing API
"""
import logging
from typing import Dict, Any
from .base import BaseAPIClient

logger = logging.getLogger(__name__)

class WeatherAPIClient(BaseAPIClient):
    """
    Client để gọi Visual Crossing Weather API
    """
    
    def __init__(
        self, 
        api_key: str,
        api_host: str,
        location: str,
        elements: str,
        max_retries: int = 3
    ):
        """
        Args:
            api_key: Visual Crossing API key
            api_host: Base URL của API
            location: Địa điểm (ví dụ: "Vietnam")
            elements: Các trường cần lấy (ví dụ: "datetime,temp,humidity")
            max_retries: Số lần retry
        """
        super().__init__(api_key, max_retries)
        self.api_host = api_host
        self.location = location
        self.elements = elements
    
    def fetch_data(self, query_date: str) -> Dict[str, Any]:
        """
        Lấy dữ liệu thời tiết hourly cho 1 ngày cụ thể
        
        Args:
            query_date: Ngày cần lấy (format: YYYY-MM-DD)
        
        Returns:
            Dict: JSON response chứa dữ liệu thời tiết
        
        Example response structure:
        {
            "queryCost": 1,
            "latitude": 14.0583,
            "longitude": 108.2772,
            "resolvedAddress": "Vietnam",
            "address": "Vietnam",
            "timezone": "Asia/Bangkok",
            "days": [
                {
                    "datetime": "2024-01-01",
                    "temp": 25.5,
                    "humidity": 75.2,
                    "hours": [
                        {
                            "datetime": "00:00:00",
                            "temp": 24.0,
                            "humidity": 78.0,
                            ...
                        },
                        ...
                    ]
                }
            ]
        }
        """
        params = {
            "unitGroup": "metric",        # Sử dụng độ C, km/h
            "include": "hours",           # ⚠️ QUAN TRỌNG: Lấy dữ liệu theo giờ
            "location": self.location,
            "key": self.api_key,
            "contentType": "json",
            "elements": self.elements,
            "datetime": query_date       # Query cho 1 ngày cụ thể
        }
        
        logger.info(f"☀️ Fetching weather data for {query_date}")
        data = self._make_request(self.api_host, params=params)
        
        # Validate response structure
        if "days" not in data:
            raise ValueError(f"Invalid response structure: Missing 'days' field")
        
        if len(data["days"]) == 0:
            raise ValueError(f"No data returned for {query_date}")
        
        # Validate có hourly data không
        if "hours" not in data["days"][0]:
            raise ValueError(f"Missing hourly data for {query_date}")
        
        logger.info(f"✅ Successfully fetched {len(data['days'][0]['hours'])} hourly records")
        
        return data
    
    def get_metadata(self) -> Dict[str, str]:
        """
        Trả về metadata của data source
        
        Returns:
            Dict: Metadata info
        """
        return {
            "source": "visual_crossing",
            "location": self.location,
            "elements": self.elements,
            "granularity": "hourly"
        }