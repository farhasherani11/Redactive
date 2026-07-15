# Redactive — production Dockerfile
# Builds the FastAPI app with all three guard layers, including the spaCy
# model (downloaded at build time so it's baked into the image, not
# fetched on every container start).

FROM python:3.11-slim

WORKDIR /app

# System deps needed to build a couple of Python packages with native
# extensions (spaCy's dependencies). Kept minimal deliberately — this is
# a slim base image, not a full dev environment.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first, separately from app code, so Docker
# can cache this layer and skip reinstalling packages on every code change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the spaCy model at build time — bakes it into the image so
# the container doesn't need network access to fetch it on startup.
RUN python -m spacy download en_core_web_sm

# Now copy the actual application code.
COPY app ./app

# Render (and most platforms) inject the port to bind via $PORT.
# Default to 8000 for local Docker testing where $PORT isn't set.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]