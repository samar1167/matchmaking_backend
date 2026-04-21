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

exec daphne \
    --bind 0.0.0.0 \
    --port 8000 \
    --access-log /app/matchmaking_project/logs/access.log \
    config.asgi:application
