# Deterministic build for Railway (or any Docker host).
# Railway automatically detects and prefers a Dockerfile over Nixpacks
# when one exists in the repo root, so this sidesteps any auto-detection
# or root-directory ambiguity that caused the ModuleNotFoundError.

FROM python:3.11-slim

# tesseract-ocr: system binary needed for the /ocr command
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching on rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project — this explicitly includes handlers/, utils/,
# utils/tools/, and everything else, regardless of any ignore-file or
# root-directory misconfiguration.
COPY . .

# Sanity check at build time: fail the BUILD loudly if handlers/ is
# somehow missing, instead of failing later at runtime with a vague
# ModuleNotFoundError deep in Railway's restart loop.
RUN test -f handlers/__init__.py || (echo "ERROR: handlers/ folder is missing from the build context!" && exit 1)
RUN test -f utils/__init__.py || (echo "ERROR: utils/ folder is missing from the build context!" && exit 1)

CMD ["python", "main.py"]
