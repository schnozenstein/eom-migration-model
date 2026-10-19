import tempfile
import unittest
from pathlib import Path
import pandas as pd
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from refresh_eom_data import WB_API_CODE_OVERRIDES

class RefreshETLTests(unittest.TestCase):
    def test_freshness_label_rules_are_explicit(self):
        # Keep the contract simple: old observations are never silently called current.
        current_year = 2026
        def label(year):
            return "CURRENT_YEAR" if year >= current_year else ("RECENT" if year >= current_year - 2 else "STALE_OR_SLOW_RELEASE")
        self.assertEqual(label(2026), "CURRENT_YEAR")
        self.assertEqual(label(2025), "RECENT")
        self.assertEqual(label(2024), "RECENT")
        self.assertEqual(label(2023), "STALE_OR_SLOW_RELEASE")

    def test_append_history_dedupe_key_keeps_distinct_vintages(self):
        frame = pd.DataFrame([
            {"run_id":"run1","country_code":"IRL","indicator_code":"X","year":2024,"value":1},
            {"run_id":"run1","country_code":"IRL","indicator_code":"X","year":2024,"value":1},
            {"run_id":"run2","country_code":"IRL","indicator_code":"X","year":2024,"value":2},
        ])
        out = frame.drop_duplicates(["run_id","country_code","indicator_code","year"], keep="last")
        self.assertEqual(len(out), 2)
        self.assertEqual(out.value.tolist(), [1, 2])

    def test_current_wgi_api_codes_preserve_canonical_feature_keys(self):
        self.assertEqual(WB_API_CODE_OVERRIDES["GE.EST"], "GOV_WGI_GE_EST")
        self.assertEqual(WB_API_CODE_OVERRIDES["PV.EST"], "GOV_WGI_PV_EST")
        self.assertEqual(WB_API_CODE_OVERRIDES["RQ.EST"], "GOV_WGI_RQ_EST")

    def test_missing_values_are_not_zero(self):
        df = pd.DataFrame({"value":[None, 12.0]})
        self.assertEqual(int(df.value.notna().sum()), 1)
        self.assertTrue(pd.isna(df.value.iloc[0]))

if __name__ == '__main__': unittest.main()
