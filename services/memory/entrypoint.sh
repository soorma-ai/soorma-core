#!/bin/sh
set -e

echo "Starting Memory Service..."
echo "Database URL: $DATABASE_URL"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the service
echo "Starting FastAPI application..."
exec uvicorn memory_service.main:app --host 0.0.0.0 --port 8002
