#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
require_env() { [[ -f .env ]] || { echo "Missing .env; run scripts/generate-env" >&2; exit 1; }; }
