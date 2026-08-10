FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN echo "--- Contents of /app ---" && ls -la /app && \
    echo "--- Contents of /app/handlers ---" && (ls -la /app/handlers || echo "handlers/ DOES NOT EXIST") && \
    echo "--- Contents of /app/utils ---" && (ls -la /app/utils || echo "utils/ DOES NOT EXIST")

RUN test -f handlers/menu.py || (echo "ERROR: handlers/menu.py is missing!" && exit 1)
RUN test -f handlers/router.py || (echo "ERROR: handlers/router.py is missing!" && exit 1)
RUN test -f utils/decorators.py || (echo "ERROR: utils/decorators.py is missing!" && exit 1)

CMD ["python", "main.py"]
