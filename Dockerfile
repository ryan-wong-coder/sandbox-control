FROM node:24-alpine AS web
WORKDIR /app/apps/web
COPY apps/web/package*.json ./
RUN npm install
COPY apps/web ./
RUN npm run build

FROM python:3.12-slim AS api
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir uv
RUN uv export --frozen --no-dev --format requirements-txt --no-hashes -o /tmp/requirements.txt \
  && uv pip install --system --no-cache -r /tmp/requirements.txt
COPY apps/api ./apps/api
COPY --from=web /app/apps/web/dist ./apps/web/dist
EXPOSE 8080
CMD ["uvicorn", "sandbox_control.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8080"]
