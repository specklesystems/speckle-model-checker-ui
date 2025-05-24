# syntax=docker/dockerfile:1

################################################################################
# 1) Base: Python for FastAPI + system tools + Cloud SDK + uv
################################################################################
FROM python:3.11-slim AS base

# Install system deps, Google Cloud SDK, uv, zsh, git, etc.
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
  curl wget git zsh exa sudo ca-certificates gnupg apt-transport-https \
  nodejs npm \
  && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
  | apt-key add - \
  && echo "deb https://packages.cloud.google.com/apt cloud-sdk main" \
  > /etc/apt/sources.list.d/google-cloud-sdk.list \
  && apt-get update \
  && apt-get install -y google-cloud-sdk \
  && curl -LsSf https://astral.sh/uv/install.sh | sh \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

################################################################################
# 2) Builder: compile your Go back-end tools (optional, you can also build in-place)
################################################################################
FROM golang:1.24.3 AS go-builder
WORKDIR /go

# Pre-install Go dev tools into /go/bin
RUN GO111MODULE=on \
  go install golang.org/x/tools/gopls@latest \
  && go install github.com/go-delve/delve/cmd/dlv@latest \
  && go install github.com/air-verse/air@latest

################################################################################
# 3) Devcontainer final: glue Python + Go together
################################################################################
FROM base

# 3a) Install Go runtime & toolchain (so you can build/run Go code interactively)
ARG GOLANG_VERSION=1.24.3
RUN wget https://go.dev/dl/go${GOLANG_VERSION}.linux-amd64.tar.gz \
  && rm -rf /usr/local/go \
  && tar -C /usr/local -xzf go${GOLANG_VERSION}.linux-amd64.tar.gz \
  && rm go${GOLANG_VERSION}.linux-amd64.tar.gz

# 3b) Create non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
  && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
  && echo "$USERNAME ALL=(root) NOPASSWD:ALL" \
  > /etc/sudoers.d/$USERNAME \
  && chmod 0440 /etc/sudoers.d/$USERNAME

# 3c) Set up Go env & workspace
ENV GOPATH=/home/${USERNAME}/go
ENV PATH=/usr/local/go/bin:${GOPATH}/bin:${PATH}

RUN mkdir -p /workspace $GOPATH/{src,bin,pkg} \
  && chown -R ${USERNAME}:${USERNAME} /workspace $GOPATH

# 3d) Copy Go tools from builder
COPY --from=go-builder /go/bin/gopls /usr/local/bin/
COPY --from=go-builder /go/bin/dlv   /usr/local/bin/
COPY --from=go-builder /go/bin/air   /usr/local/bin/

# 3e) Switch to non-root for the rest

WORKDIR /workspace

# 3f) Install Python deps for FastAPI
COPY --chown=vscode:vscode cloudrun/backend/requirements.txt \
  ./cloudrun/backend/
RUN python3 -m pip install --upgrade pip \
  && python3 -m pip install --no-cache-dir \
  -r ./cloudrun/backend/requirements.txt

# 3g) Set up Oh My Zsh
RUN git clone https://github.com/ohmyzsh/ohmyzsh.git ~/.oh-my-zsh \
  && cp ~/.oh-my-zsh/templates/zshrc.zsh-template ~/.zshrc \
  && chsh -s /usr/bin/zsh

# 3h) Default to bash (or zsh) for later terminals

USER ${USERNAME}
SHELL ["/bin/bash", "-lc"]
