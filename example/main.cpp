// =====================================================================
// Copyright (c) 2026 Andrew J. Sender <AndrewJ.Sender@gmail.com>
//
// This source code is licensed under the MIT License found in the
// LICENSE file in the root directory of this source tree.
// =====================================================================

#include <gtest/gtest.h>

int main(int argc, char** argv) {
    bool gtest_stdout = true;
    testing::InitGoogleTest(&argc, argv);
    
    // process remaining arguemnts
    for (int i = 0; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--gtest1_stdout=0") {
            gtest_stdout = false;
        }
    }
    if (!gtest_stdout) {
        testing::TestEventListeners& listeners = testing::UnitTest::GetInstance()->listeners();
        delete listeners.Release(listeners.default_result_printer());
    }
    
    int code = RUN_ALL_TESTS();
    return code;
}
