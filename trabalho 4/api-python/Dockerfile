FROM       python:3.12-slim

ENV        REDIS_URL="redis://localhost:6379" \
           CACHE="on"

WORKDIR    /app
COPY       requirements.txt /app/
RUN        pip install --no-cache-dir -r requirements.txt

COPY       *.py /app/
EXPOSE     5000

CMD        ["python", "main.py"]
