FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY classifier ./classifier
COPY models ./models
COPY run.py ./run.py

ENV PYTHONPATH=/app
ENV MANIFEST_PATH=/app/models/manifest.json

CMD ["python", "run.py"]
