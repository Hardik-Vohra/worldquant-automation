import itertools

ELITE_FIELDS = [
    "anl4_ebit_value",
    "anl4_ebitda_value",
    "anl4_fcf_flag",
    "anl4_netprofit_flag"
]

WINDOWS = [126, 252]

alphas = set()

# ------------------------
# Single field
# ------------------------

for field in ELITE_FIELDS:

    for w in WINDOWS:

        alphas.add(
            f"rank(ts_delta({field},{w}))"
        )

        alphas.add(
            f"rank(ts_rank({field},{w}))"
        )

        alphas.add(
            f"rank(ts_zscore({field},{w}))"
        )

# ------------------------
# Pair field
# ------------------------

for a, b in itertools.permutations(
    ELITE_FIELDS,
    2
):

    for w in WINDOWS:

        alphas.add(
            f"rank(ts_rank({a},{w})-ts_rank({b},{w}))"
        )

        alphas.add(
            f"rank(ts_zscore({a},{w})-ts_zscore({b},{w}))"
        )

# ------------------------
# Save
# ------------------------

alphas = sorted(list(alphas))

with open(
    "elite_batch_1.txt",
    "w"
) as f:

    for alpha in alphas:

        f.write(alpha + "\n")

print(
    "TOTAL ELITE ALPHAS:",
    len(alphas)
)