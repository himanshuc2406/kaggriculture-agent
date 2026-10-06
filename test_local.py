"""
Usage:
    python test_local.py                  # 10 games vs starter
    python test_local.py --opponent random --n 20
    python test_local.py --render          # dump replay.json for one game
"""

import argparse
import json
from kaggle_environments import make


def run_games(opponent, n, episode_steps=720, render_first=False):
    results = []
    for seed in range(n):
        env = make("kaggriculture", configuration={"episodeSteps": episode_steps, "seed": seed}, debug=(seed == 0))
        env.run(["main.py", opponent])
        final = env.steps[-1]
        r0, r1 = final[0].reward, final[1].reward
        status0, status1 = final[0].status, final[1].status
        results.append((seed, r0, r1, status0, status1))

        if seed == 0 and render_first:
            with open("replay.json", "w") as f:
                json.dump(env.toJSON(), f)
            print("Saved replay.json for seed 0")

        if status0 == "ERROR" or status1 == "ERROR":
            print(f"[seed {seed}] ERROR — status0={status0} status1={status1}")

    return results


def summarize(results):
    n = len(results)
    wins = sum(1 for _, r0, r1, s0, s1 in results if s0 != "ERROR" and (s1 == "ERROR" or r0 > r1))
    losses = sum(1 for _, r0, r1, s0, s1 in results if s1 != "ERROR" and (s0 == "ERROR" or r1 > r0))
    ties = n - wins - losses
    avg_money = sum(r0 for _, r0, _, s0, _ in results if s0 != "ERROR") / max(
        1, sum(1 for _, _, _, s0, _ in results if s0 != "ERROR")
    )

    print(f"\n=== {n} games ===")
    print(f"Wins: {wins}  Losses: {losses}  Ties: {ties}  Win rate: {wins / n:.1%}")
    print(f"Avg final money (our agent): {avg_money:.0f}")
    for seed, r0, r1, s0, s1 in results:
        print(f"  seed {seed:>3}: us={r0:>8.1f} ({s0})  opp={r1:>8.1f} ({s1})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--opponent", default="starter", choices=["random", "starter", "pass"])
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--steps", type=int, default=720)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()

    results = run_games(args.opponent, args.n, args.steps, args.render)
    summarize(results)
