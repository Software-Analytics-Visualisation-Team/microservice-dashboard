FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
COPY data/inputs.csv /app/data/inputs.csv
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8050

CMD ["python", "app.py"]
