#!/usr/bin/env bash
set -euo pipefail

GATEWAY_PORT="${DEMO_GATEWAY_PORT:-8010}"
MOCK_PORT="${DEMO_MOCK_PORT:-18000}"
HOST="${DEMO_HOST:-127.0.0.1}"

printf 'Starting mock OpenAI server on %s:%s\n' "$HOST" "$MOCK_PORT"
python -m uvicorn scripts.mock_openai_server:app --host "$HOST" --port "$MOCK_PORT" >/tmp/mock-openai-demo.log 2>&1 &
MOCK_PID=$!

printf 'Starting gateway demo server on %s:%s (CPU/no-GPU mode)\n' "$HOST" "$GATEWAY_PORT"
GATEWAY_VLLM_BASE_URL="http://${HOST}:${MOCK_PORT}" \
GATEWAY_REDIS_URL="redis://127.0.0.1:6399/0" \
python -m uvicorn gateway.app.main:app --host "$HOST" --port "$GATEWAY_PORT" >/tmp/gateway-demo.log 2>&1 &
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
  if curl -fsS "http://${HOST}:${GATEWAY_PORT}/health" >/tmp/demo-health.json; then
    break
  fi
  sleep 0.25
done

if ! test -s /tmp/demo-health.json; then
  echo "Demo failed: gateway did not become ready."
  echo "See /tmp/gateway-demo.log and /tmp/mock-openai-demo.log for details."
  exit 1
fi

curl -fsS "http://${HOST}:${GATEWAY_PORT}/chat" \
  -H 'Content-Type: application/json' \
  -H 'x-request-id: demo-req-1' \
  -d '{"messages":[{"role":"user","content":"hello from demo"}],"max_tokens":32}' >/tmp/demo-chat.json

echo "Health response:"
cat /tmp/demo-health.json
echo

echo "Chat response summary:"
python - <<'PY'
import json
with open('/tmp/demo-chat.json') as f:
    data = json.load(f)
choice = data['choices'][0]['message']['content']
usage = data.get('usage', {})
print({'assistant_preview': choice[:60], 'usage': usage})
PY

echo "Demo passed (CPU/no-GPU mock mode). For full GPU-backed mode, run: make up-gpu"
