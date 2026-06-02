import os
import time
import requests
import pandas as pd

from config import COOKIE

# ------------------------
# CONFIG
# ------------------------

DATASET_ID = "socialmedia8"
LIMIT = 50

headers = {
    "Cookie": f"t={COOKIE}",
    "Accept": "application/json"
}

# ------------------------
# CREATE FOLDER
# ------------------------

os.makedirs(
    "datasets",
    exist_ok=True
)

print(f"Downloading dataset: {DATASET_ID}")

rows = []
offset = 0

while True:

    url = (
        f"https://api.worldquantbrain.com/data-fields"
        f"?dataset.id={DATASET_ID}"
        f"&delay=1"
        f"&instrumentType=EQUITY"
        f"&limit={LIMIT}"
        f"&offset={offset}"
        f"&region=USA"
        f"&universe=TOP3000"
    )

    r = requests.get(
        url,
        headers=headers
    )

    print(
        f"OFFSET: {offset} | STATUS: {r.status_code}"
    )

    if r.status_code == 429:

        retry_after = int(
            float(
                r.headers.get(
                    "Retry-After",
                    10
                )
            )
        )

        print(
            f"429 -> waiting {retry_after}s"
        )

        time.sleep(
            retry_after + 1
        )

        continue

    if r.status_code != 200:

        print(
            "FAILED:",
            r.text
        )

        break

    data = r.json()

    results = data.get(
        "results",
        []
    )

    if not results:
        break

    for field in results:

        rows.append({
            "dataset": DATASET_ID,
            "field_id": field.get("id"),
            "type": field.get("type"),
            "description": field.get("description"),
            "coverage": field.get("coverage"),
            "alphaCount": field.get("alphaCount"),
            "userCount": field.get("userCount")
        })

    offset += LIMIT

    time.sleep(0.5)

# ------------------------
# SAVE
# ------------------------

df = pd.DataFrame(rows)

output_file = (
    f"datasets/{DATASET_ID}_fields.csv"
)

df.to_csv(
    output_file,
    index=False
)

print(
    f"\nTOTAL FIELDS: {len(df)}"
)

print(
    f"Saved -> {output_file}"
)