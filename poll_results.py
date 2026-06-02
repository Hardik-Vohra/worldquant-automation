import requests
import pandas as pd
import time

from config import COOKIE

headers = {
    "Cookie": f"t={COOKIE}",
    "Accept": "application/json;version=2.0"
}

# Load results

df = pd.read_csv(
    "results.csv",
    header=None
)

df.columns = [
    "alpha",
    "status",
    "sim_id",
    "alpha_id",
    "sharpe",
    "fitness",
    "turnover",
    "returns",
    "margin"
]

df = df.astype(object)

for col in [
    "sharpe",
    "fitness",
    "turnover",
    "returns",
    "margin"
]:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

for idx, row in df.iterrows():

    sim_id = row["sim_id"]

    if sim_id == "sim_id":
     continue

    if pd.isna(sim_id):
        continue

    try:

        # -------------------
        # Get Simulation
        # -------------------

        sim_url = (
            f"https://api.worldquantbrain.com/"
            f"simulations/{sim_id}"
        )

        r = requests.get(
            sim_url,
            headers=headers
        )

        if r.status_code != 200:

            print(
                f"Failed sim {sim_id}"
            )
            continue

        sim_data = r.json()

        if sim_data.get("status") != "COMPLETE":

            print(
                f"{sim_id} still running"
            )
            continue

        alpha_id = sim_data.get("alpha")

        if not alpha_id:
            continue

        # -------------------
        # Get Alpha
        # -------------------

        alpha_url = (
            f"https://api.worldquantbrain.com/"
            f"alphas/{alpha_id}"
        )

        r2 = requests.get(
            alpha_url,
            headers=headers
        )

        if r2.status_code != 200:

            print(
                f"Failed alpha {alpha_id}"
            )
            continue

        alpha_data = r2.json()

        is_data = alpha_data.get(
            "is",
            {}
        )

        df.loc[idx, "alpha_id"] = alpha_id
        df.loc[idx, "status"] = alpha_data.get(
            "status",
            ""
        )

        df.loc[idx, "sharpe"] = float(
    is_data.get(
        "sharpe",
        0
    )
)

        df.loc[idx, "fitness"] = float(
    is_data.get(
        "fitness",
        0
    )
)

        df.loc[idx, "turnover"] = float(
            is_data.get(
                "turnover",
                0
            )
        )
        

        df.loc[idx, "returns"] = float(
            is_data.get(
                "returns",
                0
            )
        )

        df.loc[idx, "margin"] = float(
            is_data.get(
                "margin",
                0
            )
        )

        print(
            f"{alpha_id} | "
            f"Sharpe={is_data.get('sharpe')}"
        )

        time.sleep(1)

    except Exception as e:

        print(
            "ERROR:",
            e
        )

df.to_csv(
    "results_enriched.csv",
    index=False
)

print()
print(
    "Saved -> results_enriched.csv"
)