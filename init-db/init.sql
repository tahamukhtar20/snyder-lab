CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

CREATE TABLE IF NOT EXISTS raw_data (
    participant_id INTEGER NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    metric_type TEXT NOT NULL,
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

CREATE MATERIALIZED VIEW hr_1m
WITH (timescaledb.continuous) AS
SELECT
  participant_id,
  time_bucket('1 minute', timestamp) AS bucket,
  avg(value) AS avg_hr,
  min(value) AS min_hr,
  max(value) AS max_hr
FROM raw_data
WHERE metric_type = 'heart_rate'
GROUP BY participant_id, bucket;

CREATE MATERIALIZED VIEW hr_1h
WITH (timescaledb.continuous) AS
SELECT
  participant_id,
  time_bucket('1 hour', bucket) AS bucket,
  avg(avg_hr) AS avg_hr,
  min(min_hr) AS min_hr,
  max(max_hr) AS max_hr
FROM hr_1m
GROUP BY participant_id, time_bucket('1 hour', bucket);

CREATE MATERIALIZED VIEW hr_1d
WITH (timescaledb.continuous) AS
SELECT
  participant_id,
  time_bucket('1 day', bucket) AS bucket,
  avg(avg_hr) AS avg_hr,
  min(min_hr) AS min_hr,
  max(max_hr) AS max_hr
FROM hr_1h
GROUP BY participant_id, time_bucket('1 day', bucket);

SELECT add_continuous_aggregate_policy(
  'hr_1m',
  start_offset => INTERVAL '1000 days',
  end_offset   => INTERVAL '5 minutes',
  schedule_interval => INTERVAL '5 minutes');

SELECT add_continuous_aggregate_policy(
  'hr_1h',
  start_offset => INTERVAL '1000 days',
  end_offset   => INTERVAL '2 hours',
  schedule_interval => INTERVAL '5 minutes');

SELECT add_continuous_aggregate_policy(
  'hr_1d',
  start_offset => INTERVAL '1000 days',
  end_offset   => INTERVAL '1 day',
  schedule_interval => INTERVAL '5 minutes');

ALTER TABLE raw_data SET (timescaledb.compress,
                          timescaledb.compress_segmentby = 'participant_id');
SELECT add_compression_policy('raw_data', INTERVAL '30 days');

ALTER MATERIALIZED VIEW hr_1m SET (timescaledb.compress,
                                   timescaledb.compress_segmentby = 'participant_id');
SELECT add_compression_policy('hr_1m', INTERVAL '14 days');

ALTER MATERIALIZED VIEW hr_1h SET (timescaledb.compress,
                                   timescaledb.compress_segmentby = 'participant_id');
SELECT add_compression_policy('hr_1h', INTERVAL '90 days');

CREATE INDEX raw_data_pid_time_idx
  ON raw_data (participant_id, timestamp DESC);

SET timescaledb.enable_chunk_skipping = on;
SELECT enable_chunk_skipping('raw_data', 'participant_id');

CREATE TABLE IF NOT EXISTS participant (
    participant_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    token TEXT UNIQUE
);

