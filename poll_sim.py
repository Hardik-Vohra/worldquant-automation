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
    print("HEADERS:", dict(r.headers))
    print("BODY:", r.text)

    try:
        data = r.json()
    except:
        break

    if data.get("progress", 0) >= 1:
        print("Progress reached 100%")
        break

    time.sleep(5)