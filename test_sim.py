import requests

from config import COOKIE

headers = {
    "Cookie": f"t={COOKIE}",
    "Accept": "application/json"
}

sim_id = "3cmT1c3QF4hAahR10zw6CHsH"

url = f"https://api.worldquantbrain.com/simulations/{sim_id}"

r = requests.get(
    url,
    headers=headers
)

print("STATUS:", r.status_code)
print("HEADERS:")
print(r.headers)
print()
print("BODY:")
print(r.text)