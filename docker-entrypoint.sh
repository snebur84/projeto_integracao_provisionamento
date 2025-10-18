#!/bin/sh
set -e

# Helper: try to connect to TCP host:port using python (more portable than netcat)
wait_for_tcp() {
  host="$1"
  port="$2"
  timeout="${3:-60}"
  start_ts=$(date +%s)
  echo "Waiting for $host:$port (timeout ${timeout}s)..."
  while true; do
    python - <<PYTHON
import socket, sys
s = socket.socket()
try:
    s.settimeout(1.0)
    s.connect(("${host}", ${port}))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PYTHON
    rc=$?
    if [ "$rc" -eq 0 ]; then
      echo "$host:$port is available"
      break
    fi
    now=$(date +%s)
    elapsed=$((now - start_ts))
    if [ "$elapsed" -ge "$timeout" ]; then
      echo "Timeout waiting for ${host}:${port}"
      exit 1
    fi
    sleep 1
  done
}

# Default hosts/ports used in settings
DB_HOST="${MYSQL_HOST:-db}"
DB_PORT="${MYSQL_PORT:-3306}"
MONGO_HOST="${MONGODB_HOST:-mongo}"
MONGO_PORT="${MONGODB_PORT:-27017}"

# Wait for database(s)
wait_for_tcp "$DB_HOST" "$DB_PORT" 120
wait_for_tcp "$MONGO_HOST" "$MONGO_PORT" 120

# Ensure Django settings module is available (set by compose)
if [ -z "$DJANGO_SETTINGS_MODULE" ]; then
  echo "DJANGO_SETTINGS_MODULE not set; defaulting to provision.settings_docker"
  export DJANGO_SETTINGS_MODULE=provision.settings_docker
fi

# Run migrations, collectstatic and create superuser if env provided
echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if requested (script checks env vars)
echo "Creating superuser (if DJANGO_SUPERUSER_USERNAME/DJANGO_SUPERUSER_PASSWORD provided)..."
python /app/scripts/create_superuser.py || true

# Finally exec the given CMD (gunicorn)
echo "Starting server..."
exec "$@"