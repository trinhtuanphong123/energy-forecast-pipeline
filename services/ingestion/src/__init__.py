# src/__init__.py
"""
Vietnam Energy Forecasting - Ingestion Service
"""
__version__ = "1.0.0"

# src/api_clients/__init__.py
"""
API Clients Module
"""
from .base import BaseAPIClient
from .weather import WeatherAPIClient
from .electricity import ElectricityAPIClient

__all__ = [
    'BaseAPIClient',
    'WeatherAPIClient', 
    'ElectricityAPIClient'
]