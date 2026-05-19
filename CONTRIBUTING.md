# Contributing to $repo

## Development Setup

```bash
# Clone the repo
git clone https://github.com/SuperInstance/$repo.git
cd $repo

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## Code Style

- Follow PEP 8
- Type hints required for all public APIs
- Docstrings required for all public classes and functions

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_*.py -v
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Ensure all tests pass
6. Push and open a PR
