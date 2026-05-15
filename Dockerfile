FROM node:24-bookworm-slim AS node_runtime

FROM python:3.12-slim AS api
WORKDIR /app
ENV PYTHONUNBUFFERED=1
RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates git \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*
COPY --from=node_runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node_runtime /usr/local/bin/npm /usr/local/bin/npm
COPY --from=node_runtime /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
COPY deploy/npm ./deploy/npm
RUN npm install -g --omit=optional ./deploy/npm/openai-codex-0.130.0.tgz \
  && mkdir -p /tmp/codex-platform \
  && tar -xzf ./deploy/npm/openai-codex-0.130.0-linux-x64.tgz -C /tmp/codex-platform \
  && cp -a /tmp/codex-platform/package/vendor /usr/local/lib/node_modules/@openai/codex/vendor \
  && rm -rf /tmp/codex-platform
RUN ln -sf /usr/local/lib/node_modules/@openai/codex/bin/codex.js /usr/local/bin/codex
COPY deploy/requirements-runtime.txt ./deploy/requirements-runtime.txt
COPY deploy/wheels ./deploy/wheels
RUN if find ./deploy/wheels -maxdepth 1 -name '*.whl' | grep -q .; then \
    pip install --no-index --find-links=./deploy/wheels -r ./deploy/requirements-runtime.txt; \
  else \
    pip install --no-cache-dir -r ./deploy/requirements-runtime.txt; \
  fi
COPY apps/api ./apps/api
COPY apps/web/dist ./apps/web/dist
EXPOSE 8080
CMD ["uvicorn", "sandbox_control.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8080"]
