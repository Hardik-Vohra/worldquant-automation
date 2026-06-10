from project.worldquant.submit import WorldQuantClient
from project.engine.data_manager import AlphaDatabase
from project.config import POLL_INTERVAL_SECONDS
import time


class WorldQuantPoller:
    def __init__(self, db: AlphaDatabase, client: WorldQuantClient = None):
        self.db = db
        self.client = client or WorldQuantClient()

    def poll_pending(self, max_seconds: int = 600):
        pending = self.db.get_pending_simulations()
        if not pending:
            return []

        completed = []
        deadline = time.time() + max_seconds
        while time.time() < deadline and pending:
            for row in pending:
                sim_id = row["sim_id"]
                try:
                    sim = self.client.fetch_simulation(sim_id)
                except Exception:
                    continue
                status = sim.get("status")
                if status != "COMPLETE":
                    continue
                alpha_id = sim.get("alpha")
                if not alpha_id:
                    self.db.update_metrics(
                        alpha_text=row["alpha"],
                        sim_id=sim_id,
                        status="FAILED",
                    )
                    continue
                alpha_data = self.client.fetch_alpha(alpha_id)
                is_data = alpha_data.get("is", {})
                
                # Extract all metrics from API response dynamically
                metrics = {}
                for key, value in is_data.items():
                    float_val = self._to_float(value)
                    if float_val is not None:
                        metrics[key] = float_val
                
                self.db.update_metrics(
                    alpha_text=row["alpha"],
                    sim_id=sim_id,
                    alpha_id=alpha_id,
                    status=alpha_data.get("status", "COMPLETE"),
                    metrics=metrics,
                )
                completed.append(row)
            if completed:
                break
            time.sleep(POLL_INTERVAL_SECONDS)
            pending = self.db.get_pending_simulations()
        return completed

    @staticmethod
    def _to_float(value):
        try:
            return float(value)
        except Exception:
            return None
