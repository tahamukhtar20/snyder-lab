import sys
import os
import argparse
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from utils import Logger
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
from prometheus_client import Counter, Histogram, Gauge, start_http_server

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

LOG_DIR = Path(__file__).parent / "logs" / "ingestion"

INGESTION_COUNTER = Counter('ingestion_runs_total', 'Total ingestion runs', ['status'])
INGESTION_DURATION = Histogram('ingestion_duration_seconds', 'Ingestion duration')
RECORDS_PROCESSED = Counter('records_processed_total', 'Total records processed', ['data_type'])
INGESTION_ERRORS = Counter('ingestion_errors_total', 'Total ingestion errors', ['error_type'])
DATA_POINTS_PROCESSED = Counter('data_points_processed_total', 'Total data points processed')
ACTIVE_DATABASE_CONNECTIONS = Gauge('active_database_connections', 'Active database connections')

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
        
        try:
            start_http_server(8001)
            print("Prometheus metrics server started on port 8001")
        except Exception as e:
            print(f"Server already running")

    @property
    def get_db_conn(self):
        """Get database connection with connection tracking"""
        ACTIVE_DATABASE_CONNECTIONS.inc()
        return psycopg2.connect(**self.db_config)

    def close_db_conn(self, conn):
        """Close database connection with connection tracking"""
        if conn:
            conn.close()
            ACTIVE_DATABASE_CONNECTIONS.dec()

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
        try:
            with open(self.data_dir / "hr.json", 'r') as file:
                data = json.load(file)
                return data
        except FileNotFoundError:
            INGESTION_ERRORS.labels(error_type='file_not_found').inc()
            raise
        except json.JSONDecodeError:
            INGESTION_ERRORS.labels(error_type='json_decode').inc()
            raise

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
        """Main ingestion method with monitoring"""
        print(f"Starting ingestion at {datetime.now()}")
        
        if not self.synthetic:
            INGESTION_ERRORS.labels(error_type='unsupported_mode').inc()
            raise NotImplementedError("Only synthetic data ingestion is implemented.")
        
        for day_num in range(days):
            start_time = time.time()
            conn = None
            
            try:
                with INGESTION_DURATION.time():
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
                    
                    RECORDS_PROCESSED.labels(data_type='daily_summary').inc()
                    
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
                        
                        RECORDS_PROCESSED.labels(data_type='heart_rate_zone').inc()
                    
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
                        DATA_POINTS_PROCESSED.inc()
                    
                    RECORDS_PROCESSED.labels(data_type='raw_data').inc(records_processed)
                    
                    conn.commit()
                    cursor.close()
                    
                    self._update_simulation_day(current_day + 1)
                    
                    INGESTION_COUNTER.labels(status='success').inc()
                    
                    duration = time.time() - start_time
                    print(f"Ingestion completed successfully. Processed {records_processed} records for {date_str} in {duration:.2f} seconds.")
                    
            except Exception as e:
                INGESTION_ERRORS.labels(error_type='general').inc()
                INGESTION_COUNTER.labels(status='error').inc()
                print(f"Error during ingestion: {str(e)}")
                
                if conn:
                    conn.rollback()
                
                raise
            finally:
                if conn:
                    self.close_db_conn(conn)
                
                duration = time.time() - start_time
                print(f"Ingestion process completed in {duration:.2f} seconds")

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

    def health_check(self):
        """Health check endpoint for monitoring"""
        try:
            conn = self.get_db_conn
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            self.close_db_conn(conn)
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            INGESTION_ERRORS.labels(error_type='health_check').inc()
            return {"status": "unhealthy", "error": str(e)}

if __name__ == "__main__":
    os.makedirs(LOG_DIR, exist_ok=True)
    
    log_file = LOG_DIR / f"ingestion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    print(f"Logging to {log_file}")
    
    sys.stdout = Logger(log_file)
    sys.stderr = sys.stdout
    
    parser = argparse.ArgumentParser(description="Data Ingestion Script")
    parser.add_argument('--reset', action='store_true', help="Reset the simulation to start from day 0")
    parser.add_argument('--status', action='store_true', help="Get current simulation status")
    parser.add_argument('--health', action='store_true', help="Perform health check")
    parser.add_argument('--days', type=int, default=1, help="Number of days to ingest (default: 1)")
    args = parser.parse_args()
    ingestion = DataIngestion(synthetic=True)

    if args.reset:
        ingestion.reset_simulation()
        print("Simulation reset successfully.")
        sys.exit(0)
    
    if args.status:
        status = ingestion.get_simulation_status()
        print(f"Simulation Status: {status['progress']}")
        print(f"Next Date to Process: {status['current_date']}")
        sys.exit(0)
    
    if args.health:
        health = ingestion.health_check()
        print(f"Health Status: {health}")
        sys.exit(0 if health['status'] == 'healthy' else 1)
    
    try:
        status = ingestion.get_simulation_status()
        print(f"Simulation Status: {status['progress']}")
        print(f"Next Date to Process: {status['current_date']}")
        
        ingestion.ingest(days=args.days)
        
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)
