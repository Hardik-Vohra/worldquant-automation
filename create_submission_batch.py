alphas = []

with open("elite_master_batch.txt") as f:

    for line in f:

        alpha = line.strip()

        if not alpha:
            continue

        # Skip additive formulas

        if "+" in alpha:
            continue

        alphas.append(alpha)

with open(
    "elite_submission_batch.txt",
    "w"
) as f:

    for alpha in alphas:

        f.write(alpha + "\n")

print(
    "SUBMISSION ALPHAS:",
    len(alphas)
)