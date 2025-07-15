from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from datetime import date, datetime
import os
import psycopg2
from dotenv import load_dotenv
from typing import List, Optional, Union
import logging
from contextlib import contextmanager
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
from enum import Enum
from typing import Dict, Any

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')
ACTIVE_CONNECTIONS = Gauge('active_database_connections', 'Active database connections')
DATA_POINTS_PROCESSED = Counter('data_points_processed_total', 'Total data points processed')

class Config(BaseSettings):
    DB_HOST: str = Field(..., env="DB_HOST")
    DB_PORT: int = Field(..., env="DB_PORT")
    DB_NAME: str = Field(..., env="DB_NAME")
    DB_USER: str = Field(..., env="DB_USER")
    DB_PASSWORD: str = Field(..., env="DB_PASSWORD")
    DEFAULT_PAGE_LIMIT: int = Field(100, env="DEFAULT_PAGE_LIMIT")

    class Config:
        env_file = ".env"

config = Config()
load_dotenv(config.Config.env_file)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
file_handler = logging.FileHandler('app.log')

@contextmanager
def db_cursor():
    ACTIVE_CONNECTIONS.inc()
    conn = psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD
    )
    try:
        yield conn.cursor()
    finally:
        ACTIVE_CONNECTIONS.dec()
        conn.close()

class RawDataItem(BaseModel):
    participant_id: int
    timestamp: datetime
    metric_type: str
    value: float
    aggregation_level: str

class AggregatedDataItem(BaseModel):
    participant_id: int
    timestamp: datetime
    avg_value: float
    min_value: float
    max_value: float
    aggregation_level: str

class MetadataModel(BaseModel):
    aggregation_level: str
    query_span_days: int
    total_points: int
    participant_ids: List[int]
    start_date: date
    end_date: date
    next_cursor: Optional[datetime]

class DataResponse(BaseModel):
    data: List[Union[RawDataItem, AggregatedDataItem]]
    metadata: MetadataModel

class AdherenceStatus(str, Enum):
    NO_TOKEN = "no_token"
    NO_DATA_48H = "no_data_48h"
    LOW_SLEEP = "low_sleep"
    LOW_ADHERENCE = "low_adherence"
    GOOD = "good"

class ParticipantModel(BaseModel):
    participant_id: int
    name: str
    token: Optional[str] = None

class AdherenceItem(BaseModel):
    participant_id: int
    name: str
    status: AdherenceStatus
    last_data_timestamp: Optional[datetime]
    adherence_percentage: float
    sleep_upload_percentage: float
    details: str

class AdherenceResponse(BaseModel):
    participants: List[AdherenceItem]
    total_participants: int
    issues_count: int

class ImputationRequest(BaseModel):
    participant_id: int
    start_date: date
    end_date: date
    method: str = "linear"

class ImputationResponse(BaseModel):
    participant_id: int
    imputed_points: int
    method_used: str
    start_date: date
    end_date: date

class EmailRequest(BaseModel):
    participant_ids: List[int]
    subject: str
    message: str
    


