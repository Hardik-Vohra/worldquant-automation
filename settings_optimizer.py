import random
import json
import pandas as pd

# Universes restored to include TOP3000 to capture high-alpha micro-cap opportunities
UNIVERSES = ["TOP500", "TOP1000", "TOP2000", "TOP3000"] 
DELAYS = [0, 1]
NEUTRALIZATIONS = ["NONE", "MARKET", "SECTOR", "INDUSTRY", "SUBINDUSTRY"]
DECAYS = [0, 2, 4, 8, 16]

# Truncations strictly capped at 0.03 to prevent Max Weight concentration rejections
TRUNCATIONS = [0.01, 0.02, 0.025, 0.03] 

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