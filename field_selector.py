import pandas as pd

import os

print(
    os.path.exists(
        "datasets/analyst_core_fields.csv"
    )
)

print(
    os.path.exists(
        "datasets/fundamental2_fields.csv"
    )
)
# Load datasets
analyst = pd.read_csv(
    "datasets/analyst_core_fields.csv"
)
fundamental = pd.read_csv("datasets/fundamental2_fields.csv")

# Merge
all_fields = pd.concat(
    [analyst, fundamental],
    ignore_index=True
)

# Convert numeric columns
for col in ["coverage", "userCount", "alphaCount"]:
    all_fields[col] = pd.to_numeric(
        all_fields[col],
        errors="coerce"
    )

# Score
all_fields["field_score"] = (
    all_fields["coverage"] * 40
    + all_fields["alphaCount"] * 0.001
    + all_fields["userCount"] * 0.01
)

# Keep useful fields
core = all_fields[
    (all_fields["coverage"] >= 0.60)
    &
    (all_fields["alphaCount"] >= 50)
]

core = core.sort_values(
    "field_score",
    ascending=False
)

core.to_csv(
    "core_fields.csv",
    index=False
)

print("Total Fields:", len(all_fields))
print("Core Fields:", len(core))

print(
    core[
        [
            "id",
            "coverage",
            "userCount",
            "alphaCount",
            "field_score"
        ]
    ].head(50)
)

print(
    core[["id","field_score"]]
    .head(40)
)