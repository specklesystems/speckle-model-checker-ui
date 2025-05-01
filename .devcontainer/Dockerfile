FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
  && apt-get -y install --no-install-recommends \
  curl \
  gnupg \
  lsb-release \
  vim \
  git \
  zsh \
  wget \
  sudo \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Create the vscode user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USERNAME \
  && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
  && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
  && chmod 0440 /etc/sudoers.d/$USERNAME

# Install Oh My Zsh for vscode user
USER $USERNAME
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
USER root

# Set up zsh as default shell for vscode user
RUN chsh -s $(which zsh) $USERNAME

# Install uv globally
RUN pip install uv

# Set up working directory
WORKDIR /workspace
RUN mkdir -p /workspace && chown -R $USERNAME:$USERNAME /workspace

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
  PORT=8080 \
  SHELL=/bin/zsh \
  PATH=$PATH:/home/$USERNAME/.local/bin

# Expose port
EXPOSE 8080

# Switch to vscode user by default
USER $USERNAME

# Default command
CMD ["/bin/zsh"]