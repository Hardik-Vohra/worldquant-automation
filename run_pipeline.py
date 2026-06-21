import argparse
import logging
import json
from collections import Counter
from datetime import datetime
from typing import List, Dict

import pandas as pd

from project.config import (
    DAILY_TOP10_PATH,
    DEFAULT_GENERATION_LIMIT,
    MIN_SIMULATION_INTERVAL,
    SIMULATION_BUDGET,
    BUDGET_ALLOCATION,
    SETTING_OPTIONS,
    SUBMISSION_SETTINGS,
)
from project.data.fields import FieldCatalog
from project.engine.data_manager import AlphaDatabase
from project.engine.learning_engine import LearningEngine
from project.engine.generator_engine import GeneratorEngine
from project.worldquant.parser import AlphaExpression
from project.auth import AuthenticationError
from project.worldquant.submit import WorldQuantClient
from project.worldquant.poll import WorldQuantPoller
from project.reports.summary import (
    write_report_summary,
    write_alpha_history,
    export_elite_alphas,
)

from settings_optimizer import (
    get_exploration_settings,
    mutate_settings,
    get_near_elite_simulations,
    get_settings_variants,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def select_settings_for_category(db: AlphaDatabase, category: str) -> dict:
    usage = db.get_simulation_budget_usage()
    
    # 1. Dedicated Exploration Phase logic
    phase = current_phase(db)
    if phase == "exploration" and (usage["total_used"] % 3 == 0):
        return get_exploration_settings(category)
        
    # 2. Exploitation / Historical Best
    settings_candidates = db.best_settings_by_category(category, limit=2)
    if settings_candidates:
        import random
        best = settings_candidates[0]
        # 20% chance to mutate the best known settings slightly
        if random.random() < 0.20:
            return mutate_settings(best)
        return best

    # 3. Fallbacks
    fallback = SUBMISSION_SETTINGS.copy()
    if category == "Options":
        fallback.update({"universe": "TOP2000", "neutralization": "INDUSTRY", "decay": 8})
    elif category == "Fundamental":
        fallback.update({"universe": "TOP2000", "neutralization": "SUBINDUSTRY", "decay": 4})
    else:
        fallback.update({"universe": "TOP3000", "neutralization": "SUBINDUSTRY", "decay": 4})
    return fallback


def current_phase(db: AlphaDatabase) -> str:
    used = db.get_simulation_budget_usage()["total_used"]
    if used < 500:
        return "exploration"
    if used < 1000:
        return "learning"
    return "exploitation"


def _candidate_family(row: Dict) -> str:
    return AlphaDatabase._infer_family(row.get("alpha"), row.get("category"))


def _primary_operator(alpha: str) -> str:
    try:
        operators = sorted(AlphaExpression(alpha).operator_set())
    except Exception:
        return "none"
    for operator in operators:
        if operator not in {"rank", "+", "-", "*", "/", "<", ">"}:
            return operator
    return operators[0] if operators else "none"


def _candidate_fields(alpha: str):
    try:
        return sorted(AlphaExpression(alpha).field_set())
    except Exception:
        return []


def prioritize_candidates(db: AlphaDatabase, limit: int) -> List[Dict]:
    candidates = db.get_candidates(limit=limit * 12, min_score=0.0)
    if not candidates:
        return []

    family_stats = db.family_summary()
    proven_categories = set()
    promising_categories = set()
    if not family_stats.empty:
        categories = family_stats["category"].tolist()
        proven_categories.update(categories[:2])
        promising_categories.update(categories[2:4])

    phase = current_phase(db)
    phase_allocations = {
        "exploration": {"proven": 0.10, "promising": 0.30, "exploration": 0.60},
        "learning": {"proven": 0.30, "promising": 0.35, "exploration": 0.35},
        "exploitation": BUDGET_ALLOCATION,
    }
    allocation = phase_allocations[phase]
    proven_count = int(limit * allocation["proven"])
    promising_count = int(limit * allocation["promising"])
    exploration_count = limit - proven_count - promising_count

    selected = []
    seen = set()
    family_counts = Counter()
    operator_counts = Counter()
    field_counts = Counter()
    max_family = max(1, int(limit * 0.30))
    max_operator = max(1, int(limit * 0.35))
    max_field = max(1, int(limit * 0.25))

    for row in candidates:
        row["family"] = _candidate_family(row)
        row["primary_operator"] = _primary_operator(row["alpha"])
        row["parsed_fields"] = _candidate_fields(row["alpha"])

    def can_add(row, strict=True):
        if not strict:
            return True
        if family_counts[row["family"]] >= max_family:
            return False
        if operator_counts[row["primary_operator"]] >= max_operator:
            return False
        if any(field_counts[field] >= max_field for field in row["parsed_fields"]):
            return False
        return True

    def mark(row):
        selected.append(row)
        seen.add(row["alpha"])
        family_counts[row["family"]] += 1
        operator_counts[row["primary_operator"]] += 1
        for field in row["parsed_fields"]:
            field_counts[field] += 1

    def add_pool(predicate, target_count):
        nonlocal selected
        for strict in [True, False]:
            for row in candidates:
                if len([x for x in selected if predicate(x)]) >= target_count:
                    return
                alpha = row["alpha"]
                if alpha in seen:
                    continue
                if predicate(row) and can_add(row, strict=strict):
                    mark(row)
            if len([x for x in selected if predicate(x)]) >= target_count:
                break

    add_pool(lambda row: row.get("family") in proven_categories, proven_count)
    add_pool(lambda row: row.get("generation") == 1 or row.get("family") in promising_categories, promising_count)
    add_pool(lambda row: row.get("family") not in proven_categories and row.get("generation") != 1, exploration_count)

    if len(selected) < limit:
        for strict in [True, False]:
            for row in candidates:
                if row["alpha"] not in seen and can_add(row, strict=strict):
                    mark(row)
                    if len(selected) >= limit:
                        break
            if len(selected) >= limit:
                break

    return selected[:limit]


def build_report_summary(db: AlphaDatabase, submitted: int, final_candidates: List[Dict]) -> Dict:
    usage = db.get_simulation_budget_usage()
    remaining_budget = max(0, SIMULATION_BUDGET - usage["total_used"])

    family_stats = db.family_summary()
    top_families = []
    if not family_stats.empty:
        top_families = [
            {
                "category": row["category"],
                "tested": int(row["tested"]),
                "success_rate": float(row["success_rate"]),
                "avg_sharpe": float(row["average_sharpe"] or 0),
                "avg_fitness": float(row["average_fitness"] or 0),
            }
            for _, row in family_stats.head(5).iterrows()
        ]

    settings_stats = db.settings_summary()
    top_settings = []
    if not settings_stats.empty:
        top_settings = [row.to_dict() for _, row in settings_stats.head(5).iterrows()]

    top_fields = []
    top_ops = []
    learner = LearningEngine(db)
    field_stats = learner.field_stats()
    op_stats = learner.operator_stats()

    if not field_stats.empty:
        top_fields = [
            {"field": idx, **row.to_dict()} for idx, row in field_stats.head(10).iterrows()
        ]
    if not op_stats.empty:
        top_ops = [
            {"operator": idx, **row.to_dict()} for idx, row in op_stats.head(10).iterrows()
        ]

    return {
        "Simulation Budget Remaining": remaining_budget,
        "Total Simulations Used": usage["total_used"],
        "Simulations Running": usage["running"],
        "Simulations Completed": usage["completed"],
        "Learning Phase": current_phase(db),
        "Budget Used Today": submitted,
        "Top Alpha Families": top_families,
        "Top Settings": top_settings,
        "Top Fields": top_fields,
        "Top Operators": top_ops,
        "Top 50 Daily Recommendations": [
            {
                "alpha": candidate["alpha"],
                "score": candidate.get("predicted_score", candidate.get("realized_score", candidate.get("score", 0))),
                "category": candidate.get("category"),
                "family": candidate.get("family"),
            }
            for candidate in final_candidates
        ],
    }


def main(submit: bool = True, poll: bool = True, dry_run: bool = False, submit_limit: int = 20):
    db = AlphaDatabase()
    inserted = db.load_legacy_results()
    if inserted:
        logger.info(f"Imported {inserted} legacy alpha records into the database.")

    catalog = FieldCatalog()
    learner = LearningEngine(db)
    generator = GeneratorEngine(catalog, learner, db)

    logger.info("Generating candidate alphas...")
    candidates = generator.generate_candidates(limit=DEFAULT_GENERATION_LIMIT)
    logger.info(f"Generated {len(candidates)} candidates.")

    new_alpha_count = 0
    for candidate in candidates:
        if db.insert_alpha(
            alpha=candidate["alpha"],
            generation=candidate.get("generation", 0),
            parent_alpha=candidate.get("parent_alpha"),
            category=candidate.get("category"),
            field_set=candidate.get("field_set", []),
            operator_set=candidate.get("operator_set", []),
            predicted_sharpe=candidate.get("predicted_sharpe"),
            predicted_fitness=candidate.get("predicted_fitness"),
            predicted_turnover=candidate.get("predicted_turnover"),
            score=candidate.get("predicted_score"),
            settings=candidate.get("settings"),
        ):
            new_alpha_count += 1
    logger.info(f"Inserted {new_alpha_count} new candidate alphas into the database.")

    try:
        client = WorldQuantClient()
    except AuthenticationError as exc:
        logger.error("Authentication failed: %s", exc)
        return

    poller = WorldQuantPoller(db, client)
    submitted = 0

    if submit and not dry_run:
        logger.info("Selecting submission candidates under budget constraints...")
        remaining_budget = max(0, SIMULATION_BUDGET - db.get_simulation_budget_usage()["total_used"])
        submit_limit = min(submit_limit, remaining_budget)
        if submit_limit <= 0:
            logger.info("No remaining simulation budget. Skipping submission.")
        else:
            # --- PHASE 1: Settings Optimization Pipeline (40% budget) ---
            grid_limit = int(submit_limit * 0.40)
            queued_alphas = generator.learning.get_settings_queue(limit=grid_limit)
            
            if queued_alphas:
                logger.info(f"Submitting up to {grid_limit} simulations from the Settings Optimization Queue.")
                for alpha_record in queued_alphas:
                    if submitted >= submit_limit:
                        break
                    # We might submit multiple variants per alpha if budget allows
                    variants_to_test = max(1, (grid_limit - submitted) // len(queued_alphas))
                    variants = get_settings_variants(alpha_record["alpha"], db, limit=variants_to_test)
                    
                    for settings in variants:
                        if submitted >= submit_limit:
                            break
                        try:
                            sim_id = client.submit_alpha(alpha_record["alpha"], settings=settings)
                            db.insert_simulation(alpha_record["alpha"], settings, sim_id, status="RUNNING")
                            # Mark in the alphas table so we know it has been generated
                            db.update_metrics(alpha_text=alpha_record["alpha"], sim_id=sim_id, status="RUNNING")
                            submitted += 1
                            logger.info(f"Settings Grid: {alpha_record['alpha'][:50]} -> {settings}")
                        except AuthenticationError as exc:
                            logger.error("Authentication failed during submission: %s", exc)
                            return
                        except Exception as exc:
                            logger.warning(f"Failed to submit settings-variant alpha: {exc}")

            # --- PHASE 2: Settings Mutation Pipeline for Near-Elite Alphas (30% budget) ---
            remaining_limit = submit_limit - submitted
            mutation_limit = int(submit_limit * 0.30)
            mutation_limit = min(mutation_limit, remaining_limit)
            
            if mutation_limit > 0:
                near_elites = get_near_elite_simulations(db, limit=mutation_limit)
                if near_elites:
                    logger.info(f"Submitting {len(near_elites)} near-elite alphas for Settings Mutation.")
                    for ne in near_elites:
                        if submitted >= submit_limit:
                            break
                        try:
                            base_settings = json.loads(ne["settings"]) if pd.notna(ne["settings"]) else SUBMISSION_SETTINGS
                            new_settings = mutate_settings(base_settings)
                            sim_id = client.submit_alpha(ne["alpha"], settings=new_settings)
                            db.insert_simulation(ne["alpha"], new_settings, sim_id, status="RUNNING")
                            submitted += 1
                            logger.info(f"Settings Mutated: {ne['alpha'][:50]} -> {new_settings}")
                        except AuthenticationError as exc:
                            logger.error("Authentication failed during submission: %s", exc)
                            return
                        except Exception as exc:
                            logger.warning(f"Failed to submit settings-mutated alpha: {exc}")

            # --- PHASE 3: Regular Generation Pipeline (Remaining budget) ---
            remaining_limit = submit_limit - submitted
            if remaining_limit > 0:
                batch = prioritize_candidates(db, remaining_limit)
                logger.info(f"Submitting {len(batch)} newly generated candidates under budget allocation.")
                for row in batch:
                    settings = select_settings_for_category(db, row.get("category", "Unknown"))
                    try:
                        sim_id = client.submit_alpha(row["alpha"], settings=settings)
                        db.insert_simulation(row["alpha"], settings, sim_id, status="RUNNING")
                        db.update_metrics(alpha_text=row["alpha"], sim_id=sim_id, status="RUNNING")
                        submitted += 1
                        logger.info(f"Submitted {row['alpha'][:80]} under settings {settings} -> sim {sim_id}")
                    except AuthenticationError as exc:
                        logger.error("Authentication failed during submission: %s", exc)
                        return
                    except Exception as exc:
                        logger.warning(f"Failed to submit alpha: {exc}")
                        
            logger.info(f"Submitted {submitted} alphas total in this cycle.")
    else:
        logger.info("Skipping submission phase.")
    

    if poll and not dry_run:
        logger.info("Polling WorldQuant simulation results...")
        completed = poller.poll_pending(max_seconds=600)
        logger.info(f"Completed {len(completed)} simulations.")
    else:
        logger.info("Skipping polling phase.")

    learner.refresh()
    
    # --- EXPANDED VISIBILITY FUNNEL (Top 50 instead of Top 10) ---
    final_candidates = db.get_top_scored(limit=50)
    if not final_candidates:
        logger.info("No completed alphas found; using highest predicted candidates.")
        final_candidates = sorted(
            [c for c in candidates if c.get("predicted_score") is not None],
            key=lambda x: x["predicted_score"],
            reverse=True,
        )[:50]

    summary = build_report_summary(db, submitted, final_candidates)
    report_path = write_report_summary(summary, path="project/reports/daily_report_summary.txt")
    logger.info(f"Wrote report summary to {report_path}")

    history_path = write_alpha_history(db, final_candidates, path="project/reports/alpha_history.xlsx")
    logger.info(f"Wrote alpha history to {history_path}")

    elite_path = export_elite_alphas(db, path="project/reports/elite_alphas.csv")
    logger.info(f"Wrote elite alphas to {elite_path}")

    logger.info("Run complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the WQ autonomous alpha pipeline.")
    parser.add_argument("--no-submit", action="store_true", help="Do not submit new alphas.")
    parser.add_argument("--no-poll", action="store_true", help="Do not poll WorldQuant to refresh results.")
    parser.add_argument("--dry-run", action="store_true", help="Do not submit or poll; only generate candidates.")
    parser.add_argument("--submit-limit", type=int, default=20, help="Maximum number of candidates to submit.")
    args = parser.parse_args()
    main(submit=not args.no_submit, poll=not args.no_poll, dry_run=args.dry_run, submit_limit=args.submit_limit)