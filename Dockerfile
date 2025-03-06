# Use official Python image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy the app files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set a default value for PORT if it's not provided during build
ARG PORT=8000
ENV PORT=${PORT}

# Expose the port to allow external access
EXPOSE ${PORT}

# Ensure start.sh has executable permissions
RUN chmod +x /app/start.sh

# Run the start script and keep the container running 
CMD ["sh", "-c", "/app/start.sh"]
