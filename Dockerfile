# =============================================================================
# Barista AI – Unified Dockerfile for HuggingFace Spaces
# =============================================================================
# Multi-stage build:
#   1) Node.js stage → builds the Next.js static frontend
#   2) Python stage  → serves FastAPI backend + static frontend assets
# =============================================================================

# ── Stage 1: Build frontend ──────────────────────────────────────────────────
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies first (cache layer)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

# Copy source and build static export
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ─────────────────────────────────────────────────
FROM python:3.11-slim

# HuggingFace Spaces runs containers as non-root user in /home/user
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR /home/user/app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ ./src/
COPY data/ ./data/
COPY main.py ./
COPY .env.example ./.env.example

# Copy built frontend static files from stage 1
COPY --from=frontend-builder /app/frontend/out ./frontend/out

# Set ownership
RUN chown -R user:user /home/user/app

# Switch to non-root user
USER user

# HuggingFace Spaces expects port 7860
ENV API_HOST=0.0.0.0 \
    API_PORT=7860 \
    API_DOCS_ENABLED=true \
    CORS_ORIGINS=* \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO

EXPOSE 7860

CMD ["python", "main.py", "serve", "--host", "0.0.0.0", "--port", "7860"]
