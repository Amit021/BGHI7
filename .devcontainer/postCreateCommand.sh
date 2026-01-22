#!/usr/bin/env bash
set -e

python -m pip install --upgrade pip

pip install -r requirements.txt

if [ -f requirements-dev.txt ]; then
  pip install -r requirements-dev.txt
fi

python manage.py migrate --noinput

echo "BGHI7 is ready. Run:"
echo "  python manage.py runserver 0.0.0.0:8000"
