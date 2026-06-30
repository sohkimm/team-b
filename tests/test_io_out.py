import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.io_out import save_fig, save_csv


def test_save_fig_writes_png(tmp_path):
    fig = plt.figure()
    p = tmp_path / "out.png"
    save_fig(fig, str(p))
    assert p.exists() and p.stat().st_size > 0


def test_save_csv_writes(tmp_path):
    p = tmp_path / "out.csv"
    save_csv([{"N": 4, "RMSE": 0.13}], str(p))
    assert p.exists()
    assert "RMSE" in p.read_text()
