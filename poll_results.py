import requests
import pandas as pd
import time

from config import COOKIE

headers = {
    "Cookie": f"t={COOKIE}",
    "Accept": "application/json;version=2.0"
}

# ------------------------
# Load Results
# ------------------------

df = pd.read_csv("results_elite.csv")

df = df.astype(object)

for idx, row in df.iterrows():

    sim_id = str(row["sim_id"]).strip()

    if not sim_id:
        continue

    try:

        # ------------------------
        # Get Simulation
        # ------------------------

        sim_url = (
            f"https://api.worldquantbrain.com/"
            f"simulations/{sim_id}"
        )

        r = requests.get(
            sim_url,
            headers=headers
        )

        if r.status_code != 200:

            print(f"\nFAILED SIM: {sim_id}")
            print("STATUS:", r.status_code)
            print("BODY:", r.text[:500])

            continue

        sim_data = r.json()

        print("SIM DATA:", sim_data)

        status = sim_data.get(
            "status",
            ""
        )

        if status != "COMPLETE":

            print(
                f"{sim_id} -> {status}"
            )

            continue

        alpha_id = sim_data.get(
            "alpha"
        )

        if not alpha_id:

            print(
                f"{sim_id} -> no alpha id"
            )

            continue

        print(
            f"SIM COMPLETE -> {alpha_id}"
        )

        # ------------------------
        # Get Alpha Metrics
        # ------------------------

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
                f"FAILED ALPHA: {alpha_id}"
            )

            continue

        alpha_data = r2.json()

        is_data = alpha_data.get(
            "is",
            {}
        )

        # ------------------------
        # Save Metrics
        # ------------------------

        df.loc[idx, "alpha_id"] = alpha_id

        df.loc[idx, "status"] = alpha_data.get(
            "status",
            ""
        )

        df.loc[idx, "sharpe"] = is_data.get(
            "sharpe",
            None
        )

        df.loc[idx, "fitness"] = is_data.get(
            "fitness",
            None
        )

        df.loc[idx, "turnover"] = is_data.get(
            "turnover",
            None
        )

        df.loc[idx, "returns"] = is_data.get(
            "returns",
            None
        )

        df.loc[idx, "margin"] = is_data.get(
            "margin",
            None
        )

        print(
            f"{alpha_id} | "
            f"Sharpe={is_data.get('sharpe')} | "
            f"Fitness={is_data.get('fitness')}"
        )

        time.sleep(1)

    except Exception as e:

        print(
            f"ERROR: {sim_id}"
        )

        print(e)

# ------------------------
# Save Enriched Results
# ------------------------

df.to_csv(
    "results_elite_enriched.csv",
    index=False
)

print()
print(
    "Saved -> results_elite_enriched.csv"
)