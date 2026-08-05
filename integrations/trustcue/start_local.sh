#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENWORKER_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CHURNCUE_DIR="${CHURNCUE_DIR:-$(cd "${OPENWORKER_DIR}/.." && pwd)/ChurnCue}"
TRUSTCUE_WORKSPACE="${TRUSTCUE_WORKSPACE:-${HOME}/trustcue-workspace}"
LOG_DIR="${TRUSTCUE_WORKSPACE}/.trustcue/logs"
PID_DIR="${TRUSTCUE_WORKSPACE}/.trustcue/pids"
CHURNCUE_PORT="${CHURNCUE_PORT:-8000}"
OPENWORKER_PORT="${OPENWORKER_PORT:-8765}"
WITH_UI=false
SKIP_SETUP=false

usage() {
  cat <<'EOF'
Usage: bash integrations/trustcue/start_local.sh [options]

Options:
  --with-ui       Also start the OpenWorker browser UI.
  --skip-setup    Do not create virtual environments or install dependencies.
  -h, --help      Show this help message.

Environment variables:
  CHURNCUE_DIR          Path to the ChurnCue repository.
  TRUSTCUE_WORKSPACE    OpenWorker workspace path.
  CHURNCUE_PORT         ChurnCue port, default 8000.
  OPENWORKER_PORT       OpenWorker port, default 8765.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-ui)
      WITH_UI=true
      shift
      ;;
    --skip-setup)
      SKIP_SETUP=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

mkdir -p "${TRUSTCUE_WORKSPACE}" "${LOG_DIR}" "${PID_DIR}"

command -v curl >/dev/null 2>&1 || {
  echo "curl is required." >&2
  exit 1
}

if [[ ! -d "${CHURNCUE_DIR}/.git" ]]; then
  echo "ChurnCue repository was not found at ${CHURNCUE_DIR}." >&2
  echo "Clone it first or set CHURNCUE_DIR." >&2
  exit 1
fi

if [[ "${SKIP_SETUP}" == false ]]; then
  if [[ ! -x "${CHURNCUE_DIR}/.venv/bin/churncue" ]]; then
    command -v python3.12 >/dev/null 2>&1 || {
      echo "python3.12 is required to set up ChurnCue." >&2
      exit 1
    }
    echo "Setting up ChurnCue..."
    (
      cd "${CHURNCUE_DIR}"
      python3.12 -m venv .venv
      .venv/bin/python -m pip install --upgrade pip
      .venv/bin/pip install -e '.[dev]'
      .venv/bin/python scripts/generate_demo_data.py
    )
  fi

  if [[ ! -x "${OPENWORKER_DIR}/.venv/bin/openworker-server" ]]; then
    echo "Setting up OpenWorker..."
    (
      cd "${OPENWORKER_DIR}"
      bash packaging/setup_dev_env.sh
    )
  fi
fi

if [[ ! -x "${CHURNCUE_DIR}/.venv/bin/churncue" ]]; then
  echo "ChurnCue executable is missing. Run without --skip-setup." >&2
  exit 1
fi

if [[ ! -x "${OPENWORKER_DIR}/.venv/bin/openworker-server" ]]; then
  echo "OpenWorker server executable is missing. Run without --skip-setup." >&2
  exit 1
fi

"${OPENWORKER_DIR}/.venv/bin/python" \
  "${SCRIPT_DIR}/bootstrap.py" \
  --workspace "${TRUSTCUE_WORKSPACE}" \
  --churncue-url "http://localhost:${CHURNCUE_PORT}/mcp" \
  --force

stop_stale_process() {
  local name="$1"
  local pid_file="${PID_DIR}/${name}.pid"
  if [[ -f "${pid_file}" ]]; then
    local pid
    pid="$(cat "${pid_file}")"
    if kill -0 "${pid}" 2>/dev/null; then
      echo "Stopping stale ${name} process ${pid}..."
      kill "${pid}" || true
      sleep 1
    fi
    rm -f "${pid_file}"
  fi
}

stop_stale_process churncue
stop_stale_process openworker
if [[ "${WITH_UI}" == true ]]; then
  stop_stale_process ui
fi

echo "Starting ChurnCue on port ${CHURNCUE_PORT}..."
(
  cd "${CHURNCUE_DIR}"
  CHURNCUE_PORT="${CHURNCUE_PORT}" \
    nohup .venv/bin/churncue >"${LOG_DIR}/churncue.log" 2>&1 &
  echo $! >"${PID_DIR}/churncue.pid"
)

for _ in {1..30}; do
  if curl --silent --fail "http://localhost:${CHURNCUE_PORT}/health" >/dev/null; then
    break
  fi
  sleep 1
done

if ! curl --silent --fail "http://localhost:${CHURNCUE_PORT}/health" >/dev/null; then
  echo "ChurnCue did not become healthy. See ${LOG_DIR}/churncue.log" >&2
  exit 1
fi

echo "Starting OpenWorker server on port ${OPENWORKER_PORT}..."
nohup "${OPENWORKER_DIR}/.venv/bin/openworker-server" \
  --cwd "${TRUSTCUE_WORKSPACE}" \
  --port "${OPENWORKER_PORT}" \
  >"${LOG_DIR}/openworker.log" 2>&1 &
echo $! >"${PID_DIR}/openworker.pid"
sleep 2

OPENWORKER_PID="$(cat "${PID_DIR}/openworker.pid")"
if ! kill -0 "${OPENWORKER_PID}" 2>/dev/null; then
  echo "OpenWorker failed to start. See ${LOG_DIR}/openworker.log" >&2
  exit 1
fi

if [[ "${WITH_UI}" == true ]]; then
  command -v npm >/dev/null 2>&1 || {
    echo "npm is required for --with-ui." >&2
    exit 1
  }
  echo "Starting OpenWorker browser UI..."
  (
    cd "${OPENWORKER_DIR}/surfaces/gui"
    if [[ ! -d node_modules ]]; then
      npm install
    fi
    nohup npm run dev >"${LOG_DIR}/ui.log" 2>&1 &
    echo $! >"${PID_DIR}/ui.pid"
  )
fi

cat <<EOF

TrustCue local runtime is ready.

ChurnCue health: http://localhost:${CHURNCUE_PORT}/health
ChurnCue MCP:    http://localhost:${CHURNCUE_PORT}/mcp
OpenWorker API: http://localhost:${OPENWORKER_PORT}
Workspace:      ${TRUSTCUE_WORKSPACE}
Demo prompt:    ${TRUSTCUE_WORKSPACE}/TRUSTCUE_DEMO_PROMPT.md
Logs:           ${LOG_DIR}

In OpenWorker:
1. Select the "TrustCue Retention Copilot" persona.
2. Open TRUSTCUE_DEMO_PROMPT.md and paste its request.
3. Review the rescue report.
4. Approve or edit the draft action. Do not send it during the demo.

Stop services with:
  bash integrations/trustcue/stop_local.sh
EOF
