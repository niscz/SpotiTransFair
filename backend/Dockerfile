# =========================================================================
# STUFE 1: Builder-Umgebung
# =========================================================================
FROM python:3.12-slim AS builder

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =========================================================================
# STUFE 2: Produktions-Umgebung
# =========================================================================
FROM python:3.12-slim AS production

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies for psycopg2 if needed (usually fine with binary)
# RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
