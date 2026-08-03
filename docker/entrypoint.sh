#!/bin/sh
set -e

echo "Running entrypoint for command: $@"

if [ "$SKIP_MIGRATIONS" != "1" ]; then
  echo "Waiting for database..."
  python - <<'PY'
import os, time, sys
import psycopg2

db_host = os.getenv("DB_HOST", "db")
db_port = int(os.getenv("DB_PORT", "5432"))
db_name = os.getenv("DB_NAME", "rentease")
db_user = os.getenv("DB_USER", "rentease")
db_pass = os.getenv("DB_PASSWORD", "rentease")

for attempt in range(30):
    try:
        conn = psycopg2.connect(
            host=db_host, port=db_port,
            dbname=db_name, user=db_user, password=db_pass,
            connect_timeout=3,
        )
        conn.close()
        print("Database is ready.")
        break
    except Exception as e:
        print(f"Waiting for DB ({attempt + 1}/30): {e}")
        time.sleep(2)
else:
    print("Database not reachable after 60s.", file=sys.stderr)
    sys.exit(1)
PY

  echo "Running migrations..."
  python manage.py migrate --noinput

  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

exec "$@"
