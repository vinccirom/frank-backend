FROM python:3.11-slim

# Install ffmpeg and other dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create audios directory
RUN mkdir -p audios

# Make sure the bin/rhubarb is executable
RUN chmod +x bin/rhubarb

# Set environment variables
ENV PORT=8000

# Expose the port
EXPOSE 8000

# Run the application with Gunicorn
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile - --log-level info 