import random

with open("generated_alphas_v3.txt") as f:
    alphas = [
        x.strip()
        for x in f.readlines()
        if x.strip()
    ]

random.shuffle(alphas)

selected = alphas[:5]

with open("batch1.txt","w") as f:
    for alpha in selected:
        f.write(alpha + "\n")

print(
    "Selected:",
    len(selected)
)