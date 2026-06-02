valid_alphas = []

with open("generated_alphas_v3.txt") as f:

    for line in f:

        alpha = line.strip()

        # remove empty
        if not alpha:
            continue

        # remove currency code fields
        if "currency" in alpha.lower():
            continue

        # remove obvious metadata fields
        if "_person" in alpha:
            continue

        if "_bk" in alpha:
            continue

        valid_alphas.append(alpha)

with open("filtered_alphas.txt","w") as f:

    for alpha in valid_alphas:
        f.write(alpha + "\n")

print("Valid Alphas:", len(valid_alphas))