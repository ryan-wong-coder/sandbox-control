FROM node:24-alpine AS web
WORKDIR /app/apps/web
COPY apps/web/package*.json ./
RUN npm install
COPY apps/web ./
RUN npm run build

FROM python:3.12-slim AS api
WORKDIR /app
ENV PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir \
  cryptography==48.0.0 \
  fastapi==0.136.1 \
  pydantic==2.13.4 \
  python-multipart==0.0.28 \
  "uvicorn[standard]==0.47.0"
COPY apps/api ./apps/api
COPY --from=web /app/apps/web/dist ./apps/web/dist
EXPOSE 8080
CMD ["uvicorn", "sandbox_control.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8080"]
