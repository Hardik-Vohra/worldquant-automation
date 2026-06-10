# generator_v7.py

alphas = set()

# =====================================================
# FUNDAMENTAL FIELDS
# =====================================================

fund_fields = [
    "anl4_ebit_value",
    "anl4_ebitda_value",
    "anl4_fcf_flag",
    "anl4_netprofit_flag",
    "anl4_cfo_flag",
    "anl4_netdebt_flag"
]

windows = [126, 252]

# =====================================================
# FAMILY 1
# FUNDAMENTAL MOMENTUM
# =====================================================

for field in fund_fields:

    for w in windows:

        alphas.add(
            f"rank(ts_delta({field},{w}))"
        )

        alphas.add(
            f"rank(ts_rank({field},{w}))"
        )

        alphas.add(
            f"rank(ts_zscore({field},{w}))"
        )

# =====================================================
# FAMILY 2
# FUNDAMENTAL SPREADS
# =====================================================

for f1 in fund_fields:

    for f2 in fund_fields:

        if f1 == f2:
            continue

        for w in windows:

            alphas.add(
                f"rank(ts_rank({f1},{w})-ts_rank({f2},{w}))"
            )

            alphas.add(
                f"rank(ts_zscore({f1},{w})-ts_zscore({f2},{w}))"
            )

# =====================================================
# FAMILY 3
# QUALITY COMPOSITES
# =====================================================

for w in windows:

    alphas.add(
        f"rank(ts_rank(anl4_ebit_value,{w})+ts_rank(anl4_fcf_flag,{w})-ts_rank(anl4_netdebt_flag,{w}))"
    )

    alphas.add(
        f"rank(ts_rank(anl4_cfo_flag,{w})+ts_rank(anl4_fcf_flag,{w})-ts_rank(anl4_netdebt_flag,{w}))"
    )

    alphas.add(
        f"rank(ts_zscore(anl4_ebit_value,{w})+ts_zscore(anl4_fcf_flag,{w})-ts_zscore(anl4_netdebt_flag,{w}))"
    )

# =====================================================
# OPTIONS FIELDS
# =====================================================

iv_fields = [
    "implied_volatility_mean_30",
    "implied_volatility_mean_90",
    "implied_volatility_mean_150",
    "implied_volatility_mean_270"
]

hv_fields = [
    "historical_volatility_30",
    "historical_volatility_90",
    "historical_volatility_150"
]

# =====================================================
# FAMILY 4
# VOL RISK PREMIUM
# =====================================================

for iv in iv_fields:

    for hv in hv_fields:

        alphas.add(
            f"rank({iv}-{hv})"
        )

# =====================================================
# FAMILY 5
# VOL TERM STRUCTURE
# =====================================================

alphas.add(
    "rank(implied_volatility_mean_30-implied_volatility_mean_270)"
)

alphas.add(
    "rank(implied_volatility_mean_90-implied_volatility_mean_270)"
)

alphas.add(
    "rank(historical_volatility_30-historical_volatility_90)"
)

alphas.add(
    "rank(historical_volatility_30-historical_volatility_150)"
)

# =====================================================
# FAMILY 6
# PCR REGIME FILTERS
# =====================================================

signals = [

    "(implied_volatility_call_270-implied_volatility_put_270)",

    "(implied_volatility_mean_90-historical_volatility_90)",

    "(implied_volatility_mean_30-implied_volatility_mean_270)",

    "(historical_volatility_30-historical_volatility_90)",

    "(call_open_interest_270-put_open_interest_270)"
]

conditions = [

    "pcr_oi_270<1",

    "pcr_oi_270>1",

    "ts_rank(pcr_oi_270,252)>0.8",

    "ts_rank(pcr_oi_270,252)<0.2"
]

for cond in conditions:

    for sig in signals:

        alphas.add(
            f"trade_when({cond},{sig},-1)"
        )

# =====================================================
# FAMILY 7
# HYBRIDS
# =====================================================

for w in windows:

    alphas.add(
        f"trade_when(pcr_oi_270<1,ts_delta(anl4_ebit_value,{w}),-1)"
    )

    alphas.add(
        f"trade_when(pcr_oi_270<1,ts_delta(anl4_fcf_flag,{w}),-1)"
    )

    alphas.add(
        f"trade_when(pcr_oi_270<1,ts_rank(anl4_netprofit_flag,{w}),-1)"
    )

    alphas.add(
        f"rank(ts_delta(anl4_ebit_value,{w})-(implied_volatility_mean_90-historical_volatility_90))"
    )

    alphas.add(
        f"rank(ts_zscore(anl4_fcf_flag,{w})*rank(pcr_oi_270))"
    )

# =====================================================
# SAVE
# =====================================================

alphas = sorted(list(alphas))

with open("batch_v7.txt", "w") as f:

    for alpha in alphas:
        f.write(alpha + "\n")

print()
print("=" * 50)
print("TOTAL V7 ALPHAS:", len(alphas))
print("=" * 50)
print("Saved -> batch_v7.txt")