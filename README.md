# llm-serving-gateway-bench

Local LLM serving stack using **vLLM (OpenAI-compatible server)** plus a lightweight **FastAPI gateway** with caching, rate limiting, safety toggles, and benchmarking utilities.

## Features

- OpenAI-compatible gateway proxy for chat and embeddings
- Redis cache with configurable TTL
- Rate limiting + request size limits
- Retry with exponential backoff
- Structured JSON logs (`request_id`, `model_id`)
- Safety toggles (max tokens cap, denylist demo)
- Prometheus metrics (`/metrics`)

## Architecture

```
client -> gateway (FastAPI) -> vLLM OpenAI-compatible server
                  |-> Redis (cache)
```

## Quickstart

### Prerequisites

- Docker + Docker Compose
- Python 3.11+ (for local dev and benchmarking)
- Optional: NVIDIA GPU + CUDA drivers (for fast inference)

### Run with GPU (recommended)

1. Edit `infra/docker-compose.yml` to select a model (see `MODEL` below).
2. Start the stack:

```
make up
```

This uses the `vllm/vllm-openai` image with GPU access. Ensure the NVIDIA Container Toolkit is installed.

### Run without GPU (CPU mode)

vLLM is optimized for GPUs. Running on CPU is **not recommended** and may not work for all models.
If you must run on CPU, set `USE_GPU=0` and expect very slow performance and possible model constraints.

```
USE_GPU=0 VLLM_HOST=vllm-cpu make up
```

## OpenAI-Compatibility & Model Swapping

The gateway forwards requests to vLLM’s OpenAI-compatible endpoints:

- `POST /v1/chat/completions`
- `POST /v1/embeddings` (if enabled)

To swap models, update `MODEL` in `infra/docker-compose.yml` or export it when launching:

```
MODEL=Qwen/Qwen2-0.5B-Instruct make up
```

Recommended small models:

- `Qwen/Qwen2-0.5B-Instruct`
- `TinyLlama/TinyLlama-1.1B-Chat-v1.0`
- `microsoft/phi-2` (may require extra memory)

## Gateway Endpoints

- `POST /chat` — forwards to vLLM chat completions (supports streaming)
- `POST /embed` — embedding pass-through if vLLM supports it; otherwise returns a stub response
- `GET /health`
- `GET /metrics` — Prometheus metrics (latency, cache hits, tokens/sec, request counts)

## Configuration

Gateway settings are controlled via `GATEWAY_` environment variables (see `gateway/app/config.py`).
Examples:

- `GATEWAY_CACHE_TTL_SECONDS=600`
- `GATEWAY_RATE_LIMIT_RPS=10`
- `GATEWAY_MAX_TOKENS_CAP=256`

## Benchmarking

The benchmark script sends concurrent requests and emits a Markdown report under `reports/`.

```
make bench
```

The report includes p50/p95 latency, throughput (req/s), approximate tokens/sec, and error rate.

### Interpreting Results

- **p50/p95 latency**: median and tail latency per request.
- **Throughput**: completed requests per second.
- **Tokens/sec**: approximate rate based on response usage.
- **Error rate**: failed requests / total.

## Troubleshooting

- **CUDA errors**: verify `nvidia-smi` works and the NVIDIA Container Toolkit is installed.
- **Model download issues**: ensure you have sufficient disk space and access to the model.
- **OOM**: use smaller models, reduce `max_tokens`, or set lower batch sizes.
- **CPU mode issues**: vLLM may not support your model on CPU; use GPU or a smaller model.

## Development

```
make lint
make test
```

## Repository Layout

```
bench/      # benchmark runner
data/       # prompt dataset
gateway/    # FastAPI gateway
infra/      # docker-compose and infra configs
reports/    # benchmark reports
tests/      # pytest coverage
```
