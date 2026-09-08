#!/usr/bin/env bash
# Sourced by launchers; leaves the validated executable in agents_python.
select_agents_python() {
  local repo_root="${1:?repository root required}"
  if [[ "${AGENTS_PYTHON+x}" == x ]]; then
    agents_python="$AGENTS_PYTHON"
  elif [[ -x "$repo_root/.venv/bin/python" ]]; then
    agents_python="$repo_root/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    agents_python="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    agents_python="$(command -v python)"
  else
    printf 'Python 3.11+ is required. Follow the bootstrap instructions in %s/INSTALL.md.\n' "$repo_root" >&2
    return 1
  fi

  case "$agents_python" in
    /*) ;;
    */*) agents_python="$PWD/$agents_python" ;;
  esac

  if [[ -z "$agents_python" ]] || ! "$agents_python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
    printf 'Cannot use Python interpreter "%s": Python 3.11+ is required. Follow the bootstrap instructions in %s/INSTALL.md; set AGENTS_PYTHON to a working executable if needed.\n' "$agents_python" "$repo_root" >&2
    return 1
  fi
}
