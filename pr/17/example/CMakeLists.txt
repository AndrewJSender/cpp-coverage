cmake_minimum_required(VERSION 3.15)
project(test_example VERSION 1.0 LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Force C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(ENABLE_COVERAGE "Enable LLVM or Bullseye coverage instrumentation" OFF)
set(COVERAGE_TOOL "llvm" CACHE STRING "Coverage tool (llvm or bullseye)")
set_property(CACHE COVERAGE_TOOL PROPERTY STRINGS llvm bullseye)

add_executable(coverage_example src/main.cpp src/my_lib.cpp)
target_include_directories(coverage_example PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/include")

enable_testing()
add_test(NAME coverage_example COMMAND coverage_example)

set(COVERAGE_OUTPUT_DIR "${CMAKE_BINARY_DIR}/coverage_example_output")

if(ENABLE_COVERAGE AND COVERAGE_TOOL STREQUAL "llvm")
    if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        message(FATAL_ERROR "LLVM coverage requires a Clang compiler")
    endif()
    target_compile_options(coverage_example PRIVATE -fprofile-instr-generate -fcoverage-mapping)
    target_link_options(coverage_example PRIVATE -fprofile-instr-generate -fcoverage-mapping)

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

    file(MAKE_DIRECTORY "${COVERAGE_OUTPUT_DIR}")
    set(LLVM_PROFILE "${COVERAGE_OUTPUT_DIR}/coverage-%m-%p.profraw")
    set_tests_properties(coverage_example PROPERTIES
        ENVIRONMENT "LLVM_PROFILE_FILE=${LLVM_PROFILE}"
    )
    add_custom_target(generate_profile_data
        COMMAND ${CMAKE_CTEST_COMMAND} --build-config "$<CONFIG>" --output-on-failure
        COMMAND ${CMAKE_COMMAND} -E env
            "LLVM_PROFILE_FILE=${LLVM_PROFILE}"
            ${Python3_EXECUTABLE} "${CMAKE_SOURCE_DIR}/../src/generate_profile.py"
            --test-binary "$<TARGET_FILE:coverage_example>"
            --output-directory "${COVERAGE_OUTPUT_DIR}"
        DEPENDS coverage_example
        WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
        USES_TERMINAL
    )
elseif(ENABLE_COVERAGE AND COVERAGE_TOOL STREQUAL "bullseye")
    find_program(COV01 cov01 REQUIRED)
    find_program(COVXML covxml REQUIRED)
    file(MAKE_DIRECTORY "${COVERAGE_OUTPUT_DIR}")
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
        COMMAND ${CMAKE_CTEST_COMMAND} --build-config "$<CONFIG>" --output-on-failure
        COMMAND ${COVXML} --cobertura --output
            "${COVERAGE_OUTPUT_DIR}/coverage.xml"
        COMMAND ${COV01} --off
        DEPENDS coverage_example
        WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
        USES_TERMINAL
    )
endif()
