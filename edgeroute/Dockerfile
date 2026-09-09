# Multi-stage production Dockerfile for EdgeRoute
FROM python:3.12-slim

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    OLLAMA_HOST=http://host.docker.internal:11434 \
    OLLAMA_MODEL=qwen2.5:0.5b

EXPOSE 8000 8501

# Default launch command: starts both FastAPI backend and Streamlit UI
CMD ["sh", "-c", "python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 & python -m streamlit run app/ui.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"]
