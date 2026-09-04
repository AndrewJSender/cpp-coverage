# coverage-analytics

# Example

## Constants
```zsh
export root_path=$(pwd)
export scheme="sample1_unittest"
```

### Setup with Clang Code Coverage

Note: Generates the XCode Project for MacOS

```zsh
cmake -G Xcode -S "$root_path/example" -B "$root_path/build" \
  -DENABLE_COVERAGE=ON \
  -DCOVERAGE_TOOL=llvm
```

## CMake Build, Test, Generate

```zsh
cmake --build "$root_path/build" --target generate_profile_data
```


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
python src/generate_profile.py \
--test-binary=$root_path/build/submodules/googletest/googletest/Debug/$scheme \
--output-directory=$HOME/Downloads/$scheme
```

## Run Website Locally
```
open http://localhost:8000/website
python -m http.server
```
