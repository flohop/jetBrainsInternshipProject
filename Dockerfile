# Use an official Python runtime as a parent image
FROM python:3.11-bookworm

# Set the working directory in the container
WORKDIR /telegram_bot

# Copy the current directory contents into the container at
COPY . /telegram_bot

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80

# Run main.py when the container launches
CMD ["python", "src/main.py",  "-c", "configs/dev.settings.json"]
