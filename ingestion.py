import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from utils import Logger
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

LOG_DIR = Path(__file__).parent / "logs" / "ingestion"

class DataIngestion:
    def __init__(self, synthetic=True):
        self.synthetic = synthetic
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }

        self.last_run_file = Path(__file__).parent / "last_run.json"
        self.data_dir = Path(__file__).parent / "data"
        
        self.simulation_start = datetime(2024, 1, 1)

    @property
    def get_db_conn(self):
        return psycopg2.connect(**self.db_config)
    
    def _get_simulation_day(self):
        """Get the current simulation day (0-based index from start date)"""
        if self.last_run_file.exists():
            try:
                with open(self.last_run_file, 'r') as f:
                    data = json.load(f)
                    return data.get('simulation_day', 0)
            except (json.JSONDecodeError, KeyError):
                pass
        return 0
    
    def _update_simulation_day(self, day):
        """Update the simulation day"""
        data = {}
        if self.last_run_file.exists():
            try:
                with open(self.last_run_file, 'r') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, KeyError):
                pass
        
        data.update({
            'simulation_day': day,
            'last_run': datetime.now().isoformat(),
            'simulation_date': (self.simulation_start + timedelta(days=day)).isoformat()
        })
        
        with open(self.last_run_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _get_synthetic_data(self):
        """Load synthetic data from JSON file"""
        with open(self.data_dir / "hr.json", 'r') as file:
            data = json.load(file)
        return data
    
    def _convert_to_timestamp(self, date_str, time_str):
        """Convert date and time strings to timestamp"""
        datetime_str = f"{date_str} {time_str}"
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    
    def _get_next_data_to_process(self):
        """Get the next day's data to process in the simulation"""
        current_day = self._get_simulation_day()
        data = self._get_synthetic_data()
        
        if current_day >= len(data):
            print(f"Simulation complete! All {len(data)} days of data have been processed.")
            return None, None
        
        day_data = data[current_day]
        simulation_date = self.simulation_start + timedelta(days=current_day)
        
        return day_data, simulation_date
    
    def ingest(self, days=1):
        """Main ingestion method"""
        print(f"Starting ingestion at {datetime.now()}")
        
        if not self.synthetic:
            raise NotImplementedError("Only synthetic data ingestion is implemented.")
        
        for day_num in range(days):
            try:
                day_data, simulation_date = self._get_next_data_to_process()
                
                if day_data is None:
                    print(f"Stopping ingestion after {day_num} days - simulation complete.")
                    break
                
                current_day = self._get_simulation_day()
                print(f"Processing simulation day {current_day + 1}: {simulation_date.strftime('%Y-%m-%d')}")
                
                conn = self.get_db_conn
                cursor = conn.cursor()

                participant_id = 1
                records_processed = 0

                heart_rate_day = day_data['heart_rate_day'][0]
                activities_heart = heart_rate_day['activities-heart'][0]
                activities_heart_intraday = heart_rate_day['activities-heart-intraday']

                date_str = simulation_date.strftime('%Y-%m-%d')
                
                value = activities_heart['value']
                resting_heart_rate = value.get('restingHeartRate', None)
                
                cursor.execute("""
                    INSERT INTO daily_summaries (participant_id, date, resting_heart_rate, dataset_interval, dataset_type)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (participant_id, date) DO UPDATE SET
                        resting_heart_rate = EXCLUDED.resting_heart_rate,
                        dataset_interval = EXCLUDED.dataset_interval,
                        dataset_type = EXCLUDED.dataset_type
                """, (participant_id, date_str, resting_heart_rate, 
                    activities_heart_intraday['datasetInterval'], 
                    activities_heart_intraday['datasetType']))

                heart_rate_zones = value.get('heartRateZones', [])
                for zone in heart_rate_zones:
                    cursor.execute("""
                        INSERT INTO heart_rate_zones (participant_id, date, zone_name, min_heart_rate, max_heart_rate, minutes, calories_out)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (participant_id, date, zone_name) DO UPDATE SET
                            min_heart_rate = EXCLUDED.min_heart_rate,
                            max_heart_rate = EXCLUDED.max_heart_rate,
                            minutes = EXCLUDED.minutes,
                            calories_out = EXCLUDED.calories_out
                    """, (participant_id, date_str, zone['name'], zone['min'], zone['max'], zone['minutes'], zone.get('caloriesOut')))

                dataset = activities_heart_intraday['dataset']
                for entry in dataset:
                    timestamp = self._convert_to_timestamp(date_str, entry['time'])
                    cursor.execute("""
                        INSERT INTO raw_data (participant_id, timestamp, metric_type, value)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (participant_id, timestamp, metric_type) DO UPDATE SET
                            value = EXCLUDED.value
                    """, (participant_id, timestamp, 'heart_rate', entry['value']))
                    records_processed += 1

                conn.commit()
                cursor.close()
                conn.close()
                
                self._update_simulation_day(current_day + 1)
                
                print(f"Ingestion completed successfully. Processed {records_processed} records for {date_str}.")
                
            except Exception as e:
                print(f"Error during ingestion: {str(e)}")
                if 'conn' in locals():
                    conn.rollback()
                    conn.close()
                raise
    
    def reset_simulation(self):
        """Reset the simulation to start from day 0"""
        if self.last_run_file.exists():
            self.last_run_file.unlink()
        print("Simulation reset to start from January 1, 2024")
    
    def get_simulation_status(self):
        """Get current simulation status"""
        current_day = self._get_simulation_day()
        data = self._get_synthetic_data()
        total_days = len(data)
        current_date = self.simulation_start + timedelta(days=current_day)
        
        return {
            'current_day': current_day,
            'total_days': total_days,
            'current_date': current_date.strftime('%Y-%m-%d'),
            'progress': f"{current_day}/{total_days} days processed"
        }


if __name__ == "__main__":
    os.makedirs(LOG_DIR, exist_ok=True)
    
    log_file = LOG_DIR / f"ingestion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    print(f"Logging to {log_file}")
    
    sys.stdout = Logger(log_file)
    sys.stderr = sys.stdout
    
    parser = argparse.ArgumentParser(description="Data Ingestion Script")
    parser.add_argument('--reset', action='store_true', help="Reset the simulation to start from day 0")
    parser.add_argument('--status', action='store_true', help="Get current simulation status")
    parser.add_argument('--days', type=int, default=1, help="For ingestion of multiple days, specify the number of days to ingest (default: 1)")
    args = parser.parse_args()
    
    if args.reset:
        ingestion = DataIngestion(synthetic=True)
        ingestion.reset_simulation()
        print("Simulation reset successfully.")
        sys.exit(0)
        
    if args.status:
        ingestion = DataIngestion(synthetic=True)
        status = ingestion.get_simulation_status()
        print(f"Simulation Status: {status['progress']}")
        print(f"Next Date to Process: {status['current_date']}")
        sys.exit(0)

    try:
        ingestion = DataIngestion(synthetic=True)
        
        status = ingestion.get_simulation_status()
        print(f"Simulation Status: {status['progress']}")
        print(f"Next Date to Process: {status['current_date']}")
        
        ingestion.ingest(days=args.days)

    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)