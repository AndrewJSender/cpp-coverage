# Tutorial Example

This is an example how to run a C++ (Clang) project ([example folder](../example/)) and check its code coverage.

# Setup Python Virtual Environment

Create the python virtual environment needed to run metabuild and its python modules.

```zsh
./get_habitat.sh
./habitat create code_coverage_mb
```

```powershell
.\get_habitat.bat
.\habitat.bat create code_coverage_mb
```

# Generate Project

Generate the Xcode project or Visual Studio solution. Notice the `--define="code_coverage.tool=clang"` argument is what adds [the code coverage compiler flags](https://clang.llvm.org/docs/SourceBasedCodeCoverage.html#compiling-with-coverage-enabled).
Also note, it is recommended to configure the project for the specific CPU architecture, `--define=mb.active_arch="arm64"` when checking code coverage.

## Mac ARM

```zsh
export arch="arm64"
./habitat run code_coverage_mb -- metabuild prepare --target="//example:test_binary" --define="code_coverage.tool=clang" --define=mb.active_arch="$arch"
```

## iOS ARM

```zsh
export platform="ios"
export arch="arm64"
export ios_sdk="iphonesimulator"
./habitat run code_coverage_mb -- metabuild prepare --platform="$platform" --target="//example:test_binary" --define="code_coverage.tool=clang"  --define=mb.active_arch="$arch" --define=mb.active_ios_sdk=$ios_sdk
```

## Windows x86

```powershell
$arch="x64"
.\habitat.bat run code_coverage_mb -- metabuild prepare --target="//example:test_binary" --define="code_coverage.tool=clang" --define=mb.active_arch="$arch"
```

## Windows x86 (Open C++ Coverage)

```powershell
$arch="x64"
.\habitat.bat run code_coverage_mb -- metabuild prepare --target="//example:test_binary" --define="code_coverage.tool=open_cpp_coverage" --define=mb.active_arch="$arch"
```

## Windows x86 (Bullseye)

```powershell
$env:COVFILE="$pwd\dist\tests\out\bullseye.cov"
$arch="x64"
.\habitat.bat run code_coverage_mb -- metabuild prepare --target="//example:test_binary" --define="code_coverage.tool=bullseye" --define=mb.active_arch="$arch"
```

# Build Project

Compile example library and test framework

## For desktop default

## For Mac and Linux
```zsh
./habitat run code_coverage_mb -- metabuild build --define=mb.active_arch="$arch"
```

## For Windows
```powershell 
.\habitat.bat run code_coverage_mb -- metabuild build --define=mb.active_arch="$arch"
```

## For iOS Simulator

```zsh
export platform="ios"
export ios_sdk="iphonesimulator"
./habitat run code_coverage_mb -- metabuild build --platform="$platform" --define=mb.active_arch="$arch" --define=mb.active_ios_sdk=$ios_sdk
```

# Run/Test Project

Run the test framework. This uses [the Google Test framework](https://google.github.io/googletest/).
The environment variable, `LLVM_PROFILE_FILE`, needs to be set before running the tests.
When the tests run, the file `coverage.profraw` will be generated.

## Mac

```zsh
export LLVM_PROFILE_FILE="$(pwd)/dist/tests/out/coverage.profraw"
./habitat run code_coverage_mb -- metabuild test --define=mb.active_arch="$arch"
```

## iOS

```zsh
export platform="ios"
export ios_sdk="iphonesimulator"
export SIMCTL_CHILD_LLVM_PROFILE_FILE="$(pwd)/dist/tests/out/coverage.profraw"
./habitat run code_coverage_mb -- metabuild test --platform="$platform" --define=mb.active_arch="$arch" --define=mb.active_ios_sdk=$ios_sdk
```

## Windows

```powershell
$env:LLVM_PROFILE_FILE="$pwd\dist\tests\out\coverage.profraw"
.\habitat.bat run code_coverage_mb -- metabuild test --define=mb.active_arch="$arch"
```

### Windows (Open C++ Coverage)

```powershell
$env:COVFILE="$pwd\dist\tests\out\bullseye.cov"
.\habitat.bat run code_coverage_mb -- metabuild test --define=mb.active_arch="$arch" --verbose
```

### Windows (Bullseye Coverage)

```powershell
$env:COVFILE="$pwd\dist\tests\out\bullseye.cov"
.\habitat.bat run code_coverage_mb -- metabuild test --define=mb.active_arch="$arch" --verbose
```

# Generate Profile Data

Generate the the code coverage profile data, `coverage.profdata` and `coverage_details.json`.
The environment variable, `LLVM_PROFILE_FILE`, needs to be set before profiling.

## Mac

```zsh
export arch="arm64"
export LLVM_PROFILE_FILE="$(pwd)/dist/tests/out/coverage.profraw"
./habitat run code_coverage_mb -- metabuild prepare --define=mb.active_arch="$arch" --target="//example:generate_profile_data" --define="code_coverage.tool=clang"
./habitat run code_coverage_mb -- metabuild build   --define=mb.active_arch="$arch"
```

## iOS

```zsh
export platform="ios"
export ios_sdk="iphonesimulator"
export arch="arm64"
export LLVM_PROFILE_FILE="$(pwd)/dist/tests/out/coverage.profraw"
./habitat run code_coverage_mb -- metabuild prepare --platform="$platform"  --define=mb.active_arch="$arch" --define=mb.active_ios_sdk=$ios_sdk --target="//example:generate_profile_data"
./habitat run code_coverage_mb -- metabuild build   --platform="$platform"  --define=mb.active_arch="$arch" --define=mb.active_ios_sdk=$ios_sdk
```

## Windows

```powershell
$arch="x64"
$env:LLVM_PROFILE_FILE="$pwd\dist\tests\out\coverage.profraw"
.\habitat run code_coverage_mb -- metabuild prepare --define=mb.active_arch="$arch" --target="//example:generate_profile_data"
.\habitat run code_coverage_mb -- metabuild build   --define=mb.active_arch="$arch"
```

### Windows (Open C++ Coverage)

```powershell
$arch="x64"
$env:COVFILE="$pwd\dist\tests\out\open_cpp_coverage.cov"
.\habitat run code_coverage_mb -- metabuild prepare --define=mb.active_arch="$arch" --define="code_coverage.tool=open_cpp_coverage" --target="//example:generate_profile_data"
.\habitat run code_coverage_mb -- metabuild build   --define=mb.active_arch="$arch"
```

# Generate Code Coverage Website

## Locally

### For Mac

```zsh
export LLVM_PROFILE_FILE="$(pwd)/dist/tests/out/coverage.profraw"
./habitat run code_coverage_mb -- metabuild prepare --define=mb.active_arch="$arch" --target="//example:generate_website"
./habitat run code_coverage_mb -- metabuild build   --define=mb.active_arch="$arch"
```

### For iOS

```zsh
export platform="ios"
export ios_sdk="iphonesimulator"
export arch="arm64"
export LLVM_PROFILE_FILE="$(pwd)/dist/tests/out/coverage.profraw"
./habitat run code_coverage_mb -- metabuild prepare  --platform="$platform"  --define=mb.active_arch="$arch" --define=mb.active_ios_sdk=$ios_sdk --target="//example:generate_website"
./habitat run code_coverage_mb -- metabuild build    --platform="$platform"  --define=mb.active_arch="$arch" --define=mb.active_ios_sdk=$ios_sdk
```

### For Windows

```powershell
$env:LLVM_PROFILE_FILE="$pwd\dist\tests\out\coverage.profraw"
.\habitat run code_coverage_mb -- metabuild prepare --define=mb.active_arch="$arch" --target="//example:generate_website"
.\habitat run code_coverage_mb -- metabuild build   --define=mb.active_arch="$arch"
```

### Windows (Open C++ Coverage)

```powershell
$arch="x64"
$env:COVFILE="$pwd\dist\tests\out\open_cpp_coverage.cov"
.\habitat run code_coverage_mb -- metabuild prepare --define=mb.active_arch="$arch" --define="code_coverage.tool=open_cpp_coverage" --target="//example:generate_website"
.\habitat run code_coverage_mb -- metabuild build   --define=mb.active_arch="$arch"
```

## Remotely (posix)

```zsh
export branch="main"
export build_number=7
./get_habitat.sh
./habitat create code_coverage_mb
./habitat run code_coverage_mb -- metabuild prepare --define="code_coverage.branch_name=$branch" --define="code_coverage.build_number=$build_number" --define="code_coverage.tool=clang" --target=//example:generate_website_from_remote
./habitat run code_coverage_mb -- metabuild build
```

# Run web server locally

There are many ways to have one's machine run as a web server. This seemed the simlest and most appropriate because we're using python.
Note this needs to run from the root path of the git repository.

```zsh
python -m http.server
```

## Open Code Coverage Website

### For Mac

```zsh
open http://localhost:8000/website/
```

### For Windows

```zsh
Start-Process http://localhost:8000/website/
```
## DVA Coverage Tool - Run Website

DVA developed a tool to profile and report code coverage.  This is another way to run the coverage report in a website.
https://git.corp.adobe.com/AdobeShared/coverage

### One-time setup

```
git clone https://git.corp.adobe.com/AdobeShared/coverage
cd coverage
export dva_coverage_path=$(pwd)
```

```
./scripts/setup_venv.sh
. ./.venv/bin/activate
./scripts/run_prechecks.sh
```

### Run servce_lcov

```
. $dva_coverage_path/.venv/bin/activate
cov serve_lcov --root="example" "dist/tests/out/coverage.lcov"
```
