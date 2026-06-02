import pandas as pd

df = pd.read_csv("results.csv")
print(df.shape)
print(df.columns.tolist())