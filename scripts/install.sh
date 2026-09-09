#!/usr/bin/env bash
set -euo pipefail

REPO_RAW_BASE="https://raw.githubusercontent.com/VZhuck/architect-ai-toolkit/main"
CONFIG_FILE="ossify-cogents.json"
FORCE=false

for arg in "$@"; do
  case "$arg" in
    --force) FORCE=true ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if ! command -v uv >/dev/null 2>&1; then
  echo "Error: 'uv' is required but was not found on PATH." >&2
  echo "Install it from: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

if ! command -v ossify-cogents >/dev/null 2>&1; then
  echo "ossify-cogents not found, installing via uv tool install..."
  uv tool install git+https://github.com/VZhuck/ossify-cogents.git
fi

if [[ -f "$CONFIG_FILE" && "$FORCE" != "true" ]]; then
  echo "Error: '$CONFIG_FILE' already exists in the current directory." >&2
  echo "Rerun with --force to overwrite it." >&2
  exit 1
fi

echo "Fetching $CONFIG_FILE from architect-ai-toolkit (main)..."
curl -fsSL "$REPO_RAW_BASE/$CONFIG_FILE" -o "$CONFIG_FILE"

echo "Running ossify-cogents install..."
ossify-cogents install
