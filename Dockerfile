FROM python:3.10-slim

WORKDIR /app
COPY ./requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY ./football_tracking_be .

ENV PORT=8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
