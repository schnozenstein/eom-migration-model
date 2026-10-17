import unittest
import numpy as np
import pandas as pd
from eom_empirical.model import to_wide, add_derived_features, equal_weight_energy, make_lagged_panel

class ModelTests(unittest.TestCase):
    def setUp(self):
        rows=[]
        for c, gdp, cost, unemp, rq, ge, pv, pop in [
            ("AAA", 50000, 1.2, 4.0, 1.2, 1.1, 1.0, 1_000_000),
            ("BBB", 25000, 0.7, 8.0, 0.4, 0.5, 0.4, 2_000_000),
            ("CCC", 40000, 0.9, 5.5, 0.8, 0.8, 0.7, 1_500_000),
        ]:
            for y in range(2015, 2022):
                vals={"NY.GDP.PCAP.PP.KD":gdp*(1+(y-2015)*0.02), "PA.NUS.PPPC.RF":cost,
                "SL.UEM.TOTL.ZS":unemp, "RQ.EST":rq, "GE.EST":ge, "PV.EST":pv,
                "SP.POP.TOTL":pop, "SM.POP.NETM":(gdp/1000)*(y-2010)}
                for ind,val in vals.items():
                    rows.append({"country_code":c,"year":y,"indicator_code":ind,"value":val})
        self.long=pd.DataFrame(rows)

    def test_wide_and_derived_features(self):
        wide=add_derived_features(to_wide(self.long))
        self.assertIn("net_migration_per_1000", wide.columns)
        self.assertIn("salary_proxy", wide.columns)
        self.assertTrue(np.isfinite(wide["salary_proxy"].dropna()).all())

    def test_energy_direction(self):
        wide=add_derived_features(to_wide(self.long))
        latest=wide[wide.year==2021]
        scored=equal_weight_energy(latest)
        self.assertEqual(len(scored),3)
        self.assertEqual(sorted(scored.energy_rank.dropna().astype(int)),[1,2,3])
        self.assertTrue(scored.score_status.str.contains("not personal probability").all())

    def test_lagged_target_alignment(self):
        wide=add_derived_features(to_wide(self.long))
        lagged, cols=make_lagged_panel(wide)
        row=lagged[(lagged.country_code=="AAA") & (lagged.year==2018)].iloc[0]
        self.assertEqual(row.target_year,2019)
        self.assertTrue(row.target_net_migration_per_1000 > 0)
        self.assertEqual(len(cols),6)

if __name__ == "__main__":
    unittest.main()
