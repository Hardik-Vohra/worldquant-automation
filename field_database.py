import pandas as pd

df = pd.read_csv("datasets/analyst_fields.csv")

core_fields = df[
    (df["coverage"] > 0.7) &
    (df["alphaCount"] > 500)
]

print("CORE FIELDS:", len(core_fields))

core_fields.to_csv(
    "datasets/analyst_core_fields.csv",
    index=False
)

print("Saved analyst_core_fields.csv")