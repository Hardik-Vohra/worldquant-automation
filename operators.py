WINDOWS = [20, 63, 126, 252]

# Arithmetic Operators
ARITHMETIC_OPERATORS = [
    "abs",
    "add",
    "subtract",
    "multiply",
    "divide",
    "inverse",
    "power",
    "signed_power",
    "sqrt",
    "log",
    "max",
    "min",
    "sign",
    "reverse",
    "densify",
]

# Time Series Operators
TS_OPERATORS = [
    "ts_delta",
    "ts_rank",
    "ts_zscore",
    "ts_mean",
    "ts_sum",
    "ts_std_dev",
    "ts_delay",
    "ts_scale",
    "ts_av_diff",
    "ts_corr",
    "ts_covariance",
    "ts_decay_linear",
    "ts_backfill",
    "ts_arg_max",
    "ts_arg_min",
    "ts_product",
    "ts_quantile",
    "ts_regression",
    "ts_count_nans",
    "ts_step",
    "kth_element",
    "last_diff_value",
    "days_from_last_change",
    "hump",
]

# Logical Operators
LOGICAL_OPERATORS = [
    "and",
    "or",
    "not",
    "if_else",
    "is_nan",
]

# Comparison Operators
COMPARISON_OPERATORS = [
    "<",
    "<=",
    "==",
    ">",
    ">=",
    "!=",
]

# Cross-Sectional Operators
CROSS_SECTIONAL_OPERATORS = [
    "rank",
    "zscore",
    "normalize",
    "scale",
    "quantile",
    "winsorize",
    "vector_neut",
]

# Vector Operators
VECTOR_OPERATORS = [
    "vec_avg",
    "vec_sum",
]

# Transformation Operators
TRANSFORMATION_OPERATORS = [
    "bucket",
    "trade_when",
]

# Group Operators
GROUP_OPERATORS = [
    "group_rank",
    "group_zscore",
    "group_neutralize",
    "group_scale",
    "group_mean",
    "group_backfill",
]

# All operators combined
ALL_OPERATORS = (
    ARITHMETIC_OPERATORS +
    TS_OPERATORS +
    LOGICAL_OPERATORS +
    CROSS_SECTIONAL_OPERATORS +
    VECTOR_OPERATORS +
    TRANSFORMATION_OPERATORS +
    GROUP_OPERATORS
)

# Basic operators for simple expressions
BASIC_OPERATORS = [
    "rank",
    "zscore",
]