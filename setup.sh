#!/usr/bin/env bash

set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

if ! cd "$PROJECT_ROOT"; then
  printf 'Failed to enter project directory: %s\n' "$PROJECT_ROOT"
  exit 1
fi

if [ -t 1 ] && command -v tput >/dev/null 2>&1; then
  COLOR_COUNT="$(tput colors 2>/dev/null || printf '0')"
else
  COLOR_COUNT="0"
fi

if [ "$COLOR_COUNT" -ge 8 ]; then
  BOLD="$(tput bold)"
  RESET="$(tput sgr0)"
  RED="$(tput setaf 1)"
  GREEN="$(tput setaf 2)"
  YELLOW="$(tput setaf 3)"
  BLUE="$(tput setaf 4)"
  MAGENTA="$(tput setaf 5)"
  CYAN="$(tput setaf 6)"
else
  BOLD=''
  RESET=''
  RED=''
  GREEN=''
  YELLOW=''
  BLUE=''
  MAGENTA=''
  CYAN=''
fi

print_banner() {
  printf '\n'
  printf '%s%sMoneyPrinter Interactive Setup%s\n' "$BOLD" "$MAGENTA" "$RESET"
  printf '%s--------------------------------%s\n' "$MAGENTA" "$RESET"
  printf '%sThis script helps you prepare your local environment.%s\n\n' "$CYAN" "$RESET"
}

info() {
  printf '%s[INFO]%s %s\n' "$BLUE" "$RESET" "$1"
}

ok() {
  printf '%s[OK]%s   %s\n' "$GREEN" "$RESET" "$1"
}

warn() {
  printf '%s[WARN]%s %s\n' "$YELLOW" "$RESET" "$1"
}

error() {
  printf '%s[ERR]%s  %s\n' "$RED" "$RESET" "$1"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

ask_yes_no() {
  prompt="$1"
  default="$2"

  while true; do
    if [ "$default" = "y" ]; then
      printf '%s [Y/n]: ' "$prompt"
    else
      printf '%s [y/N]: ' "$prompt"
    fi

    read -r reply
    case "$reply" in
      [Yy]|[Yy][Ee][Ss])
        return 0
        ;;
      [Nn]|[Nn][Oo])
        return 1
        ;;
      '')
        if [ "$default" = "y" ]; then
          return 0
        fi
        return 1
        ;;
      *)
        warn 'Please answer y or n.'
        ;;
    esac
  done
}

check_python_version() {
  if ! command_exists python3; then
    error 'python3 not found (required: 3.11+).'
    return 1
  fi

  PYTHON_VERSION="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))' 2>/dev/null || printf '0.0.0')"
  MAJOR="$(printf '%s' "$PYTHON_VERSION" | cut -d. -f1)"
  MINOR="$(printf '%s' "$PYTHON_VERSION" | cut -d. -f2)"

  if [ "$MAJOR" -gt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; }; then
    ok "python3 found ($PYTHON_VERSION)"
    return 0
  fi

  error "python3 version is $PYTHON_VERSION (need 3.11+)"
  return 1
}

check_prereqs() {
  info 'Checking prerequisites...'

  missing_critical=0

  if ! check_python_version; then
    missing_critical=1
  fi

  if command_exists uv; then
    ok 'uv found'
  else
    error 'uv not found (install: https://docs.astral.sh/uv/getting-started/installation/)'
    missing_critical=1
  fi

  if command_exists ffmpeg; then
    ok 'ffmpeg found'
  else
    warn 'ffmpeg not found (required for video generation).'
  fi

  if command_exists magick || command_exists convert; then
    ok 'ImageMagick found'
  else
    warn 'ImageMagick not found (some text rendering features may fail).'
  fi

  if command_exists ollama; then
    ok 'ollama found'
  else
    warn 'ollama not found (required for script generation).'
  fi

  if [ "$missing_critical" -eq 1 ]; then
    error 'Missing critical dependencies. Please install them, then rerun setup.'
    return 1
  fi

  return 0
}

