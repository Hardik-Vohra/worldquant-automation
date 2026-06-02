import requests
import time
from config import COOKIE

with open("current_sim.txt") as f:
    SIM_ID = f.read().strip()

headers = {
    "Cookie": f"t={COOKIE}",
    "Accept": "application/json;version=2.0"
}

while True:

    r = requests.get(
        f"https://api.worldquantbrain.com/simulations/{SIM_ID}",
        headers=headers
    )

    print("\nSTATUS:", r.status_code)

    data = r.json()

    print(data)

    if "progress" in data:
        print(f"Progress: {data['progress']*100:.1f}%")
    else:
        print(data)

    if data.get("status") == "COMPLETE":

        alpha_id = data.get("alpha")

        print("ALPHA_ID:", alpha_id)

        with open("current_alpha.txt", "w") as f:
            f.write(alpha_id)

        break

    time.sleep(5)