FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md requirements.txt cli.py ./
COPY src ./src
COPY .env.example ./

RUN pip install --upgrade pip && pip install .
RUN chmod +x /app/cli.py && ln -sf /app/cli.py /usr/local/bin/cli.py

RUN mkdir -p /app/data /app/storage

EXPOSE 8000

CMD ["sh", "-c", "python -m maria_rag_agent.cli init-db && uvicorn maria_rag_agent.api:app --host 0.0.0.0 --port ${API_PORT:-8000}"]
