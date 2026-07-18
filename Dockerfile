FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    nmap \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files
COPY hades/ ./hades/
COPY modules/ ./modules/
COPY lib/ ./lib/
COPY templates/ ./templates/
COPY payloads.txt .
COPY main.py .
COPY hades.py .

# Create config directory for sqlite database and logs
RUN mkdir -p config

EXPOSE 9656

# Start the web server
CMD ["python", "hades.py", "--web"]
