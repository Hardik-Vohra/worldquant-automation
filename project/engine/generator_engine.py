import itertools
import random
from collections import Counter
from project.data.fields import FieldCatalog
from project.engine.learning_engine import LearningEngine
from project.engine.scoring_engine import score_metrics
from project.worldquant.parser import AlphaExpression
from project.engine.data_manager import AlphaDatabase
from typing import List, Dict
import sys
sys.path.insert(0, '/'.join(__file__.split('/')[:-3]))
from operators import WINDOWS


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
        self.windows = WINDOWS
        self.max_family_share = 0.30
        self.max_primary_operator_share = 0.25 # Allows diverse inner logics
        self.max_field_share = 0.25

    def generate_candidates(self, limit=200) -> List[Dict]:
        self.entropy_stats = self.learning.calculate_entropy()
        self.cat_stats = self.learning.category_stats()
        self.op_stats = self.learning.operator_stats()
        self.field_stats = self.learning.field_stats()
        
        candidates = []
        candidates.extend(self._generate_fundamental())
        candidates.extend(self._generate_options())
        candidates.extend(self._generate_volatility())
        candidates.extend(self._generate_hybrid())
        candidates.extend(self._generate_regime())

        parents = self.db.get_successful_alphas(limit=20)
        for parent in parents:
            candidates.extend(self._generate_mutations(parent["alpha"]))

        unique = {}
        seen_canonicals = set()
        seen_core_fields = set() 
        
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
            fields = tuple(sorted(expr.field_set()))
            
            if len(fields) <= 2:
                if fields in seen_core_fields:
                    continue
                seen_core_fields.add(fields)

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
        # NEW: Ignore 'rank' and 'zscore' to find the actual core inner mathematical driver
        for op in ["ts_zscore", "ts_delta", "trade_when", "ts_mean", "ts_std_dev"]:
            if op in operators:
                return op
        for op in operators:
            if op not in {"rank", "zscore", "group_neutralize", "+", "-", "*", "/", "<", ">"}:
                return op
        return operators[0] if operators else "none"

    def _ranking_key(self, candidate: Dict):
        alpha = candidate.get("alpha", "")
        score = candidate.get("predicted_score") or 0.0
        confidence = candidate.get("confidence") or 0.0
        family = candidate.get("family") or candidate.get("category") or ""
        
        penalty = 0.0
        if getattr(self, "entropy_stats", None):
            if self.entropy_stats.get("family_entropy", 1.5) < 1.4:
                if family in self.cat_stats.index:
                    total = self.cat_stats["count"].sum()
                    if total > 0:
                        penalty += (self.cat_stats.loc[family, "count"] / total) * 0.15
                        
            if self.entropy_stats.get("operator_entropy", 2.5) < 2.5:
                op = self._primary_operator(candidate)
                if op in self.op_stats.index:
                    total = self.op_stats["count"].sum()
                    if total > 0:
                        penalty += (self.op_stats.loc[op, "count"] / total) * 0.10
                        
            if self.entropy_stats.get("field_entropy", 4.5) < 4.0:
                fields = candidate.get("field_set", [])
                max_field_penalty = 0.0
                total = self.field_stats["count"].sum()
                if total > 0:
                    for f in fields:
                        if f in self.field_stats.index:
                            f_penalty = (self.field_stats.loc[f, "count"] / total) * 0.15
                            max_field_penalty = max(max_field_penalty, f_penalty)
                penalty += max_field_penalty

        family_bonus = 0.03 if family in {"options_regime_trade_when", "iv_hv_spread", "pcr", "options_simple"} else 0.0
        novelty = (sum(ord(ch) for ch in alpha) % 997) / 100000.0

        # Capped pairing exploration bonus (max 0.04, cannot dominate scoring)
        pairing_bonus = 0.0
        MAX_PAIRING_BONUS = 0.04
        if getattr(self, "_pairing_scores", None):
            fields = candidate.get("field_set", [])
            for f in fields:
                if f in self._pairing_scores:
                    pairing_bonus = max(pairing_bonus, self._pairing_scores[f])
        pairing_bonus = min(MAX_PAIRING_BONUS, pairing_bonus)

        return (score + family_bonus + pairing_bonus - penalty, confidence, -len(candidate.get("field_set") or []), novelty)

    def _apply_diversity_controls(self, ranked: List[Dict], limit: int) -> List[Dict]:
        if not ranked:
            return []
        # Replaced hard bans with weighted diversity pressure in _ranking_key.
        # Just interleave the top ranked candidates up to the limit.
        return self._interleave_by_family(ranked[:limit])

    def _interleave_by_family(self, candidates: List[Dict]) -> List[Dict]:
        grouped = {}
        for candidate in candidates:
            grouped.setdefault(candidate.get("family") or candidate.get("category") or "unknown", []).append(candidate)
        ordered = []
        while grouped:
            family_order = sorted(grouped, key=lambda f: grouped[f][0].get("predicted_score") or 0.0, reverse=True)
            for family in family_order:
                ordered.append(grouped[family].pop(0))
                if not grouped[family]: del grouped[family]
            if len(ordered) >= len(candidates): break
        return ordered

    def _build_reason(self, expression: AlphaExpression, predicted: dict, category: str = None) -> str:
        reasons = []
        if category: reasons.append(f"Category={category}")
        if predicted["predicted_sharpe"] >= 1.2: reasons.append("High predicted Sharpe ceiling")
        if not reasons: reasons.append("Predicted strong candidate")
        return "; ".join(reasons)

    def _generate_fundamental(self) -> List[Dict]:
        proven_fields = self.learning.top_fields(limit=4)
        explore_fields = self.catalog.sample_exploration_fields("Fundamental", min_coverage=0.80, sample_size=6)
        fields = list(set(proven_fields + explore_fields))
        
        candidates = []
        for field in fields:
            for w in self.windows:
                # Safely ranked to pass Web GUI constraints
                candidates.append(self._build_candidate(f"rank(ts_zscore({field}, {w}))", category="Fundamental"))
                candidates.append(self._build_candidate(f"rank(ts_delta({field}, {w}))", category="Fundamental"))
        return [c for c in candidates if c]

    def _generate_options(self) -> List[Dict]:
        proven_pcr = self.catalog.get_pcr_fields(limit=2)
        explore_pcr = self.catalog.sample_exploration_fields("Options", min_coverage=0.60, sample_size=4)
        pcr_fields = list(set(proven_pcr + explore_pcr))
        
        iv_fields = self.catalog.get_implied_volatility_fields(limit=4) or ["implied_volatility_mean_90"]
        hv_fields = self.catalog.get_historical_volatility_fields(limit=4) or ["historical_volatility_90"]
        
        candidates = []
        if len(iv_fields) >= 2:
            candidates.append(self._build_candidate(f"rank(({iv_fields[0]}-{iv_fields[1]})/{iv_fields[1]})", category="Options"))
            candidates.append(self._build_candidate(f"rank(ts_zscore(({iv_fields[0]}-{iv_fields[1]})/{iv_fields[1]}, 63))", category="Options"))

        if iv_fields and hv_fields:
            vrp = f"({iv_fields[0]}-{hv_fields[0]})"
            candidates.append(self._build_candidate(f"rank(ts_zscore({vrp}, 63))", category="Options"))
            
        for pcr in pcr_fields:
            for w in [20, 63, 126]:
                candidates.append(self._build_candidate(f"rank(ts_zscore({pcr}, {w}))", category="Options"))
                candidates.append(self._build_candidate(f"rank(trade_when({pcr}>1.2, -ts_zscore(returns,{w}), ts_zscore(returns,{w})))", category="Options"))
                
        return [c for c in candidates if c]

    def _generate_volatility(self) -> List[Dict]:
        fields = self.catalog.sample_exploration_fields("Volatility", min_coverage=0.70, sample_size=6)
        candidates = []
        for field in fields:
            for w in [63, 126, 252]:
                candidates.append(self._build_candidate(f"rank(ts_zscore({field},{w}))", category="Volatility"))
                candidates.append(self._build_candidate(f"rank(ts_delta({field},{w})/{field})", category="Volatility"))
        return [c for c in candidates if c]

    def _generate_hybrid(self) -> List[Dict]:
        """Generate hybrid alphas by injecting high-value signal fields into
        proven elite frameworks (trade_when, IV, PCR, HV filters).

        Uses pairing-level learning to prioritise high-quality, high-coverage,
        under-explored (field, filter) combinations.
        """
        # Prioritised signal fields — ordered by strategic value
        priority_fields = [
            "anl4_af_eps_value",
            "anl4_afv4_eps_high",
            "anl4_afv4_eps_low",
            "actual_eps_value_quarterly",
            "actual_sales_value_quarterly",
            "adj_net_income_avg",
            "anl4_adjusted_netincome_ft",
            "anl4_cfo_number",
            "anl4_fcf_flag",
            "anl4_netprofit_flag",
            "actual_cashflow_per_share_value_quarterly",
            "anl4_basicdetailrec_ratingvalue",
            "anl4_eaz2lrec_ratingvalue",
            "anl4_cff_flag",
            "anl4_afv4_div_std",
            "anl4_afv4_div_low",
            "anl4_afv4_div_median",
        ]

        # Ask learning engine for the best unexplored pairings
        top_pairings = self.learning.unexplored_pairings(priority_fields, limit=30)

        # Build a lookup of pairing_score by field for _ranking_key bonus
        self._pairing_scores = {}
        for p in top_pairings:
            existing = self._pairing_scores.get(p["field"], 0.0)
            self._pairing_scores[p["field"]] = max(existing, p["pairing_score"])

        # Retrieve available filter fields from the catalog
        iv_fields = self.catalog.get_implied_volatility_fields(limit=3) or ["implied_volatility_mean_90"]
        pcr_fields = self.catalog.get_pcr_fields(limit=2) or ["pcr_oi_270"]
        hv_fields = self.catalog.get_historical_volatility_fields(limit=2) or ["historical_volatility_63"]

        candidates = []
        seen_pairings = set()

        for pairing in top_pairings:
            field = pairing["field"]
            filt = pairing["filter"]
            pair_key = (field, filt)
            if pair_key in seen_pairings:
                continue
            seen_pairings.add(pair_key)

            for w in [63, 126, 252]:
                if filt == "trade_when":
                    # Inject into IV regime framework
                    for iv in iv_fields[:2]:
                        candidates.append(self._build_candidate(
                            f"rank(trade_when(ts_zscore({iv},63)<0, ts_zscore({field},{w}), 0))",
                            category="Hybrid",
                        ))
                    # Inject into PCR regime framework
                    for pcr in pcr_fields[:1]:
                        candidates.append(self._build_candidate(
                            f"rank(trade_when({pcr}>1.2, -ts_zscore({field},{w}), ts_zscore({field},{w})))",
                            category="Hybrid",
                        ))
                elif filt == "implied_volatility":
                    for iv in iv_fields[:2]:
                        candidates.append(self._build_candidate(
                            f"rank(ts_zscore({field},{w}) * (1/ts_rank({iv},{w})))",
                            category="Hybrid",
                        ))
                        candidates.append(self._build_candidate(
                            f"rank(trade_when(ts_zscore({iv},63)<0, ts_zscore({field},{w}), 0))",
                            category="Hybrid",
                        ))
                elif filt == "pcr":
                    for pcr in pcr_fields[:1]:
                        candidates.append(self._build_candidate(
                            f"rank(trade_when(ts_zscore({pcr},63)>1.5, -ts_zscore({field},{w}), ts_zscore({field},{w})))",
                            category="Hybrid",
                        ))
                        candidates.append(self._build_candidate(
                            f"rank(ts_zscore({field},{w}) * ts_zscore({pcr},{w}))",
                            category="Hybrid",
                        ))
                elif filt == "historical_volatility":
                    for hv in hv_fields[:2]:
                        candidates.append(self._build_candidate(
                            f"rank(ts_zscore({field},{w}) * (1/ts_rank({hv},{w})))",
                            category="Hybrid",
                        ))
                        candidates.append(self._build_candidate(
                            f"rank(trade_when(ts_delta({hv},20)<0, ts_zscore({field},{w}), 0))",
                            category="Hybrid",
                        ))

        # Preserve the original simple hybrid generation as fallback
        fund_fields = self.catalog.sample_exploration_fields("Fundamental", min_coverage=0.85, sample_size=3)
        option_fields = self.catalog.get_implied_volatility_fields(limit=3)
        for f, o in itertools.product(fund_fields, option_fields):
            for w in [63, 252]:
                candidates.append(self._build_candidate(f"rank(ts_zscore({f},{w}) * (1/ts_rank({o},{w})))", category="Hybrid"))
                candidates.append(self._build_candidate(f"rank(trade_when(ts_zscore({o},63)<0, ts_zscore({f},{w}), 0))", category="Hybrid"))

        return [c for c in candidates if c]

    def _generate_regime(self) -> List[Dict]:
        candidates = []
        pcr = "pcr_oi_270"
        iv_mid = "implied_volatility_mean_90"
        conditions = [f"ts_zscore({pcr},63)>1.5", f"ts_delta({iv_mid},20)>0"]
        signals = ["ts_zscore(returns, 20)", f"ts_zscore({pcr}, 20)"]
        
        for cond in conditions:
            for signal in signals:
                candidates.append(self._build_candidate(f"rank(trade_when({cond}, -{signal}, {signal}))", category="Regime"))
        return [c for c in candidates if c]

    def _generate_mutations(self, parent_alpha: str) -> List[Dict]:
        from project.engine.mutation_engine import MutationEngine
        mutator = MutationEngine(self.catalog, self.learning)
        mutants = []
        for candidate in mutator.mutate_alpha(parent_alpha, max_mutations=10):
            built = self._build_candidate(candidate, generation=1, parent_alpha=parent_alpha, category="Mutation")
            if built: mutants.append(built)
        return mutants