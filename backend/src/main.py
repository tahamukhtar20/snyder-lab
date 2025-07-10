from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date, datetime
import os
import psycopg2
from dotenv import load_dotenv
from typing import List, Optional

load_dotenv()

def get_db_conn():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

app = FastAPI(title="Metrics API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RawDataItem(BaseModel):
    participant_id: int
    timestamp: datetime
    metric_type: str
    value: float

@app.get("/data", response_model=List[RawDataItem])
def get_raw_data(
    metric: str = Query("heart_rate", description="Metric type to filter by"),
    start_date: date = Query(..., description="Start date (inclusive)") ,
    end_date: date = Query(..., description="End date (inclusive)"),
    user_id: Optional[int] = Query(1, description="Participant ID")
):
    """
    Fetch raw heart-rate data between start_date and end_date for a participant.
    """
    conn = get_db_conn()
    if metric != "heart_rate":
        raise HTTPException(status_code=400, detail="Unsupported metric type. Only 'heart_rate' is supported.")
    try:
        cur = conn.cursor()
        cur.execute(
            '''
            SELECT participant_id, timestamp, metric_type, value
            FROM raw_data
            WHERE participant_id = %s
              AND timestamp::date BETWEEN %s AND %s
            ORDER BY timestamp
            ''',
            (user_id, start_date, end_date)
        )
        rows = cur.fetchall()
        return [RawDataItem(
            participant_id=row[0],
            timestamp=row[1],
            metric_type=row[2],
            value=row[3]
        ) for row in rows]
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()


@app.get("/status")
def health_check():
    """Simple health check."""
    try:
        conn = get_db_conn()
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
