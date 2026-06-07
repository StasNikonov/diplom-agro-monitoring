FROM python:3.12-slim

WORKDIR /app

# libgdal-dev needed if rasterio builds from source (no binary wheel for platform)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ libpq-dev libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

COPY worker/requirements.txt requirements.txt
# --prefer-binary: use pre-built wheel if available; fall back to source build with system GDAL
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Shared backend app code (models, config, database)
COPY backend/app /app/app

# Worker entrypoint and tasks
COPY worker/worker.py worker.py
COPY worker/tasks /app/tasks

ENV PYTHONPATH=/app

CMD ["python", "worker.py"]
