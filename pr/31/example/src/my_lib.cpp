// Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
// Licensed under the MIT License. See LICENSE for details.

#include <iostream>
#include "my_lib.hpp"

#if defined(__APPLE__)
#include <TargetConditionals.h>
#endif

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

std::string CoverageClass::platformName() {
    std::string platform_name;
#if defined(_MSC_VER)
    platform_name = "MSVC";
#elif defined(TARGET_OS_IPHONE) && TARGET_OS_IPHONE
    platform_name = "iOS";
#elif defined(TARGET_OS_OSX) && TARGET_OS_OSX
    platform_name = "macOS";
#else
    platform_name = "Other";
#endif
    return platform_name;
}
