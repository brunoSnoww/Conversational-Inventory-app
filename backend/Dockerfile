FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt backend/requirements-api.txt backend/requirements-ai.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY sql/ ./sql/

EXPOSE 8000

# Prod default — docker-compose.yml overrides with runserver for local dev.
CMD [
  "uvicorn", "app.main:app",
  "--host", "0.0.0.0",
  "--port", "8000",
]
