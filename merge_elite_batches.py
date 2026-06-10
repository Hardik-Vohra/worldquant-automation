files = [
    "elite_batch_1.txt",
    "elite_batch_2.txt"
]

alphas = set()

for file in files:

    with open(file, "r") as f:

        for line in f:

            alpha = line.strip()

            if alpha:
                alphas.add(alpha)

with open(
    "elite_master_batch.txt",
    "w"
) as f:

    for alpha in sorted(alphas):

        f.write(alpha + "\n")

print(
    "TOTAL UNIQUE ALPHAS:",
    len(alphas)
)

print(
    "Saved -> elite_master_batch.txt"
)