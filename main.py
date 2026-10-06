"""
Kaggriculture agent v1 — rule-based priority FSM.
Strategy: wheat bootstrap -> melon/carrot rotation -> goose ranching -> hire hands
          once task queue depth justifies fib hire cost. Sells throttled per-turn
          to avoid crashing own price on premium goods.
"""

# NOTE: kaggle_environments appends this file's directory to sys.path before
# exec'ing it, so plain imports of sibling modules (config.py, state.py,
# pathing.py) work for both local runs (env.run(["main.py", ...])) and
# Kaggle's competition runner. Do not add __file__-based path logic here —
# __file__ is not defined in the exec'd namespace and will raise NameError.
from config import CROPS, ANIMALS, SELL_CAP_PER_TURN, MAX_MARKET_ORDERS, FERTILIZER_COST
from state import GameState
from pathing import step_toward, is_shed_adjacent, nearest_shed_tile, manhattan

PLANT_CAP = 4  # fixed, not scaled by same-day hand count — see scan_tasks() comment

WHEAT_SEED_RESERVE = 3
WHEAT_SEED_BUY_MONEY_FLOOR = 200      # keep this much cash buffer before buying seeds
MELON_UNLOCK_MONEY = 500
GOOSE_UNLOCK_MONEY = 1200
HIRE_TASK_THRESHOLD = 4               # min unassigned tasks to justify hiring another hand
LAND_BUY_MONEY_FLOOR = 1500


# ---------- tile-local actions (unit already standing on the tile) ----------

def local_action_for_plant(state, tile, day):
    crop = tile["crop"]
    spec = CROPS[crop]

    if tile["consecutive_unwatered"] >= 1 and not tile["watered_today"]:
        return ["WATER"]

    ready = tile["yield_units"] > 0
    is_ongoing = spec["ongoing"]
    past_first_yield = (day - tile["planted_day"]) >= spec["first_yield_day"]
    if ready and (is_ongoing or past_first_yield):
        return ["HARVEST"]

    if not tile["watered_today"]:
        return ["WATER"]

    if (not is_ongoing and tile["fertilized_until_day"] < day
            and state.shed.get("FERTILIZER", 0) > 0
            and (day - tile["planted_day"]) < spec["max_yield_day"]):
        return ["FERTILIZE"]

    return None


def local_action_for_structure(state, tile, day):
    if tile["animal"] is None:
        return None

    if tile["consecutive_unfed"] >= 1 and not tile["fed_today"]:
        if state.shed.get("WHEAT", 0) > 0:
            return ["FEED"]

    if tile["yield_units"] > 0:
        return ["HARVEST"]

    if not tile["fed_today"] and state.shed.get("WHEAT", 0) > 0:
        return ["FEED"]

    if tile["fertilizer_available"]:
        return ["COLLECT_FERTILIZER"]

    if not tile["cared_today"]:
        return ["CARE"]

    return None


def active_plant_count(state):
    return sum(1 for _, _, t in state.iter_tiles() if isinstance(t, dict) and t.get("kind") == "PLANT")


def local_action(state, x, y, inv):
    tile = state.tile_at(x, y)

    if is_shed_adjacent(x, y) and sum(v for k, v in inv.items()) > 0:
        return ["DROP"]

    if isinstance(tile, dict):
        kind = tile.get("kind")
        if kind == "PLANT":
            act = local_action_for_plant(state, tile, state.day)
            if act:
                return act
        elif kind in ("COOP", "PASTURE"):
            act = local_action_for_structure(state, tile, state.day)
            if act:
                return act
        elif kind == "WEED":
            return ["DIG"]

    if tile is None and state.seeds.get("WHEAT", 0) > 0 and active_plant_count(state) < PLANT_CAP:
        return ["PLANT", "WHEAT"]

    return None


# ---------- global task scanning (for units with nothing to do locally) ----------

def scan_tasks(state):
    """Returns list of (priority, x, y, kind) — lower priority number = more urgent."""
    tasks = []
    day = state.day
    for x, y, tile in state.iter_tiles():
        if not isinstance(tile, dict):
            continue
        kind = tile.get("kind")
        if kind == "PLANT":
            crop = tile["crop"]
            spec = CROPS[crop]
            urgent = tile["consecutive_unwatered"] >= 1 and not tile["watered_today"]
            ready = tile["yield_units"] > 0 and (
                spec["ongoing"] or (day - tile["planted_day"]) >= spec["first_yield_day"]
            )
            if urgent:
                tasks.append((0, x, y, "water"))
            elif ready:
                tasks.append((1, x, y, "harvest"))
            elif not tile["watered_today"]:
                tasks.append((2, x, y, "water"))
        elif kind in ("COOP", "PASTURE") and tile["animal"] is not None:
            urgent = tile["consecutive_unfed"] >= 1 and not tile["fed_today"]
            if urgent:
                tasks.append((0, x, y, "feed"))
            elif tile["yield_units"] > 0:
                tasks.append((1, x, y, "harvest"))
            elif not tile["fed_today"]:
                tasks.append((2, x, y, "feed"))
            elif tile["fertilizer_available"]:
                tasks.append((3, x, y, "collect_fert"))
            elif not tile["cared_today"]:
                tasks.append((3, x, y, "care"))
        elif kind == "WEED":
            tasks.append((3, x, y, "dig"))

    # planting: throttled to PLANT_CAP so the farmer/hands don't keep planting
    # new tiles and starve older ones of water/harvest (which turns them to
    # weeds and burns seed cost for nothing). TUNE: raise once hiring is a
    # persistent daily habit rather than opportunistic.
    if state.seeds.get("WHEAT", 0) > 0 and active_plant_count(state) < PLANT_CAP:
        for x, y, tile in state.iter_tiles():
            if tile is None:
                tasks.append((4, x, y, "plant"))  # lowest priority: service existing plants first
                break

    tasks.sort(key=lambda t: t[0])
    return tasks


