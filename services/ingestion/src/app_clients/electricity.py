"""
api_clients/electricity.py
⚡ Client để lấy dữ liệu điện từ Electricity Maps API
"""
import logging
from typing import Dict, Any
from .base import BaseAPIClient

logger = logging.getLogger(__name__)

class ElectricityAPIClient(BaseAPIClient):
    """
    Client để gọi Electricity Maps API
    Hỗ trợ nhiều signal: carbon_intensity, total_load, price, etc.
    """
    
    def __init__(
        self, 
        api_key: str,
        api_host: str,
        zone: str,
        granularity: str,
        endpoint_mapping: Dict[str, str],
        max_retries: int = 3
    ):
        """
        Args:
            api_key: Electricity Maps API key
            api_host: Base URL của API
            zone: Mã khu vực (ví dụ: "VN")
            granularity: Độ chi tiết dữ liệu ("hourly")
            endpoint_mapping: Dict mapping signal_name -> endpoint_path
            max_retries: Số lần retry
        """
        super().__init__(api_key, max_retries)
        self.api_host = api_host
        self.zone = zone
        self.granularity = granularity
        self.endpoint_mapping = endpoint_mapping
    
    def fetch_data(self, query_date: str, signal_name: str) -> Dict[str, Any]:
        """
        Lấy dữ liệu electricity cho 1 signal cụ thể trong 1 ngày
        
        Args:
            query_date: Ngày cần lấy (format: YYYY-MM-DD)
            signal_name: Tên signal (ví dụ: "carbon_intensity", "total_load")
        
        Returns:
            Dict: JSON response chứa dữ liệu
        
        Example response structure:
        {
            "zone": "VN",
            "history": [
                {
                    "datetime": "2024-01-01T00:00:00Z",
                    "carbonIntensity": 450,
                    "fossilFreePercentage": 35,
                    ...
                },
                ...
            ]
        }
        """
        # Lấy endpoint path từ mapping
        api_path = self.endpoint_mapping.get(
            signal_name, 
            signal_name.replace('_', '-')  # Fallback: convert snake_case -> kebab-case
        )
        
        # Construct full URL
        endpoint = f"{self.api_host}/{api_path}/past-range"
        
        # Define time range: 00:00:00 to 23:59:59 UTC
        start_time = f"{query_date}T00:00:00Z"
        end_time = f"{query_date}T23:59:59Z"
        
        headers = {
            "auth-token": self.api_key
        }
        
        params = {
            "zone": self.zone,
            "start": start_time,
            "end": end_time,
            "temporalGranularity": self.granularity
        }
        
        logger.info(f"⚡ Fetching {signal_name} data for {query_date}")
        data = self._make_request(endpoint, headers=headers, params=params)
        
        # Validate response structure
        if "history" not in data and "data" not in data:
            # Một số endpoint trả về "data" thay vì "history"
            logger.warning(f"⚠️ Response không có field 'history' hoặc 'data', trả về raw response")
        
        # Add metadata vào response
        data["_metadata"] = {
            "signal": signal_name,
            "query_date": query_date,
            "zone": self.zone
        }
        
        logger.info(f"✅ Successfully fetched {signal_name} data")
        
        return data
    
    def fetch_all_signals(self, query_date: str, signal_list: list) -> Dict[str, Any]:
        """
        Lấy tất cả signals cho 1 ngày cụ thể
        
        Args:
            query_date: Ngày cần lấy (format: YYYY-MM-DD)
            signal_list: List các signal cần lấy
        
        Returns:
            Dict: Dict chứa tất cả signals
            {
                "carbon_intensity": {...},
                "total_load": {...},
                ...
            }
        """
        results = {}
        
        for signal in signal_list:
            try:
                data = self.fetch_data(query_date, signal)
                results[signal] = data
                logger.info(f"✅ {signal}: OK")
            except Exception as e:
                logger.error(f"❌ {signal}: FAILED - {str(e)}")
                # Không raise exception, tiếp tục với signal khác
                results[signal] = {"error": str(e)}
        
        return results
    
    def get_metadata(self) -> Dict[str, str]:
        """
        Trả về metadata của data source
        
        Returns:
            Dict: Metadata info
        """
        return {
            "source": "electricity_maps",
            "zone": self.zone,
            "granularity": self.granularity,
            "available_signals": list(self.endpoint_mapping.keys())
        }