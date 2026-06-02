import random

with open("generated_alphas_v4.txt") as f:
    alphas = [
        x.strip()
        for x in f.readlines()
        if x.strip()
    ]

random.shuffle(alphas)

selected = alphas[:20]

with open("batch2.txt", "w") as f:
    for alpha in selected:
        f.write(alpha + "\n")

print("Batch Size:", len(selected))