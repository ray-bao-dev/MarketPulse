FROM python:3.12-slim

WORKDIR /app

COPY classifier/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/marketpulse ./marketpulse
COPY classifier/classifier ./classifier
COPY classifier/models ./models
COPY classifier/run.py ./run.py

ENV PYTHONPATH=/app
ENV MODEL_DIR=/app/models
ENV MANIFEST_PATH=/app/models/manifest.json

CMD ["python", "run.py"]
