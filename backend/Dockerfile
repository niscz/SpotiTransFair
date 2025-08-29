# =========================================================================
# STUFE 1: Builder-Umgebung
# =========================================================================
FROM python:3.13-slim AS builder

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =========================================================================
# STUFE 2: Produktions-Umgebung
# =========================================================================
FROM python:3.13-slim AS production

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

ENV PATH="/opt/venv/bin:$PATH"

RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

# Starte die Anwendung mit Gunicorn, das den Uvicorn-Worker verwaltet.
CMD ["gunicorn", "--config", "config/gunicorn.conf.py", "main:app"]
