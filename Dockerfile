FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY asset_pipeline/ ./asset_pipeline/
COPY seed_data/ ./seed_data/
COPY --from=frontend-build /app/frontend/dist ./frontend_dist

RUN mkdir -p data/output data/reference_images data/jobs data/themes data/custom_frameworks

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "asset_pipeline.api.main:app", "--host", "0.0.0.0", "--port", "8000"]