import requests
from config import COOKIE

url = "https://api.worldquantbrain.com/simulations/490kyS58e4luaVD1cNj17fAL"

headers = {
    "Cookie": f"t={COOKIE}",
    "Accept": "application/json;version=2.0"
}

r = requests.get(url, headers=headers)

print("STATUS:", r.status_code)
print(r.text)