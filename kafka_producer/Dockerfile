FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install required system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    netcat-traditional \
    build-essential \
    gcc && \
    rm -rf /var/lib/apt/lists/*


# Upgrade pip and install essential packages
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy the application files
COPY ./kafka_producer .
COPY ./.env .


RUN pip install --no-cache-dir -r requirements.txt
