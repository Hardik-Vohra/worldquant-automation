import pandas as pd
import re
from pathlib import Path
from project.config import MASTER_FIELDS_CSV

CATEGORY_RULES = [
    ("Options", ["pcr", "open_interest", "implied_volatility", "option", "call_", "_call", "put_", "_put"]),
    ("Volatility", ["historical_volatility", "volatility", "stddev", "variance"]),
    ("Fundamental", ["ebit", "ebitda", "fcf", "netprofit", "cfo", "netdebt", "cashflow", "profit", "revenue", "sales", "income", "earnings", "debt"]),
    ("Analyst", ["anl4", "analyst", "forecast", "estvalue", "guidance", "revision", "estimate", "broker"]),
    ("Sentiment", ["sentiment", "social", "news", "buzz", "analyst", "broker"]),
    ("Risk", ["beta", "drawdown", "risk", "volatility", "var"]),
    ("Group", ["sector", "industry", "subindustry", "region", "country", "group", "style"]),
    ("Price/Volume", ["close", "open", "high", "low", "volume", "turnover", "vwap", "price", "volume", "oi"]),
]

VECTOR_TYPES = {"VECTOR", "MATRIX"}


class FieldCatalog:
    def __init__(self, path: Path = None):
        self.path = Path(path) if path else MASTER_FIELDS_CSV
        self.fields = self._load_fields()

    def _load_fields(self):
        df = pd.read_csv(self.path, dtype=str)
        df = df.fillna("")
        df["field_id"] = df["field_id"].astype(str)
        df["field_category"] = df.apply(self._tag_category, axis=1)
        df["field_tags"] = df.apply(self._tag_list, axis=1)
        return df

    def _tag_category(self, row):
        field_id = row["field_id"].lower()
        description = str(row.get("description", "")).lower()
        dataset = str(row.get("dataset", "")).lower()

        for category, keywords in CATEGORY_RULES:
            for keyword in keywords:
                if keyword in field_id or keyword in description or keyword in dataset:
                    return category

        if row.get("type", "").upper() in VECTOR_TYPES:
            return row.get("type", "Unknown")

        return "Unknown"

    def _tag_list(self, row):
        tags = {self._tag_category(row)}
        if row.get("type", "") in VECTOR_TYPES:
            tags.add(row["type"])
        return sorted(tags)

    def get_fields_by_category(self, category, min_alpha_count=0, limit=None):
        df = self.fields
        if category:
            df = df[df["field_category"] == category]
        if min_alpha_count:
            df = df[pd.to_numeric(df.get("alphaCount", 0), errors="coerce").fillna(0) >= min_alpha_count]
        fields = df["field_id"].tolist()
        if limit:
            fields = fields[:limit]
        return fields

    def get_fields_matching(self, keywords, min_alpha_count=0, limit=None):
        """Return fields matching explicit alpha-data keywords."""
        keywords = [keyword.lower() for keyword in keywords]
        df = self.fields.copy()
        description = df["description"] if "description" in df.columns else pd.Series("", index=df.index)
        dataset = df["dataset"] if "dataset" in df.columns else pd.Series("", index=df.index)
        text = (
            df["field_id"].str.lower()
            + " "
            + description.astype(str).str.lower()
            + " "
            + dataset.astype(str).str.lower()
        )
        mask = pd.Series(False, index=df.index)
        for keyword in keywords:
            mask = mask | text.str.contains(re.escape(keyword), regex=True)
        df = df[mask]
        if min_alpha_count:
            df = df[pd.to_numeric(df.get("alphaCount", 0), errors="coerce").fillna(0) >= min_alpha_count]
        fields = df["field_id"].tolist()
        if limit:
            fields = fields[:limit]
        return fields

    def get_pcr_fields(self, min_alpha_count=0, limit=None):
        return self.get_fields_matching(["pcr"], min_alpha_count=min_alpha_count, limit=limit)

    def get_implied_volatility_fields(self, min_alpha_count=0, limit=None):
        return self.get_fields_matching(["implied_volatility"], min_alpha_count=min_alpha_count, limit=limit)

    def get_historical_volatility_fields(self, min_alpha_count=0, limit=None):
        return self.get_fields_matching(["historical_volatility"], min_alpha_count=min_alpha_count, limit=limit)

    def get_open_interest_fields(self, min_alpha_count=0, limit=None):
        return self.get_fields_matching(["open_interest", "call_open_interest", "put_open_interest"], min_alpha_count=min_alpha_count, limit=limit)

    def get_all_categories(self):
        return sorted(set(self.fields["field_category"].tolist()))

    def get_field_info(self, field_id):
        row = self.fields[self.fields["field_id"] == field_id]
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    def recommend_fields(self, categories=None, limit=40):
        categories = categories or ["Fundamental", "Options", "Volatility"]
        candidates = self.fields[self.fields["field_category"].isin(categories)]
        candidates = candidates.sort_values(by=["alphaCount", "coverage"], ascending=[False, False])
        return candidates["field_id"].head(limit).tolist()


if __name__ == "__main__":
    catalog = FieldCatalog()
    print(catalog.get_all_categories())
    print(catalog.get_fields_by_category("Fundamental", min_alpha_count=100)[:20])
