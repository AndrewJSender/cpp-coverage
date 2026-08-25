


#include <gtest/gtest.h>

#include "Coordinate.hpp"

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
    EXPECT_EQ(c1.distanceTo(c2), 12);
}
