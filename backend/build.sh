#!/usr/bin/env bash
# Render build command. Runs on every deploy, before the service starts.
set -o errexit

pip install --upgrade pip
pip install -r requirements-postgres.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Loads demo products and the five demo accounts. Delete this line
# once you have real data, or it will run on every single deploy.
python manage.py seed