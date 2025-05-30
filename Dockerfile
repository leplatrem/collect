FROM python:3.12.5 as python-base

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off \
    UV_HOME=/opt/uv \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PYSETUP_PATH="/opt/pysetup"

RUN python3 -m venv $UV_HOME && \
    $UV_HOME/bin/pip install uv && \
    $UV_HOME/bin/uv --version

WORKDIR $PYSETUP_PATH
COPY ./uv.lock ./pyproject.toml ./
RUN $UV_HOME/bin/uv sync --no-dev --no-progress

FROM python:3.12.5-slim as production

ENV PATH="/opt/pysetup/.venv/bin:$PATH" \
    HOST=0.0.0.0 \
    PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    VENV_PATH="/opt/pysetup/.venv" \
    DJANGO_STATIC_ROOT="/mnt/static"
ENV GUNICORN_CMD_ARGS="--bind ${HOST}:${PORT} --access-logfile '-' --error-logfile '-' --capture-output"

COPY --from=python-base $VENV_PATH $VENV_PATH

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gettext \
    libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

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

USER app
WORKDIR /app

COPY --chown=app:app . .
COPY env.local .env

ARG COMMANDS_CACHE_BUST=1

# Compile translation messages
RUN django-admin compilemessages

# Collect static files
RUN django-admin collectstatic --noinput --settings=collect.settings

EXPOSE $PORT
CMD ["gunicorn", "collect.wsgi"]
