import requests
import csv
import time

from config import COOKIE

print("COOKIE LENGTH:", len(COOKIE))
print("COOKIE START:", COOKIE[:30])

headers = {
    "Cookie": f"t={COOKIE}",
    "Content-Type": "application/json",
    "Accept": "application/json;version=2.0"
}

import os

RESULTS_FILE = "results_elite.csv"

if not os.path.exists(RESULTS_FILE):

    with open(
        RESULTS_FILE,
        "w",
        newline=""
    ) as f:

        writer = csv.writer(
            f,
            quoting=csv.QUOTE_ALL
        )

        writer.writerow([
            "alpha",
            "status",
            "sim_id",
            "alpha_id",
            "sharpe",
            "fitness",
            "turnover",
            "returns",
            "margin"
        ])

# EXISTING CODE CONTINUES
with open("elite_submission_batch.txt") as f:
    alphas = [
        x.strip()
        for x in f.readlines()
        if x.strip()
    ]

print("Alphas Found:", len(alphas))

for alpha in alphas:

    payload = {
        "type": "REGULAR",
        "settings": {
            "nanHandling": "OFF",
            "instrumentType": "EQUITY",
            "delay": 1,
            "universe": "TOP3000",
            "truncation": 0.08,
            "unitHandling": "VERIFY",
            "testPeriod": "P1Y",
            "pasteurization": "ON",
            "region": "USA",
            "language": "FASTEXPR",
            "decay": 4,
            "neutralization": "SUBINDUSTRY",
            "visualization": False
        },
        "regular": alpha
    }

    try:

        while True:

            r = requests.post(
                "https://api.worldquantbrain.com/simulations",
                headers=headers,
                json=payload
            )

            print("STATUS:", r.status_code)

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

            break

        location = r.headers.get("Location")

        print("LOCATION:", location)

        if location:

            sim_id = location.split("/")[-1]

            print("SIM:", sim_id)

            with open(
                RESULTS_FILE,
                "a",
                newline=""
            ) as f:

                writer = csv.writer(
    f,
    quoting=csv.QUOTE_ALL
)

                writer.writerow([
                    alpha,
                    "RUNNING",
                    sim_id,
                    "",
                    "",
                    "",
                    "",
                    "",
                    ""
                ])

        else:

            print(
                "FAILED:",
                alpha
            )

        time.sleep(45)

    except Exception as e:

        print(
            "ERROR:",
            e
        ) 