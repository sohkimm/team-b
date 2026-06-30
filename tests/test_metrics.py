import numpy as np
from src.metrics import stats


def test_stats_handcalc():
    ref = np.array([1.0, 2.0, 3.0, 4.0])
    evalv = np.array([1.1, 2.1, 2.9, 4.2])
    s = stats(evalv, ref)
    assert s["N"] == 4
    # diffs = [0.1, 0.1, -0.1, 0.2]; bias = 0.075
    assert np.isclose(s["Bias"], 0.075)
    assert np.isclose(s["RMSE"], np.sqrt(np.mean([0.01, 0.01, 0.01, 0.04])))
    assert np.isclose(s["MAE"], np.mean([0.1, 0.1, 0.1, 0.2]))
    assert s["R"] > 0.98


def test_stats_masks_nan_both():
    ref = np.array([1.0, np.nan, 3.0])
    evalv = np.array([1.0, 2.0, np.nan])
    s = stats(evalv, ref)
    assert s["N"] == 1  # only index 0 valid in both


def test_nse_can_be_negative():
    ref = np.array([1.0, 2.0, 3.0])
    evalv = np.array([3.0, 2.0, 1.0])  # worse than mean
    s = stats(evalv, ref)
    assert s["R2_nse"] < 0
