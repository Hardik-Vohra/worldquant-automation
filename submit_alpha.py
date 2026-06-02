import requests
import csv

from config import COOKIE

headers = {
    "Cookie": f"t={COOKIE}",
    "Content-Type": "application/json",
    "Accept": "application/json;version=2.0"
}
ALPHA = "rank(volume)"
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
    "regular": ALPHA
}

r = requests.post(
    "https://api.worldquantbrain.com/simulations",
    headers=headers,
    json=payload
)
location = r.headers.get("Location")

print("STATUS:", r.status_code)
print("LOCATION:", location)

if location:
    sim_id = location.split("/")[-1]
    print("SIM_ID:", sim_id)

    # Save latest simulation ID
    with open("current_sim.txt", "w") as f:
        f.write(sim_id)

    with open("results.csv", "a", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            ALPHA,
            "RUNNING",
            sim_id,
            "",
            "",
            "",
            "",
            "",
            "",
        ])