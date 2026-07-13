FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
COPY data/processed_runtime_data.csv /app/data/processed_runtime_data.csv
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

ENV DASH_URL_PREFIX=/

CMD ["python", "app.py"]

EXPOSE 8050
