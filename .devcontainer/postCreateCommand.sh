#!/usr/bin/env bash
set -e

python -m pip install --upgrade pip

pip install -r requirements.txt

if [ -f requirements-dev.txt ]; then
  pip install -r requirements-dev.txt
fi

python manage.py migrate --noinput

# Make start script executable
chmod +x .devcontainer/startServer.sh

echo "✅ BGHI7 setup complete. Django server will start automatically."
