FROM python:3.11-slim

WORKDIR /app

COPY app.py .
COPY page_list ./page_list
COPY schema ./schema
COPY utils ./utils
COPY requirements.txt ./
COPY .env.docker ./.env

RUN pip install --no-cache-dir -r requirements.txt

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]

EXPOSE 8501