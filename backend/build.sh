#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing Python dependencies from backend root..."
pip install -r requirements.txt

echo "Running database migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Build completed successfully!"
