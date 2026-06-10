import itertools

FIELDS = [
    "anl4_ebit_value",
    "anl4_ebitda_value",
    "anl4_fcf_flag",
    "anl4_netprofit_flag"
]

WINDOWS = [126, 252]

alphas = set()

for a, b in itertools.permutations(
    FIELDS,
    2
):

    for w in WINDOWS:

        # winner family

        alphas.add(
            f"rank(ts_zscore({a},{w})-ts_zscore({b},{w}))"
        )

        alphas.add(
            f"rank(ts_rank({a},{w})-ts_rank({b},{w}))"
        )

        # reverse spread

        alphas.add(
            f"rank(ts_zscore({b},{w})-ts_zscore({a},{w}))"
        )

        # blended

        alphas.add(
            f"rank(ts_zscore({a},{w})+ts_zscore({b},{w}))"
        )

        alphas.add(
            f"rank(ts_rank({a},{w})+ts_rank({b},{w}))"
        )

# single field reinforcements

for field in FIELDS:

    for w in WINDOWS:

        alphas.add(
            f"rank(ts_delta({field},{w}))"
        )

        alphas.add(
            f"rank(ts_zscore({field},{w}))"
        )

alphas = sorted(list(alphas))

with open(
    "elite_batch_2.txt",
    "w"
) as f:

    for alpha in alphas:
        f.write(alpha + "\n")

print(
    "TOTAL ELITE MUTATIONS:",
    len(alphas)
)