# Built from `pip install rasa` rather than FROM rasa/rasa:<tag>.
#
# Rasa's own pre-built Docker Hub images have moved around as the company
# has shifted focus toward its commercial "Rasa Pro" product, so pinning
# to a specific external image tag here would risk the build breaking
# without warning. Installing the open-source `rasa` package by version
# number is the more stable, reproducible choice for coursework that
# needs to still build correctly at marking time.
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Pin the exact version you tested against - update this and re-build if
# you upgrade locally, so the container matches what you developed with.
RUN pip install --no-cache-dir rasa==3.6.20

COPY . .

EXPOSE 5005

# Trains a model on container start (first boot only takes a while - the
# trained model is cached at /app/models for subsequent restarts), then
# serves it with the REST/webhook channels enabled and CORS open so the
# static frontend (served from a different origin) can call it directly.
CMD ["sh", "-c", "rasa train --fixed-model-name eco-travel-model && rasa run --enable-api --cors '*' --port 5005"]
