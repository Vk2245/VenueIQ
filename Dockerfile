# --- Build Stage ---
FROM python:3.13-slim AS builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Runtime Stage ---
FROM python:3.13-slim

# Security: Create non-root user
RUN groupadd -r venueiq && useradd -r -g venueiq venueiq

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/venueiq/.local
ENV PATH=/home/venueiq/.local/bin:$PATH

# Copy application code
COPY . .

# Ensure the non-root user owns the app
RUN chown -R venueiq:venueiq /app

# Switch to non-root user
USER venueiq

# Expose port
EXPOSE 8000

# Health check for Cloud Run / Render
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 8000)}/health')" || exit 1

# Run with uvicorn leveraging the dynamic PORT env var
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
