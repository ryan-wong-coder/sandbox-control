FROM node:24-alpine AS web
WORKDIR /app/apps/web
COPY apps/web/package*.json ./
RUN npm install
COPY apps/web ./
RUN npm run build

FROM python:3.12-slim AS api
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY deploy/requirements-runtime.txt ./deploy/requirements-runtime.txt
COPY deploy/wheels ./deploy/wheels
RUN if find ./deploy/wheels -maxdepth 1 -name '*.whl' | grep -q .; then \
    pip install --no-index --find-links=./deploy/wheels -r ./deploy/requirements-runtime.txt; \
  else \
    pip install --no-cache-dir -r ./deploy/requirements-runtime.txt; \
  fi
COPY apps/api ./apps/api
COPY --from=web /app/apps/web/dist ./apps/web/dist
EXPOSE 8080
CMD ["uvicorn", "sandbox_control.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8080"]
