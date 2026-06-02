import requests
import csv
from config import COOKIE

with open("current_alpha.txt") as f:
    ALPHA_ID = f.read().strip()

headers = {
    "Cookie": f"t={COOKIE}",
    "Accept": "application/json;version=2.0"
}

url = f"https://api.worldquantbrain.com/alphas/{ALPHA_ID}"

r = requests.get(url, headers=headers)

print("STATUS:", r.status_code)

data = r.json()

data = r.json()

print("\nIS:")
print(data["is"])

print("\nTRAIN:")
print(data["train"])

print("\nTEST:")
print(data["test"])

metrics = data["is"]

print("\nSharpe:", metrics["sharpe"])
print("Fitness:", metrics["fitness"])
print("Turnover:", metrics["turnover"])
print("Returns:", metrics["returns"])
print("Drawdown:", metrics["drawdown"])

with open("results.csv", "a", newline="") as f:
    writer = csv.writer(f)

    writer.writerow([
        ALPHA_ID,
        metrics["sharpe"],
        metrics["fitness"],
        metrics["turnover"],
        metrics["returns"],
        metrics["drawdown"]
    ])