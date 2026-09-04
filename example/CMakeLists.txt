cmake_minimum_required(VERSION 3.15)
project(test_example VERSION 1.0 LANGUAGES CXX)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Force C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(ENABLE_COVERAGE "Enable LLVM or Bullseye coverage instrumentation" OFF)
set(COVERAGE_TOOL "llvm" CACHE STRING "Coverage tool (llvm or bullseye)")
set_property(CACHE COVERAGE_TOOL PROPERTY STRINGS llvm bullseye)

# Prevent GoogleTest from overriding your project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
set(gtest_build_samples ON CACHE BOOL "" FORCE)

# Add the submodule directory to your build.
# GoogleTest creates sample targets such as sample1_unittest when this option is enabled.
add_subdirectory(submodules/googletest EXCLUDE_FROM_ALL)

enable_testing()

set(SAMPLE_UNIT_TEST_LIST)
foreach(sample_index RANGE 1 10)
    set(sample_target "sample${sample_index}_unittest")
    list(APPEND SAMPLE_UNIT_TEST_LIST ${sample_target})
endforeach()

# Apply code-coverage instrumentation only to the generated GoogleTest sample targets.
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    foreach(sample_target IN LISTS SAMPLE_UNIT_TEST_LIST)
        if(ENABLE_COVERAGE AND COVERAGE_TOOL STREQUAL "llvm" AND TARGET ${sample_target})
            target_compile_options(${sample_target} PRIVATE -fprofile-instr-generate -fcoverage-mapping)
            target_link_options(${sample_target} PRIVATE -fprofile-instr-generate -fcoverage-mapping)
        endif()
    endforeach()
endif()

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

    set(PROFILE_COMMANDS)
    set(PROFILE_TARGETS)
    foreach(sample_target IN LISTS SAMPLE_UNIT_TEST_LIST)
        set(COVERAGE_OUTPUT_DIR "${CMAKE_BINARY_DIR}/${sample_target}_output")
        file(MAKE_DIRECTORY "${COVERAGE_OUTPUT_DIR}")
        set(LLVM_PROFILE "${COVERAGE_OUTPUT_DIR}/coverage.profraw")
        if(TARGET ${sample_target})
            list(APPEND PROFILE_TARGETS ${sample_target})
            list(APPEND PROFILE_COMMANDS
                COMMAND ${CMAKE_COMMAND} -E env
                    "LLVM_PROFILE_FILE=${LLVM_PROFILE}"
                    ${Python3_EXECUTABLE} "${CMAKE_SOURCE_DIR}/../src/generate_profile.py"
                    --test-binary "$<TARGET_FILE:${sample_target}>"
                    --output-directory "${COVERAGE_OUTPUT_DIR}"
            )
            add_test(NAME ${sample_target} COMMAND $<TARGET_FILE:${sample_target}>)
            set_tests_properties(${sample_target} PROPERTIES
                ENVIRONMENT "LLVM_PROFILE_FILE=${LLVM_PROFILE}"
            )
        endif()
    endforeach()
    add_custom_target(generate_profile_data
        COMMAND ${CMAKE_CTEST_COMMAND} --build-config "$<CONFIG>" --output-on-failure
        ${PROFILE_COMMANDS}
        DEPENDS ${PROFILE_TARGETS}
        WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
        USES_TERMINAL
    )
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
        COMMAND ${CMAKE_CTEST_COMMAND} --build-config "$<CONFIG>" --output-on-failure
        COMMAND ${COVXML} --cobertura --output
            "${COVERAGE_OUTPUT_DIR}/coverage.xml"
        COMMAND ${COV01} --off
        WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
        USES_TERMINAL
    )
endif()
