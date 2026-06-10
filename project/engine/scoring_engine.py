from project.config import PERFORMANCE_THRESHOLDS

ELITE_OBJECTIVE = {
    "sharpe": 1.25,
    "fitness": 1.05,
    "turnover": 0.25,
}


def score_metrics(sharpe, fitness, turnover):
    if sharpe is None or fitness is None:
        return None
    turnover = turnover or 0.0
    sharpe_score = sharpe / ELITE_OBJECTIVE["sharpe"]
    fitness_score = fitness / ELITE_OBJECTIVE["fitness"]
    turnover_score = (ELITE_OBJECTIVE["turnover"] - turnover) / ELITE_OBJECTIVE["turnover"]
    turnover_score = max(-1.0, min(1.0, turnover_score))

    threshold_bonus = 0.0
    if sharpe > ELITE_OBJECTIVE["sharpe"]:
        threshold_bonus += 0.15
    if fitness > ELITE_OBJECTIVE["fitness"]:
        threshold_bonus += 0.15
    if turnover < ELITE_OBJECTIVE["turnover"]:
        threshold_bonus += 0.08

    return sharpe_score * 0.45 + fitness_score * 0.40 + turnover_score * 0.15 + threshold_bonus


def classify_alpha(sharpe, fitness):
    if sharpe is None or fitness is None:
        return "Unknown"
    if sharpe >= PERFORMANCE_THRESHOLDS["excellent"]["sharpe"] and fitness >= PERFORMANCE_THRESHOLDS["excellent"]["fitness"]:
        return "Excellent"
    if sharpe >= PERFORMANCE_THRESHOLDS["elite"]["sharpe"] and fitness >= PERFORMANCE_THRESHOLDS["elite"]["fitness"]:
        return "Elite"
    return "Candidate"
