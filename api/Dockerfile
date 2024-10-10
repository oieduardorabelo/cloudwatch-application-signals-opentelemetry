FROM --platform=linux/amd64 python:3.10-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY . /api

WORKDIR /api

RUN groupadd -g 1001 appgroup && \
    useradd -m -u 1001 -g appgroup appuser && \
    chown -R appuser /api

USER appuser

RUN uv sync --frozen --no-cache

HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

CMD ["uv", "run", "python", "api"]