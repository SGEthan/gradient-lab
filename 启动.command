#!/bin/zsh
set -euo pipefail

project_dir="$(cd "$(dirname "$0")" && pwd)"
if [[ -d "$project_dir/../../work" && "$(basename "$(dirname "$project_dir")")" == outputs ]]; then
  runtime_dir="$project_dir/../../work/gradient-lab-runtime"
else
  runtime_dir="$project_dir/.runtime"
fi
python_bin="$runtime_dir/venv/bin/python"
port="${GRADIENT_LAB_PORT:-8765}"
address="http://127.0.0.1:$port"

if /usr/bin/curl --noproxy "*" -fsS --max-time 1 "$address/api/health" 2>/dev/null | /usr/bin/grep -q '"app": "gradient-lab"'; then
  /usr/bin/open "$address"
  exit 0
fi

if [[ ! -x "$python_bin" ]]; then
  mkdir -p "$runtime_dir"
  python3 -m venv "$runtime_dir/venv"
fi
if ! "$python_bin" -c 'import numpy, torch' >/dev/null 2>&1; then
  "$python_bin" -m pip install --disable-pip-version-check -r "$project_dir/requirements.txt"
fi

"$python_bin" -B "$project_dir/server.py" --port "$port" &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT
for attempt in {1..30}; do
  if /usr/bin/curl --noproxy "*" -fsS --max-time 1 "$address/api/health" >/dev/null 2>&1; then
    /usr/bin/open "$address"
    wait "$server_pid"
    exit
  fi
  kill -0 "$server_pid" 2>/dev/null || { wait "$server_pid"; exit 1; }
  sleep 0.1
done
print -u2 "Gradient Lab 未能启动。请检查上方的错误信息。"
exit 1
