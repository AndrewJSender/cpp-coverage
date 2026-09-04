cmake_minimum_required(VERSION 3.15)
project(test_example VERSION 1.0 LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Force C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(ENABLE_COVERAGE "Enable LLVM or Bullseye coverage instrumentation" OFF)
set(COVERAGE_TOOL "llvm" CACHE STRING "Coverage tool (llvm or bullseye)")
set_property(CACHE COVERAGE_TOOL PROPERTY STRINGS llvm bullseye)
set(COVERAGE_OUTPUT_DIR "${CMAKE_BINARY_DIR}/coverage")

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
        if(ENABLE_COVERAGE AND COVERAGE_TOOL STREQUAL "llvm" AND TARGET ${sample_target})
            target_compile_options(${sample_target} PRIVATE -fprofile-instr-generate -fcoverage-mapping)
            target_link_options(${sample_target} PRIVATE -fprofile-instr-generate -fcoverage-mapping)
        endif()
    endforeach()
endif()

file(MAKE_DIRECTORY "${COVERAGE_OUTPUT_DIR}")

if(ENABLE_COVERAGE AND COVERAGE_TOOL STREQUAL "llvm")
    find_program(LLVM_PROFDATA llvm-profdata)
    find_program(LLVM_COV llvm-cov)
    if(APPLE AND (NOT LLVM_PROFDATA OR NOT LLVM_COV))
        execute_process(
            COMMAND xcrun --find llvm-profdata
            OUTPUT_VARIABLE LLVM_PROFDATA
            OUTPUT_STRIP_TRAILING_WHITESPACE
            RESULT_VARIABLE LLVM_PROFDATA_RESULT
        )
        execute_process(
            COMMAND xcrun --find llvm-cov
            OUTPUT_VARIABLE LLVM_COV
            OUTPUT_STRIP_TRAILING_WHITESPACE
            RESULT_VARIABLE LLVM_COV_RESULT
        )
    endif()
    if(NOT LLVM_PROFDATA OR NOT LLVM_COV)
        message(FATAL_ERROR "LLVM coverage requires llvm-profdata and llvm-cov")
    endif()

    set(LLVM_PROFILE "${COVERAGE_OUTPUT_DIR}/coverage.profraw")
    add_custom_target(generate_profile_data
        COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure
        COMMAND ${LLVM_PROFDATA} merge -sparse
            "${LLVM_PROFILE}"
            -o "${COVERAGE_OUTPUT_DIR}/coverage.profdata"
        COMMAND ${LLVM_COV} export --format=text
            --instr-profile="${COVERAGE_OUTPUT_DIR}/coverage.profdata"
            "$<TARGET_FILE:sample1_unittest>"
            > "${COVERAGE_OUTPUT_DIR}/coverage_details.json"
        COMMAND ${LLVM_COV} export --format=text --summary-only
            --instr-profile="${COVERAGE_OUTPUT_DIR}/coverage.profdata"
            "$<TARGET_FILE:sample1_unittest>"
            > "${COVERAGE_OUTPUT_DIR}/coverage_summary.json"
        COMMAND ${LLVM_COV} show --format=html
            --output-dir="${COVERAGE_OUTPUT_DIR}/coverage_html"
            --instr-profile="${COVERAGE_OUTPUT_DIR}/coverage.profdata"
            "$<TARGET_FILE:sample1_unittest>"
        DEPENDS sample1_unittest
        WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
        USES_TERMINAL
    )
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
            add_test(NAME ${sample_target} COMMAND $<TARGET_FILE:${sample_target}>)
            set_tests_properties(${sample_target} PROPERTIES
                ENVIRONMENT "LLVM_PROFILE_FILE=${LLVM_PROFILE}"
            )
        endif()
    endforeach()
elseif(ENABLE_COVERAGE AND COVERAGE_TOOL STREQUAL "bullseye")
    find_program(COV01 cov01 REQUIRED)
    find_program(COVXML covxml REQUIRED)
    set(COVFILE "${COVERAGE_OUTPUT_DIR}/coverage.cov")

    add_custom_target(bullseye_on
        COMMAND ${COV01} --on
        COMMAND ${CMAKE_COMMAND} -E touch "${COVFILE}"
        USES_TERMINAL
    )
    add_custom_target(bullseye_off
        COMMAND ${COV01} --off
        USES_TERMINAL
    )
    add_custom_target(generate_profile_data
        COMMAND ${COV01} --on
        COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure
        COMMAND ${COVXML} --cobertura --output
            "${COVERAGE_OUTPUT_DIR}/coverage.xml"
        COMMAND ${COV01} --off
        WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
        USES_TERMINAL
    )
endif()
