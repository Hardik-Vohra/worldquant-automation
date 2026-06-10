import itertools

from alpha_templates import (
    WINDOWS,
    SINGLE_FIELD,
    PAIR_FIELD,
    HYBRID
)

from field_groups import (
    ANALYST_FIELDS,
    OPTION_FIELDS,
    SENTIMENT_FIELDS,
    RISK_FIELDS
)

alphas = set()

# ------------------------
# ALL FIELDS
# ------------------------

ALL_FIELDS = (
    ANALYST_FIELDS
    + OPTION_FIELDS
    + SENTIMENT_FIELDS
    + RISK_FIELDS
)

# ------------------------
# SINGLE FIELD
# ------------------------

for field in ALL_FIELDS:

    for w in WINDOWS:

        for template in SINGLE_FIELD:

            alpha = template.format(
                field=field,
                w=w
            )

            alphas.add(alpha)

# ------------------------
# PAIR FIELD
# ------------------------

for field1, field2 in itertools.combinations(
    ALL_FIELDS,
    2
):

    for w in WINDOWS:

        for template in PAIR_FIELD:

            alpha = template.format(
                field1=field1,
                field2=field2,
                w=w
            )

            alphas.add(alpha)

# ------------------------
# HYBRIDS
# ------------------------

HYBRID_PAIRS = []

# Analyst + Option

for a in ANALYST_FIELDS:
    for o in OPTION_FIELDS:
        HYBRID_PAIRS.append((a, o))

# Analyst + Sentiment

for a in ANALYST_FIELDS:
    for s in SENTIMENT_FIELDS:
        HYBRID_PAIRS.append((a, s))

# Sentiment + Option

for s in SENTIMENT_FIELDS:
    for o in OPTION_FIELDS:
        HYBRID_PAIRS.append((s, o))

# Risk + Analyst

for r in RISK_FIELDS:
    for a in ANALYST_FIELDS:
        HYBRID_PAIRS.append((r, a))

for field1, field2 in HYBRID_PAIRS:

    for w in WINDOWS:

        for template in HYBRID:

            alpha = template.format(
                field1=field1,
                field2=field2,
                w=w
            )

            alphas.add(alpha)

# ------------------------
# SAVE
# ------------------------

alphas = sorted(list(alphas))

with open(
    "generated_alphas_v6.txt",
    "w"
) as f:

    for alpha in alphas:

        f.write(alpha + "\n")

print(
    "TOTAL V6 ALPHAS:",
    len(alphas)
)

print(
    "Saved -> generated_alphas_v6.txt"
)