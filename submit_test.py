import requests
from config import COOKIE

url = "https://api.worldquantbrain.com/authentication"

headers = {
    "Cookie": f"t={COOKIE}"
}

r = requests.get(url, headers=headers)

print("Status:", r.status_code)
print(r.text)