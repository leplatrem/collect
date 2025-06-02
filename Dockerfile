FROM python:3.12.5 AS python-base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app \
    # App vars
    HOST=0.0.0.0 \
    PORT=8000 \
    DJANGO_STATIC_ROOT="/mnt/static"

ENV GUNICORN_CMD_ARGS="--bind ${HOST}:${PORT} --access-logfile '-' --error-logfile '-' --capture-output"

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev gettext libmagic1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install uv

# Set up user and group
ARG userid=10001
ARG groupid=10001
RUN groupadd --gid $groupid app && \
    useradd -g app --uid $userid --shell /usr/sbin/nologin --create-home app

# Prepare db, media and static folders
RUN mkdir /mnt/media && \
    chown app:app /mnt/media && \
    mkdir /mnt/static && \
    chown app:app /mnt/static && \
    mkdir /mnt/db && \
    chown app:app /mnt/db

# Copy sources, but install into /app (`UV_PROJECT_ENVIRONMENT`)
ADD . /src
WORKDIR /src
RUN uv sync --locked --no-progress

WORKDIR /app
COPY manage.py .
ENV DOTENV_FILE=/src/env.local

ARG COMMANDS_CACHE_BUST=1

# Compile translation messages
RUN uv run django-admin compilemessages

# Collect static files
RUN uv run django-admin collectstatic --noinput --settings=collect.settings

USER app
EXPOSE $PORT
CMD ["uv", "run", "gunicorn", "collect.wsgi"]
