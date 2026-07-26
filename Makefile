.PHONY: install backend frontend seed test build up down logs

install:
	cd backend && pip install -r requirements.txt   # SQLite dev; use requirements-postgres.txt for Postgres
	cd frontend && npm install

backend:
	cd backend && python manage.py runserver 8000

frontend:
	cd frontend && npm run dev

seed:
	cd backend && python manage.py migrate && python manage.py seed

test:
	cd backend && python manage.py test

build:
	cd frontend && npm run build

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f backend
