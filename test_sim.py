import requests
from config import COOKIE

headers = {
    "Cookie": f"t={COOKIE}",
    "Content-Type": "application/json",
    "Accept": "application/json;version=2.0"
}

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
    "regular": "rank(volume)"
}

r = requests.post(
    "https://api.worldquantbrain.com/simulations",
    headers=headers,
    json=payload
)

print("STATUS:", r.status_code)
print("HEADERS:", r.headers)
print("TEXT:", r.text)