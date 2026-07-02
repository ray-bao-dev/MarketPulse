FROM python:3.12-slim-bookworm

WORKDIR /app

# Default `pip install torch` pulls CUDA libs (~2GB). Railway trains on CPU only.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY trainer/requirements.txt ./trainer/requirements.txt
RUN pip install --no-cache-dir -r trainer/requirements.txt

COPY backend/marketpulse ./marketpulse
COPY classifier ./classifier
COPY trainer ./trainer

ENV PYTHONPATH=/app:/app/classifier
ENV ARTIFACTS_DIR=/app/artifacts

WORKDIR /app/trainer
CMD ["python", "run.py"]
