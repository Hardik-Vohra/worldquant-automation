import pandas as pd
import glob

for file in glob.glob("datasets/*.csv"):

    try:
        df = pd.read_csv(file)

        print(
            f"{file:<40} "
            f"Rows={len(df)} "
            f"Cols={len(df.columns)}"
        )

    except Exception as e:
        print(
            f"{file:<40} "
            f"ERROR -> {e}"
        )