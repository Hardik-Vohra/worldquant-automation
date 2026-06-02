import requests
from config import COOKIE

session = requests.Session()

session.headers.update({
    "Accept": "application/json;version=2.0",
    "Content-Type": "application/json",
    "Origin": "https://platform.worldquantbrain.com",
    "Referer": "https://platform.worldquantbrain.com/"
})

session.cookies.set("t", COOKIE)

r = session.get(
    "https://api.worldquantbrain.com/authentication"
)

print("AUTH:", r.status_code)
print("COOKIES AFTER AUTH:", session.cookies.get_dict())

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

r2 = session.post(
    "https://api.worldquantbrain.com/simulations",
    json=payload
)

print("SIM:", r2.status_code)
print("TEXT:", r2.text)
print("LOCATION:", r2.headers.get("Location"))