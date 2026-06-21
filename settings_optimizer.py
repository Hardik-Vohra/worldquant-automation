import random
import json
import itertools
import pandas as pd

from project.config import (
    SUBMISSION_SETTINGS,
    SETTINGS_GRID,
    SETTINGS_MAX_VARIANTS_PER_ALPHA,
    WQ_SUBMISSION_CHECKS,
)

# Legacy options kept for backward compatibility
UNIVERSES = ["TOP500", "TOP1000", "TOP2000", "TOP3000"] 
DELAYS = [0, 1]
NEUTRALIZATIONS = ["NONE", "MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY"]
DECAYS = [0, 2, 4, 8, 16]

# Truncations strictly capped at 0.03 to prevent Max Weight concentration rejections
TRUNCATIONS = [0.01, 0.02, 0.025, 0.03] 


# ------------------------------------------------------------------ #
#  Structured Settings Grid                                           #
# ------------------------------------------------------------------ #

def _build_grid():
    """Build the full curated settings grid (3 × 4 × 4 = 48 combos)."""
    combos = []
    for u, n, d in itertools.product(
        SETTINGS_GRID["universe"],
        SETTINGS_GRID["neutralization"],
        SETTINGS_GRID["decay"],
    ):
        settings = SUBMISSION_SETTINGS.copy()
        settings["universe"] = u
        settings["neutralization"] = n
        settings["decay"] = d
        # Weight concentration mitigation: use stricter truncation for smaller universes
        if u == "TOP1000":
            settings["truncation"] = 0.01
        elif u == "TOP2000":
            settings["truncation"] = 0.02
        else:
            settings["truncation"] = 0.03
        combos.append(settings)
    return combos

FULL_SETTINGS_GRID = _build_grid()


def get_settings_variants(alpha_text, db, limit=None):
    """Return a ranked list of untested settings variants for a given alpha.

    Uses structure-aware learning:
    1. Determines the alpha's family.
    2. Queries historical (family, settings) pass rates.
    3. Filters out settings already tested for this alpha.
    4. Ranks untested settings by predicted pass probability.
    5. Returns top `limit` settings to simulate.
    """
    limit = limit or SETTINGS_MAX_VARIANTS_PER_ALPHA

    # Get already-tested settings for this alpha
    tested = set()
    try:
        rows = db.conn.execute(
            "SELECT settings FROM simulations WHERE alpha = ?", [alpha_text]
        ).fetchall()
        for row in rows:
            if row[0]:
                tested.add(row[0])
    except Exception:
        pass

    # Get family-level settings performance
    family = db._infer_family(alpha_text)
    family_perf = settings_family_stats(db)

    # Score each untested grid setting
    scored = []
    for settings in FULL_SETTINGS_GRID:
        settings_key = json.dumps(settings, sort_keys=True)
        if settings_key in tested:
            continue

        # Look up historical performance for this (family, settings) combo
        score = _predict_settings_score(family, settings, family_perf)
        scored.append((score, settings))

    # Sort by predicted score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scored[:limit]]


def _predict_settings_score(family, settings, family_perf):
    """Predict pass probability for a (family, settings) combination.

    Combines:
    - Historical pass rate for this family+neutralization combo
    - Weight concentration risk based on universe size
    - Sub-universe Sharpe risk based on neutralization
    """
    base_score = 0.50  # Neutral prior

    u = settings.get("universe", "TOP3000")
    n = settings.get("neutralization", "SUBINDUSTRY")
    d = settings.get("decay", 4)

    # Universe risk: smaller universes have higher weight concentration risk
    universe_risk = {"TOP1000": -0.15, "TOP2000": -0.05, "TOP3000": 0.05}.get(u, 0.0)

    # Neutralization risk: NONE has highest sub-universe Sharpe failure risk
    neut_risk = {
        "NONE": -0.20,
        "MARKET": -0.05,
        "SECTOR": 0.0,
        "INDUSTRY": 0.05,
        "SUBINDUSTRY": 0.10,
    }.get(n, 0.0)

    # Decay: moderate decay is safer for turnover checks
    decay_bonus = {0: -0.05, 4: 0.05, 8: 0.10, 16: 0.05}.get(d, 0.0)

    # Historical family performance for this neutralization (if available)
    family_bonus = 0.0
    if not family_perf.empty:
        match = family_perf[
            (family_perf["family"] == family) & (family_perf["neutralization"] == n)
        ]
        if not match.empty:
            row = match.iloc[0]
            family_bonus = float(row.get("pass_rate", 0.0)) * 0.20
            # Penalise high rejection rates
            family_bonus -= float(row.get("rejection_rate", 0.0)) * 0.15

    return base_score + universe_risk + neut_risk + decay_bonus + family_bonus


