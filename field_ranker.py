import pandas as pd
import glob

all_dfs = []

for file in glob.glob("datasets/*_fields.csv"):

    df = pd.read_csv(file)

    df["dataset_source"] = (
        file.split("\\")[-1]
        .replace("_fields.csv", "")
    )

    all_dfs.append(df)

master = pd.concat(all_dfs, ignore_index=True)

master["field_score"] = (
    master["coverage"] * 40
    + master["alphaCount"] * 0.001
    + master["userCount"] * 0.01
)

master = master.sort_values(
    "field_score",
    ascending=False
)

master.to_csv(
    "field_database.csv",
    index=False
)

core_fields = master[
    (master["coverage"] >= 0.60)
    &
    (master["alphaCount"] >= 50)
]

core_fields.to_csv(
    "core_fields.csv",
    index=False
)

print("Total fields:", len(master))
print("Core fields:", len(core_fields))