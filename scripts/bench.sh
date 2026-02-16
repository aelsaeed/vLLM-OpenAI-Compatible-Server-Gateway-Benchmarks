#!/usr/bin/env bash
set -euo pipefail

HOST="${BENCH_HOST:-127.0.0.1}"
GATEWAY_PORT="${BENCH_GATEWAY_PORT:-8011}"
MOCK_PORT="${BENCH_MOCK_PORT:-18001}"
TOTAL_REQUESTS="${BENCH_TOTAL_REQUESTS:-12}"
CONCURRENCY="${BENCH_CONCURRENCY:-3}"

python -m uvicorn scripts.mock_openai_server:app --host "$HOST" --port "$MOCK_PORT" >/tmp/mock-openai-bench.log 2>&1 &
MOCK_PID=$!

GATEWAY_VLLM_BASE_URL="http://${HOST}:${MOCK_PORT}" \
GATEWAY_REDIS_URL="redis://127.0.0.1:6399/0" \
python -m uvicorn gateway.app.main:app --host "$HOST" --port "$GATEWAY_PORT" >/tmp/gateway-bench.log 2>&1 &
GATEWAY_PID=$!

cleanup() {
  for pid in "$GATEWAY_PID" "$MOCK_PID"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
      wait "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT

for _ in {1..40}; do
  if curl -fsS "http://${HOST}:${GATEWAY_PORT}/health" >/dev/null; then
    break
  fi
  sleep 0.25
done

python -m bench.run_bench \
  --gateway-url "http://${HOST}:${GATEWAY_PORT}" \
  --total-requests "$TOTAL_REQUESTS" \
  --concurrency "$CONCURRENCY"
