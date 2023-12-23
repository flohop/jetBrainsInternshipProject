# Use an official Python runtime as a parent image
FROM python:3.11-bookworm

# Set the working directory in the container
WORKDIR /telegram_bot

# Copy the current directory contents into the container at
COPY . /telegram_bot

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
# Run main.py when the container launches
CMD ["python", "src/main.py"]