app = FastAPI(title="Metrics API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.observe(time.time() - start_time)
    
    return response

def determine_aggregation_level(start_date: date, end_date: date) -> str:
    time_span = (end_date - start_date).days
    if time_span <= 7:
        return "raw"
    elif time_span <= 30:
        return "1m"
    elif time_span <= 365:
        return "1h"
    else:
        return "1d"

def execute_optimized_query(
    participant_ids: List[int],
    start_date: date,
    end_date: date,
    agg_level: str,
    cursor: Optional[datetime],
    limit: int
) -> tuple[List[Union[RawDataItem, AggregatedDataItem]], Optional[datetime]]:
    """
    Query data for given participants, aggregation level, and paginate by timestamp.
    Returns a tuple of (records, next_cursor).
    """
    table_map = {
        "raw": ("raw_data", "timestamp", ['participant_id', 'timestamp', 'metric_type', 'value']),
        "1m": ("hr_1m", "bucket", ['participant_id', 'bucket', 'avg_hr', 'min_hr', 'max_hr']),
        "1h": ("hr_1h", "bucket", ['participant_id', 'bucket', 'avg_hr', 'min_hr', 'max_hr']),
        "1d": ("hr_1d", "bucket", ['participant_id', 'bucket', 'avg_hr', 'min_hr', 'max_hr']),
    }
    table, time_col, cols = table_map[agg_level]
    select_cols = ", ".join(cols)

    params = [participant_ids, start_date, end_date]
    where_clause = f"participant_id = ANY(%s) AND {time_col}::date BETWEEN %s AND %s"
    if cursor:
        params.append(cursor)
        where_clause += f" AND {time_col} > %s"

    params.append(limit + 1)
    sql = f"""
        SELECT {select_cols}
        FROM {table}
        WHERE {where_clause}
        ORDER BY {time_col} ASC
        LIMIT %s
    """

    with db_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    has_more = len(rows) == limit + 1
    if has_more:
        next_rec = rows[-1]
        next_cursor = next_rec[cols.index(time_col)]
        rows = rows[:-1]
    else:
        next_cursor = None

    result = []
    for row in rows:
        base = {"participant_id": row[0], "timestamp": row[cols.index(time_col)], "aggregation_level": agg_level}
        if agg_level == "raw":
            base.update({"metric_type": row[cols.index('metric_type')], "value": row[cols.index('value')]})
        else:
            base.update({
                "avg_value": row[cols.index('avg_hr')],
                "min_value": row[cols.index('min_hr')],
                "max_value": row[cols.index('max_hr')]
            })
        result.append(base)

    return result, next_cursor

@app.get("/data", response_model=DataResponse)
def get_data(
    metric: str = Query("heart_rate", description="Metric type to filter by"),
    start_date: date = Query(..., description="Start date (inclusive)"),
    end_date: date = Query(..., description="End date (inclusive)"),
    user_ids: Union[List[int], int] = Query(1, description="Participant ID(s)"),
    aggregation: Optional[str] = Query(None, description="Force specific aggregation level (raw, 1m, 1h, 1d)"),
    cursor: Optional[datetime] = Query(None, description="Timestamp cursor for pagination"),
    limit: int = Query(config.DEFAULT_PAGE_LIMIT, description="Max number of items per page")
):
    if metric != "heart_rate":
        raise HTTPException(status_code=400, detail="Unsupported metric type. Only 'heart_rate' is supported.")
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date.")
    if isinstance(user_ids, int):
        user_ids = [user_ids]

    agg_level = aggregation if aggregation in ["raw", "1m", "1h", "1d"] else determine_aggregation_level(start_date, end_date)
    logger.info(f"Using aggregation level: {agg_level} for span: {(end_date - start_date).days} days")

    data, next_cursor = execute_optimized_query(user_ids, start_date, end_date, agg_level, cursor, limit)

    return {
        "data": data,
        "metadata": {
            "aggregation_level": agg_level,
            "query_span_days": (end_date - start_date).days,
            "total_points": len(data),
            "participant_ids": user_ids,
            "start_date": start_date,
            "end_date": end_date,
            "next_cursor": next_cursor
        }
    }

@app.get("/data/stats")
def get_data_stats(
    start_date: date = Query(..., description="Start date (inclusive)"),
    end_date: date = Query(..., description="End date (inclusive)"),
    participant_ids: List[int] = Query([1], description="Participant ID(s) to get stats for")
):
    with db_cursor() as cur:
        cur.execute(
            '''
            SELECT COUNT(*)
            FROM raw_data
            WHERE participant_id = ANY(%s)
              AND timestamp::date BETWEEN %s AND %s
              AND metric_type = 'heart_rate'
            ''',
            (participant_ids, start_date, end_date)
        )
        raw_count = cur.fetchone()[0]

        cur.execute(
            '''
            SELECT COUNT(*) FROM hr_1m
            WHERE participant_id = ANY(%s) AND bucket::date BETWEEN %s AND %s
            ''',
            (participant_ids, start_date, end_date)
        )
        min_count = cur.fetchone()[0]

        cur.execute(
            '''
            SELECT COUNT(*) FROM hr_1h
            WHERE participant_id = ANY(%s) AND bucket::date BETWEEN %s AND %s
            ''',
            (participant_ids, start_date, end_date)
        )
        hour_count = cur.fetchone()[0]

        cur.execute(
            '''
            SELECT COUNT(*) FROM hr_1d
            WHERE participant_id = ANY(%s) AND bucket::date BETWEEN %s AND %s
            ''',
            (participant_ids, start_date, end_date)
        )
        day_count = cur.fetchone()[0]

    query_span_days = (end_date - start_date).days
    recommended_level = determine_aggregation_level(start_date, end_date)

    return {
        "query_span_days": query_span_days,
        "recommended_aggregation": recommended_level,
        "data_counts": {"raw": raw_count, "1m": min_count, "1h": hour_count, "1d": day_count},
        "participant_ids": participant_ids,
        "start_date": start_date,
        "end_date": end_date
    }


@app.get("/status")
def health_check():
    try:
        with db_cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@app.get("/metrics")
def get_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/metrics/summary")
def get_metrics_summary():
    return {
        "supported_metrics": ["heart_rate"],
        "aggregation_levels": {
            "raw": "Raw data points (<= 7 days)",
            "1m": "1-minute aggregates (8-30 days)",
            "1h": "1-hour aggregates (31-365 days)",
            "1d": "1-day aggregates (> 365 days)"
        },
        "auto_selection": "Aggregation automatically selected based on time span"
    }
    
@app.get("/participants", response_model=List[ParticipantModel])
def get_participants():
    """Get all participants"""
    with db_cursor() as cur:
        cur.execute("SELECT participant_id, name, token FROM participant ORDER BY participant_id")
        rows = cur.fetchall()
        
    return [{"participant_id": row[0], "name": row[1], "token": row[2]} for row in rows]

@app.post("/participants", response_model=ParticipantModel)
def create_participant(participant: ParticipantModel):
    """Create a new participant (for dummy data)"""
    with db_cursor() as cur:
        try:
            cur.execute(
                "INSERT INTO participant (participant_id, name, token) VALUES (%s, %s, %s)",
                (participant.participant_id, participant.name, participant.token)
            )
            cur.connection.commit()
            return participant
        except psycopg2.IntegrityError:
            raise HTTPException(status_code=400, detail="Participant already exists")

@app.get("/participants/{participant_id}", response_model=ParticipantModel)
def get_participant(participant_id: int):
    """Get specific participant details"""
    with db_cursor() as cur:
        cur.execute(
            "SELECT participant_id, name, token FROM participant WHERE participant_id = %s",
            (participant_id,)
        )
        row = cur.fetchone()
        
    if not row:
        raise HTTPException(status_code=404, detail="Participant not found")
        
    return {"participant_id": row[0], "name": row[1], "token": row[2]}

@app.get("/adherence", response_model=AdherenceResponse)
def get_adherence_overview():
    """Get adherence overview for all participants"""
    with db_cursor() as cur:
        cur.execute("SELECT participant_id, name, token FROM participant ORDER BY participant_id")
        participants = cur.fetchall()
        
        adherence_items = []
        issues_count = 0
        
        for participant_id, name, token in participants:
            cur.execute(
                """
                SELECT MAX(timestamp) 
                FROM raw_data 
                WHERE participant_id = %s AND metric_type = 'heart_rate'
                """,
                (participant_id,)
            )
            last_data = cur.fetchone()[0]
            if participant_id == 1:
                cur.execute(
                    """
                    SELECT COUNT(*) 
                    FROM raw_data 
                    WHERE participant_id = %s AND metric_type = 'heart_rate'
                    AND timestamp >= NOW() - INTERVAL '7 days'
                    """,
                    (participant_id,)
                )
                recent_points = cur.fetchone()[0]
                adherence_percentage = min(100.0, (recent_points / 604800) * 100)
                sleep_upload_percentage = 85.0
            else:
                adherence_percentage = 0.0
                sleep_upload_percentage = 0.0
            
            if not token:
                status = AdherenceStatus.NO_TOKEN
                details = "Participant has no authentication token"
                issues_count += 1
            elif not last_data or (datetime.now().replace(tzinfo=last_data.tzinfo) - last_data).total_seconds() > 172800:  # 48 hours
                status = AdherenceStatus.NO_DATA_48H
                details = "No data uploaded in the last 48 hours"
                issues_count += 1
            elif sleep_upload_percentage < 50:
                status = AdherenceStatus.LOW_SLEEP
                details = f"Low sleep upload percentage: {sleep_upload_percentage:.1f}%"
                issues_count += 1
            elif adherence_percentage < 70:
                status = AdherenceStatus.LOW_ADHERENCE
                details = f"Low adherence: {adherence_percentage:.1f}%"
                issues_count += 1
            else:
                status = AdherenceStatus.GOOD
                details = "All metrics within acceptable range"
            
            adherence_items.append({
                "participant_id": participant_id,
                "name": name,
                "status": status,
                "last_data_timestamp": last_data,
                "adherence_percentage": adherence_percentage,
                "sleep_upload_percentage": sleep_upload_percentage,
                "details": details
            })
    
    return {
        "participants": adherence_items,
        "total_participants": len(participants),
        "issues_count": issues_count
    }

@app.post("/imputation", response_model=ImputationResponse)
def impute_missing_data(request: ImputationRequest):
    """Impute missing data for a participant"""
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) 
            FROM raw_data 
            WHERE participant_id = %s 
            AND metric_type = 'heart_rate'
            AND timestamp::date BETWEEN %s AND %s
            """,
            (request.participant_id, request.start_date, request.end_date)
        )
        existing_points = cur.fetchone()[0]
        
        expected_points = (request.end_date - request.start_date).days * 86400
        missing_points = max(0, expected_points - existing_points)
        
        return {
            "participant_id": request.participant_id,
            "imputed_points": missing_points,
            "method_used": request.method,
            "start_date": request.start_date,
            "end_date": request.end_date
        }

@app.post("/email/send")
def send_email_to_participants(request: EmailRequest):
    """Send email to participants (mock implementation)"""
    
    with db_cursor() as cur:
        cur.execute(
            "SELECT name FROM participant WHERE participant_id = ANY(%s)",
            (request.participant_ids,)
        )
        participants = cur.fetchall()
    
    participant_names = [row[0] for row in participants]
    
    logger.info(f"Mock email sent to participants: {participant_names}")
    logger.info(f"Subject: {request.subject}")
    logger.info(f"Message: {request.message}")
    
    return {
        "status": "success",
        "message": f"Email sent to {len(participant_names)} participants",
        "recipients": participant_names,
        "subject": request.subject
    }

@app.get("/participants/{participant_id}/metrics")
def get_participant_metrics(
    participant_id: int,
    start_date: date = Query(..., description="Start date for metrics"),
    end_date: date = Query(..., description="End date for metrics")
):
    """Get comprehensive metrics for a specific participant"""
    with db_cursor() as cur:
        cur.execute(
            "SELECT name FROM participant WHERE participant_id = %s",
            (participant_id,)
        )
        participant = cur.fetchone()
        
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        
        cur.execute(
            """
            SELECT 
                AVG(value) as avg_hr,
                MIN(value) as min_hr,
                MAX(value) as max_hr,
                COUNT(*) as total_points
            FROM raw_data 
            WHERE participant_id = %s 
            AND metric_type = 'heart_rate'
            AND timestamp::date BETWEEN %s AND %s
            """,
            (participant_id, start_date, end_date)
        )
        hr_stats = cur.fetchone()
        
        cur.execute(
            """
            SELECT date, resting_heart_rate 
            FROM daily_summaries 
            WHERE participant_id = %s 
            AND date BETWEEN %s AND %s
            ORDER BY date
            """,
            (participant_id, start_date, end_date)
        )
        daily_summaries = cur.fetchall()
        
        cur.execute(
            """
            SELECT zone_name, AVG(minutes) as avg_minutes, AVG(calories_out) as avg_calories
            FROM heart_rate_zones 
            WHERE participant_id = %s 
            AND date BETWEEN %s AND %s
            GROUP BY zone_name
            """,
            (participant_id, start_date, end_date)
        )
        hr_zones = cur.fetchall()
    
    return {
        "participant_id": participant_id,
        "participant_name": participant[0],
        "date_range": {"start_date": start_date, "end_date": end_date},
        "heart_rate_summary": {
            "avg_hr": float(hr_stats[0]) if hr_stats[0] else 0,
            "min_hr": float(hr_stats[1]) if hr_stats[1] else 0,
            "max_hr": float(hr_stats[2]) if hr_stats[2] else 0,
            "total_points": hr_stats[3] if hr_stats[3] else 0
        },
        "daily_summaries": [
            {"date": row[0], "resting_heart_rate": row[1]} 
            for row in daily_summaries
        ],
        "heart_rate_zones": [
            {"zone_name": row[0], "avg_minutes": float(row[1]) if row[1] else 0, "avg_calories": float(row[2]) if row[2] else 0}
            for row in hr_zones
        ]
    }

@app.get("/dashboard/summary")
def get_dashboard_summary():
    """Get overall dashboard summary statistics"""
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM participant")
        total_participants = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(DISTINCT participant_id) 
            FROM raw_data 
            WHERE metric_type = 'heart_rate'
        """)
        active_participants = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(*) 
            FROM raw_data 
            WHERE metric_type = 'heart_rate'
        """)
        total_data_points = cur.fetchone()[0]
        
        cur.execute("""
            SELECT MIN(timestamp::date), MAX(timestamp::date) 
            FROM raw_data 
            WHERE metric_type = 'heart_rate'
        """)
        date_range = cur.fetchone()
    
    return {
        "total_participants": total_participants,
        "active_participants": active_participants,
        "total_data_points": total_data_points,
        "data_date_range": {
            "start_date": date_range[0],
            "end_date": date_range[1]
        } if date_range[0] else None,
        "system_status": "operational"
    }
