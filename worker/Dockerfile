FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/marketpulse ./marketpulse
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY worker/run.py ./run.py

ENV PYTHONPATH=/app

CMD ["sh", "-c", "alembic upgrade head && python run.py"]