# ------------------------------------------------------------------ #
#  Structure-Aware Settings Learning                                  #
# ------------------------------------------------------------------ #

def settings_family_stats(db):
    """Aggregate (alpha_family, neutralization) → performance metrics.

    Returns DataFrame with: family, neutralization, count, pass_rate,
    elite_rate, rejection_rate, avg_sharpe, weight_conc_fail_rate,
    sub_universe_fail_rate.
    """
    try:
        sim_df = pd.read_sql_query(
            "SELECT s.*, a.category FROM simulations s LEFT JOIN alphas a ON s.alpha = a.alpha",
            db.conn,
        )
    except Exception:
        return pd.DataFrame()

    if sim_df.empty or "settings" not in sim_df.columns:
        return pd.DataFrame()

    sim_df = sim_df[sim_df["settings"].notna()].copy()
    if sim_df.empty:
        return pd.DataFrame()

    # Extract family and neutralization
    from project.engine.data_manager import AlphaDatabase
    sim_df["family"] = sim_df.apply(
        lambda r: AlphaDatabase._infer_family(r.get("alpha"), r.get("category")), axis=1
    )
    sim_df["neutralization"] = sim_df["settings"].apply(
        lambda s: json.loads(s).get("neutralization", "UNKNOWN") if pd.notna(s) else "UNKNOWN"
    )

    # Compute pass/fail metrics
    sim_df["passed"] = (
        (sim_df["sharpe"] >= WQ_SUBMISSION_CHECKS["sharpe_min"]) &
        (sim_df["fitness"] >= WQ_SUBMISSION_CHECKS["fitness_min"]) &
        (sim_df["turnover"] >= WQ_SUBMISSION_CHECKS["turnover_min"]) &
        (sim_df["turnover"] <= WQ_SUBMISSION_CHECKS["turnover_max"])
    ).fillna(False)

    sim_df["elite"] = (
        sim_df["passed"] &
        (sim_df["sharpe"] >= 1.50) &
        (sim_df["fitness"] >= 1.20) &
        (sim_df["turnover"] <= 0.15)
    ).fillna(False)

    rej_col = "rejection_reason" if "rejection_reason" in sim_df.columns else None
    if rej_col:
        sim_df["has_rejection"] = sim_df[rej_col].apply(lambda x: bool(str(x or "").strip()))
        sim_df["weight_conc_fail"] = sim_df[rej_col].apply(lambda x: "CONCENTRATED_WEIGHT" in str(x or ""))
        sim_df["sub_universe_fail"] = sim_df[rej_col].apply(lambda x: "LOW_SUB_UNIVERSE_SHARPE" in str(x or ""))
    else:
        sim_df["has_rejection"] = False
        sim_df["weight_conc_fail"] = False
        sim_df["sub_universe_fail"] = False

    grouped = sim_df.groupby(["family", "neutralization"]).agg(
        count=("alpha", "count"),
        pass_rate=("passed", "mean"),
        elite_rate=("elite", "mean"),
        rejection_rate=("has_rejection", "mean"),
        avg_sharpe=("sharpe", "mean"),
        weight_conc_fail_rate=("weight_conc_fail", "mean"),
        sub_universe_fail_rate=("sub_universe_fail", "mean"),
    ).reset_index()

    return grouped.sort_values(["pass_rate", "elite_rate"], ascending=[False, False])


