import pandas as pd
import random

# ==========================
# LOAD FIELDS
# ==========================

analyst = pd.read_csv(
    "datasets/analyst_core_fields.csv"
)

fundamental = pd.read_csv(
    "datasets/fundamental2_fields.csv"
)

# ==========================
# FILTER GOOD FIELDS
# ==========================

def get_fields(df):

    if "coverage" in df.columns:
        df = df[df["coverage"] >= 0.60]

    if "alphaCount" in df.columns:
        df = df[df["alphaCount"] >= 50]

    return (
        df["id"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

analyst_fields = get_fields(analyst)
fundamental_fields = get_fields(fundamental)

print("Analyst Fields:", len(analyst_fields))
print("Fundamental Fields:", len(fundamental_fields))

# ==========================
# PARAMETERS
# ==========================

windows = [
    20,
    63,
    126,
    252
]

single_templates = [

    "rank({f})",

    "rank(ts_rank({f},{w}))",

    "rank(ts_zscore({f},{w}))",

    "rank(ts_delta({f},{w}))",

    "rank({f}/ts_mean({f},{w}))",

    "rank(ts_scale({f},{w}))",

    "rank(ts_quantile({f},{w}))",

    "rank(-ts_zscore({f},{w}))",

    "rank(ts_rank(ts_delta({f},{w1}),{w2}))",

    "rank(ts_zscore(ts_mean({f},{w1}),{w2}))",

    "hump(rank(ts_rank({f},252)),0.01)",

    "hump(rank(ts_zscore({f},252)),0.01)",

]

pair_templates = [

    "rank({f1}/{f2})",

    "rank({f1}*{f2})",

    "rank(ts_zscore({f1},126)-ts_zscore({f2},126))",

    "rank(ts_rank({f1},252)-ts_rank({f2},252))",

    "rank(ts_delta({f1},63)/ts_delta({f2},63))",

]

alphas = set()

# ==========================
# ANALYST ALPHAS
# ==========================

for field in analyst_fields:

    for template in single_templates:

        try:

            alpha = template.format(
                f=field,
                w=random.choice(windows),
                w1=random.choice(windows),
                w2=random.choice(windows)
            )

            alphas.add(alpha)

        except:
            pass

# ==========================
# FUNDAMENTAL ALPHAS
# ==========================

for field in fundamental_fields:

    for template in single_templates:

        try:

            alpha = template.format(
                f=field,
                w=random.choice(windows),
                w1=random.choice(windows),
                w2=random.choice(windows)
            )

            alphas.add(alpha)

        except:
            pass

# ==========================
# MIXED ALPHAS
# ==========================

for _ in range(3000):

    try:

        f1 = random.choice(analyst_fields)
        f2 = random.choice(fundamental_fields)

        template = random.choice(pair_templates)

        alpha = template.format(
            f1=f1,
            f2=f2
        )

        alphas.add(alpha)

    except:
        pass

# ==========================
# SAVE
# ==========================

alphas = sorted(list(alphas))

with open(
    "generated_alphas.txt",
    "w",
    encoding="utf-8"
) as f:

    for alpha in alphas:
        f.write(alpha + "\n")

print()
print("=" * 50)
print("TOTAL ALPHAS GENERATED:", len(alphas))
print("Saved -> generated_alphas.txt")
print("=" * 50)