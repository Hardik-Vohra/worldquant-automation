import sqlite3
from pathlib import Path
from datetime import datetime
import csv
import json
import pandas as pd
from project.config import DB_PATH, LEGACY_RESULTS_CSV
from project.engine.scoring_engine import score_metrics


class AlphaDatabase:
    def __init__(self, path: Path = None):
        self.path = Path(path) if path else DB_PATH
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alphas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alpha TEXT UNIQUE,
                generation INTEGER,
                parent_alpha TEXT,
                category TEXT,
                field_set TEXT,
                operator_set TEXT,
                status TEXT,
                sim_id TEXT,
                alpha_id TEXT,
                sharpe REAL,
                fitness REAL,
                turnover REAL,
                returns REAL,
                margin REAL,
                predicted_sharpe REAL,
                predicted_fitness REAL,
                predicted_turnover REAL,
                score REAL,
                settings TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alpha TEXT,
                settings TEXT,
                sim_id TEXT UNIQUE,
                alpha_id TEXT,
                status TEXT,
                sharpe REAL,
                fitness REAL,
                turnover REAL,
                returns REAL,
                margin REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )
        self.conn.commit()
        self._migrate_schema()

    def _migrate_schema(self):
        """Auto-detect and add new columns to alphas table."""
        alphas_cols = {row[1] for row in self.conn.execute("PRAGMA table_info(alphas)").fetchall()}
        sims_cols = {row[1] for row in self.conn.execute("PRAGMA table_info(simulations)").fetchall()}
        
        # Add expected metric columns to alphas if missing
        for col in ["sharpe", "fitness", "turnover", "returns", "margin", "settings"]:
            if col not in alphas_cols:
                self.conn.execute(f"ALTER TABLE alphas ADD COLUMN {col} {'TEXT' if col == 'settings' else 'REAL'}")
        
        # Ensure simulations table has all metric columns
        for col in ["sharpe", "fitness", "turnover", "returns", "margin"]:
            if col not in sims_cols:
                self.conn.execute(f"ALTER TABLE simulations ADD COLUMN {col} REAL")
        
        self.conn.commit()

    def add_column_if_missing(self, table: str, column: str, col_type: str = "REAL"):
        """Dynamically add a column to a table if it doesn't exist."""
        cols = {row[1] for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in cols:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            self.conn.commit()
            return True
        return False

    def insert_alpha(
        self,
        alpha,
        generation=0,
        parent_alpha=None,
        category=None,
        field_set=None,
        operator_set=None,
        predicted_sharpe=None,
        predicted_fitness=None,
        predicted_turnover=None,
        score=None,
        settings=None,
    ):
        if self.alpha_exists(alpha):
            return False
        self.conn.execute(
            """
            INSERT INTO alphas (
                alpha, generation, parent_alpha, category,
                field_set, operator_set, status,
                predicted_sharpe, predicted_fitness,
                predicted_turnover, score, settings
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                alpha,
                generation,
                parent_alpha,
                category,
                ",".join(sorted(field_set)) if field_set else None,
                ",".join(sorted(operator_set)) if operator_set else None,
                "NEW",
                predicted_sharpe,
                predicted_fitness,
                predicted_turnover,
                score,
                json.dumps(settings, sort_keys=True) if settings else None,
            ],
        )
        self.conn.commit()
        return True

    def alpha_exists(self, alpha):
        cur = self.conn.execute(
            "SELECT 1 FROM alphas WHERE alpha = ? LIMIT 1", [alpha]
        )
        return cur.fetchone() is not None

    def update_metrics(
        self,
        alpha_text=None,
        sim_id=None,
        alpha_id=None,
        status=None,
        metrics: dict = None,
        **kwargs
    ):
        """Update metrics for an alpha, automatically adding columns as needed."""
        # Support both old individual params and new metrics dict
        if metrics is None:
            metrics = {}
            for key in ["sharpe", "fitness", "turnover", "returns", "margin"]:
                if key in kwargs:
                    metrics[key] = kwargs[key]
        
        # Add columns dynamically
        for col_name, col_value in metrics.items():
            if col_name and col_value is not None:
                self.add_column_if_missing("alphas", col_name, "REAL")
        
        assignments = []
        values = []
        if status is not None:
            assignments.append("status = ?")
            values.append(status)
        if sim_id is not None:
            assignments.append("sim_id = ?")
            values.append(sim_id)
        if alpha_id is not None:
            assignments.append("alpha_id = ?")
            values.append(alpha_id)
        
        # Add all metric columns
        for col_name, col_value in metrics.items():
            if col_value is not None:
                assignments.append(f"{col_name} = ?")
                values.append(col_value)
        
        # Compute score from sharpe and fitness if available
        if "sharpe" in metrics and "fitness" in metrics:
            computed_turnover = metrics.get("turnover", 0.0) or 0.0
            assignments.append("score = ?")
            values.append(score_metrics(metrics["sharpe"], metrics["fitness"], computed_turnover))
        
        if not assignments:
            return False
        values.append(alpha_text)
        query = f"UPDATE alphas SET {', '.join(assignments)} WHERE alpha = ?"
        self.conn.execute(query, values)
        self.conn.commit()
        
        # Also update simulation record
        if sim_id is not None:
            self.update_simulation(sim_id, status=status, alpha_id=alpha_id, metrics=metrics)
        return True

    def update_settings(self, alpha_text, settings):
        self.conn.execute(
            "UPDATE alphas SET settings = ? WHERE alpha = ?",
            [json.dumps(settings, sort_keys=True), alpha_text],
        )
        self.conn.commit()
        return True

    def insert_simulation(self, alpha_text, settings, sim_id, status="RUNNING", alpha_id=None):
        self.conn.execute(
            "INSERT OR IGNORE INTO simulations (alpha, settings, sim_id, alpha_id, status) VALUES (?, ?, ?, ?, ?)",
            [
                alpha_text,
                json.dumps(settings, sort_keys=True) if settings else None,
                sim_id,
                alpha_id,
                status,
            ],
        )
        self.conn.commit()
        return True

    def update_simulation(self, sim_id, status=None, alpha_id=None, metrics: dict = None, **kwargs):
        """Update simulation metrics, automatically adding columns as needed."""
        if metrics is None:
            metrics = {}
            for key in ["sharpe", "fitness", "turnover", "returns", "margin"]:
                if key in kwargs:
                    metrics[key] = kwargs[key]
        
        # Add columns dynamically
        for col_name, col_value in metrics.items():
            if col_name and col_value is not None:
                self.add_column_if_missing("simulations", col_name, "REAL")
        
        assignments = []
        values = []
        if status is not None:
            assignments.append("status = ?")
            values.append(status)
        if alpha_id is not None:
            assignments.append("alpha_id = ?")
            values.append(alpha_id)
        
        # Add all metric columns
        for col_name, col_value in metrics.items():
            if col_value is not None:
                assignments.append(f"{col_name} = ?")
                values.append(col_value)
        
        if not assignments:
            return False
        values.append(sim_id)
        query = f"UPDATE simulations SET {', '.join(assignments)} WHERE sim_id = ?"
        self.conn.execute(query, values)
        self.conn.commit()
        return True

    def get_pending_simulations(self):
        cur = self.conn.execute(
            "SELECT alpha, sim_id, alpha_id, status FROM simulations WHERE status IN ('NEW', 'RUNNING') AND sim_id IS NOT NULL"
        )
        return [dict(row) for row in cur.fetchall()]

    def get_simulation_budget_usage(self):
        df = pd.read_sql_query("SELECT * FROM simulations", self.conn)
        total_used = int(df["sim_id"].notna().sum()) if not df.empty else 0
        return {
            "total_used": total_used,
            "completed": int((df["status"] == "COMPLETED").sum()) if not df.empty else 0,
            "running": int((df["status"] == "RUNNING").sum()) if not df.empty else 0,
            "pending": int((df["status"] == "NEW").sum()) if not df.empty else 0,
        }

    def family_summary(self):
        df = pd.read_sql_query(
            "SELECT s.*, a.category FROM simulations s LEFT JOIN alphas a ON s.alpha = a.alpha",
            self.conn,
        )
        if df.empty:
            return pd.DataFrame()
        df = df[df["sharpe"].notna()].copy()
        if df.empty:
            return pd.DataFrame()
        df["family"] = df.apply(lambda row: self._infer_family(row.get("alpha"), row.get("category")), axis=1)
        df["passed_sharpe_1"] = df["sharpe"] >= 1.0
        df["passed_sharpe_1_25"] = df["sharpe"] >= 1.25
        df["passed_fitness_1"] = df["fitness"] >= 1.05
        df["passed_turnover"] = df["turnover"] < 0.25
        df["elite_objective"] = df["passed_sharpe_1_25"] & df["passed_fitness_1"] & df["passed_turnover"]
        grouped = df.groupby("family").agg(
            tested=("alpha", "count"),
            sharpe_gt_1=("passed_sharpe_1", "sum"),
            sharpe_gt_1_25=("passed_sharpe_1_25", "sum"),
            fitness_gt_1_05=("passed_fitness_1", "sum"),
            turnover_ok=("passed_turnover", "sum"),
            elite_count=("elite_objective", "sum"),
            average_sharpe=("sharpe", "mean"),
            average_fitness=("fitness", "mean"),
            average_turnover=("turnover", "mean"),
        )
        grouped["elite_rate"] = grouped["elite_count"] / grouped["tested"].replace(0, 1)
        grouped["success_rate"] = grouped["sharpe_gt_1_25"] / grouped["tested"].replace(0, 1)
        result = grouped.sort_values(["elite_rate", "average_sharpe"], ascending=[False, False]).reset_index()
        result["category"] = result["family"]
        return result

    def settings_summary(self):
        df = pd.read_sql_query(
            "SELECT s.*, a.category FROM simulations s LEFT JOIN alphas a ON s.alpha = a.alpha",
            self.conn,
        )
        if df.empty or "settings" not in df.columns:
            return pd.DataFrame()
        df = df[df["settings"].notna()].copy()
        if df.empty:
            return pd.DataFrame()
        df["settings_parsed"] = df["settings"].apply(lambda x: json.loads(x) if pd.notna(x) else {})
        settings_df = pd.json_normalize(df["settings_parsed"])
        if settings_df.empty:
            return pd.DataFrame()
        settings_df.index = df.index
        merged = pd.concat([df, settings_df], axis=1)
        group_cols = [col for col in settings_df.columns if col in merged.columns]
        if not group_cols:
            return pd.DataFrame()
        summary = merged.groupby(group_cols).agg(
            tested=("alpha", "count"),
            average_sharpe=("sharpe", "mean"),
            average_fitness=("fitness", "mean"),
            average_turnover=("turnover", "mean"),
        ).sort_values(["average_sharpe", "tested"], ascending=[False, False]).reset_index()
        return summary

    def best_settings_by_category(self, category, limit=3):
        df = pd.read_sql_query(
            "SELECT s.*, a.category FROM simulations s LEFT JOIN alphas a ON s.alpha = a.alpha",
            self.conn,
        )
        if df.empty or "settings" not in df.columns:
            return []
        df = df[df["category"] == category].copy()
        df = df[df["settings"].notna()]
        if df.empty:
            return []
        df["settings_parsed"] = df["settings"].apply(lambda x: json.loads(x) if pd.notna(x) else {})
        settings_df = pd.json_normalize(df["settings_parsed"])
        if settings_df.empty:
            return []
        settings_df.index = df.index
        merged = pd.concat([df, settings_df], axis=1)
        group_cols = [col for col in settings_df.columns if col in merged.columns]
        summary = merged.groupby(group_cols).agg(
            tested=("alpha", "count"),
            average_sharpe=("sharpe", "mean"),
            average_fitness=("fitness", "mean"),
            average_turnover=("turnover", "mean"),
        ).sort_values(["average_sharpe", "tested"], ascending=[False, False]).reset_index()
        results = []
        for _, row in summary.head(limit).iterrows():
            settings = {col: row[col] for col in group_cols}
            results.append(settings)
        return results

    def update_status_by_simulation(self, sim_id, status):
        self.conn.execute(
            "UPDATE simulations SET status = ? WHERE sim_id = ?",
            [status, sim_id],
        )
        self.conn.execute(
            "UPDATE alphas SET status = ? WHERE sim_id = ?",
            [status, sim_id],
        )
        self.conn.commit()

    def get_candidates(self, limit=100, min_score=None):
        df = pd.read_sql_query("SELECT * FROM alphas WHERE status = 'NEW'", self.conn)
        if df.empty:
            return []
        for col in ["predicted_sharpe", "predicted_fitness", "predicted_turnover", "score"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["selection_score"] = df.apply(self._candidate_selection_score, axis=1)
        if min_score is not None:
            df = df[df["selection_score"] >= min_score]
        if df.empty:
            return []
        df["score"] = df["selection_score"]
        df = df.sort_values(["selection_score", "predicted_sharpe", "predicted_fitness"], ascending=[False, False, False])
        return df.head(limit).to_dict(orient="records")

    def get_top_scored(self, limit=10):
        df = pd.read_sql_query("SELECT * FROM alphas WHERE sharpe IS NOT NULL", self.conn)
        if df.empty:
            return []
        for col in ["sharpe", "fitness", "turnover"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["realized_score"] = df.apply(
            lambda row: score_metrics(row["sharpe"], row["fitness"], row["turnover"]),
            axis=1,
        )
        df = df.sort_values(["realized_score", "sharpe", "fitness"], ascending=[False, False, False])
        return df.head(limit).to_dict(orient="records")

    def operator_performance(self):
        df = self.to_dataframe()
        df = df[df["sharpe"].notna()].copy() if not df.empty else df
        if df.empty:
            return pd.DataFrame()
        rows = []
        for _, row in df.iterrows():
            operators = self._parse_operator_set(row)
            for operator in operators:
                rows.append({**row.to_dict(), "operator": operator})
        if not rows:
            return pd.DataFrame()
        perf = pd.DataFrame(rows)
        perf["elite_objective"] = (perf["sharpe"] > 1.25) & (perf["fitness"] > 1.05) & (perf["turnover"] < 0.25)
        return perf.groupby("operator").agg(
            tested=("alpha", "count"),
            average_sharpe=("sharpe", "mean"),
            average_fitness=("fitness", "mean"),
            average_turnover=("turnover", "mean"),
            elite_count=("elite_objective", "sum"),
        ).sort_values(["average_sharpe", "tested"], ascending=[False, False]).reset_index()

    def field_performance(self):
        df = self.to_dataframe()
        df = df[df["sharpe"].notna()].copy() if not df.empty else df
        if df.empty:
            return pd.DataFrame()
        rows = []
        for _, row in df.iterrows():
            fields = self._parse_field_set(row)
            for field in fields:
                rows.append({**row.to_dict(), "field": field})
        if not rows:
            return pd.DataFrame()
        perf = pd.DataFrame(rows)
        perf["elite_objective"] = (perf["sharpe"] > 1.25) & (perf["fitness"] > 1.05) & (perf["turnover"] < 0.25)
        return perf.groupby("field").agg(
            tested=("alpha", "count"),
            average_sharpe=("sharpe", "mean"),
            average_fitness=("fitness", "mean"),
            average_turnover=("turnover", "mean"),
            elite_count=("elite_objective", "sum"),
        ).sort_values(["average_sharpe", "tested"], ascending=[False, False]).reset_index()

    def get_successful_alphas(self, min_sharpe=1.0, min_fitness=0.8, limit=50):
        cur = self.conn.execute(
            "SELECT * FROM alphas WHERE sharpe >= ? AND fitness >= ? ORDER BY sharpe DESC, fitness DESC LIMIT ?",
            [min_sharpe, min_fitness, limit],
        )
        return [dict(row) for row in cur.fetchall()]

    def load_legacy_results(self, path: Path = None):
        source = Path(path) if path else LEGACY_RESULTS_CSV
        if not source.exists():
            return 0
        data = pd.read_csv(source, dtype=str).fillna("")
        inserted = 0
        for _, row in data.iterrows():
            alpha = str(row.get("alpha", "")).strip()
            if not alpha:
                continue
            if self.alpha_exists(alpha):
                continue
            self.conn.execute(
                "INSERT OR IGNORE INTO alphas (alpha, status, sim_id, alpha_id, sharpe, fitness, turnover, returns, margin) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    alpha,
                    row.get("status", ""),
                    row.get("sim_id", ""),
                    row.get("alpha_id", ""),
                    self._to_float(row.get("sharpe", None)),
                    self._to_float(row.get("fitness", None)),
                    self._to_float(row.get("turnover", None)),
                    self._to_float(row.get("returns", None)),
                    self._to_float(row.get("margin", None)),
                ],
            )
            inserted += 1
        self.conn.commit()
        return inserted

    def to_dataframe(self):
        return pd.read_sql_query("SELECT * FROM alphas", self.conn)

    @staticmethod
    def _to_float(value):
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _infer_family(alpha, category=None):
        lowered = str(alpha or "").lower()
        if "trade_when" in lowered and any(token in lowered for token in ["pcr", "implied_volatility", "historical_volatility", "open_interest", "call_", "put_"]):
            return "options_regime_trade_when"
        if "trade_when" in lowered:
            return "trade_when_other"
        if "pcr" in lowered:
            return "pcr"
        if "implied_volatility" in lowered and "historical_volatility" in lowered:
            return "iv_hv_spread"
        if any(token in lowered for token in ["implied_volatility", "open_interest", "call_", "put_"]):
            return "options_simple"
        if any(token in lowered for token in ["anl4", "ebit", "fcf", "netprofit", "cfo", "netdebt", "ebitda", "eps", "cashflow", "sales", "net_income"]):
            if any(token in lowered for token in ["-", "+", "*", "/"]):
                return "fundamental_spread_composite"
            return "fundamental_single_ts"
        return category or "unknown"

    @staticmethod
    def _parse_field_set(row):
        field_set = row.get("field_set")
        if isinstance(field_set, str) and field_set.strip():
            return [item.strip() for item in field_set.split(",") if item.strip()]
        try:
            from project.worldquant.parser import AlphaExpression
            return sorted(AlphaExpression(row.get("alpha", "")).field_set())
        except Exception:
            return []

    @staticmethod
    def _parse_operator_set(row):
        operator_set = row.get("operator_set")
        if isinstance(operator_set, str) and operator_set.strip():
            return [item.strip() for item in operator_set.split(",") if item.strip()]
        try:
            from project.worldquant.parser import AlphaExpression
            return sorted(AlphaExpression(row.get("alpha", "")).operator_set())
        except Exception:
            return []

    @staticmethod
    def _candidate_selection_score(row):
        score = score_metrics(
            row.get("predicted_sharpe"),
            row.get("predicted_fitness"),
            row.get("predicted_turnover"),
        )
        if score is None:
            score = row.get("score") or 0.0
        family = AlphaDatabase._infer_family(row.get("alpha"), row.get("category"))
        if family in {"options_regime_trade_when", "iv_hv_spread", "pcr", "options_simple"}:
            score += 0.015
        alpha = str(row.get("alpha") or "")
        score += (sum(ord(ch) for ch in alpha) % 997) / 1000000.0
        return score

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    db = AlphaDatabase()
    added = db.load_legacy_results()
    print(f"Loaded legacy results: {added}")
