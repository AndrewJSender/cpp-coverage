# coverage-analytics

# Example

## Setup
```
export root_path=$(pwd)
python $root_path/example/submodules/cmake-project-generator/src/generate.py \
--source-dir=$root_path/example \
--build-dir=$root_path/build 
```

## CMake coverage

Configure with LLVM coverage enabled, then generate the profile report:

```sh
cmake -S example -B build -DENABLE_COVERAGE=ON -DCOVERAGE_TOOL=llvm
cmake --build build --target generate_profile_data
```

The CMake `generate_profile_data` target replaces the former metabuild
`mb.genrule` and writes reports under `build/coverage`.
