# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app
COPY ./app.py /app/


# Install the required packages
RUN pip install --upgrade pip
RUN pip install -v --no-cache-dir -r requirements.txt

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Define the command to run the app using Streamlit
CMD ["streamlit", "run", "app.py"]
