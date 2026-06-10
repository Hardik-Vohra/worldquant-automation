import requests
from config import COOKIE

headers = {
    "Cookie": f"t={COOKIE}",
    "Accept": "application/json;version=2.0"
}

alpha_id = "gJ3k5kj0"

r = requests.get(
    f"https://api.worldquantbrain.com/alphas/{alpha_id}",
    headers=headers
)

print(r.status_code)
print(r.json())