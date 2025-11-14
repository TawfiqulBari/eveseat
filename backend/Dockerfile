FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    ipython \
    ipdb

# Copy application code
COPY . .

# Expose port
EXPOSE 8000 8001 5555

FROM base as production

# Copy application code
COPY . .

# Expose port
EXPOSE 8000 8001 5555

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

