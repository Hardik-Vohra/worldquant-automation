from elite_fields import TOP_FIELDS
import random

alphas = set()

windows_short = [20, 63]
windows_long = [126, 252]

# =====================
# FAMILY 1
# Earnings Momentum
# =====================

for field in TOP_FIELDS:

    for w in windows_long:

        alphas.add(
            f"rank(ts_rank({field},{w}))"
        )

        alphas.add(
            f"rank(ts_zscore({field},{w}))"
        )

        alphas.add(
            f"rank(-ts_zscore({field},{w}))"
        )

# =====================
# FAMILY 2
# Revisions
# =====================

for field in TOP_FIELDS:

    for w in windows_short:

        alphas.add(
            f"rank(ts_delta({field},{w}))"
        )

        alphas.add(
            f"rank(ts_delta({field},{w})/ts_std_dev({field},252))"
        )

# =====================
# FAMILY 3
# Relative To Mean
# =====================

for field in TOP_FIELDS:

    for w in windows_long:

        alphas.add(
            f"rank({field}/ts_mean({field},{w}))"
        )

# =====================
# FAMILY 4
# Pair Signals
# =====================

for i in range(len(TOP_FIELDS)):

    for j in range(i + 1, len(TOP_FIELDS)):

        f1 = TOP_FIELDS[i]
        f2 = TOP_FIELDS[j]

        alphas.add(
            f"rank({f1}/{f2})"
        )

        alphas.add(
            f"rank({f1}*{f2})"
        )

        alphas.add(
            f"rank(ts_rank({f1},252)-ts_rank({f2},252))"
        )

        alphas.add(
            f"rank(ts_zscore({f1},126)-ts_zscore({f2},126))"
        )

# =====================
# FAMILY 5
# Low Turnover
# =====================

for field in TOP_FIELDS:

    alphas.add(
        f"hump(rank(ts_rank({field},252)),0.01)"
    )

    alphas.add(
        f"hump(rank(ts_zscore({field},252)),0.01)"
    )

# =====================
# SAVE
# =====================

alphas = sorted(list(alphas))

with open(
    "generated_alphas_v3.txt",
    "w",
    encoding="utf-8"
) as f:

    for alpha in alphas:
        f.write(alpha + "\n")

print("=" * 50)
print("TOTAL V3 ALPHAS:", len(alphas))
print("Saved -> generated_alphas_v3.txt")
print("=" * 50)