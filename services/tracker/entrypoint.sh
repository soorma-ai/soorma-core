#!/bin/sh
set -e

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting tracker service..."
exec uvicorn tracker_service.main:app --host 0.0.0.0 --port 8084
