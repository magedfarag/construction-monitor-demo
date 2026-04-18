#!/usr/bin/env bash
set -euo pipefail

HOOK_NAME="${1:-}"
if [[ -z "$HOOK_NAME" ]]; then
  echo "dispatch-hook.sh requires a hook name" >&2
  exit 1
fi

OPT_HOME="${COPILOT_OPTIMIZER_HOME:-${HOME}/.copilot-optimizer}"
ENTRYPOINT="$OPT_HOME/src/index.mjs"

if [[ ! -f "$ENTRYPOINT" ]]; then
  echo "External optimizer entrypoint not found: $ENTRYPOINT" >&2
  exit 1
fi

node "$ENTRYPOINT" hook "$HOOK_NAME"
