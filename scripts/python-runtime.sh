#!/usr/bin/env bash
# Sourced by launchers; keep compatible with Bash 3.2.
set -euo pipefail

agents_json=0
for agents_arg in "$@"; do
  if [[ "$agents_arg" == "--json" ]]; then
    agents_json=1
  fi
done

# Print the error to stderr and, with --json, the one JSON object to stdout. Exit code 3: a required tool is missing.
# Messages must not contain double quotes or backslashes.
agents_runtime_error() {
  printf '%s\n' "error: $1" >&2
  if [[ "$agents_json" == 1 ]]; then
    printf '{"ok": false, "errors": ["error: %s"], "warnings": [], "notes": []}\n' "$1"
  fi
  return 3
}

select_agents_python() {
  local candidate
  local version_check='import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'

  if [[ ${AGENTS_PYTHON+x} ]]; then
    if [[ -n "$AGENTS_PYTHON" ]] && "$AGENTS_PYTHON" -c "$version_check" >/dev/null 2>&1; then
      agents_python="$AGENTS_PYTHON"
      case "$agents_python" in
        /*) ;;
        */*) agents_python="$PWD/$agents_python" ;;
      esac
      return 0
    fi
    agents_runtime_error 'AGENTS_PYTHON must name a working Python 3.11+ executable (not a command with flags). See INSTALL.md.' || return $?
  fi

  local runtime_root
  runtime_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  candidate="$runtime_root/.venv/bin/python"
  if [[ -e "$candidate" || -L "$candidate" ]]; then
    if "$candidate" -c "$version_check" >/dev/null 2>&1; then
      agents_python="$candidate"
      return 0
    fi
    agents_runtime_error 'the repository .venv/bin/python must be a working Python 3.11+ executable. Repair the virtual environment or set AGENTS_PYTHON to a supported executable. See INSTALL.md.' || return $?
  fi

  for candidate in python python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "$version_check" >/dev/null 2>&1; then
      agents_python="$candidate"
      return 0
    fi
  done
  agents_runtime_error 'Python 3.11+ is required. Neither python nor python3 on PATH is usable. Activate a supported virtual environment or set AGENTS_PYTHON to its executable. See INSTALL.md.' || return $?
}

select_agents_python
