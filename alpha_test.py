import requests
from config import COOKIE

ALPHA_ID = "O0odkl3g"

headers = {
    "Cookie": f"t={COOKIE}",
    "Accept": "application/json;version=2.0"
}

r = requests.get(
    f"https://api.worldquantbrain.com/alphas/{ALPHA_ID}",
    headers=headers
)

print("STATUS:", r.status_code)
print(r.text)