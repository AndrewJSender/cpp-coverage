// =====================================================================
// Project Name: MyAwesomeProject
// File Name: Coordinate.hpp
//
// Copyright (c) 2026 Andrew J. Sender <AndrewJ.Sender@gmail.com>
//
// This source code is licensed under the MIT License found in the
// LICENSE file in the root directory of this source tree.
// =====================================================================


#pragma once
class Coordinate {
public:
    Coordinate(double x, double y);

    Coordinate get();

    void set(double x, double y);

    double distanceTo(const Coordinate& other) const;

private:
    double m_x;
    double m_y;
};
