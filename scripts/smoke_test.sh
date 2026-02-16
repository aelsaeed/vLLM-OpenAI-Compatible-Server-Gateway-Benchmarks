#!/usr/bin/env bash
set -euo pipefail

python -m pytest -q tests/test_safety.py
python - <<'PY'
from gateway.app.main import app

routes = {route.path for route in app.router.routes}
required = {"/health", "/metrics", "/chat", "/embed"}
missing = sorted(required - routes)
if missing:
    raise SystemExit(f"Missing expected routes: {missing}")
print("Smoke routes check passed")
PY
