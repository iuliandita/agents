#!/usr/bin/env bash
# Sourced by render wrappers; keep compatible with Bash 3.2.
set -euo pipefail

select_agents_python() {
  local candidate
  local version_check='import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'

  if [[ ${AGENTS_PYTHON+x} ]]; then
    if [[ -n "$AGENTS_PYTHON" ]] && "$AGENTS_PYTHON" -c "$version_check" >/dev/null 2>&1; then
      agents_python="$AGENTS_PYTHON"
      return 0
    fi
    printf '%s\n' 'AGENTS_PYTHON must name a working Python 3.11+ executable (not a command with flags). See INSTALL.md.' >&2
    return 1
  fi

  for candidate in python python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "$version_check" >/dev/null 2>&1; then
      agents_python="$candidate"
      return 0
    fi
  done
  printf '%s\n' 'Python 3.11+ is required. Neither python nor python3 on PATH is usable. Activate a supported virtual environment or set AGENTS_PYTHON to its executable. See INSTALL.md.' >&2
  return 1
}

select_agents_python
