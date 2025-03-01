# Use official Python image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy the app files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy .env file
COPY .env .env

# Expose the port from the .env file
ARG PORT
ENV PORT=${PORT}
EXPOSE ${PORT}

# Set executable permissions for the start script
RUN chmod +x start.sh

# Run the start script
CMD ["sh", "-c", "/app/start.sh"]
