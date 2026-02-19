# Use a stable Python 3.12 image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies for psycopg2 and Pillow
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Run build steps
RUN python manage.py collectstatic --no-input

# Expose port (Cloud Run uses 8080 by default)
EXPOSE 8080

# Start Gunicorn
CMD ["gunicorn", "--bind", ":8080", "--workers", "2", "core.wsgi:application"]