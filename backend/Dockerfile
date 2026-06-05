FROM python:3.11-slim

WORKDIR /app

# System deps for HiGHS (the solver bundles a .so; just need libstdc++)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Engine source
COPY engine/ engine/

# Price data cache (bundled so no live API fetches in the container)
COPY engine/data/cache/ engine/data/cache/

# FastAPI app
COPY backend/main.py .

# Hugging Face Spaces expects port 7860
ENV PORT=7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
