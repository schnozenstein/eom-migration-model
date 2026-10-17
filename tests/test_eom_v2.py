import pandas as pd
from eom_empirical.eom_v2 import QOL_WEIGHTS, QOL_INPUT_COLUMNS

def test_qol_weights_sum_to_one():
    assert abs(sum(QOL_WEIGHTS.values()) - 1.0) < 1e-9

def test_qol_inputs_are_separate_dimensions():
    assert "life_evaluation" in QOL_INPUT_COLUMNS
    assert "work_life_balance" in QOL_INPUT_COLUMNS
    assert "leisure_cultural_access" in QOL_INPUT_COLUMNS
    assert len(set(QOL_INPUT_COLUMNS)) == len(QOL_INPUT_COLUMNS)
