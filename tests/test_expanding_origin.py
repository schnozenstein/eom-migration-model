import unittest
import pandas as pd
import numpy as np
from eom_empirical.evaluation import expanding_origin_backtest

class ExpandingOriginTests(unittest.TestCase):
    def test_only_earlier_target_years_train_each_fold(self):
        rows=[]
        for country_i,country in enumerate(['AAA','BBB','CCC','DDD']):
            for year in range(2010,2019):
                target_year=year+1
                x=float(country_i + (year-2010)*0.2)
                rows.append({'country_code':country,'year':year,'target_year':target_year,
                    'target_net_migration_per_1000':x+0.1,
                    'net_migration_per_1000_feature_year':x,
                    'f1':x,'f2':float(country_i*2 + (year-2010)*0.1)})
        pred,folds=expanding_origin_backtest(pd.DataFrame(rows),['f1','f2'],min_train_rows=8,min_test_rows=4)
        self.assertGreaterEqual(pred['target_year'].nunique(),3)
        for _,row in folds.iterrows():
            self.assertLess(row['training_target_year_max'],row['target_year'])
        self.assertIn('persistence_baseline',pred.columns)
        self.assertIn('ridge_prediction',pred.columns)

if __name__=='__main__': unittest.main()
