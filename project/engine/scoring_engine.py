from project.config import PERFORMANCE_THRESHOLDS

ELITE_OBJECTIVE = {
    "sharpe": 1.50,    # Increased from 1.25
    "fitness": 1.20,   # Increased from 1.05
    "turnover": 0.15,  # Decreased from 0.25 (Preferred objective)
}

def score_metrics(sharpe, fitness, turnover):
    if sharpe is None or fitness is None:
        return None
    turnover = turnover or 0.0
    
    sharpe_score = sharpe / ELITE_OBJECTIVE["sharpe"]
    fitness_score = fitness / ELITE_OBJECTIVE["fitness"]
    
    # Harsh penalty for high turnover (>0.20)
    if turnover > 0.20:
        turnover_score = -2.0 * ((turnover - 0.20) / 0.10)
    else:
        turnover_score = (ELITE_OBJECTIVE["turnover"] - turnover) / ELITE_OBJECTIVE["turnover"]
    turnover_score = max(-1.0, min(1.0, turnover_score))

    # Threshold bonuses for achieving actual elite status
    threshold_bonus = 0.0
    if sharpe >= 1.25:
        threshold_bonus += 0.20
    if fitness >= 1.05:
        threshold_bonus += 0.20
    if turnover <= 0.20:
        threshold_bonus += 0.15

    return sharpe_score * 0.45 + fitness_score * 0.35 + turnover_score * 0.20 + threshold_bonus


def classify_alpha(sharpe, fitness):
    if sharpe is None or fitness is None:
        return "Unknown"
    if sharpe >= 1.50 and fitness >= 1.20:
        return "Elite"
    if sharpe >= 1.25 and fitness >= 1.05:
        return "Excellent"
    return "Candidate"