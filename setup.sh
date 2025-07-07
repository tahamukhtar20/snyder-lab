#!/bin/bash

echo "Starting Stanford Snyder Lab Challenge"

if [ ! -f .env ]; then
    echo ".env file not found! Please create a .env file with the required environment variables."
    exit 1
fi

echo "Task 0.b: Data Extraction"
pip install -r requirements.txt --quiet
if [ -d "data" ]; then
    echo "Data folder already exists. Skipping data extraction."
else
    echo "Data folder not found. Running data extraction..."
    mkdir -p data
    python -m misc.extract_data
fi

echo "Task 1: Ingestion"

if ! command -v docker &> /dev/null || ! command -v docker-compose &> /dev/null; then
    echo "Docker and Docker Compose are required but not installed. Please install them and try again."
    exit 1
fi

echo "Stopping any existing containers..."
docker-compose down

echo "Building and starting services..."
docker-compose up -d --build

echo "Waiting for TimescaleDB to be ready..."
sleep 10

max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker-compose exec -T timescaledb pg_isready -U ${DB_USER:-postgres} -d ${DB_NAME:-fitbit_db} > /dev/null 2>&1; then
        echo "TimescaleDB is ready!"
        break
    fi
    echo "Waiting for TimescaleDB... attempt $((attempt + 1)) of $max_attempts"
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
    echo "TimescaleDB failed to start within expected time."
    exit 1
fi

echo "Running initial ingestion"
docker-compose exec -T ingestion python ingestion.py

echo "Container status:"
docker-compose ps
