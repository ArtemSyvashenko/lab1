FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir fastapi uvicorn pymysql cryptography responses Werkzeug

COPY app.py migrate.py ./

EXPOSE 3000

CMD ["python", "app.py", "--port", "3000"]
