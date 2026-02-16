# Contributing

Thanks for contributing to this project.

## Development setup
1. Use Python 3.11+
2. Install dependencies and hooks:
   ```bash
   make setup
   ```

## Local quality checks
Run before opening a PR:
```bash
make lint
make typecheck
make test
make demo
```

## Pull requests
- Keep changes focused and small when possible.
- Update README/CHANGELOG for user-facing behavior changes.
- Fill out the PR template checklist completely.
