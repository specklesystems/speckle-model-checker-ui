#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$HOME/.config/gcloud"
sudo chown -R vscode:vscode "$HOME/.config/gcloud"

# 1) If we're already authenticated, do nothing.
if gcloud auth list --format='value(account)' | grep -q .; then
  echo "✔ gcloud already authenticated"
  exit 0
fi

echo "🚀 Bootstrapping gcloud inside devcontainer…"

# 2) Log in (this will print the URL & prompt for your code)
gcloud auth login --no-launch-browser || true

# 3) Create/switch to a named config so users can keep their 'default' untouched
gcloud config configurations create devcontainer --quiet || true
gcloud config configurations activate devcontainer --quiet

# 4) Run gcloud init to pick project, region, etc.
gcloud init --skip-diagnostics --console-only --configuration=devcontainer --quiet || true

echo "✔ gcloud is ready—credentials & config now live in your Docker volume."
