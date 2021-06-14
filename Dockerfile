FROM python:3.9-slim

RUN apt-get update \
  && apt-get install -y gnupg2 build-essential

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN pip install -e /app/module