import pandas as pd

df = pd.read_csv("selected_fields.csv")

print("\nFIELDS PER DATASET\n")

print(
    df["dataset"]
    .value_counts()
    .sort_values(ascending=False)
)

print("\nTYPE DISTRIBUTION\n")

print(
    df["type"]
    .value_counts()
)