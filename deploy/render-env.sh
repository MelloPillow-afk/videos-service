#!/usr/bin/env bash
# Prints the production env file: deploy/env.yaml plus the settings that name our Neon
# and Cloudflare accounts, which live in GitHub repository variables instead of this repo.
#
# Reads the variables as one JSON object on stdin: toJSON(vars) in Actions, or locally
#   gh variable list --json name,value --jq 'map({(.name): .value}) | add'
set -euo pipefail

vars=$(cat)
cat "$(dirname "$0")/env.yaml"
for name in CORS_ALLOWED_ORIGINS AUTH_ISSUER AUTH_JWKS_URL AUTH_AUDIENCE R2_ENDPOINT_URL MEDIA_BASE_URL; do
  value=$(jq -r --arg name "$name" '.[$name] // empty' <<<"$vars")
  if [ -z "$value" ]; then
    echo "missing repository variable $name" >&2
    exit 1
  fi
  # A JSON string is a valid double-quoted YAML scalar.
  jq -nr --arg name "$name" --arg value "$value" '"\($name): \($value | tojson)"'
done
