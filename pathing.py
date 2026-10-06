from config import BOARD_SIZE


def shed_adjacent_tiles():
    half = BOARD_SIZE // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]


def is_shed_adjacent(x, y):
    return (x, y) in shed_adjacent_tiles()


def nearest_shed_tile(x, y):
    return min(shed_adjacent_tiles(), key=lambda p: abs(p[0] - x) + abs(p[1] - y))


def step_toward(fx, fy, tx, ty):
    """One greedy step direction command toward (tx, ty). None if already there."""
    dx, dy = tx - fx, ty - fy
    if dx == 0 and dy == 0:
        return None
    if abs(dx) >= abs(dy):
        return "EAST" if dx > 0 else "WEST"
    return "SOUTH" if dy > 0 else "NORTH"


def manhattan(fx, fy, tx, ty):
    return abs(tx - fx) + abs(ty - fy)
