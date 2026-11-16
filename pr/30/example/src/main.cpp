// Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
// Licensed under the MIT License. See LICENSE for details.

#include <iostream>
#include "my_lib.hpp"

int main() {
    std::cout << "Hello World\n";
    std::cout << "Platform: " << CoverageClass::platformName() << '\n';
    CoverageClass coverage;
    coverage.functionCovered();
    return 0;
}
