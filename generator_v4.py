import itertools

fields = [
    "anl4_netdebt_flag",
    "anl4_ebit_value",
    "anl4_netprofit_flag",
    "anl4_cfo_flag",
    "anl4_fcf_flag",
    "anl4_ebitda_value"
]

windows = [63, 126, 252]

alphas = []

# Ratio alphas
for a, b in itertools.permutations(fields, 2):
    alphas.append(f"rank({a}/{b})")

# Rank spread alphas
for a, b in itertools.permutations(fields, 2):
    for w in windows:
        alphas.append(
            f"rank(ts_rank({a},{w})-ts_rank({b},{w}))"
        )

# Z-score spread alphas
for a, b in itertools.permutations(fields, 2):
    for w in windows:
        alphas.append(
            f"rank(ts_zscore({a},{w})-ts_zscore({b},{w}))"
        )

# Momentum style
for a in fields:
    for w in windows:
        alphas.append(
            f"rank(ts_delta({a},{w}))"
        )

alphas = sorted(list(set(alphas)))

with open("generated_alphas_v4.txt", "w") as f:
    for alpha in alphas:
        f.write(alpha + "\n")

print("TOTAL V4 ALPHAS:", len(alphas))