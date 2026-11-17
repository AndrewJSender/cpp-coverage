// Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
// Licensed under the MIT License. See LICENSE for details.

#ifndef MY_LIB_HPP
#define MY_LIB_HPP

#if defined(__APPLE__)
#include <TargetConditionals.h>
#endif

class CoverageClass {
public:
    void functionCovered();
    void functionNotCovered();
    static const char* platformName() {
#if defined(_MSC_VER)
        return "MSVC";
#elif defined(TARGET_OS_IPHONE) && TARGET_OS_IPHONE
        return "iOS";
#elif defined(TARGET_OS_OSX) && TARGET_OS_OSX
        return "macOS";
#else
        return "Other";
#endif
    }
};

#endif // MY_LIB_HPP
