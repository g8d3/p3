FROM node:22-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl jq ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash agent
USER agent
WORKDIR /workspace

# No ENTRYPOINT - let the caller specify the command
