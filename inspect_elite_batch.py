with open("elite_master_batch.txt") as f:

    lines = [
        line.strip()
        for line in f
        if line.strip()
    ]

print("TOTAL:", len(lines))

print("\nFIRST 20:\n")

for alpha in lines[:20]:

    print(alpha)