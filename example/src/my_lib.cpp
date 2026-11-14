// Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
// Licensed under the MIT License. See LICENSE for details.

#include <iostream>
#include "my_lib.hpp"

#if defined(_MSC_VER)
#define COVERAGE_EXAMPLE_PLATFORM "MSVC"
#elif defined(__APPLE__)
#include <TargetConditionals.h>
#if TARGET_OS_IPHONE
#define COVERAGE_EXAMPLE_PLATFORM "iOS"
#elif TARGET_OS_OSX
#define COVERAGE_EXAMPLE_PLATFORM "macOS"
#else
#define COVERAGE_EXAMPLE_PLATFORM "Apple"
#endif
#else
#define COVERAGE_EXAMPLE_PLATFORM "Other"
#endif

const char* CoverageClass::platformName() {
    return COVERAGE_EXAMPLE_PLATFORM;
}

void CoverageClass::functionCovered() {
    int x = 42;
    bool regionNotCovered = true;
    if (x == 42 || regionNotCovered) {
        std::cout << "x is 42\n";
    } else {
        std::cout << "branch not covered" << std::endl;
    }

    return;
    std::cout << "line not covered" << std::endl;
}

void CoverageClass::functionNotCovered() {}