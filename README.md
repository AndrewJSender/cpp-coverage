# C++ Code Coverage

A small coverage tooling project for generating coverage reports and a static website view from test outputs.

## Installation

```zsh
pip install coverage-analytics
```

## Quick start

```zsh
# Generate coverage reports and website data from an instrumented test binary.
coverage-analytics profile --test-binary build/Debug/coverage_example \
  --output-directory build/coverage_example_output

# Analyze coverage of lines changed since main.
coverage-analytics diff main --coverage build/coverage_example_output

# Enforce the changed-coverage gate in CI (GitHub Actions).
coverage-analytics diff "$BASE_SHA...HEAD" --coverage build/coverage_example_output \
  --format json > diff-coverage.json
coverage-analytics gate diff-coverage.json
```

## Documentation

### Getting started

- [Build and run the example](docs/getting-started.md)

### Guides

- [Changed-code coverage](docs/changed-code-coverage.md)
- [Coverage website](docs/coverage-website.md)

### Reference

- [Coverage tools and report formats](docs/reference.md)

## License

Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
