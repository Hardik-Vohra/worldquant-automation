import os
import pandas as pd

DATASET_FOLDER = "datasets"

all_dfs = []

for file in os.listdir(DATASET_FOLDER):

    if file.endswith(".csv"):

        filepath = os.path.join(
            DATASET_FOLDER,
            file
        )

        try:

            df = pd.read_csv(filepath)

            print(
                f"Loaded: {file} | Rows: {len(df)}"
            )

            all_dfs.append(df)

        except Exception as e:

            print(
                f"Failed: {file}"
            )

            print(e)

if not all_dfs:

    print("No CSV files found.")
    exit()

master_df = pd.concat(
    all_dfs,
    ignore_index=True
)

master_df = master_df.drop_duplicates(
    subset=["dataset", "field_id"]
)

master_df.to_csv(
    "master_fields.csv",
    index=False
)

print("\n====================")
print("TOTAL DATASETS:", len(all_dfs))
print("TOTAL FIELDS:", len(master_df))
print("====================")
print("Saved -> master_fields.csv")