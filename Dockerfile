FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/logs/ingestion /app/data

RUN echo "0 1 * * * cd /app && python3 ingestion.py >> /app/logs/ingestion/cron.log 2>&1" > /etc/cron.d/fitbit-ingestion

RUN chmod 0644 /etc/cron.d/fitbit-ingestion
RUN crontab /etc/cron.d/fitbit-ingestion

RUN touch /app/logs/ingestion/cron.log

RUN echo '#!/bin/bash\n\
echo "Starting cron service..."\n\
echo "Running initial ingestion..."\n\
cd /app && python ingestion.py\n\
echo "Initial ingestion completed"\n\
cron -f' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]