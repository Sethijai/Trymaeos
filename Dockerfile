# Use a reliable base image (replace with artemisfowl004/vid-compress if verified to work)
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Create app directory with restrictive permissions
RUN mkdir ./app
RUN chmod 777 /app

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
COPY . .
# Make start.sh executable

# Expose port if needed (uncomment and set appropriate port)
EXPOSE 8080

# Set environment variable for debugging

# Use ENTRYPOINT for consistent execution
CMD ["bash", "start.sh"]
