# Dockerfile
# This file is used by Google Cloud Run to build a container image for our app.
# A container packages up our code and all its dependencies so it runs reliably anywhere.

# 1. Use the official lightweight Python 3.12 image
FROM python:3.12-slim

# 2. Allow statements and log messages to immediately appear in the knative logs
ENV PYTHONUNBUFFERED True

# 3. Create and set the working directory inside the container
ENV APP_HOME /app
WORKDIR $APP_HOME

# 4. Copy all local files to the container working directory
COPY . ./

# 5. Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# 6. Run the web service on container startup.
# We use gunicorn to serve the Flask app in production.
# Gunicorn will bind to the dynamic port supplied by Cloud Run (via the $PORT environment variable)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
