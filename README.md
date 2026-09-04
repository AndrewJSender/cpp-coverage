# coverage-analytics

# Example

## Constants
```zsh
export root_path=$(pwd)
export scheme="sample1_unittest"
```

## Setup
```zsh
python $root_path/example/submodules/cmake-project-generator/src/generate.py \
--source-dir=$root_path/example \
--build-dir=$root_path/build 
```

### Turn on Clang Code Coverage
```zsh
cmake -S "$root_path/example" -B "$root_path/build" \
  -DENABLE_COVERAGE=ON \
  -DCOVERAGE_TOOL=llvm
```

On macOS, CMake uses `xcrun` to locate `llvm-profdata` and `llvm-cov` when
they are not already on `PATH`.

## Build
```
xcodebuild -project "$root_path/build/test_example.xcodeproj"  -scheme "$scheme"
```

## Test
```zsh
export LLVM_PROFILE_FILE="$HOME/Downloads/$scheme/coverage.profraw"
"$root_path/build/submodules/googletest/googletest/Debug/$scheme"
```

## Generate Profile & Website

```zsh
cmake --build "$root_path/build" --target generate_profile_data
```

Alternatively, run the Python report generator after the instrumented test
has created `coverage.profraw`:

```zsh
python src/generate_profile.py \
--test-binary=$root_path/build/submodules/googletest/googletest/Debug/$scheme \
--output-directory=$HOME/Downloads/$scheme
```

Reports are written to `build/coverage`, and website data is written to
`website/data`.

## Run Website Locally
```
open http://localhost:8000/website
python -m http.server
```
