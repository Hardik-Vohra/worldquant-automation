WINDOWS = [20, 63, 126, 252]

# ------------------------
# Single Field
# ------------------------

SINGLE_FIELD = [

    "rank(ts_delta({field},{w}))",

    "rank(ts_rank({field},{w}))",

    "rank(ts_zscore({field},{w}))",

    "rank(ts_decay_linear({field},20))"
]

# ------------------------
# Pair Field
# ------------------------

PAIR_FIELD = [

    "rank(ts_rank({field1},{w})-ts_rank({field2},{w}))",

    "rank(ts_zscore({field1},{w})-ts_zscore({field2},{w}))",

    "rank({field1}/{field2})",

    "rank(ts_corr({field1},{field2},{w}))"
]

# ------------------------
# Hybrid
# ------------------------

HYBRID = [

    "rank(ts_delta({field1},{w}))*rank(ts_zscore({field2},{w}))",

    "rank(ts_rank({field1},{w}))*rank(ts_rank({field2},{w}))",

    "rank(ts_zscore({field1},{w}))-rank(ts_zscore({field2},{w}))"
]