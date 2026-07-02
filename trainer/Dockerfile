FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libta-lib0 \
    libta-lib0-dev \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY trainer/requirements.txt ./trainer/requirements.txt
RUN pip install --no-cache-dir -r trainer/requirements.txt

COPY classifier ./classifier
COPY trainer ./trainer

ENV PYTHONPATH=/app:/app/classifier
ENV ARTIFACTS_DIR=/app/artifacts

WORKDIR /app/trainer
CMD ["python", "run.py"]
