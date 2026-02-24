import math

class HexGrid:
    def __init__(self, size=50, flat_top=True):
        self.size = size  # Outer radius (center to corner)
        self.flat_top = flat_top

    @property
    def width(self):
        # Distance between opposite corners
        if self.flat_top:
            return self.size * 2
        else:
            return math.sqrt(3) * self.size

    @property
    def height(self):
        # Distance between opposite sides
        if self.flat_top:
            return math.sqrt(3) * self.size
        else:
            return self.size * 2

    def hex_to_pixel(self, q, r):
        """
        Converts axial hex coordinates (q, r) to pixel coordinates (x, y).
        """
        if self.flat_top:
            x = self.size * (3/2 * q)
            y = self.size * (math.sqrt(3)/2 * q + math.sqrt(3) * r)
        else:
            x = self.size * (math.sqrt(3) * q + math.sqrt(3)/2 * r)
            y = self.size * (3/2 * r)
        return x, y

    def pixel_to_hex(self, x, y):
        """
        Converts pixel coordinates (x, y) to fractional hex coordinates (q, r).
        """
        if self.flat_top:
            q = (2/3 * x) / self.size
            r = (-1/3 * x + math.sqrt(3)/3 * y) / self.size
        else:
            q = (math.sqrt(3)/3 * x - 1/3 * y) / self.size
            r = (2/3 * y) / self.size
        return self.axial_round(q, r)

    def axial_round(self, q, r):
        """
        Rounds fractional hex coordinates to the nearest integer hex.
        """
        s = -q - r
        rq, rr, rs = round(q), round(r), round(s)
        
        q_diff = abs(rq - q)
        r_diff = abs(rr - r)
        s_diff = abs(rs - s)

        if q_diff > r_diff and q_diff > s_diff:
            rq = -rr - rs
        elif r_diff > s_diff:
            rr = -rq - rs
        # else s is unchanged (implied)
        
        return int(rq), int(rr)
