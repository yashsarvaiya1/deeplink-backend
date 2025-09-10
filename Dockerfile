
FROM python:3.12-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --prefix=/install -r requirements.txt

FROM python:3.12-slim

RUN useradd --create-home --shell /bin/bash appuser
USER appuser

WORKDIR /app

COPY --from=builder /install /home/appuser/.local

ENV PATH=/home/appuser/.local/bin:$PATH

COPY --chown=appuser:appuser . .

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["fastapi", "run", "main.py"]
