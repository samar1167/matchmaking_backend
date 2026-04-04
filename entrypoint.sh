#!/bin/bash
set -e

echo "Waiting for MySQL..."
until python -c "
import MySQLdb
MySQLdb.connect(host='${DB_HOST}', user='${DB_USER}', passwd='${DB_PASSWORD}', db='${DB_NAME}')
" 2>/dev/null; do
  echo "MySQL not ready — retrying in 2s..."
  sleep 2
done

echo "MySQL ready."

cd /app/matchmaking_project

mkdir -p /app/matchmaking_project/logs

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile /app/matchmaking_project/logs/access.log \
    --error-logfile /app/matchmaking_project/logs/error.log