#!/usr/bin/env bash
set -euo pipefail

# 1) Install Oh My Zsh if missing
if [ ! -d "/home/vscode/.oh-my-zsh" ]; then
  git clone https://github.com/ohmyzsh/ohmyzsh.git /home/vscode/.oh-my-zsh
  chown -R vscode:vscode /home/vscode/.oh-my-zsh
fi

# 2) Copy & source my custom zshrc
cp ./.devcontainer/cloudrun/zshrc.cloudrun /home/vscode/.zshrc
grep -qxF 'source ~/.zshrc' /home/vscode/.zshenv \
  || echo 'source ~/.zshrc' >> /home/vscode/.zshenv

# 3) Ensure Go workspace exists & is owned by vscode
mkdir -p /home/vscode/go
chown -R vscode:vscode /home/vscode/go
