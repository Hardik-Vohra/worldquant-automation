import pandas as pd

WINNER_THRESHOLD = 0.7
LOSER_THRESHOLD = -0.7

alphas = set()


df = pd.read_csv("results_enriched.csv")

# Clean rows
df = df[pd.to_numeric(df["sharpe"], errors="coerce").notna()]
df["sharpe"] = df["sharpe"].astype(float)

existing_alphas = set(
    df["alpha"]
    .dropna()
    .astype(str)
    .tolist()
)

winners = df[df["sharpe"] > WINNER_THRESHOLD]
losers = df[df["sharpe"] < LOSER_THRESHOLD]

windows = [63, 126, 252]

# ------------------------
# Winner mutations
# ------------------------

for _, row in winners.iterrows():

    alpha = str(row["alpha"])

    # keep winner
    if alpha not in existing_alphas:
      alphas.add(alpha)

    # mutate windows
    for old_w in [63, 126, 252]:
        for new_w in windows:

            if old_w != new_w:

                mutated = alpha.replace(
                    f",{old_w})",
                    f",{new_w})"
                )

                if mutated not in existing_alphas:
                  alphas.add(mutated)

# ------------------------
# Loser inversions
# ------------------------

for _, row in losers.iterrows():

    alpha = str(row["alpha"])

    if "/" in alpha:

        try:

            inside = alpha[
                alpha.index("(")+1:
                alpha.rindex(")")
            ]

            left, right = inside.split("/")

            candidate = f"rank({right}/{left})"

            if candidate not in existing_alphas:
                  alphas.add(candidate)

        except:
            pass

    else:

        alphas.add(
            f"-({alpha})"
        )

# ------------------------
# Save
# ------------------------

# Remove duplicates

alphas = set(alphas)

# Remove known bad forms

cleaned = []

for alpha in alphas:

    if alpha.startswith("-(rank("):
        continue

    cleaned.append(alpha)

# Add improved inverse candidates

cleaned.append(
    "rank(ts_zscore(anl4_cfo_flag,252)-ts_zscore(anl4_fcf_flag,252))"
)

cleaned.append(
    "rank(-ts_delta(anl4_fcf_flag,126))"
)

# Remove duplicates again

cleaned = sorted(list(set(cleaned)))

# Save ready-to-submit batch

with open("batch_next_v2.txt", "w") as f:

    for alpha in cleaned:
        f.write(alpha + "\n")

print("NEXT BATCH V2:", len(cleaned))
print("Saved -> batch_next_v2.txt")