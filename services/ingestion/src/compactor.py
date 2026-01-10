"""
compactor.py
🗜️ Gộp các hourly files thành 1 file compacted cho mỗi ngày
"""
import logging
from typing import Dict, Any, List
from s3_writer import S3Writer
from config import Config

logger = logging.getLogger(__name__)

class DataCompactor:
    """
    Class để compact hourly data thành daily data
    """
    
    def __init__(self, s3_writer: S3Writer):
        """
        Args:
            s3_writer: S3Writer instance
        """
        self.s3_writer = s3_writer
    
    def _extract_hour_from_data(self, hourly_data: Dict[str, Any]) -> str:
        """
        Trích xuất giờ từ dữ liệu hourly
        
        Args:
            hourly_data: Dict chứa data của 1 giờ
        
        Returns:
            str: Hour string (format: HH)
        """
        # Weather data structure: days[0].hours[0].datetime
        if 'days' in hourly_data and len(hourly_data['days']) > 0:
            if 'hours' in hourly_data['days'][0] and len(hourly_data['days'][0]['hours']) > 0:
                hour_str = hourly_data['days'][0]['hours'][0]['datetime']  # "13:00:00"
                return hour_str.split(':')[0]  # "13"
        
        # Electricity data structure: history[0].datetime
        if 'history' in hourly_data and len(hourly_data['history']) > 0:
            datetime_str = hourly_data['history'][0]['datetime']  # "2024-01-11T13:00:00Z"
            return datetime_str.split('T')[1].split(':')[0]  # "13"
        
        # Fallback: check metadata
        if '_metadata' in hourly_data and 'hour' in hourly_data['_metadata']:
            return hourly_data['_metadata']['hour']
        
        logger.warning("⚠️ Cannot extract hour from data, using filename")
        return None
    
    def compact_weather_data(self, query_date: str) -> Dict[str, Any]:
        """
        Compact weather hourly files thành 1 file
        
        Args:
            query_date: Ngày cần compact (format: YYYY-MM-DD)
        
        Returns:
            dict: Stats về quá trình compact
        """
        logger.info(f"🗜️ Compacting weather data for {query_date}")
        
        # List all hourly files
        hourly_files = self.s3_writer.list_hourly_files("weather", query_date)
        
        if not hourly_files:
            logger.warning(f"⚠️ No hourly files found for {query_date}")
            return {"status": "no_files", "files_processed": 0}
        
        logger.info(f"📁 Found {len(hourly_files)} hourly files")
        
        # Read all hourly data
        all_hours = []
        template_data = None
        
        for file_key in hourly_files:
            try:
                data = self.s3_writer.read_json(file_key)
                
                # First file: save as template (queryCost, latitude, etc.)
                if template_data is None:
                    template_data = {
                        k: v for k, v in data.items() 
                        if k not in ['days', '_metadata']
                    }
                
                # Extract hourly data
                if 'days' in data and len(data['days']) > 0:
                    if 'hours' in data['days'][0] and len(data['days'][0]['hours']) > 0:
                        hour_data = data['days'][0]['hours'][0]
                        all_hours.append(hour_data)
                
            except Exception as e:
                logger.error(f"❌ Error reading {file_key}: {str(e)}")
                continue
        
        if not all_hours:
            logger.error("❌ No valid hourly data found")
            return {"status": "error", "error": "no_valid_data"}
        
        # Sort by datetime
        all_hours.sort(key=lambda x: x['datetime'])
        
        # Build compacted structure
        compacted_data = template_data.copy()
        compacted_data['days'] = [{
            'datetime': query_date,
            'hours': all_hours
        }]
        
        # Write compacted file
        s3_uri = self.s3_writer.write_weather_data(
            data=compacted_data,
            query_date=query_date,
            hour=None  # None = compacted file
        )
        
        logger.info(f"✅ Compacted {len(all_hours)} hours -> {s3_uri}")
        
        # Delete hourly files
        deleted_count = 0
        for file_key in hourly_files:
            try:
                self.s3_writer.delete_file(file_key)
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ Error deleting {file_key}: {str(e)}")
        
        logger.info(f"🗑️ Deleted {deleted_count}/{len(hourly_files)} hourly files")
        
        return {
            "status": "success",
            "date": query_date,
            "hours_compacted": len(all_hours),
            "files_deleted": deleted_count,
            "output_uri": s3_uri
        }
    
    def compact_electricity_data(self, query_date: str, signal_name: str) -> Dict[str, Any]:
        """
        Compact electricity hourly files thành 1 file
        
        Args:
            query_date: Ngày cần compact (format: YYYY-MM-DD)
            signal_name: Tên signal
        
        Returns:
            dict: Stats về quá trình compact
        """
        logger.info(f"🗜️ Compacting {signal_name} data for {query_date}")
        
        # List all hourly files
        hourly_files = self.s3_writer.list_hourly_files(
            "electricity", 
            query_date, 
            signal_name
        )
        
        if not hourly_files:
            logger.warning(f"⚠️ No hourly files found for {signal_name} on {query_date}")
            return {"status": "no_files", "files_processed": 0}
        
        logger.info(f"📁 Found {len(hourly_files)} hourly files")
        
        # Read all hourly data
        all_history = []
        template_data = None
        
        for file_key in hourly_files:
            try:
                data = self.s3_writer.read_json(file_key)
                
                # First file: save as template
                if template_data is None:
                    template_data = {
                        k: v for k, v in data.items() 
                        if k not in ['history', '_metadata']
                    }
                
                # Extract history data
                if 'history' in data and len(data['history']) > 0:
                    all_history.extend(data['history'])
                
            except Exception as e:
                logger.error(f"❌ Error reading {file_key}: {str(e)}")
                continue
        
        if not all_history:
            logger.error("❌ No valid history data found")
            return {"status": "error", "error": "no_valid_data"}
        
        # Sort by datetime
        all_history.sort(key=lambda x: x['datetime'])
        
        # Build compacted structure
        compacted_data = template_data.copy()
        compacted_data['history'] = all_history
        compacted_data['_metadata'] = {
            "signal": signal_name,
            "query_date": query_date,
            "zone": Config.ELECTRICITY_ZONE
        }
        
        # Write compacted file
        s3_uri = self.s3_writer.write_electricity_data(
            data=compacted_data,
            signal_name=signal_name,
            query_date=query_date,
            hour=None  # None = compacted file
        )
        
        logger.info(f"✅ Compacted {len(all_history)} records -> {s3_uri}")
        
        # Delete hourly files
        deleted_count = 0
        for file_key in hourly_files:
            try:
                self.s3_writer.delete_file(file_key)
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ Error deleting {file_key}: {str(e)}")
        
        logger.info(f"🗑️ Deleted {deleted_count}/{len(hourly_files)} hourly files")
        
        return {
            "status": "success",
            "signal": signal_name,
            "date": query_date,
            "records_compacted": len(all_history),
            "files_deleted": deleted_count,
            "output_uri": s3_uri
        }
    
    def compact_all(self, query_date: str) -> Dict[str, Any]:
        """
        Compact tất cả dữ liệu (weather + all electricity signals) cho 1 ngày
        
        Args:
            query_date: Ngày cần compact (format: YYYY-MM-DD)
        
        Returns:
            dict: Tổng hợp kết quả
        """
        logger.info(f"🗜️ Starting full compaction for {query_date}")
        
        results = {
            "date": query_date,
            "weather": None,
            "electricity": {}
        }
        
        # Compact weather data
        try:
            weather_result = self.compact_weather_data(query_date)
            results["weather"] = weather_result
        except Exception as e:
            logger.error(f"❌ Weather compaction failed: {str(e)}")
            results["weather"] = {"status": "error", "error": str(e)}
        
        # Compact electricity data (all signals)
        for signal in Config.ELECTRICITY_SIGNALS:
            try:
                elec_result = self.compact_electricity_data(query_date, signal)
                results["electricity"][signal] = elec_result
            except Exception as e:
                logger.error(f"❌ {signal} compaction failed: {str(e)}")
                results["electricity"][signal] = {"status": "error", "error": str(e)}
        
        logger.info(f"✅ Compaction completed for {query_date}")
        
        return results