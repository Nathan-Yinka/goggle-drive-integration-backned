#!/bin/sh

# Apply migrations
echo "Applying database migrations..."
alembic upgrade head

# Start the application
echo "Starting the application..."
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT
