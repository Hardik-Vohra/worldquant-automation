import requests
from config import COOKIE

url = (
    "https://api.worldquantbrain.com/data-fields?"
    "dataset.id=analyst4"
    "&delay=1"
    "&instrumentType=EQUITY"
    "&limit=5"
    "&offset=0"
    "&region=USA"
    "&universe=TOP3000"
)

headers = {
    "Cookie": f"t={COOKIE}",
    "Accept": "application/json;version=2.0",
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(url, headers=headers)

print("STATUS:", r.status_code)
print()
print(r.text)