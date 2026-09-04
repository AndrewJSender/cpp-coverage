# coverage-analytics

# Example

## Setup
```
export root_path=$(pwd)
python $root_path/example/submodules/cmake-project-generator/src/generate.py \
--source-dir=$root_path/example \
--build-dir=$root_path/build 
```


```sh
export LLVM_PROFILE_FILE=$HOME/Downloads/coverage.profraw
```

The script can also be run directly after an instrumented test has produced
`coverage.profraw`:

```sh
python src/generate_profile.py \
--test-binary=$root_path/build/submodules/googletest/googletest/Debug/sample1_unittest \
--output-directory=$LLVM_PROFILE_FILE
```
