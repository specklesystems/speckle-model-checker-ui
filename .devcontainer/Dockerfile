FROM mcr.microsoft.com/devcontainers/python:3.11

# Install additional packages
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
  && apt-get -y install --no-install-recommends \
  curl \
  gnupg \
  lsb-release \
  vim \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /workspace