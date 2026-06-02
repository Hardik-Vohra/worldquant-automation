import itertools

fields = [
    "volume",
    "returns",
    "close",
    "open",
    "high",
    "low",
    "vwap"
]

windows = [
    5,
    10,
    20,
    63,
    126,
    252
]

templates = [
    "rank({field})",
    "rank(ts_rank({field},{w}))",
    "rank(ts_zscore({field},{w}))",
    "rank({field}/ts_mean({field},{w}))",
    "rank(ts_delta({field},{w}))"
]

alphas = []

for template in templates:
    for field in fields:
        for w in windows:
            try:
                alpha = template.format(
                    field=field,
                    w=w
                )
                alphas.append(alpha)
            except:
                pass

alphas = list(set(alphas))

with open("generated_alphas.txt","w") as f:
    for alpha in alphas:
        f.write(alpha+"\n")

print(f"Generated {len(alphas)} alphas")