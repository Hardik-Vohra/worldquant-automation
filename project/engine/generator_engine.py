import itertools
from collections import Counter
from project.data.fields import FieldCatalog
from project.engine.learning_engine import LearningEngine
from project.engine.scoring_engine import score_metrics
from project.worldquant.parser import AlphaExpression
from project.engine.data_manager import AlphaDatabase
from typing import List, Dict
import sys
sys.path.insert(0, '/'.join(__file__.split('/')[:-3]))  # Add root to path
from operators import (
    TS_OPERATORS, ARITHMETIC_OPERATORS, CROSS_SECTIONAL_OPERATORS, WINDOWS
)


class GeneratorEngine:
    def __init__(
        self,
        catalog: FieldCatalog,
        learning: LearningEngine,
        db: AlphaDatabase,
    ):
        self.catalog = catalog
        self.learning = learning
        self.db = db
        self.windows = WINDOWS  # [20, 63, 126, 252] from operators
        self.max_family_share = 0.30
        self.max_primary_operator_share = 0.35
        self.max_field_share = 0.25

    def generate_candidates(self, limit=200) -> List[Dict]:
        candidates = []
        candidates.extend(self._generate_fundamental())
        candidates.extend(self._generate_options())
        candidates.extend(self._generate_volatility())
        candidates.extend(self._generate_hybrid())
        candidates.extend(self._generate_regime())

        # If there are strong winners, propose mutations around them.
        parents = self.db.get_successful_alphas(limit=20)
        for parent in parents:
            candidates.extend(self._generate_mutations(parent["alpha"]))

        unique = {}
        seen_canonicals = set()
        for candidate in candidates:
            if not candidate:
                continue
            alpha = candidate["alpha"]
            if self.db.alpha_exists(alpha):
                continue
            signature = candidate.get("signature")
            if signature in seen_canonicals:
                continue
            expr = AlphaExpression(alpha)
            duplicate = False
            for other in unique.values():
                if other.get("category") != candidate.get("category"):
                    continue
                other_expr = AlphaExpression(other["alpha"])
                if expr.signature() == other_expr.signature():
                    duplicate = True
                    break
                if expr.structure_signature() == other_expr.structure_signature():
                    fields_a = expr.field_set()
                    fields_b = other_expr.field_set()
                    if fields_a and fields_b:
                        overlap = len(fields_a & fields_b) / len(fields_a | fields_b)
                        if overlap >= 0.8:
                            duplicate = True
                            break
            if duplicate:
                continue
            seen_canonicals.add(signature)
            unique[alpha] = candidate
        ranked = sorted(unique.values(), key=self._ranking_key, reverse=True)
        return self._apply_diversity_controls(ranked, limit)

    def _build_candidate(self, alpha_text: str, generation=0, parent_alpha=None, category=None) -> Dict:
        try:
            expression = AlphaExpression(alpha_text)
        except Exception:
            return None
        predicted = self.learning.predict_metrics(expression, category=category)
        family = self._infer_family(alpha_text, expression, category)
        score = score_metrics(
            predicted["predicted_sharpe"],
            predicted["predicted_fitness"],
            predicted["predicted_turnover"],
        ) + self._tie_break_bonus(alpha_text, expression, family)
        return {
            "alpha": alpha_text,
            "generation": generation,
            "parent_alpha": parent_alpha,
            "category": category,
            "field_set": sorted(expression.field_set()),
            "operator_set": sorted(expression.operator_set()),
            "family": family,
            "predicted_sharpe": predicted["predicted_sharpe"],
            "predicted_fitness": predicted["predicted_fitness"],
            "predicted_turnover": predicted["predicted_turnover"],
            "predicted_score": score,
            "confidence": predicted["confidence"],
            "signature": expression.signature(),
            "structure": expression.structure_signature(),
            "similarity": 0.0,
            "reason": self._build_reason(expression, predicted, category),
        }

    def _tie_break_bonus(self, alpha_text: str, expression: AlphaExpression, family: str) -> float:
        family_bonus = 0.015 if family in {"options_regime_trade_when", "iv_hv_spread", "pcr", "options_simple"} else 0.0
        operator_bonus = min(0.008, 0.002 * len(expression.operator_set()))
        field_bonus = min(0.006, 0.001 * len(expression.field_set()))
        deterministic = (sum(ord(ch) for ch in alpha_text) % 997) / 1000000.0
        return family_bonus + operator_bonus + field_bonus + deterministic

    def _infer_family(self, alpha_text: str, expression: AlphaExpression, category: str = None) -> str:
        lowered = alpha_text.lower()
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
        if category == "Volatility":
            return "volatility"
        if any(token in lowered for token in ["anl4", "ebit", "fcf", "netprofit", "cfo", "netdebt", "ebitda", "eps", "cashflow", "sales", "net_income"]):
            operators = expression.operator_set()
            if any(op in operators for op in ["-", "+", "*", "/"]):
                return "fundamental_spread_composite"
            return "fundamental_single_ts"
        return category or "unknown"

    def _primary_operator(self, candidate: Dict) -> str:
        operators = candidate.get("operator_set") or []
        for operator in operators:
            if operator not in {"rank", "+", "-", "*", "/", "<", ">"}:
                return operator
        return operators[0] if operators else "none"

    def _ranking_key(self, candidate: Dict):
        alpha = candidate.get("alpha", "")
        score = candidate.get("predicted_score") or 0.0
        confidence = candidate.get("confidence") or 0.0
        family = candidate.get("family") or candidate.get("category") or ""
        family_bonus = 0.03 if family in {"options_regime_trade_when", "iv_hv_spread", "pcr", "options_simple"} else 0.0
        novelty = (sum(ord(ch) for ch in alpha) % 997) / 100000.0
        return (score + family_bonus, confidence, -len(candidate.get("field_set") or []), novelty)

    def _apply_diversity_controls(self, ranked: List[Dict], limit: int) -> List[Dict]:
        if not ranked:
            return []
        family_cap = max(1, int(limit * self.max_family_share))
        operator_cap = max(1, int(limit * self.max_primary_operator_share))
        field_cap = max(1, int(limit * self.max_field_share))
        selected = []
        seen = set()
        family_counts = Counter()
        operator_counts = Counter()
        field_counts = Counter()

        def can_add(candidate, strict=True):
            family = candidate.get("family") or candidate.get("category") or "unknown"
            primary_operator = self._primary_operator(candidate)
            fields = candidate.get("field_set") or []
            if not strict:
                return True
            if family_counts[family] >= family_cap:
                return False
            if operator_counts[primary_operator] >= operator_cap:
                return False
            if any(field_counts[field] >= field_cap for field in fields):
                return False
            return True

        for strict in [True, False]:
            for candidate in ranked:
                alpha = candidate["alpha"]
                if alpha in seen or not can_add(candidate, strict=strict):
                    continue
                selected.append(candidate)
                seen.add(alpha)
                family_counts[candidate.get("family") or candidate.get("category") or "unknown"] += 1
                operator_counts[self._primary_operator(candidate)] += 1
                for field in candidate.get("field_set") or []:
                    field_counts[field] += 1
                if len(selected) >= limit:
                    return self._interleave_by_family(selected)
        return self._interleave_by_family(selected)

    def _interleave_by_family(self, candidates: List[Dict]) -> List[Dict]:
        grouped = {}
        for candidate in candidates:
            grouped.setdefault(candidate.get("family") or candidate.get("category") or "unknown", []).append(candidate)
        ordered = []
        while grouped:
            family_order = sorted(
                grouped,
                key=lambda family: grouped[family][0].get("predicted_score") or 0.0,
                reverse=True,
            )
            for family in family_order:
                ordered.append(grouped[family].pop(0))
                if not grouped[family]:
                    del grouped[family]
            if len(ordered) >= len(candidates):
                break
        return ordered

    def _build_reason(self, expression: AlphaExpression, predicted: dict, category: str = None) -> str:
        reasons = []
        if category:
            reasons.append(f"Category={category}")
        top_fields = set(self.learning.top_fields(limit=20))
        if expression.field_set() and top_fields.intersection(expression.field_set()):
            reasons.append("Uses historically strong field")
        top_ops = set(self.learning.top_operators(limit=20))
        if expression.operator_set() and top_ops.intersection(expression.operator_set()):
            reasons.append("Uses strong historical operator")
        if predicted["predicted_sharpe"] >= 1.2:
            reasons.append("High predicted Sharpe")
        if predicted["confidence"] >= 0.75:
            reasons.append("High confidence")
        if not reasons:
            reasons.append("Predicted strong candidate")
        return "; ".join(reasons)

    def _generate_fundamental(self) -> List[Dict]:
        fields = self.learning.top_fields(limit=8) or self.catalog.get_fields_by_category("Fundamental", min_alpha_count=50, limit=8)
        candidates = []
        # Core time-series operators
        core_ts_ops = ["ts_delta", "ts_rank", "ts_zscore", "ts_mean", "ts_std_dev", "ts_scale"]
        for field in fields:
            for w in self.windows:
                for op in core_ts_ops:
                    candidates.append(self._build_candidate(f"rank({op}({field},{w}))", category="Fundamental"))
        
        # Two-field combinations
        for f1, f2 in itertools.permutations(fields, 2):
            if f1 == f2:
                continue
            for w in self.windows:
                candidates.append(self._build_candidate(f"rank(ts_rank({f1},{w})-ts_rank({f2},{w}))", category="Fundamental"))
                candidates.append(self._build_candidate(f"rank(ts_zscore({f1},{w})-ts_zscore({f2},{w}))", category="Fundamental"))
                candidates.append(self._build_candidate(f"rank(ts_delta({f1},{w})-ts_delta({f2},{w}))", category="Fundamental"))
        
        # Three-field aggregates
        if len(fields) >= 3:
            candidates.append(self._build_candidate(
                f"rank(ts_rank({fields[0]},{self.windows[-1]})+ts_rank({fields[1]},{self.windows[-1]})-ts_rank({fields[2]},{self.windows[-1]}))",
                category="Fundamental",
            ))
        return [c for c in candidates if c]

    def _generate_options(self) -> List[Dict]:
        pcr_fields = self.catalog.get_pcr_fields(min_alpha_count=0, limit=6) or ["pcr_oi_270"]
        iv_fields = self.catalog.get_implied_volatility_fields(min_alpha_count=0, limit=8) or [
            "implied_volatility_mean_30",
            "implied_volatility_mean_90",
            "implied_volatility_mean_270",
        ]
        hv_fields = self.catalog.get_historical_volatility_fields(min_alpha_count=0, limit=6) or [
            "historical_volatility_30",
            "historical_volatility_90",
            "historical_volatility_150",
        ]
        oi_fields = self.catalog.get_open_interest_fields(min_alpha_count=0, limit=8) or [
            "call_open_interest_270",
            "put_open_interest_270",
        ]
        fields = list(dict.fromkeys(pcr_fields + iv_fields + hv_fields + oi_fields))[:24]
        pcr = pcr_fields[0]
        iv_short = iv_fields[0]
        iv_mid = iv_fields[min(1, len(iv_fields) - 1)]
        iv_long = iv_fields[-1]
        hv_short = hv_fields[0]
        hv_mid = hv_fields[min(1, len(hv_fields) - 1)]
        call_oi = next((field for field in oi_fields if "call" in field.lower()), oi_fields[0] if oi_fields else "call_open_interest_270")
        put_oi = next((field for field in oi_fields if "put" in field.lower()), oi_fields[-1] if oi_fields else "put_open_interest_270")
        candidates = []
        signals = [
            f"({iv_short}-{iv_long})",
            f"({iv_mid}-{hv_mid})",
            f"({hv_short}-{hv_mid})",
            f"({call_oi}-{put_oi})",
            f"({pcr}*({iv_mid}-{hv_mid}))",
        ]
        conditions = [
            f"{pcr}<1",
            f"{pcr}>1",
            f"ts_rank({pcr},252)>0.8",
            f"ts_rank({pcr},252)<0.2",
            f"ts_zscore({pcr},126)>0",
        ]
        # Simple rank signals
        for signal in signals:
            candidates.append(self._build_candidate(f"rank{signal}", category="Options"))
            candidates.append(self._build_candidate(f"zscore({signal})", category="Options"))
        
        # Trade-when conditions
        for cond in conditions:
            for signal in signals:
                candidates.append(self._build_candidate(f"trade_when({cond},{signal},-1)", category="Options"))
        
        # Field-based operators
        core_ts_ops = ["ts_delta", "ts_rank", "ts_zscore", "ts_mean"]
        for field in fields:
            for w in self.windows:
                for op in core_ts_ops:
                    candidates.append(self._build_candidate(f"rank({op}({field},{w}))", category="Options"))
        return [c for c in candidates if c]

    def _generate_volatility(self) -> List[Dict]:
        fields = list(dict.fromkeys(
            self.catalog.get_historical_volatility_fields(min_alpha_count=0, limit=8)
            + self.catalog.get_implied_volatility_fields(min_alpha_count=0, limit=8)
            + self.catalog.get_fields_by_category("Volatility", min_alpha_count=20, limit=8)
        ))[:16]
        candidates = []
        core_ts_ops = ["ts_rank", "ts_delta", "ts_zscore", "ts_mean", "ts_std_dev"]
        
        if fields:
            for field in fields:
                for w in self.windows:
                    for op in core_ts_ops:
                        candidates.append(self._build_candidate(f"rank({op}({field},{w}))", category="Volatility"))
        
        # Volatility spread signals
        vol_signals = [
            "(implied_volatility_mean_30-implied_volatility_mean_270)",
            "(implied_volatility_mean_90-implied_volatility_mean_270)",
            "(historical_volatility_30-historical_volatility_90)",
            "(historical_volatility_30-historical_volatility_150)",
        ]
        for sig in vol_signals:
            candidates.append(self._build_candidate(f"rank{sig}", category="Volatility"))
            candidates.append(self._build_candidate(f"zscore({sig})", category="Volatility"))
        
        return [c for c in candidates if c]

    def _generate_hybrid(self) -> List[Dict]:
        fund_fields = self.learning.top_fields(limit=6) or self.catalog.get_fields_by_category("Fundamental", min_alpha_count=50, limit=6)
        option_fields = list(dict.fromkeys(
            self.catalog.get_pcr_fields(min_alpha_count=0, limit=4)
            + self.catalog.get_implied_volatility_fields(min_alpha_count=0, limit=4)
            + self.catalog.get_historical_volatility_fields(min_alpha_count=0, limit=4)
            + self.catalog.get_open_interest_fields(min_alpha_count=0, limit=4)
        )) or self.catalog.get_fields_by_category("Options", min_alpha_count=20, limit=6)
        candidates = []
        
        hybrid_ops = ["ts_delta", "ts_zscore", "ts_rank", "ts_mean"]
        
        for f, o in itertools.product(fund_fields, option_fields):
            for w in self.windows:
                for op in hybrid_ops:
                    candidates.append(self._build_candidate(
                        f"rank({op}({f},{w})-ts_zscore({o},{w}))",
                        category="Hybrid",
                    ))
                candidates.append(self._build_candidate(
                    f"trade_when(ts_rank({o},{w})>0.6,ts_delta({f},{w}),-1)",
                    category="Hybrid",
                ))
                candidates.append(self._build_candidate(
                    f"rank(ts_zscore({f},{w})*rank({o}))",
                    category="Hybrid",
                ))
        return [c for c in candidates if c]

    def _generate_regime(self) -> List[Dict]:
        candidates = []
        pcr_fields = self.catalog.get_pcr_fields(min_alpha_count=0, limit=3) or ["pcr_oi_270"]
        iv_fields = self.catalog.get_implied_volatility_fields(min_alpha_count=0, limit=4) or ["implied_volatility_mean_30", "implied_volatility_mean_90", "implied_volatility_mean_270"]
        hv_fields = self.catalog.get_historical_volatility_fields(min_alpha_count=0, limit=3) or ["historical_volatility_30", "historical_volatility_90"]
        oi_fields = self.catalog.get_open_interest_fields(min_alpha_count=0, limit=4) or ["call_open_interest_270", "put_open_interest_270"]
        pcr = pcr_fields[0]
        iv_short = iv_fields[0]
        iv_mid = iv_fields[min(1, len(iv_fields) - 1)]
        iv_long = iv_fields[-1]
        hv_mid = hv_fields[min(1, len(hv_fields) - 1)]
        call_oi = next((field for field in oi_fields if "call" in field.lower()), oi_fields[0] if oi_fields else "call_open_interest_270")
        put_oi = next((field for field in oi_fields if "put" in field.lower()), oi_fields[-1] if oi_fields else "put_open_interest_270")
        conditions = [
            f"{pcr}<1",
            f"{pcr}>1",
            f"ts_rank({pcr},252)>0.8",
            f"ts_rank({pcr},252)<0.2",
            f"ts_zscore({iv_mid},126)>0",
        ]
        signals = [
            f"({iv_short}-{iv_long})",
            f"({iv_mid}-{hv_mid})",
            f"({call_oi}-{put_oi})",
            f"({pcr}*({iv_mid}-{hv_mid}))",
        ]
        
        # Trade-when regime shifts
        for cond in conditions:
            for signal in signals:
                candidates.append(self._build_candidate(f"trade_when({cond},{signal},-1)", category="Regime"))
        
        # Conditional normalization (zscore applied only in certain regimes)
        for cond in conditions:
            for signal in signals:
                candidates.append(self._build_candidate(f"if_else({cond},zscore({signal}),0)", category="Regime"))
        
        return [c for c in candidates if c]

    def _generate_mutations(self, parent_alpha: str) -> List[Dict]:
        from project.engine.mutation_engine import MutationEngine

        mutator = MutationEngine(self.catalog, self.learning)
        mutants = []
        for candidate in mutator.mutate_alpha(parent_alpha, max_mutations=10):
            built = self._build_candidate(candidate, generation=1, parent_alpha=parent_alpha, category="Mutation")
            if built:
                mutants.append(built)
        return mutants


if __name__ == "__main__":
    from project.engine.data_manager import AlphaDatabase

    db = AlphaDatabase()
    catalog = FieldCatalog()
    learner = LearningEngine(db)
    generator = GeneratorEngine(catalog, learner, db)
    print(len(generator.generate_candidates(limit=50)))
