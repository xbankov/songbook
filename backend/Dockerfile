# Use the official Python image as the base image
FROM python:3.11.5

# Set the working directory inside the container
WORKDIR /src

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY ./src .

# Expose the port that FastAPI is running on (default: 8000)
EXPOSE 8000

# Command to run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]