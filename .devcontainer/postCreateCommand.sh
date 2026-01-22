#!/usr/bin/env bash
set -e

python -m pip install --upgrade pip

pip install -r requirements.txt

if [ -f requirements-dev.txt ]; then
  pip install -r requirements-dev.txt
fi

python manage.py migrate --noinput

# Copy VS Code tasks for auto-start
mkdir -p .vscode
cp .devcontainer/tasks.json .vscode/tasks.json

echo "BGHI7 is ready. The Django server will start automatically."
