# Getting Started

A small coverage tooling project for generating coverage reports and a static website view from test outputs.

## Overview

This project reads coverage artifacts from tools such as LLVM, Bullseye, and OpenCppCoverage, converts them into a consistent summary format, and generates a local website for exploring the results.

## Installation

Install the `coverage-analytics` command line tool from PyPI, or in editable mode from a checkout:

```zsh
pip install coverage-analytics
# or, from a checkout:
pip install -e .
```

The CLI provides three commands:

- `coverage-analytics profile`: generate coverage reports and website data from test outputs
- `coverage-analytics diff`: analyze coverage of changed lines between Git revisions
- `coverage-analytics gate`: enforce the changed-coverage gate in CI

## Example

The example builds a single `coverage_example` executable from `example/src/main.cpp`.

### Constants
```zsh
export root_path=$(pwd)
```

### Setup with Clang Code Coverage

Note: Generates the Xcode project for macOS.

```zsh
export root_path=$(pwd)
cmake -G Xcode -S "$root_path/example" -B "$root_path/build" \
 -DENABLE_COVERAGE=ON \
 -DCOVERAGE_TOOL=llvm
```

### CMake Build, Test, Generate Coverage Data

```zsh
export root_path=$(pwd)
cmake --build "$root_path/build" --target generate_profile_data
```

### Build, Test, Generate Step-by-Step

#### Select Target

```zsh
export target="coverage_example"
```

#### Build by Xcode

```zsh
xcodebuild -project "$root_path/build/test_example.xcodeproj" -scheme "$target"
```

#### Build by CMake

```zsh
cmake --build "$root_path/build" --target "$target"
```

#### Test

```zsh
export test_output_path="$root_path/build/$target""_output"
export LLVM_PROFILE_FILE="$test_output_path/coverage.profraw"
"$root_path/build/Debug/$target"
```

#### Generate Profile & Website

```zsh
pip install -e .
coverage-analytics profile \
 --test-binary="$root_path/build/Debug/$target" \
 --output-directory="$test_output_path"
```
