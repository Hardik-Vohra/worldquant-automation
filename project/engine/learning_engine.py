import pandas as pd
from typing import List
from project.worldquant.parser import AlphaExpression
from project.engine.data_manager import AlphaDatabase
from project.engine.scoring_engine import ELITE_OBJECTIVE


def _p90(x):
    """Calculate the 90th percentile to find the elite potential (ceiling) of a field/operator."""
    return float(x.quantile(0.90)) if len(x) >= 3 else float(x.mean())


class LearningEngine:
    def __init__(self, db: AlphaDatabase):
        self.db = db
        self._reload()

    def _reload(self):
        self.df = self.db.to_dataframe()
        self.df = self.df[self.df["sharpe"].notna()] if not self.df.empty else self.df
        self._stats_cache = {}

    def _simulation_df(self):
        try:
            return pd.read_sql_query(
                "SELECT s.*, a.category FROM simulations s LEFT JOIN alphas a ON s.alpha = a.alpha",
                self.db.conn,
            )
        except Exception:
            return pd.DataFrame()

    def _winner_expressions(self):
        sim_df = self._simulation_df()
        winners = sim_df[(sim_df["sharpe"] >= 1.0) & (sim_df["fitness"] >= 0.8)]
        return [AlphaExpression(alpha) for alpha in winners["alpha"].dropna().unique()] if not winners.empty else []

    def _failure_expressions(self):
        sim_df = self._simulation_df()
        failures = sim_df[(sim_df["sharpe"].notna()) & ((sim_df["sharpe"] < 1.0) | (sim_df["fitness"] < 0.8))]
        return [AlphaExpression(alpha) for alpha in failures["alpha"].dropna().unique()] if not failures.empty else []

    def family_success_rates(self):
        family_df = self.db.family_summary()
        if family_df.empty:
            return {}
        return {
            row["category"]: float(row["success_rate"])
            for _, row in family_df.iterrows()
        }

    def refresh(self):
        self._reload()

    def _explode(self, column):
        if column not in self.df.columns:
            return pd.DataFrame()
        exploded = self.df.copy()
        exploded[column] = exploded[column].fillna("")
        exploded[column] = exploded[column].str.split(",")
        exploded = exploded.explode(column)
        exploded[column] = exploded[column].str.strip()
        exploded = exploded[exploded[column] != ""]
        return exploded

    def calculate_entropy(self):
        import numpy as np
        from collections import Counter
        if self.df.empty:
            return {"operator_entropy": 2.5, "field_entropy": 4.5, "family_entropy": 1.5}
        
        recent_df = self.df.tail(1000)
        
        def _ent(series):
            items = []
            for item_set in series.dropna():
                if isinstance(item_set, str):
                    items.extend([i.strip() for i in item_set.split(',') if i.strip()])
            counts = Counter(items)
            total = sum(counts.values())
            if total == 0: return 1.0
            probs = [c/total for c in counts.values()]
            return -sum(p * np.log2(p) for p in probs if p > 0)
            
        op_ent = _ent(recent_df["operator_set"]) if "operator_set" in recent_df.columns else 2.5
        field_ent = _ent(recent_df["field_set"]) if "field_set" in recent_df.columns else 4.5
        
        if "category" in recent_df.columns:
            cats = recent_df["category"].dropna().tolist()
            counts = Counter(cats)
            total = sum(counts.values())
            probs = [c/total for c in counts.values()] if total > 0 else [1]
            family_ent = -sum(p * np.log2(p) for p in probs if p > 0)
        else:
            family_ent = 1.5
            
        return {
            "operator_entropy": float(op_ent),
            "field_entropy": float(field_ent),
            "family_entropy": float(family_ent),
        }

    def _get_agg_funcs(self, df):
        funcs = {
            "average_sharpe": ("sharpe", "mean"),
            "p90_sharpe": ("sharpe", _p90),
            "average_fitness": ("fitness", "mean"),
            "p90_fitness": ("fitness", _p90),
            "average_turnover": ("turnover", "mean"),
            "count": ("alpha", "count"),
        }
        if "rejection_reason" in df.columns:
            df["rejected"] = df["rejection_reason"].notna() & (df["rejection_reason"] != "")
            funcs["rejection_rate"] = ("rejected", "mean")
        return funcs

    def field_stats(self):
        if "field_stats" in self._stats_cache:
            return self._stats_cache["field_stats"]
        exploded = self._explode("field_set")
        if exploded.empty:
            return pd.DataFrame()
        funcs = self._get_agg_funcs(exploded)
        grouped = exploded.groupby("field_set").agg(**funcs)
        grouped["quality_score"] = grouped.apply(self._quality_from_row, axis=1)
        result = grouped.sort_values(["quality_score", "p90_sharpe", "count"], ascending=[False, False, False])
        self._stats_cache["field_stats"] = result
        return result

    def operator_stats(self):
        if "operator_stats" in self._stats_cache:
            return self._stats_cache["operator_stats"]
        exploded = self._explode("operator_set")
        if exploded.empty:
            return pd.DataFrame()
        funcs = self._get_agg_funcs(exploded)
        grouped = exploded.groupby("operator_set").agg(**funcs)
        grouped["quality_score"] = grouped.apply(self._quality_from_row, axis=1)
        result = grouped.sort_values(["quality_score", "p90_sharpe", "count"], ascending=[False, False, False])
        self._stats_cache["operator_stats"] = result
        return result

    def category_stats(self):
        if "category_stats" in self._stats_cache:
            return self._stats_cache["category_stats"]
        if "category" not in self.df.columns or self.df.empty:
            return pd.DataFrame()
        funcs = self._get_agg_funcs(self.df)
        grouped = self.df.groupby("category").agg(**funcs)
        grouped["quality_score"] = grouped.apply(self._quality_from_row, axis=1)
        result = grouped.sort_values(["quality_score", "p90_sharpe", "count"], ascending=[False, False, False])
        self._stats_cache["category_stats"] = result
        return result

    def simulation_count(self):
        sim_df = self._simulation_df()
        return int(sim_df["sim_id"].notna().sum()) if not sim_df.empty and "sim_id" in sim_df.columns else 0

    def current_phase(self):
        used = self.simulation_count()
        if used < 500:
            return "exploration"
        if used < 1000:
            return "learning"
        return "exploitation"

    def _quality_from_row(self, row):
        # Base quality off the 90th percentile to reward ceiling potential
        sharpe = row.get("p90_sharpe", 0) or 0
        fitness = row.get("p90_fitness", 0) or 0
        turnover = row.get("average_turnover", 0.25)
        rejection_rate = row.get("rejection_rate", 0.0) or 0.0
        if pd.isna(turnover):
            turnover = 0.25
            
        turnover_component = (ELITE_OBJECTIVE["turnover"] - turnover) / ELITE_OBJECTIVE["turnover"]
        turnover_component = max(-1.0, min(1.0, turnover_component))
        base_quality = sharpe / ELITE_OBJECTIVE["sharpe"] * 0.45 + fitness / ELITE_OBJECTIVE["fitness"] * 0.40 + turnover_component * 0.15
        return base_quality * (1.0 - (rejection_rate * 0.40))  # Up to 40% penalty for 100% rejection rate

    def _overall_means(self):
        if self.df.empty:
            return {"sharpe": 0.12, "p90_sharpe": 0.25, "fitness": 0.08, "p90_fitness": 0.15, "turnover": 0.08}
        return {
            "sharpe": float(self.df["sharpe"].mean() if "sharpe" in self.df else 0.12),
            "p90_sharpe": float(self.df["sharpe"].quantile(0.90) if "sharpe" in self.df and len(self.df) >= 3 else 0.25),
            "fitness": float(self.df["fitness"].mean() if "fitness" in self.df else 0.08),
            "p90_fitness": float(self.df["fitness"].quantile(0.90) if "fitness" in self.df and len(self.df) >= 3 else 0.15),
            "turnover": float(self.df["turnover"].mean() if "turnover" in self.df else 0.08),
        }

    def _similarity_to_expressions(self, expression: AlphaExpression, expressions: List[AlphaExpression]):
        if not expressions:
            return 0.0
        return float(sum(expression.similarity(other) for other in expressions) / len(expressions))

    def predict_metrics(self, expression: AlphaExpression, category: str = None):
        if self.df.empty:
            return {
                "predicted_sharpe": 0.20,
                "predicted_fitness": 0.12,
                "predicted_turnover": 0.08,
                "confidence": 0.5,
            }

        field_stats = self.field_stats()
        operator_stats = self.operator_stats()
        category_stats = self.category_stats()
        overall = self._overall_means()

        fields = expression.field_set()
        operators = expression.operator_set()

        # Extract P90 Scores instead of average scores
        field_scores = [field_stats.loc[field, "p90_sharpe"] for field in fields if field in field_stats.index]
        field_fitness = [field_stats.loc[field, "p90_fitness"] for field in fields if field in field_stats.index]
        field_turnover = [field_stats.loc[field, "average_turnover"] for field in fields if field in field_stats.index]
        field_rejections = [field_stats.loc[field, "rejection_rate"] for field in fields if field in field_stats.index and "rejection_rate" in field_stats.columns]

        operator_scores = [operator_stats.loc[op, "p90_sharpe"] for op in operators if op in operator_stats.index]
        operator_fitness = [operator_stats.loc[op, "p90_fitness"] for op in operators if op in operator_stats.index]
        operator_turnover = [operator_stats.loc[op, "average_turnover"] for op in operators if op in operator_stats.index]
        operator_rejections = [operator_stats.loc[op, "rejection_rate"] for op in operators if op in operator_stats.index and "rejection_rate" in operator_stats.columns]

        average_field = float(sum(field_scores) / len(field_scores)) if field_scores else overall["p90_sharpe"]
        average_operator = float(sum(operator_scores) / len(operator_scores)) if operator_scores else overall["p90_sharpe"]
        average_field_fitness = float(sum(field_fitness) / len(field_fitness)) if field_fitness else overall["p90_fitness"]
        average_operator_fitness = float(sum(operator_fitness) / len(operator_fitness)) if operator_fitness else overall["p90_fitness"]
        average_field_turnover = float(sum(field_turnover) / len(field_turnover)) if field_turnover else overall["turnover"]
        average_operator_turnover = float(sum(operator_turnover) / len(operator_turnover)) if operator_turnover else overall["turnover"]
        
        avg_field_rej = float(sum(field_rejections) / len(field_rejections)) if field_rejections else 0.0
        avg_op_rej = float(sum(operator_rejections) / len(operator_rejections)) if operator_rejections else 0.0
        rejection_penalty = (avg_field_rej * 0.4 + avg_op_rej * 0.6) * 0.4  # Max 0.4 penalty

        category_sharpe = overall["p90_sharpe"]
        category_fitness = overall["p90_fitness"]
        category_turnover = overall["turnover"]
        category_count = 0
        
        if category and not category_stats.empty and category in category_stats.index:
            category_row = category_stats.loc[category]
            category_sharpe = float(category_row["p90_sharpe"])
            category_fitness = float(category_row["p90_fitness"])
            category_turnover = float(category_row["average_turnover"])
            category_count = int(category_row["count"])

        phase = self.current_phase()
        underexplored_bonus = 0.10 if phase == "exploration" and category_count < 25 else 0.0
        if phase == "learning" and category_count < 50:
            underexplored_bonus = 0.05

        winner_similarity = self._similarity_to_expressions(expression, self._winner_expressions())
        failure_similarity = self._similarity_to_expressions(expression, self._failure_expressions())

        similarity_bonus = min(0.08, winner_similarity * 0.10)
        similarity_penalty = min(0.12, failure_similarity * 0.12)

        predicted_sharpe = round(
            max(-1.0, min(2.5, average_field * 0.38 + average_operator * 0.27 + category_sharpe * 0.25 + 0.05 + underexplored_bonus + similarity_bonus - similarity_penalty - rejection_penalty)),
            3,
        )
        predicted_fitness = round(
            max(-1.0, min(2.5, average_field_fitness * 0.38 + average_operator_fitness * 0.27 + category_fitness * 0.25 + predicted_sharpe * 0.10 + underexplored_bonus * 0.4 - rejection_penalty)),
            3,
        )
        predicted_turnover = round(
            max(0.01, min(0.8, average_field_turnover * 0.40 + average_operator_turnover * 0.30 + category_turnover * 0.20 + 0.01 * max(0, len(fields) - 1))),
            3,
        )
        confidence = min(
            0.98,
            0.40
            + 0.08 * min(2, len(field_scores))
            + 0.06 * min(2, len(operator_scores))
            + 0.02 * min(5, category_count),
        )

        return {
            "predicted_sharpe": predicted_sharpe,
            "predicted_fitness": predicted_fitness,
            "predicted_turnover": predicted_turnover,
            "confidence": round(confidence, 2),
        }

    def top_fields(self, limit=20):
        stats = self.field_stats()
        return stats.head(limit).index.tolist() if not stats.empty else []

    def top_operators(self, limit=20):
        stats = self.operator_stats()
        return stats.head(limit).index.tolist() if not stats.empty else []

    def top_categories(self, limit=10):
        stats = self.category_stats()
        return stats.head(limit).index.tolist() if not stats.empty else []

    def winning_fields(self, min_sharpe=1.0):
        stats = self.field_stats()
        return stats[stats["p90_sharpe"] >= min_sharpe].index.tolist() if not stats.empty else []

    def winning_operators(self, min_sharpe=1.0):
        stats = self.operator_stats()
        return stats[stats["p90_sharpe"] >= min_sharpe].index.tolist() if not stats.empty else []

    def describe(self):
        return {
            "fields": self.field_stats().head(10).to_dict(orient="index") if not self.df.empty else {},
            "operators": self.operator_stats().head(10).to_dict(orient="index") if not self.df.empty else {},
            "categories": self.category_stats().head(10).to_dict(orient="index") if not self.df.empty else {},
        }


if __name__ == "__main__":
    from project.engine.data_manager import AlphaDatabase

    db = AlphaDatabase()
    learner = LearningEngine(db)
    print(learner.describe())