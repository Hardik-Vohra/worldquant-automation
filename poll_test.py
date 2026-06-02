import requests
from config import COOKIE

SIM_ID = "42OmHQ49E4yfcvQr5f3lhE4"

headers = {
    "Cookie": f"t={COOKIE}",
    "Accept": "application/json;version=2.0"
}

r = requests.get(
    f"https://api.worldquantbrain.com/simulations/{SIM_ID}",
    headers=headers
)

print("STATUS:", r.status_code)
print(r.text)