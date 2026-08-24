

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
