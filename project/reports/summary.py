from project.config import DAILY_TOP10_PATH, REPORTS_DIR
from typing import List, Dict
import pandas as pd
import json


def _number(value, default=0.0):
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def write_daily_top10(candidates: List[Dict], path: str = None):
    path = path or DAILY_TOP10_PATH
    with open(path, "w", encoding="utf-8") as f:
        for rank, candidate in enumerate(candidates, start=1):
            sharpe = _number(candidate.get("predicted_sharpe", candidate.get("sharpe")))
            fitness = _number(candidate.get("predicted_fitness", candidate.get("fitness")))
            turnover = _number(candidate.get("predicted_turnover", candidate.get("turnover")))
            score = _number(candidate.get("predicted_score", candidate.get("realized_score", candidate.get("score"))))
            f.write(f"{rank}.\n")
            f.write(f"Alpha: {candidate['alpha']}\n")
            f.write(f"Sharpe: {sharpe:.3f}\n")
            f.write(f"Fitness: {fitness:.3f}\n")
            f.write(f"Turnover: {turnover:.3f}\n")
            f.write(f"Score: {score:.3f}\n")
            f.write(f"Confidence Score: {_number(candidate.get('confidence')):.2f}\n")
            if candidate.get("parent_alpha"):
                f.write(f"Parent Alpha: {candidate['parent_alpha']}\n")
            if candidate.get("reason", None):
                f.write(f"Reason Selected: {candidate['reason']}\n")
            f.write("---\n")
    return path


def write_report_summary(summary: Dict, path: str = None):
    path = path or str(REPORTS_DIR / "daily_report_summary.txt")
    with open(path, "w", encoding="utf-8") as f:
        for section, data in summary.items():
            f.write(f"## {section}\n")
            if isinstance(data, dict):
                for key, value in data.items():
                    f.write(f"- {key}: {value}\n")
            elif isinstance(data, list):
                for record in data:
                    if isinstance(record, dict):
                        f.write("- " + "; ".join(f"{k}: {v}" for k, v in record.items()) + "\n")
                    else:
                        f.write(f"- {record}\n")
            else:
                f.write(f"{data}\n")
            f.write("\n")
    return path


def write_alpha_history(db, top_candidates: List[Dict], path: str = None):
    """Generate comprehensive Excel workbook with all metrics and analytics."""
    path = path or str(REPORTS_DIR / "alpha_history.xlsx")
    all_results = db.to_dataframe()
    
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # Sheet 1: All Results (all metrics dynamically included)
        all_results.to_excel(writer, sheet_name="All Results", index=False)
        
        # Sheet 2: Elite Results under the objective KPI.
        if "sharpe" in all_results.columns and "fitness" in all_results.columns:
            elite = all_results[
                (all_results["sharpe"].notna()) & 
                (all_results["sharpe"] > 1.25) & 
                (all_results["fitness"].notna()) & 
                (all_results["fitness"] > 1.05) &
                (all_results["turnover"].notna()) &
                (all_results["turnover"] < 0.25)
            ]
        else:
            elite = pd.DataFrame()
        elite.to_excel(writer, sheet_name="Elite Results", index=False)
        
        # Sheet 3: Best Settings
        settings_df = db.settings_summary()
        if not settings_df.empty:
            settings_df.to_excel(writer, sheet_name="Best Settings", index=False)
        else:
            pd.DataFrame([]).to_excel(writer, sheet_name="Best Settings", index=False)
        
        # Sheet 4: Best Fields
        field_perf = db.field_performance()
        if not field_perf.empty:
            field_perf.to_excel(writer, sheet_name="Best Fields", index=False)
        else:
            pd.DataFrame([]).to_excel(writer, sheet_name="Best Fields", index=False)
        
        # Sheet 5: Best Operators
        op_perf = db.operator_performance()
        if not op_perf.empty:
            op_perf.to_excel(writer, sheet_name="Best Operators", index=False)
        else:
            pd.DataFrame([]).to_excel(writer, sheet_name="Best Operators", index=False)
        
        # Sheet 6: Daily Top 10
        recommendations = pd.DataFrame(top_candidates)
        if not recommendations.empty:
            recommendations.to_excel(writer, sheet_name="Top 10 Daily", index=False)
        else:
            pd.DataFrame([]).to_excel(writer, sheet_name="Top 10 Daily", index=False)
        
        # Sheet 7: Simulation Budget
        budget_info = db.get_simulation_budget_usage()
        budget_df = pd.DataFrame([budget_info])
        budget_df.to_excel(writer, sheet_name="Simulation Budget", index=False)
        
        # Sheet 8: Family Summary (by category)
        family_df = db.family_summary()
        if not family_df.empty:
            family_df.to_excel(writer, sheet_name="Family Summary", index=False)
        else:
            pd.DataFrame([]).to_excel(writer, sheet_name="Family Summary", index=False)

        # Added performance dashboards.
        family_df.to_excel(writer, sheet_name="Alpha Family Performance", index=False)
        op_perf.to_excel(writer, sheet_name="Operator Performance", index=False)
        field_perf.to_excel(writer, sheet_name="Field Performance", index=False)
        settings_df.to_excel(writer, sheet_name="Settings Performance", index=False)
        _elite_funnel(all_results).to_excel(writer, sheet_name="Elite Candidate Funnel", index=False)
        _budget_efficiency(db, all_results).to_excel(writer, sheet_name="Budget Efficiency", index=False)
    
    return path


