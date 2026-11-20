# Dockerfile — o sotawhat de leitura numa VPS (SDD §6.15): a interface e as perguntas ao grafo sobre uma
# cópia do insight.db. A coleta, a triagem e as chaves de API ficam no seu computador; aqui não entra .env.
# Uso: docker compose -f compose.vps.yaml up -d --build   (veja o README, "Perguntas ao grafo numa VPS")
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    SOTAWHAT_IN_CONTAINER=1 \
    SOTAWHAT_DATA_DIR=/data \
    SOTAWHAT_CONFIG_DIR=/app/config

WORKDIR /app
COPY pyproject.toml README.md ./
COPY sotawhat ./sotawhat
RUN pip install --no-cache-dir . && mkdir -p /data /app/config

# dentro do contêiner a interface escuta em 0.0.0.0; o compose publica a porta só no 127.0.0.1 da VPS
EXPOSE 8765
CMD ["sotawhat", "serve", "--no-browser"]
