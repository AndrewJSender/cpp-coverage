cmake_minimum_required(VERSION 3.15)
project(test_example VERSION 1.0 LANGUAGES CXX)

# Force C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Prevent GoogleTest from overriding your project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
set(gtest_build_samples ON CACHE BOOL "" FORCE)

# Add the submodule directory to your build.
# GoogleTest creates sample targets such as sample1_unittest when this option is enabled.
add_subdirectory(submodules/googletest EXCLUDE_FROM_ALL)

enable_testing()

# Apply code-coverage instrumentation only to the generated GoogleTest sample targets.
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    foreach(sample_target
            sample1_unittest
            sample2_unittest
            sample3_unittest
            sample4_unittest
            sample5_unittest
            sample6_unittest
            sample7_unittest
            sample8_unittest
            sample9_unittest
            sample10_unittest)
        if(TARGET ${sample_target})
            target_compile_options(${sample_target} PRIVATE -fprofile-instr-generate -fcoverage-mapping)
            target_link_options(${sample_target} PRIVATE -fprofile-instr-generate -fcoverage-mapping)
        endif()
    endforeach()
endif()
