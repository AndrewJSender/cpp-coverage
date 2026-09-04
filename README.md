# coverage-analytics

# Example

## Constants
```zsh
export root_path=$(pwd)
```

## Setup with Clang Code Coverage

Note: Generates the XCode Project for MacOS

```zsh
cmake -G Xcode -S "$root_path/example" -B "$root_path/build" \
  -DENABLE_COVERAGE=ON \
  -DCOVERAGE_TOOL=llvm
```

## CMake Build, Test, Generate All

```zsh
cmake --build "$root_path/build" --target generate_profile_data
```

### Build, Test, Generate Step-By-Step

### Select Target

```
export target="sample1_unittest"
```

### Build by Xcode

```
xcodebuild -project "$root_path/build/test_example.xcodeproj"  -scheme "$target"
```

### Build by CMake
```zsh
cmake --build "$root_path/build" --target "$target"
```


### Test
```zsh
export test_output_path="$root_path/build/$target""_output"
export LLVM_PROFILE_FILE="$test_output_path/coverage.profraw"
"$root_path/build/submodules/googletest/googletest/Debug/$target"
```

### Generate Profile & Website

```zsh
python src/generate_profile.py \
--test-binary="$root_path/build/submodules/googletest/googletest/Debug/$scheme" \
--output-directory="$test_output_path"
```

## Run Website Locally
```
open http://localhost:8000/website
python -m http.server
```
