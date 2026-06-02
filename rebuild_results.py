import pandas as pd

data = [
    ["rank(est_eps/ts_mean(est_eps,126))","RUNNING","42OmHQ49E4yfcvQr5f3lhE4","","","","","",""],
    ["rank(ts_rank(anl4_netdebt_flag,252)-ts_rank(anl4_netprofit_flag,252))","RUNNING","fAplI9VU4P28NrRMEdzP45","","","","","",""],
    ["rank(ts_zscore(anl4_cff_flag,126)-ts_zscore(est_eps,126))","RUNNING","uIT8AeXE4iq8JCnyDcM4O6","","","","","",""],
    ["rank(ts_zscore(anl4_netprofit_flag,126)-ts_zscore(est_eps,126))","RUNNING","x6gvt4kz4lda3MhJTu0uiR","","","","","",""],
    ["rank(anl4_netdebt_flag/anl4_ebit_value)","RUNNING","2Aat6b4rY4Wh8Nz4wW4jFiN","","","","","",""]
]

df = pd.DataFrame(
    data,
    columns=[
        "alpha",
        "status",
        "sim_id",
        "alpha_id",
        "sharpe",
        "fitness",
        "turnover",
        "returns",
        "margin"
    ]
)

df.to_csv(
    "results.csv",
    index=False
)

print("results.csv rebuilt")