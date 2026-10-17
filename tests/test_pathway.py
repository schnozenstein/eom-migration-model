import unittest
import pandas as pd
from eom_empirical.summarize_pathway import build_summary, wilson_interval

class PathwayTests(unittest.TestCase):
    def test_wilson_interval(self):
        rate, low, high = wilson_interval(80, 100)
        self.assertAlmostEqual(rate, 0.8)
        self.assertLess(low, rate)
        self.assertGreater(high, rate)

    def test_summary_pools_only_observed_counts(self):
        rows=[]
        for i in range(2):
            rows.append({"destination_id":"GBR", "programme_id":"MOT-1",
                "graduation_count":80, "graduation_denominator":100,
                "relevant_employed_6m_count":60, "employment_denominator":80,
                "sponsored_status_24m_count":40, "sponsorship_denominator":80,
                "employed_destination_3y_count":30, "retention_denominator":60,
                "long_term_status_8y_count":None, "settlement_denominator":None})
        result=build_summary(pd.DataFrame(rows)).iloc[0]
        self.assertAlmostEqual(result.graduation_rate, 0.8)
        self.assertTrue(pd.isna(result.long_term_status_8y_rate))

if __name__ == "__main__":
    unittest.main()
