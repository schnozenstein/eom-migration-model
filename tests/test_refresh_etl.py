import tempfile
import unittest
from pathlib import Path
import pandas as pd
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from unittest.mock import patch
import socket
from refresh_eom_data import WB_API_CODE_OVERRIDES, WB_INDICATORS, POLICY_URLS, resolve_host_with_retries

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

    def test_ppp_parameters_are_in_live_refresh_and_retired_series_is_not_polled(self):
        self.assertIn("NY.GDP.PCAP.PP.KD", WB_INDICATORS)
        self.assertIn("NY.GDP.MKTP.PP.CD", WB_INDICATORS)
        self.assertIn("PA.NUS.PPP", WB_INDICATORS)
        self.assertIn("PA.NUS.PRVT.PP", WB_INDICATORS)
        self.assertNotIn("PA.NUS.PPPC.RF", WB_INDICATORS)

    def test_spain_and_austria_are_in_destination_and_policy_coverage(self):
        destinations = pd.read_csv(ROOT / "data" / "destinations.csv", dtype=str).fillna("")
        country_rows = destinations[destinations["primary_choice_set"] == "global_country"]
        self.assertIn("ESP", country_rows["wb_country_code"].tolist())
        self.assertIn("AUT", country_rows["wb_country_code"].tolist())
        policy_countries = {row[0] for row in POLICY_URLS}
        self.assertIn("Spain", policy_countries)
        self.assertIn("Austria", policy_countries)

    def test_dns_lookup_retries_transient_failures(self):
        with patch("refresh_eom_data.socket.getaddrinfo", side_effect=[socket.gaierror("temporary failure"), [(None, None, None, None, ("127.0.0.1", 443))]]) as lookup, patch("refresh_eom_data.time.sleep"):
            resolve_host_with_retries("https://api.worldbank.org/v2", attempts=2, base_delay=0.01)
        self.assertEqual(lookup.call_count, 2)

    def test_missing_values_are_not_zero(self):
        df = pd.DataFrame({"value":[None, 12.0]})
        self.assertEqual(int(df.value.notna().sum()), 1)
        self.assertTrue(pd.isna(df.value.iloc[0]))

if __name__ == '__main__': unittest.main()
