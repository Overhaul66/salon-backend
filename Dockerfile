FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Collect static files (WhiteNoise serves them in production)
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run migrations, seed the service catalog, then start the web server
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_catalog && python manage.py seed_data  && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120"]
