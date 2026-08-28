web: python manage.py migrate --noinput && python manage.py seed_catalog && gunicorn config.wsgi:application --workers 2 --timeout 120
