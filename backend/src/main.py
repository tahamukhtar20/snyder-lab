from fastapi import FastAPI, HTTPException, Query
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

app = FastAPI(title="Metrics API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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