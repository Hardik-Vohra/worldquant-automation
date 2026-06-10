import pandas as pd

df = pd.read_csv("selected_fields.csv")

# MATRIX only

df = df[
    df["type"] == "MATRIX"
]

# Score

df["score"] = (
    df["coverage"] * 100
    +
    df["alphaCount"] * 0.0005
    +
    df["userCount"] * 0.005
)

df = df.sort_values(
    "score",
    ascending=False
)

top100 = df.head(100)

top100.to_csv(
    "top100_fields.csv",
    index=False
)

print(top100[
    [
        "dataset",
        "field_id",
        "score",
        "coverage",
        "alphaCount"
    ]
])

# ------------------------
# Alternative fields only
# ------------------------

top_alt = df[
    df["dataset"] != "pv1"
]

top_alt = top_alt.sort_values(
    "score",
    ascending=False
)

top_alt = top_alt.head(100)

top_alt.to_csv(
    "top100_alternative_fields.csv",
    index=False
)

print(
    "\nSaved -> top100_alternative_fields.csv"
)

print(
    top_alt[
        [
            "dataset",
            "field_id",
            "score"
        ]
    ].head(20)
)