// Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
// Licensed under the MIT License. See LICENSE for details.

#include <iostream>
#include "my_lib.hpp"

int main() {
    CoverageClass coverage;
    coverage.functionCovered();
    std::cout << "Platform: " << coverage.platformName() << std::endl;
    return 0;
}
