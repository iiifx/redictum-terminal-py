FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    pulseaudio-utils \
    alsa-utils \
    ffmpeg \
    xclip \
    xdotool \
    cmake \
    build-essential \
    git \
    xvfb \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir pynput rich PyYAML

WORKDIR /opt/redictum-test

# Fake binaries override real paplay/arecord in PATH
# (/usr/local/bin has priority over /usr/bin)
COPY docker/fake-paplay  /usr/local/bin/paplay
COPY docker/fake-arecord /usr/local/bin/arecord
COPY docker/fake-whisper-cli /usr/local/bin/whisper-cli
RUN chmod +x /usr/local/bin/paplay /usr/local/bin/arecord /usr/local/bin/whisper-cli

COPY redictum ./redictum

COPY docker/run_e2e.sh ./run_e2e.sh
RUN chmod +x ./run_e2e.sh

ENTRYPOINT ["./run_e2e.sh"]
