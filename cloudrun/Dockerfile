# Builder
FROM python:3.11-slim AS builder
WORKDIR /wheels
COPY backend/requirements.txt .
RUN python -m pip wheel --wheel-dir . -r requirements.txt

# Final
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /wheels /wheels
COPY backend/requirements.txt .
RUN python -m pip install --upgrade pip \
  && pip install --no-index --find-links /wheels -r requirements.txt

# flatten the backend so auth.py & main.py live at /app
COPY backend/ .  
COPY frontend/ ./frontend

# Copy the firebase service account key
# This is a secret, so don't include it in the repo
COPY firebase-service-account-key.json /app/firebase-service-account-key.json

ENV PORT=8080
EXPOSE 8080
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8080"]
