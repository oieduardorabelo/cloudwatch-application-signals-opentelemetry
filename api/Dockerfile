FROM --platform=linux/amd64 python:3.10-slim

RUN useradd -m app_user

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY . /api

WORKDIR /api

RUN chown -R app_user:app_user /api

USER app_user

RUN uv sync --frozen --no-cache

HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

CMD ["uv", "run", "python", "api"]