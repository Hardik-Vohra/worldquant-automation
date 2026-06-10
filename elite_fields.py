import pandas as pd
import numpy as np

df = pd.read_csv("master_fields.csv")

# ------------------------
# Clean
# ------------------------

df["coverage"] = pd.to_numeric(
    df["coverage"],
    errors="coerce"
).fillna(0)

df["alphaCount"] = pd.to_numeric(
    df["alphaCount"],
    errors="coerce"
).fillna(0)

df["userCount"] = pd.to_numeric(
    df["userCount"],
    errors="coerce"
).fillna(0)

# ------------------------
# Strong filters
# ------------------------

elite = df[
    (df["coverage"] >= 0.60)
]

# ------------------------
# Field score
# ------------------------

elite["score"] = (
    elite["coverage"] * 100
    +
    np.log1p(elite["alphaCount"]) * 10
    +
    np.log1p(elite["userCount"]) * 5
)

# ------------------------
# Sort
# ------------------------

elite = elite.sort_values(
    "score",
    ascending=False
)

# Keep top 1000

elite = elite.head(1000)

# ------------------------
# Save
# ------------------------

elite.to_csv(
    "elite_fields.csv",
    index=False
)

print(
    f"Elite Fields: {len(elite)}"
)

print(
    elite[
        [
            "dataset",
            "field_id",
            "coverage",
            "alphaCount",
            "userCount",
            "score"
        ]
    ].head(20)
)