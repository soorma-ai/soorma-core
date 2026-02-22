#!/bin/bash
set -e

echo "Tracker Service Entrypoint - Starting database migration check..."

# Wait for database to be ready
echo "Waiting for PostgreSQL to be ready..."
until python -c "import psycopg2; psycopg2.connect('$SYNC_DATABASE_URL' if '$SYNC_DATABASE_URL' else '$DATABASE_URL'.replace('+asyncpg', '+psycopg2'))" 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is ready!"

# Run migrations
echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting Tracker Service..."
exec uvicorn tracker_service.main:app --host 0.0.0.0 --port 8084
