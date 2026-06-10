import pandas as pd

df = pd.read_csv("elite_fields.csv")

good_datasets = [
    "analyst4",
    "option8",
    "option9",
    "socialmedia12",
    "socialmedia8",
    "news12",
    "model51",
    "pv13",
    "pv1"
]

selected = df[
    df["dataset"].isin(
        good_datasets
    )
]

selected.to_csv(
    "selected_fields.csv",
    index=False
)

print(
    len(selected)
)