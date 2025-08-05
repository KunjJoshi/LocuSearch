# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make port 8080 available (Cloud Run expects 8080)
EXPOSE 8080

# Run the application
# Cloud Run expects the app to listen on port 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]