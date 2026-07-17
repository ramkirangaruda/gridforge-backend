# Backend (FastAPI) image.
# Build context is the REPO ROOT (not backend/), because:
#   - requirements.txt lives at the repo root
#   - backend/main.py uses absolute imports like `from backend.api...`,
#     which requires the repo root to be on sys.path / the working dir.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY backend/ ./backend/

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
