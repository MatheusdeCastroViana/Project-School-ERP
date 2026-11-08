#!/usr/bin/env bash
set -o errexit # parar no primeiro erro

pip install -r requirements.txt
python manage.py collectstatic --no-input # copia os estáticos para a pasta staticfiles/
python manage.py migrate