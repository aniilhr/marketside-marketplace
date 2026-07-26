# Deployment guide

## Dependencies

`requirements.txt` is the SQLite/local set and needs no compiler or system libraries.
`requirements-postgres.txt` adds `psycopg2-binary` on top and is what Docker, CI and production
use. Install the second one whenever `USE_SQLITE=0`.

Pinned versions target **Python 3.12**. On 3.13 or 3.14 several packages have no prebuilt wheels
yet and pip will try to compile them from source.

## Environment variables

Backend (`backend/.env` locally, `backend/.env.docker` for compose, or host env vars):

| Variable | Default | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev key | Set a long random value in production |
| `DJANGO_DEBUG` | 1 | Must be 0 in production |
| `DJANGO_ALLOWED_HOSTS` | `*` | Comma-separated domains |
| `USE_SQLITE` | 1 | 0 to use PostgreSQL |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | marketplace | Postgres connection |
| `REDIS_URL` | redis://localhost:6379/0 | Celery broker and result backend |
| `CELERY_EAGER` | 1 | 1 runs tasks inline; 0 requires a worker |
| `ACCESS_TOKEN_MINUTES` | 60 | JWT access lifetime |
| `REFRESH_TOKEN_DAYS` | 7 | JWT refresh lifetime |
| `CORS_ALLOW_ALL` | 1 | 0 in production, then set `CORS_ALLOWED_ORIGINS` |
| `EMAIL_BACKEND` | console | Swap for SMTP to send real codes |
| `PLATFORM_COMMISSION_PERCENT` | 8 | Marketplace take rate per order line |
| `SEED_ON_START` | 1 | 0 in production |

Frontend (`frontend/.env`): `VITE_API_URL` — leave empty to use the Nginx/Vite proxy, or set the
absolute API URL when the API lives on another domain.

## Production checklist

- [ ] `DJANGO_DEBUG=0`, real `DJANGO_SECRET_KEY`, explicit `DJANGO_ALLOWED_HOSTS`
- [ ] `CORS_ALLOW_ALL=0` with an explicit origin list
- [ ] PostgreSQL with automated backups (`pg_dump` on a schedule)
- [ ] `SEED_ON_START=0`, then `createsuperuser` for your real admin
- [ ] SMTP configured so verification and reset codes actually arrive
- [ ] Real payment keys wired into the checkout service before taking money
- [ ] TLS terminated by a reverse proxy; HSTS is already on when `DEBUG=0`
- [ ] Celery worker running if `CELERY_EAGER=0`
- [ ] Log aggregation and an uptime check against `/api/health/`

## Single VPS with Docker

```bash
git clone <your-repo> && cd marketplace
cp backend/.env.docker backend/.env.docker.local   # edit secrets
docker compose up -d --build
docker compose exec backend python manage.py createsuperuser
```

Put Caddy in front for automatic HTTPS:

```
yourdomain.com {
    reverse_proxy localhost:3000
}
```

## Platform-as-a-service

**Render / Railway** — deploy `backend/` as a web service (`gunicorn config.wsgi:application
--bind 0.0.0.0:$PORT`), attach managed Postgres and Redis, set the env vars above, and run
`python manage.py migrate` as the release command. Deploy `frontend/` as a static site with build
command `npm run build`, publish directory `dist`, and `VITE_API_URL` pointing at the backend URL.

**Fly.io** — `fly launch` in `backend/`, `fly postgres create`, `fly redis create`, then
`fly deploy`. The included Dockerfile works unchanged.

## Scaling notes

Gunicorn runs 3 workers by default; raise it to `2 × cores + 1`. Product list queries already use
`select_related`, and hot paths are indexed. When traffic grows, cache the catalog list responses
in Redis, move media to S3 with `django-storages`, and split Celery into separate queues for email
and reports.
