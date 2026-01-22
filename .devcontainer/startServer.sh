#!/usr/bin/env bash

# Kill any existing Django server on port 8000
pkill -f "manage.py runserver" 2>/dev/null || true

# Start Django server in background
echo "Starting Django server on port 8000..."
python manage.py runserver 0.0.0.0:8000 &

# Wait a moment for server to start
sleep 2

echo "✅ Django server is running at http://localhost:8000"
echo "   View logs: tail -f /tmp/django.log"
