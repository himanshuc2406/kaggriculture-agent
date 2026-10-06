"""Static game data. Keep in sync with the competition's Object Types / Price Function tables."""

BOARD_SIZE = 10
SHED_CAPACITY = 100
TURNS_PER_DAY = 24

CROPS = {
    # seed_cost, base_price, first_yield_day, max_yield_day, max_yield (fertilized), unfert_max, ongoing
    "WHEAT":      {"seed_cost": 10,  "base_price": 25,  "first_yield_day": 2,  "max_yield_day": 4,  "max_yield": 6, "unfert_max": 4, "ongoing": False},
    "CARROT":     {"seed_cost": 20,  "base_price": 35,  "first_yield_day": 2,  "max_yield_day": 3,  "max_yield": 4, "unfert_max": 3, "ongoing": False},
    "MELON":      {"seed_cost": 80,  "base_price": 250, "first_yield_day": 10, "max_yield_day": 10, "max_yield": 6, "unfert_max": 6, "ongoing": False},
    "TOMATO":     {"seed_cost": 50,  "base_price": 60,  "first_yield_day": 8,  "max_yield_day": 11, "max_yield": 4, "ongoing": True,  "interval": 1},
    "STRAWBERRY": {"seed_cost": 100, "base_price": 120, "first_yield_day": 10, "max_yield_day": 16, "max_yield": 4, "ongoing": True,  "interval": 2},
}

ANIMALS = {
    "GOOSE": {"cost": 300, "product": "EGG",  "structure": "COOP",    "base_price": 50,  "interval": 1, "max_held": 4},
    "COW":   {"cost": 400, "product": "MILK", "structure": "PASTURE", "base_price": 160, "interval": 2, "max_held": 6},
    "SHEEP": {"cost": 500, "product": "WOOL", "structure": "PASTURE", "base_price": 200, "interval": 3, "max_held": 6},
}

FERTILIZER_COST = 100
LAND_COSTS = [1000, 2000, 4000]  # cost of 2nd, 3rd, 4th quadrant

# Per-turn sell cap per product — throttle to avoid crashing our own price.
# Premium goods (base > 100) crash hard on gluts, so cap them tighter.
SELL_CAP_PER_TURN = {
    "WHEAT": 8, "CARROT": 6, "TOMATO": 4, "STRAWBERRY": 2,
    "MELON": 3, "EGG": 6, "MILK": 3, "WOOL": 2, "FERTILIZER": 4,
}

MAX_MARKET_ORDERS = 10
