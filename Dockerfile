FROM python:3.12.5 AS python-base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app \
    # App vars
    HOST=0.0.0.0 \
    PORT=8000 \
    DJANGO_MEDIA_ROOT=/mnt/media/uploads \
    DJANGO_STATIC_ROOT=/mnt/static \
    DJANGO_DEBUG=false \
    DJANGO_SECURE_SSL_REDIRECT=false \
    # Media files are served by the web server in front of the app (see
    # `etc/apache/`), never by Django, which would serve them one worker at a
    # time and inline (see `DJANGO_MEDIA_FILES_SERVED`).
    DJANGO_MEDIA_FILES_SERVED=false \
    # Number of gunicorn worker processes. Without it, gunicorn defaults to a
    # single worker, which serves a single request at a time. Rule of thumb:
    # twice the number of CPU cores, plus one.
    WEB_CONCURRENCY=5

# `--threads` above 1 switches gunicorn to threaded workers, so each worker can
# serve several requests while waiting on the database.
# `--max-requests` recycles workers regularly, so that the memory held after
# processing a big image is returned to the system.
ENV GUNICORN_CMD_ARGS="--bind ${HOST}:${PORT} --threads 4 --timeout 60 --max-requests 1000 --max-requests-jitter 100 --access-logfile '-' --error-logfile '-' --capture-output"

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