def settings_pairing_stats(db):
    """Aggregate (pairing_filter, neutralization) → performance metrics.

    Uses LearningEngine._detect_filters() to identify pairing structures.
    """
    try:
        sim_df = pd.read_sql_query(
            "SELECT s.*, a.category FROM simulations s LEFT JOIN alphas a ON s.alpha = a.alpha",
            db.conn,
        )
    except Exception:
        return pd.DataFrame()

    if sim_df.empty or "settings" not in sim_df.columns:
        return pd.DataFrame()

    sim_df = sim_df[sim_df["settings"].notna()].copy()
    if sim_df.empty:
        return pd.DataFrame()

    from project.engine.learning_engine import LearningEngine
    le = LearningEngine(db)

    rows = []
    for _, row in sim_df.iterrows():
        alpha = row.get("alpha") or ""
        filters = le._detect_filters(alpha)
        if not filters:
            continue
        neut = json.loads(row["settings"]).get("neutralization", "UNKNOWN") if pd.notna(row["settings"]) else "UNKNOWN"
        rej = str(row.get("rejection_reason") or "")

        for filt in filters:
            rows.append({
                "filter": filt,
                "neutralization": neut,
                "sharpe": row.get("sharpe"),
                "fitness": row.get("fitness"),
                "turnover": row.get("turnover"),
                "passed": (
                    row.get("sharpe") is not None and not pd.isna(row.get("sharpe")) and
                    row["sharpe"] >= WQ_SUBMISSION_CHECKS["sharpe_min"] and
                    row.get("fitness") is not None and not pd.isna(row.get("fitness")) and
                    row["fitness"] >= WQ_SUBMISSION_CHECKS["fitness_min"]
                ),
                "weight_conc_fail": "CONCENTRATED_WEIGHT" in rej,
                "sub_universe_fail": "LOW_SUB_UNIVERSE_SHARPE" in rej,
                "has_rejection": bool(rej.strip()),
            })

    if not rows:
        return pd.DataFrame()

    pdf = pd.DataFrame(rows)
    grouped = pdf.groupby(["filter", "neutralization"]).agg(
        count=("sharpe", "size"),
        pass_rate=("passed", "mean"),
        rejection_rate=("has_rejection", "mean"),
        avg_sharpe=("sharpe", "mean"),
        weight_conc_fail_rate=("weight_conc_fail", "mean"),
        sub_universe_fail_rate=("sub_universe_fail", "mean"),
    ).reset_index()

    return grouped.sort_values(["pass_rate", "count"], ascending=[False, False])


# ------------------------------------------------------------------ #
#  Legacy API (preserved for backward compatibility)                  #
# ------------------------------------------------------------------ #

def get_exploration_settings(category=None):
    """Generate a random but logical set of settings for exploration."""
    return {
        "universe": random.choice(UNIVERSES),
        "delay": random.choice(DELAYS),
        "neutralization": random.choice(NEUTRALIZATIONS),
        "decay": random.choice(DECAYS),
        "truncation": random.choice(TRUNCATIONS),
        "testPeriod": "P3Y"
    }

def mutate_settings(base_settings: dict):
    """Mutate 1 or 2 parameters of a near-elite setting to push it over the edge."""
    new_settings = base_settings.copy()
    mutations = random.sample(["universe", "delay", "neutralization", "decay", "truncation"], k=random.choice([1, 2]))
    
    for mutation_target in mutations:
        if mutation_target == "universe":
            new_settings["universe"] = random.choice([u for u in UNIVERSES if u != new_settings.get("universe")])
        elif mutation_target == "delay":
            new_settings["delay"] = 1 if new_settings.get("delay", 1) == 0 else 0
        elif mutation_target == "neutralization":
            new_settings["neutralization"] = random.choice([n for n in NEUTRALIZATIONS if n != new_settings.get("neutralization")])
        elif mutation_target == "decay":
            new_settings["decay"] = random.choice([d for d in DECAYS if d != new_settings.get("decay")])
        elif mutation_target == "truncation":
            new_settings["truncation"] = random.choice([t for t in TRUNCATIONS if t != new_settings.get("truncation")])
            
    return new_settings

def get_near_elite_simulations(db, limit=5):
    """Retrieve alphas from the simulations table that are near-elite but sub-optimal in settings."""
    query = """
        SELECT alpha, settings, sharpe, fitness, turnover 
        FROM simulations 
        WHERE sharpe >= 1.10 AND fitness >= 0.90 AND turnover < 0.35
    """
    df = pd.read_sql_query(query, db.conn)
    if df.empty:
        return []
    
    df = df.sort_values(["sharpe", "fitness"], ascending=[False, False])
    df = df[df["settings"].notna()]
    return df.head(limit).to_dict(orient="records")