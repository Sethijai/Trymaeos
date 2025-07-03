# Use a reliable base image (replace with artemisfowl004/vid-compress if verified to work)
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Create app directory with restrictive permissions
RUN mkdir -p /app && chmod 755 /app

# Update package lists and install dependencies in one layer
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        git \
        python3 \
        python3-pip \
        wget \
        zstd \
        p7zip-full \
        ffmpeg \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy only necessary files
COPY start.sh .
COPY app/ ./app/  # Adjust based on your project structure

# Make start.sh executable
RUN chmod +x start.sh

# Expose port if needed (uncomment and set appropriate port)
# EXPOSE 8080

# Set environment variable for debugging
ENV PYTHONUNBUFFERED=1

# Use ENTRYPOINT for consistent execution
ENTRYPOINT ["bash", "start.sh"]
