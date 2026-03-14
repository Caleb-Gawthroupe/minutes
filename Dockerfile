FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Install system dependencies for xvfb and browsers
RUN apt-get update && apt-get install -y \
    xvfb \
    libgbm1 \
    libnss3 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (already in the image, but ensuring chromium is ready)
RUN playwright install chromium

# Copy source code
COPY . .

# Set Python path
ENV PYTHONPATH=/app/src

# Create downloads directory with permissions
RUN mkdir -p /app/downloads && chmod 777 /app/downloads

# Run the pipeline with xvfb
CMD ["xvfb-run", "--server-args=-screen 0 1280x1024x24", "python", "-m", "main"]
