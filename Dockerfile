# Выкачиваем из dockerhub образ с python
# FROM python:slim
FROM python:3.11.8-slim
WORKDIR /clim
COPY requirements.txt /clim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . /clim
ENV FLASK_APP start.py
EXPOSE 5000
