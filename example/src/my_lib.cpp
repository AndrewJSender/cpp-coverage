// Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
// Licensed under the MIT License. See LICENSE for details.

#include <iostream>
#include "my_lib.hpp"

#if defined(__APPLE__)
#include <TargetConditionals.h>
#endif

const char* CoverageClass::platformName() {
#if defined(_MSC_VER)
    return "MSVC";
#elif TARGET_OS_IPHONE
    return "iOS";
#elif TARGET_OS_OSX
    return "macOS";
#else
    return "Other";
#endif
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