#!/usr/bin/env bash
set -euo pipefail

TRUSTCUE_WORKSPACE="${TRUSTCUE_WORKSPACE:-${HOME}/trustcue-workspace}"
PID_DIR="${TRUSTCUE_WORKSPACE}/.trustcue/pids"

stop_process() {
  local name="$1"
  local pid_file="${PID_DIR}/${name}.pid"

  if [[ ! -f "${pid_file}" ]]; then
    echo "${name}: no PID file"
    return
  fi

  local pid
  pid="$(cat "${pid_file}")"
  if kill -0 "${pid}" 2>/dev/null; then
    echo "Stopping ${name} process ${pid}..."
    kill "${pid}"
    for _ in {1..10}; do
      if ! kill -0 "${pid}" 2>/dev/null; then
        break
      fi
      sleep 1
    done
    if kill -0 "${pid}" 2>/dev/null; then
      echo "${name} did not stop gracefully; terminating it." >&2
      kill -TERM "${pid}" 2>/dev/null || true
    fi
  else
    echo "${name}: process ${pid} is not running"
  fi
  rm -f "${pid_file}"
}

stop_process ui
stop_process openworker
stop_process churncue

echo "TrustCue local services stopped."
