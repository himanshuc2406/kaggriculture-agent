"""Parses the raw observation dict into convenient accessors. No mutation of obs."""

from config import BOARD_SIZE


class GameState:
    def __init__(self, obs):
        self.obs = obs
        self.player = obs["player"]
        self.day = obs["day"]
        self.hour = obs["hour"]
        self.farm = obs["farms"][self.player]
        self.opp_farm = obs["farms"][1 - self.player]
        self.market = obs["market"]
        self.town = obs["town"]
        self.private = obs["private"]

    @property
    def money(self):
        return self.farm["money"]

    @property
    def tiles(self):
        return self.farm["tiles"]

    @property
    def farmer_pos(self):
        return tuple(self.farm["farmer"])

    @property
    def hand_positions(self):
        return [tuple(p) for p in self.farm["hands"]]

    @property
    def unlocked_quadrants(self):
        return set(self.farm["unlocked_quadrants"])

    @property
    def hires_today(self):
        return self.farm["hires_today"]

    @property
    def shed(self):
        return self.private["shed"]

    @property
    def seeds(self):
        return self.private["seeds"]

    @property
    def inventories(self):
        # index 0 = farmer, rest = hands, in same order as farm["hands"]
        return self.private["inventories"]

    def tile_at(self, x, y):
        if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
            return self.tiles[y][x]
        return "LOCKED"

    def price(self, item):
        return self.market["prices"].get(item, 0)

    def all_unit_positions(self):
        """[(index, x, y, inventory)] — index 0 is farmer, 1..n are hands, in hands order."""
        units = [(0, self.farmer_pos[0], self.farmer_pos[1], self.inventories[0])]
        for i, pos in enumerate(self.hand_positions):
            units.append((i + 1, pos[0], pos[1], self.inventories[i + 1]))
        return units

    def iter_tiles(self):
        """Yield (x, y, tile) for every non-locked tile."""
        for y in range(BOARD_SIZE):
            row = self.tiles[y]
            for x in range(BOARD_SIZE):
                t = row[x]
                if t != "LOCKED":
                    yield x, y, t
