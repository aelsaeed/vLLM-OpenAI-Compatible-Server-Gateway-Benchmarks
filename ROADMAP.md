# Roadmap

## Milestone 1: Stabilize demo
- Make `make demo` runnable in under a minute on a fresh Python 3.11 environment.
- Keep demo mode dry by default (no model download/GPU required).
- Add smoke checks for endpoints and startup health.

## Milestone 2: Observability + metrics
- Expand request/latency/token dashboards from `/metrics`.
- Add benchmark trend snapshots in CI artifacts.
- Improve structured logs for cache hits/misses and upstream failures.

## Milestone 3: Hardening + docs
- Tighten gateway failure handling and timeout policies.
- Add load-test scenarios and regression thresholds.
- Publish deployment and operations runbooks.
