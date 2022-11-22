#!/bin/bash

# Set FLASK_ENV to "production" if not set or null
FLASK_ENV="${FLASK_ENV:=production}"

if [ "$FLASK_ENV" = "development" ]; then
  python -m flask run --host=0.0.0.0 --port=8000
elif [ "$FLASK_ENV" = "production" ]; then
  gunicorn --chdir /app/src "app:create_app()" -w 2 --threads 2 -b 0.0.0.0:8000
fi
