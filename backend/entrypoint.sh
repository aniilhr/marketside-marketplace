#!/usr/bin/env bash
set -e

if [ "${USE_SQLITE:-0}" != "1" ]; then
  echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
  until python -c "
import os, socket, sys
s = socket.socket()
s.settimeout(2)
try:
    s.connect((os.getenv('POSTGRES_HOST', 'db'), int(os.getenv('POSTGRES_PORT', '5432'))))
except Exception:
    sys.exit(1)
"; do
    sleep 1
  done
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${SEED_ON_START:-1}" = "1" ]; then
  python manage.py seed
fi

exec "$@"
