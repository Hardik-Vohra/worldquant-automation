import re
import random
from typing import List
from project.worldquant.parser import AlphaExpression
from project.data.fields import FieldCatalog
from project.engine.learning_engine import LearningEngine

WINDOWS = [20, 63, 126, 252]
PCR_THRESHOLDS = [0.8, 1.0, 1.2]
REGIME_TEMPLATES = [
    "trade_when(pcr_oi_270>1,{signal},-1)",
    "trade_when(pcr_oi_270<1,{signal},-1)",
    "trade_when(ts_rank(pcr_oi_270,252)>0.8,{signal},-1)",
    "trade_when(ts_rank(pcr_oi_270,252)<0.2,{signal},-1)",
]
OPERATOR_REPLACE = {
    "ts_delta": ["ts_rank", "ts_zscore"],
    "ts_rank": ["ts_delta", "ts_zscore"],
    "ts_zscore": ["ts_rank", "ts_delta"],
}


class MutationEngine:
    def __init__(self, catalog: FieldCatalog, learning: LearningEngine):
        self.catalog = catalog
        self.learning = learning

    def mutate_alpha(self, alpha: str, max_mutations: int = 12) -> List[str]:
        try:
            expr = AlphaExpression(alpha)
        except Exception:
            return []
        mutations = {alpha}
        mutations.update(self._mutate_windows(alpha))
        mutations.update(self._mutate_operator_patterns(alpha))
        mutations.update(self._mutate_field_replacements(alpha, expr))
        mutations.update(self._mutate_regime(alpha))
        mutations.update(self._mutate_pcr_thresholds(alpha))
        mutations.update(self._mutate_option_spreads(alpha))
        mutations.update(self._mutate_flip_sign(alpha))
        result = [item for item in mutations if item != alpha]
        random.shuffle(result)
        return result[:max_mutations]

    def _mutate_windows(self, alpha: str):
        results = set()
        for window in WINDOWS:
            mutated = re.sub(r",\s*(20|63|126|252)\)", f",{window})", alpha)
            if mutated != alpha:
                results.add(mutated)
        return results

    def _mutate_operator_patterns(self, alpha: str):
        results = set()
        for source, replacements in OPERATOR_REPLACE.items():
            if source in alpha:
                for replacement in replacements:
                    results.add(alpha.replace(source, replacement))
        return results

    def _mutate_field_replacements(self, alpha: str, expr: AlphaExpression):
        results = set()
        fields = expr.field_set()
        for field in fields:
            info = self.catalog.get_field_info(field)
            if not info:
                continue
            category = info.get("field_category")
            if not category:
                continue
            alternatives = self.catalog.get_fields_by_category(category, min_alpha_count=20, limit=20)
            for alt in alternatives:
                if alt != field:
                    results.add(alpha.replace(field, alt))
        return results

    def _mutate_regime(self, alpha: str):
        results = set()
        if "trade_when(" not in alpha:
            pcr_fields = self.catalog.get_pcr_fields(limit=2) or ["pcr_oi_270"]
            iv_fields = self.catalog.get_implied_volatility_fields(limit=3) or [
                "implied_volatility_mean_30",
                "implied_volatility_mean_90",
                "implied_volatility_mean_270",
            ]
            hv_fields = self.catalog.get_historical_volatility_fields(limit=2) or [
                "historical_volatility_30",
                "historical_volatility_90",
            ]
            oi_fields = self.catalog.get_open_interest_fields(limit=2) or [
                "call_open_interest_270",
                "put_open_interest_270",
            ]
            pcr = pcr_fields[0]
            iv_short = iv_fields[0]
            iv_mid = iv_fields[min(1, len(iv_fields) - 1)]
            iv_long = iv_fields[-1]
            hv_mid = hv_fields[min(1, len(hv_fields) - 1)]
            call_oi = next((field for field in oi_fields if "call" in field.lower()), oi_fields[0])
            put_oi = next((field for field in oi_fields if "put" in field.lower()), oi_fields[-1])
            templates = [
                f"trade_when({pcr}>1,{{signal}},-1)",
                f"trade_when({pcr}<1,{{signal}},-1)",
                f"trade_when(ts_rank({pcr},252)>0.8,{{signal}},-1)",
                f"trade_when(ts_rank({pcr},252)<0.2,{{signal}},-1)",
            ]
            signals = [
                "ts_delta(anl4_ebit_value,126)",
                "ts_zscore(anl4_fcf_flag,126)",
                f"rank({pcr})",
                f"({iv_short}-{iv_long})",
                f"({iv_mid}-{hv_mid})",
                f"({call_oi}-{put_oi})",
            ]
            for template in templates:
                for signal in signals:
                    results.add(template.format(signal=signal))
        return results

    def _mutate_pcr_thresholds(self, alpha: str):
        results = set()
        if "pcr" not in alpha:
            return results
        for threshold in PCR_THRESHOLDS:
            results.add(re.sub(r"pcr_oi_270\s*>\s*[0-9.]+", f"pcr_oi_270>{threshold}", alpha))
            results.add(re.sub(r"pcr_oi_270\s*<\s*[0-9.]+", f"pcr_oi_270<{threshold}", alpha))
        return {item for item in results if item != alpha}

    def _mutate_option_spreads(self, alpha: str):
        results = set()
        spread_pairs = [
            ("implied_volatility_mean_30", "implied_volatility_mean_270"),
            ("implied_volatility_mean_90", "historical_volatility_90"),
            ("historical_volatility_30", "historical_volatility_90"),
            ("call_open_interest_270", "put_open_interest_270"),
        ]
        if not any(left in alpha or right in alpha for left, right in spread_pairs):
            return results
        for left, right in spread_pairs:
            results.add(f"rank({left}-{right})")
            results.add(f"trade_when(pcr_oi_270<1,({left}-{right}),-1)")
            results.add(f"trade_when(ts_rank(pcr_oi_270,252)>0.8,({left}-{right}),-1)")
        return results

    def _mutate_flip_sign(self, alpha: str):
        results = set()
        if alpha.startswith("rank(") and not alpha.startswith("rank(-"):
            inner = alpha[5:-1]
            results.add(f"rank(-{inner})")
            results.add(f"-rank({inner})")
        return results


if __name__ == "__main__":
    from project.engine.data_manager import AlphaDatabase

    db = AlphaDatabase()
    from project.engine.learning_engine import LearningEngine
    from project.data.fields import FieldCatalog

    catalog = FieldCatalog()
    learner = LearningEngine(db)
    engine = MutationEngine(catalog, learner)
    print(engine.mutate_alpha("rank(ts_delta(anl4_ebit_value,126))"))
