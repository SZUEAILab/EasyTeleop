# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_NO_CACHE=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        pkg-config \
        libssl-dev \
        libffi-dev \
        libgl1 \
        libglib2.0-0 \
        libstdc++6 \
        libopus0 \
        libvpx-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

RUN pip install --upgrade pip && pip install uv

COPY pyproject.toml setup.py MANIFEST.in uv.lock README.md LICENSE ./
COPY src ./src
COPY run ./run
COPY docs ./docs

RUN uv pip install --system -e .

CMD ["python", "-c", "import EasyTeleop; print('EasyTeleop container ready')"]
