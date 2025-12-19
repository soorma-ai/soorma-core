#!/bin/sh
set -e

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting registry service..."
exec uvicorn registry_service.main:app --host 0.0.0.0 --port 8000
