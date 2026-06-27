FROM python:3.11-slim

WORKDIR /app

COPY src/requirements.txt .
COPY data/ /data/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY src/ .

EXPOSE 8050

CMD ["python", "app.py"]