configure_local_database_url() {
  if [ ! -f .env ]; then
    return 0
  fi

  db_result="$(python3 - <<'PY'
from pathlib import Path

env_path = Path('.env')
text = env_path.read_text(encoding='utf-8')
has_trailing_newline = text.endswith('\n')
lines = text.splitlines()
target = 'DATABASE_URL="sqlite:///moneyprinter.db"'

for index, line in enumerate(lines):
    if not line.startswith('DATABASE_URL='):
        continue

    value = line.split('=', 1)[1].strip().strip('"').strip("'")
    if value == '' or value.startswith('postgresql+psycopg://'):
        lines[index] = target
        env_path.write_text(
            '\n'.join(lines) + ('\n' if has_trailing_newline else ''),
            encoding='utf-8',
        )
        print('updated')
    else:
        print('kept')
    break
else:
    lines.append(target)
    env_path.write_text(
        '\n'.join(lines) + ('\n' if has_trailing_newline or lines else ''),
        encoding='utf-8',
    )
    print('added')
PY
)"

  case "$db_result" in
    updated)
      info 'Set DATABASE_URL to local SQLite default in .env'
      ;;
    added)
      info 'Added DATABASE_URL local SQLite default to .env'
      ;;
    *)
      info 'Keeping existing DATABASE_URL in .env'
      ;;
  esac
}

setup_env_file() {
  if [ ! -f .env.example ]; then
    warn '.env.example is missing; skipping env setup.'
    return 0
  fi

  if [ -f .env ]; then
    if ask_yes_no '.env already exists. Overwrite it from .env.example?' 'n'; then
      cp .env.example .env
      ok '.env overwritten from .env.example'
    else
      info 'Keeping existing .env'
    fi
  else
    cp .env.example .env
    ok 'Created .env from .env.example'
  fi

  configure_local_database_url

  if ask_yes_no 'Open .env now to edit required keys?' 'y'; then
    if [ -n "${EDITOR:-}" ] && command_exists "$EDITOR"; then
      "$EDITOR" .env
    elif command_exists nano; then
      nano .env
    elif command_exists vi; then
      vi .env
    else
      warn "No terminal editor detected. Please edit $PROJECT_ROOT/.env manually."
    fi
  fi
}

install_dependencies() {
  if ask_yes_no 'Install Python dependencies with uv sync?' 'y'; then
    info 'Running uv sync...'
    if uv sync; then
      ok 'Dependencies installed'
    else
      error 'uv sync failed'
      return 1
    fi
  else
    warn 'Skipped dependency installation.'
  fi

  return 0
}

check_ollama_models() {
  if ! command_exists ollama; then
    return 0
  fi

  if ! ask_yes_no 'Check local Ollama models now?' 'y'; then
    return 0
  fi

  info 'Querying Ollama model list...'
  if ollama list; then
    ok 'Ollama is reachable.'
  else
    warn 'Could not query Ollama. If needed, run: ollama serve'
    return 0
  fi

  if ask_yes_no 'Pull default model llama3.1:8b now?' 'n'; then
    printf 'Model name [llama3.1:8b]: '
    read -r model_name
    model_name="${model_name:-llama3.1:8b}"

    info "Pulling model $model_name ..."
    if ollama pull "$model_name"; then
      ok "Model $model_name is ready"
    else
      warn "Failed to pull model $model_name"
    fi
  fi
}

print_next_steps() {
  printf '\n%sNext steps%s\n' "$BOLD" "$RESET"
  printf '%s1.%s Start backend: %suv run python Backend/main.py%s\n' "$CYAN" "$RESET" "$BOLD" "$RESET"
  printf '%s2.%s Start worker (new terminal): %suv run python Backend/worker.py%s\n' "$CYAN" "$RESET" "$BOLD" "$RESET"
  printf '%s3.%s Start frontend (new terminal): %spython3 -m http.server 3000 --directory Frontend%s\n' "$CYAN" "$RESET" "$BOLD" "$RESET"
  printf '%s4.%s Open: %shttp://localhost:3000%s\n\n' "$CYAN" "$RESET" "$BOLD" "$RESET"
}

main() {
  print_banner

  if ! check_prereqs; then
    exit 1
  fi

  setup_env_file

  if ! install_dependencies; then
    exit 1
  fi

  check_ollama_models
  print_next_steps
  ok 'Setup complete. Happy building!'
}

main "$@"
