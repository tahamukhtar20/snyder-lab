CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE IF NOT EXISTS raw_data (
    participant_id INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (participant_id, timestamp, metric_type)
);

SELECT create_hypertable('raw_data', 'timestamp', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS daily_summaries (
    participant_id INTEGER NOT NULL,
    date DATE NOT NULL,
    resting_heart_rate INTEGER,
    dataset_interval INTEGER,
    dataset_type VARCHAR(50),
    PRIMARY KEY (participant_id, date)
);

CREATE TABLE IF NOT EXISTS heart_rate_zones (
    participant_id INTEGER NOT NULL,
    date DATE NOT NULL,
    zone_name VARCHAR(50) NOT NULL,
    min_heart_rate INTEGER,
    max_heart_rate INTEGER,
    minutes INTEGER,
    calories_out DOUBLE PRECISION,
    PRIMARY KEY (participant_id, date, zone_name)
);
