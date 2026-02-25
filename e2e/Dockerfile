FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    alsa-utils \
    ffmpeg \
    xclip \
    xdotool \
    xvfb \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir pynput rich

WORKDIR /opt/redictum-test

# Fake binaries override real paplay/arecord in PATH
# (/usr/local/bin has priority over /usr/bin)
COPY e2e/fake-paplay  /usr/local/bin/paplay
COPY e2e/fake-arecord /usr/local/bin/arecord
COPY e2e/fake-pactl   /usr/local/bin/pactl
COPY e2e/fake-whisper-cli /usr/local/bin/whisper-cli
RUN chmod +x /usr/local/bin/paplay /usr/local/bin/arecord /usr/local/bin/pactl /usr/local/bin/whisper-cli

# Place fake whisper-cli and model at default config paths so check_whisper()
# passes on first run without interactive prompts (stdin is /dev/null).
RUN mkdir -p /root/whisper.cpp/build/bin /root/whisper.cpp/models \
    && ln -s /usr/local/bin/whisper-cli /root/whisper.cpp/build/bin/whisper-cli \
    && touch /root/whisper.cpp/models/ggml-large-v3-turbo-q5_0.bin

COPY redictum ./redictum

COPY e2e/run_e2e.sh ./run_e2e.sh
RUN chmod +x ./run_e2e.sh

ENTRYPOINT ["./run_e2e.sh"]
