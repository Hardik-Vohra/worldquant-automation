import re
import random
from typing import List
from project.worldquant.parser import AlphaExpression
from project.data.fields import FieldCatalog
from project.engine.learning_engine import LearningEngine

WINDOWS = [20, 63, 126, 252]
PCR_THRESHOLDS = [0.8, 1.0, 1.2, 1.5]
ZSCORE_THRESHOLDS = ["1.0", "1.5", "2.0", "2.5"]

OPERATOR_REPLACE = {
    "ts_delta": ["ts_zscore", "ts_mean"],
    "ts_rank": ["ts_zscore"], 
    "ts_zscore": ["ts_mean", "ts_delta"],
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
        mutations.update(self._mutate_zscore_thresholds(alpha))
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
            if not info: continue
            category = info.get("field_category")
            if not category: continue
            
            alternatives = self.catalog.get_fields_by_category(category, min_alpha_count=0, limit=20)
            for alt in alternatives:
                if alt != field:
                    results.add(alpha.replace(field, alt))
        return results

    def _mutate_regime(self, alpha: str):
        results = set()
        if "trade_when(" not in alpha:
            pcr = "pcr_oi_270"
            iv_mid = "implied_volatility_mean_90"
            hv_mid = "historical_volatility_90"
            
            # NEW: Wrap all regime templates in rank() to pass Max Weight limits
            templates = [
                f"rank(trade_when({pcr}>1, -{{signal}}, {{signal}}))",
                f"rank(trade_when(ts_zscore({iv_mid},63)>1.5, {{signal}}, -{{signal}}))",
                f"rank(trade_when(ts_zscore({pcr},63)<-1.5, {{signal}}, -{{signal}}))",
            ]
            signals = [
                "ts_zscore(returns,20)",
                f"ts_zscore({iv_mid}-{hv_mid},63)",
                f"ts_zscore({pcr}, 20)"
            ]
            for template in templates:
                for signal in signals:
                    results.add(template.format(signal=signal))
        return results

    def _mutate_pcr_thresholds(self, alpha: str):
        results = set()
        if "pcr" not in alpha: return results
        for threshold in PCR_THRESHOLDS:
            results.add(re.sub(r"pcr_oi_270\s*>\s*[0-9.]+", f"pcr_oi_270>{threshold}", alpha))
            results.add(re.sub(r"pcr_oi_270\s*<\s*[0-9.]+", f"pcr_oi_270<{threshold}", alpha))
        return {item for item in results if item != alpha}

    def _mutate_zscore_thresholds(self, alpha: str):
        results = set()
        if "ts_zscore" not in alpha or (">" not in alpha and "<" not in alpha): 
            return results
        for threshold in ZSCORE_THRESHOLDS:
            results.add(re.sub(r">\s*[0-9.]+", f">{threshold}", alpha))
            results.add(re.sub(r"<\s*-[0-9.]+", f"<-{threshold}", alpha))
        return {item for item in results if item != alpha}

    def _mutate_option_spreads(self, alpha: str):
        results = set()
        spread_pairs = [
            ("implied_volatility_mean_30", "implied_volatility_mean_270"),
            ("implied_volatility_mean_90", "historical_volatility_90"),
        ]
        for left, right in spread_pairs:
            if left in alpha and right in alpha:
                if f"({left}-{right})" in alpha:
                    results.add(alpha.replace(f"({left}-{right})", f"(({left}-{right})/{right})"))
        return results

    def _mutate_flip_sign(self, alpha: str):
        results = set()
        if alpha.startswith("rank(") and not alpha.startswith("rank(-"):
            inner = alpha[5:-1]
            results.add(f"rank(-{inner})")
            results.add(f"-rank({inner})")
        elif alpha.startswith("ts_zscore(") and not alpha.startswith("ts_zscore(-"):
            inner = alpha[10:-1]
            results.add(f"ts_zscore(-{inner})")
        return results