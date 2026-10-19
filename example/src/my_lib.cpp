// Copyright (c) 2026 Andrew J. Sender (AndrewJ.Sender@gmail.com)
// Licensed under the MIT License. See LICENSE for details.

#include <iostream>
#include "my_lib.hpp"

void CoverageClass::fnCovered() {
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

void CoverageClass::fnNotCovered() {}