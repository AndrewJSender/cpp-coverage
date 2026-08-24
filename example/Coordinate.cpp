

#include <cmath>

#include "Coordinate.h"

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
