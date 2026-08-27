// =====================================================================
// Project Name: MyAwesomeProject
// File Name: Coordinate.hpp
//
// Copyright (c) 2026 Andrew J. Sender <AndrewJ.Sender@gmail.com>
//
// This source code is licensed under the MIT License found in the
// LICENSE file in the root directory of this source tree.
// =====================================================================


#include <gtest/gtest.h>

#include "Coordinate.hpp"

#include <unistd.h>

TEST(SampleTest, Addition) {
  bool condition = 1 + 1 == 2;
  EXPECT_TRUE(condition);
}

TEST(SampleTest, Subraction) {
  bool condition = 1-1 == 0;
  EXPECT_TRUE(condition);
}

TEST(Coordinate, Distance) {
    Coordinate c1(0,0);
    Coordinate c2(1,0);
    sleep(2);
    EXPECT_EQ(c1.distanceTo(c2), 1);
}