def export_elite_alphas(db, path: str = None):
    """Export elite alphas under the objective KPI."""
    path = path or str(REPORTS_DIR / "elite_alphas.csv")
    all_results = db.to_dataframe()
    if "sharpe" in all_results.columns and "fitness" in all_results.columns:
        elite = all_results[
            (all_results["sharpe"].notna()) & 
            (all_results["sharpe"] > 1.25) & 
            (all_results["fitness"].notna()) & 
            (all_results["fitness"] > 1.05) &
            (all_results["turnover"].notna()) &
            (all_results["turnover"] < 0.25)
        ]
    else:
        elite = all_results
    elite.to_csv(path, index=False)
    return path


def _elite_funnel(all_results: pd.DataFrame):
    if all_results.empty or "sharpe" not in all_results.columns:
        return pd.DataFrame([])
    evaluated = all_results[all_results["sharpe"].notna()].copy()
    if evaluated.empty:
        return pd.DataFrame([{
            "evaluated": 0,
            "sharpe_gt_1_25": 0,
            "fitness_gt_1_05": 0,
            "turnover_lt_0_25": 0,
            "elite_count": 0,
            "elite_discovery_rate": 0.0,
        }])
    sharpe_pass = evaluated["sharpe"] > 1.25
    fitness_pass = evaluated["fitness"] > 1.05
    turnover_pass = evaluated["turnover"] < 0.25
    elite = sharpe_pass & fitness_pass & turnover_pass
    return pd.DataFrame([{
        "evaluated": int(len(evaluated)),
        "sharpe_gt_1_25": int(sharpe_pass.sum()),
        "fitness_gt_1_05": int(fitness_pass.sum()),
        "turnover_lt_0_25": int(turnover_pass.sum()),
        "elite_count": int(elite.sum()),
        "elite_discovery_rate": float(elite.sum() / max(1, len(evaluated))),
    }])


def _budget_efficiency(db, all_results: pd.DataFrame):
    usage = db.get_simulation_budget_usage()
    funnel = _elite_funnel(all_results)
    elite_count = int(funnel.iloc[0]["elite_count"]) if not funnel.empty else 0
    total_used = usage["total_used"]
    return pd.DataFrame([{
        **usage,
        "elite_count": elite_count,
        "elite_discovery_rate": float(elite_count / max(1, total_used)),
        "simulations_per_elite": None if elite_count == 0 else float(total_used / elite_count),
    }])
