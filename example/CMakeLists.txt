cmake_minimum_required(VERSION 3.15)
project(test_example VERSION 1.0 LANGUAGES CXX)

# Force C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Prevent GoogleTest from overriding your project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)

# Add the submodule directory to your build (EXCLUDE_FROM_ALL prevents building targets you don't use)
add_subdirectory(submodules/googletest EXCLUDE_FROM_ALL)

# Enable testing capabilities in CMake
enable_testing()

# Add your source files here
add_executable(test_example main.cpp tests.cpp Coordinate.hpp Coordinate.cpp)

target_link_libraries(test_example PRIVATE GTest::gtest_main)

