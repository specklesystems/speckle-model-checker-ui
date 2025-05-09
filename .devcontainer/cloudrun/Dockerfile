FROM python:3.13-slim

# Add Google Cloud SDK apt repo
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  apt-transport-https \
  ca-certificates \
  gnupg \
  && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
  && echo "deb https://packages.cloud.google.com/apt cloud-sdk main" \
  > /etc/apt/sources.list.d/google-cloud-sdk.list


# Install the SDK
RUN apt-get update && apt-get install -y google-cloud-sdk

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
  && apt-get -y install --no-install-recommends \
  curl \
  git \
  nodejs \
  npm \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
  && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
  && apt-get update \
  && apt-get install -y sudo \
  && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
  && chmod 0440 /etc/sudoers.d/$USERNAME

# Set up the working directory
WORKDIR /workspace

# Install Zsh and Oh My Zsh for the non-root user
RUN apt-get update && apt-get install -y zsh git curl exa \
  && usermod --shell /usr/bin/zsh vscode \
  && runuser -l vscode -c \
  'sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended'

# Switch to non-root user
USER $USERNAME

# Set zsh as default shell explicitly for vscode user
RUN sudo chsh -s /usr/bin/zsh vscode

# Add uv to PATH
ENV PATH="/home/$USERNAME/.cargo/bin:${PATH}"

RUN pip install --upgrade pip

# Set up the default shell
SHELL ["/bin/bash", "-c"] 