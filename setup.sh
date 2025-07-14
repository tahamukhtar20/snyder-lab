#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <task_number>"
    echo "Please provide a task number (0, 1, 2 etc) to run the respective task."
    echo "0: Data Extraction"
    echo "1: Ingestion"
    echo "2: Access"
    echo "3: Optimization"
    echo "4: Analysis Dashboard"
    echo "Example: $0 1"
    exit 1
fi
if [ "$1" == "0" ]; then
    echo "Task 0.b: Data Extraction"
    pip install -r requirements.txt --quiet
    if [ -d "data" ]; then
        echo "Data folder already exists. Skipping data extraction."
    else
        echo "Data folder not found. Running data extraction..."
        mkdir -p data
        python -m misc.create_data
        echo "Data extraction completed."
    fi
elif [ "$1" == "1" ]; then
    echo "Task 1: Ingestion"

    if [ ! -f .env ]; then
        echo ".env file not found! Please create a .env file with the required environment variables."
        exit 1
    fi

    pip install -r requirements.txt --quiet
    if [ -d "data" ]; then
        echo "Data folder already exists. Skipping data extraction."
    else
        echo "Data folder not found. Running data extraction..."
        mkdir -p data
        python -m misc.extract_data
    fi

    if ! command -v docker &> /dev/null || ! command -v docker-compose &> /dev/null; then
        echo "Docker and Docker Compose are required but not installed. Please install them and try again."
        exit 1
    fi

    echo "Stopping any existing containers..."
    docker-compose down -v

    echo "Building and starting services..."
    docker-compose up -d --build ingestion timescaledb

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

elif [ "$1" == "2" ] || [ "$1" == "3" ]; then
    if [ "$1" == "2" ]; then
        echo "Task 2: Access"
    elif [ "$1" == "3" ]; then
        echo "Task 3: Optimization"
    else
        echo "Invalid task number. Please use 2 for Access or 3 for Optimization."
        exit 1
    fi
    if [ ! -f .env ]; then
        echo ".env file not found! Please create a .env file with the required environment variables."
        exit 1
    fi

    pip install -r requirements.txt --quiet
    if [ -d "data" ]; then
        echo "Data folder already exists. Skipping data extraction."
    else
        echo "Data folder not found. Running data extraction..."
        mkdir -p data
        python -m misc.extract_data
    fi

    if ! command -v docker &> /dev/null || ! command -v docker-compose &> /dev/null; then
        echo "Docker and Docker Compose are required but not installed. Please install them and try again."
        exit 1
    fi

    echo "Running ingestion for 30 days of data"

    docker-compose down -v
    docker-compose rm -f
    docker-compose build --no-cache
    docker-compose up -d --build ingestion timescaledb frontend backend

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

    docker-compose exec -T ingestion python ingestion.py --days 30

    echo "Container status:"
    docker-compose ps

elif [ "$1" == "4" ]; then
    echo "Task 4: Analysis Dashboard"

    if [ ! -f .env ]; then
        echo ".env file not found! Please create a .env file with the required environment variables."
        exit 1
    fi

    pip install -r requirements.txt --quiet
    if [ -d "data" ]; then
        echo "Data folder already exists. Skipping data extraction."
    else
        echo "Data folder not found. Running data extraction..."
        mkdir -p data
        python -m misc.extract_data
    fi

    if ! command -v docker &> /dev/null || ! command -v docker-compose &> /dev/null; then
        echo "Docker and Docker Compose are required but not installed. Please install them and try again."
        exit 1
    fi

    echo "Running ingestion for 30 days of data"

    docker-compose down -v
    docker-compose rm -f
    docker-compose build --no-cache
    docker-compose up -d --build ingestion timescaledb frontend backend

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

    docker-compose exec -T ingestion python users.py

    docker-compose exec -T ingestion python ingestion.py --days 30

    echo "Container status:"
    docker-compose ps

else
  echo "Invalid argument, please use one of the following to run their respective tasks:"
    echo "0: Data Extraction"
    echo "1: Ingestion"
    echo "2: Access"
    echo "3: Optimization"
    echo "4: Analysis Dashboard"
    exit 1
fi
