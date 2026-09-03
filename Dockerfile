FROM python:3.12-slim

WORKDIR /app

# Prevent Python from buffering stdout/stderr and writing .pyc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY free_games_bot ./free_games_bot

# Create directory for SQLite database storage
RUN mkdir -p /app/data

VOLUME ["/app/data"]

CMD ["python", "-m", "free_games_bot.main"]