def assign_and_move(state, units_needing_task):
    """Greedy nearest-task assignment for units with no local action."""
    tasks = scan_tasks(state)
    used = set()
    actions = {}

    for idx, x, y, inv in units_needing_task:
        best = None
        best_dist = None
        for i, (prio, tx, ty, kind) in enumerate(tasks):
            if i in used:
                continue
            d = manhattan(x, y, tx, ty)
            score = (prio, d)
            if best is None or score < best[0]:
                best = (score, i, tx, ty)
        if best is None:
            actions[idx] = ["PASS"]
            continue
        _, i, tx, ty = best
        used.add(i)
        direction = step_toward(x, y, tx, ty)
        actions[idx] = [direction] if direction else ["PASS"]

    return actions


# ---------- economy / market orders ----------

def build_market_orders(state):
    orders = []
    money = state.money
    shed = state.shed

    # throttled sells first (revenue funds everything else this turn's processing order)
    for item, cap in SELL_CAP_PER_TURN.items():
        qty = min(shed.get(item, 0), cap)
        if qty > 0 and len(orders) < MAX_MARKET_ORDERS:
            orders.append(["SELL", item, qty])

    if len(orders) >= MAX_MARKET_ORDERS:
        return orders[:MAX_MARKET_ORDERS]

    # seed buys
    wheat_seeds = state.seeds.get("WHEAT", 0)
    if (wheat_seeds < WHEAT_SEED_RESERVE
            and money >= WHEAT_SEED_BUY_MONEY_FLOOR + CROPS["WHEAT"]["seed_cost"]):
        orders.append(["BUY_SEED", "WHEAT", WHEAT_SEED_RESERVE - wheat_seeds])

    if money >= MELON_UNLOCK_MONEY + CROPS["MELON"]["seed_cost"] and state.seeds.get("MELON", 0) == 0:
        orders.append(["BUY_SEED", "MELON", 1])

    # animals
    if money >= GOOSE_UNLOCK_MONEY + ANIMALS["GOOSE"]["cost"]:
        has_empty_coop = any(
            isinstance(t, dict) and t.get("kind") == "COOP" and t.get("animal") is None
            for _, _, t in state.iter_tiles()
        )
        has_coop = any(isinstance(t, dict) and t.get("kind") == "COOP" for _, _, t in state.iter_tiles())
        if not has_coop:
            pass  # need BUILD_COOP first, handled by unit action layer in a future iteration
        elif has_empty_coop:
            orders.append(["BUY_ANIMAL", "GOOSE", 1])

    if len(orders) >= MAX_MARKET_ORDERS:
        return orders[:MAX_MARKET_ORDERS]

    # hire hand if task backlog is deep and money comfortable — capped at 1/day
    # for v1 (fib hire cost escalates fast: 1,1,2,3,5,8,... per extra hand).
    tasks = scan_tasks(state)
    if (len(tasks) >= HIRE_TASK_THRESHOLD and money >= LAND_BUY_MONEY_FLOOR
            and state.hires_today < 1):
        orders.append(["HIRE"])

    # land expansion once cash-rich and current land looks full
    empty_tiles = sum(1 for _, _, t in state.iter_tiles() if t is None)
    if empty_tiles <= 2 and money >= LAND_BUY_MONEY_FLOOR:
        orders.append(["BUY_LAND"])

    return orders[:MAX_MARKET_ORDERS]


# ---------- top-level agent ----------

def agent(obs):
    state = GameState(obs)

    units = state.all_unit_positions()  # [(idx, x, y, inv), ...]
    unit_actions = {}
    remaining = []

    for idx, x, y, inv in units:
        act = local_action(state, x, y, inv)
        if act:
            unit_actions[idx] = act
        else:
            remaining.append((idx, x, y, inv))

    if remaining:
        unit_actions.update(assign_and_move(state, remaining))

    farmer_action = unit_actions.get(0, ["PASS"])
    hand_actions = [unit_actions.get(i + 1, ["PASS"]) for i in range(len(state.hand_positions))]
    market_orders = build_market_orders(state)

    return {"farmer": farmer_action, "hands": hand_actions, "market": market_orders}
