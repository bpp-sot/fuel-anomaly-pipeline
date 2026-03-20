FROM python:3.12-slim

# libgomp1 is required by numpy on Debian/Ubuntu-based images.
# fontconfig and fonts-dejavu provide font support for matplotlib chart rendering.
RUN apt-get update && apt-get install -y \
    libgomp1 \
    fontconfig \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home appuser

WORKDIR /app

# Copy runtime requirements first so Docker caches this layer separately.
# Re-running pip install is only triggered when requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code.
COPY src/ ./src/
COPY main.py .

RUN chown -R appuser:appuser /app
USER appuser

# /app/output is the path used inside the container for all reports and charts.
# Mount a host directory here with: -v "$(pwd)/output:/app/output"
VOLUME ["/app/output"]

ENTRYPOINT ["python", "main.py"]
