"""
api_clients/base.py
🔌 Base class cho tất cả API clients (Retry logic, Error handling)
"""
import time
import logging
import requests
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseAPIClient(ABC):
    """
    Abstract base class cho API clients
    Cung cấp:
    - Retry logic
    - Error handling
    - Logging
    """
    
    def __init__(self, api_key: str, max_retries: int = 3, retry_delay: int = 5):
        """
        Args:
            api_key: API key để authenticate
            max_retries: Số lần retry tối đa
            retry_delay: Thời gian chờ giữa các lần retry (seconds)
        """
        self.api_key = api_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def _make_request(
        self, 
        url: str, 
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Thực hiện HTTP request với retry logic
        
        Args:
            url: URL endpoint
            headers: HTTP headers
            params: Query parameters
            method: HTTP method (GET, POST, etc.)
        
        Returns:
            Dict: JSON response
        
        Raises:
            Exception: Nếu request thất bại sau max_retries lần
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"🌐 Calling {url} (Attempt {attempt}/{self.max_retries})")
                
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    timeout=30  # Timeout sau 30s
                )
                
                # Raise exception nếu status code 4xx hoặc 5xx
                response.raise_for_status()
                
                logger.info(f"✅ Request thành công (Status: {response.status_code})")
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response else "Unknown"
                logger.error(f"❌ HTTP Error {status_code}: {str(e)}")
                
                # Không retry với 4xx errors (Client errors)
                if 400 <= status_code < 500:
                    logger.error("🚫 Client error - Không retry")
                    raise
                
                # Retry với 5xx errors (Server errors)
                if attempt < self.max_retries:
                    logger.warning(f"⏳ Retry sau {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"💥 Thất bại sau {self.max_retries} lần retry")
                    raise
                    
            except requests.exceptions.Timeout:
                logger.error(f"⏰ Request timeout")
                if attempt < self.max_retries:
                    logger.warning(f"⏳ Retry sau {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"💥 Thất bại sau {self.max_retries} lần retry")
                    raise
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Request error: {str(e)}")
                if attempt < self.max_retries:
                    logger.warning(f"⏳ Retry sau {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"💥 Thất bại sau {self.max_retries} lần retry")
                    raise
    
    @abstractmethod
    def fetch_data(self, query_date: str) -> Dict[str, Any]:
        """
        Abstract method - Phải được implement ở subclass
        
        Args:
            query_date: Ngày cần lấy dữ liệu (format: YYYY-MM-DD)
        
        Returns:
            Dict: Raw JSON data
        """
        pass