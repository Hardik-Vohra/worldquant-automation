import requests

FULL_COOKIE = r"""PASTE THE ENTIRE COOKIE STRING FROM CURL HERE"""

headers = {
    "Accept": "application/json;version=2.0",
    "Content-Type": "application/json",
    "Cookie": FULL_COOKIE,
    "Origin": "https://platform.worldquantbrain.com",
    "Referer": "https://platform.worldquantbrain.com/",
    "User-Agent": "Mozilla/5.0"
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
        "decay": 0,
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
print("TEXT:", r.text)
print("LOCATION:", r.headers.get("Location"))