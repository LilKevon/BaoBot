
import random
from collections import Counter

# Match cogs/slots.py
TRIPLE_MULTIPLIERS = [7, 5, 4, 3, 3, 3, 3, 3]

SIMULATIONS = 100_000
BET = 100
STARTING_BALANCE = 1_000_000


def simulate_spin(rng):
    roll = rng.randrange(100)

    if roll < 50:
        return "Loss", 0

    if roll < 98:
        return "Pair", 1.5

    multiplier = rng.choice(TRIPLE_MULTIPLIERS)
    return "Triple", multiplier


def simulate():
    rng = random.Random()

    balance = STARTING_BALANCE
    wagered = 0
    paid_out = 0
    outcomes = Counter()
    payouts = Counter()

    largest_payout = 0
    longest_loss_streak = 0
    current_loss_streak = 0
    completed = 0

    for _ in range(SIMULATIONS):
        if balance < BET:
            break

        outcome, multiplier = simulate_spin(rng)
        payout = int(BET * multiplier)

        balance += payout - BET
        wagered += BET
        paid_out += payout
        completed += 1

        outcomes[outcome] += 1
        payouts[multiplier] += 1

        largest_payout = max(largest_payout, payout)

        if outcome == "Loss":
            current_loss_streak += 1
            longest_loss_streak = max(
                longest_loss_streak, current_loss_streak
            )
        else:
            current_loss_streak = 0

    print("\n🎰 BAO SLOTS SIMULATOR 🎰")
    print("=" * 42)

    print(f"Requested spins: {SIMULATIONS:,}")
    print(f"Completed spins: {completed:,}")
    print(f"Bet per spin:    {BET:,} BC")

    print("\n💰 ECONOMY")
    print(f"Starting balance: {STARTING_BALANCE:,} BC")
    print(f"Final balance:    {balance:,} BC")
    print(f"Net profit:       {balance - STARTING_BALANCE:+,} BC")
    print(f"Total wagered:    {wagered:,} BC")
    print(f"Total paid out:   {paid_out:,} BC")

    if wagered:
        rtp = paid_out / wagered * 100
        print(f"Actual RTP:       {rtp:.2f}%")
        print("Expected RTP:     79.75%")

    print("\n🎲 OUTCOME DISTRIBUTION")

    for outcome, expected in [
        ("Loss", 50),
        ("Pair", 48),
        ("Triple", 2),
    ]:
        count = outcomes[outcome]
        percentage = count / completed * 100 if completed else 0

        print(
            f"{outcome:<8}: {count:>7,} "
            f"({percentage:>6.2f}%) "
            f"Expected: {expected}%"
        )

    print("\n🏆 TRIPLE JACKPOTS")

    for multiplier in [3, 4, 5, 7]:
        print(
            f"{multiplier}x payout: "
            f"{payouts[multiplier]:,} times"
        )

    print(f"\nBiggest payout: {largest_payout:,} BC")
    print(f"Longest loss streak: {longest_loss_streak}")

    if completed < SIMULATIONS:
        print("\n⚠️ Player ran out of BaoCoins!")


if __name__ == "__main__":
    simulate()
