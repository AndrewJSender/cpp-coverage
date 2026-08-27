// =====================================================================
// Project Name: MyAwesomeProject
// File Name: Coordinate.hpp
//
// Copyright (c) 2026 Andrew J. Sender <AndrewJ.Sender@gmail.com>
//
// This source code is licensed under the MIT License found in the
// LICENSE file in the root directory of this source tree.
// =====================================================================

#include <cmath>

#include "Coordinate.hpp"

Coordinate::Coordinate(double x, double y) : m_x(x), m_y(y) {}

Coordinate Coordinate::get() {
    return *this;
}

void Coordinate::set(double x, double y) {
    m_x = x;
    m_y = y;
}

double Coordinate::distanceTo(const Coordinate& other) const {
    double dx = m_x - other.m_x;
    double dy = m_y - other.m_y;
    return std::sqrt(dx * dx + dy * dy);
}
