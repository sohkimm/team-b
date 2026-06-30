import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def make_scatter(eval_da, ref_da, stat, title="", lim=None):
    """1:1 산점도. lim=(lo,hi)를 주면 x·y 축을 동일 범위로 고정(두 그림 비교용)."""
    e = np.asarray(getattr(eval_da, "values", eval_da)).ravel()
    r = np.asarray(getattr(ref_da, "values", ref_da)).ravel()
    mask = ~np.isnan(e) & ~np.isnan(r)
    e, r = e[mask], r[mask]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(r, e, s=6, alpha=0.4)
    if lim is not None:
        lo, hi = float(lim[0]), float(lim[1])
    else:
        lo = float(min(r.min(), e.min())) if e.size else 0.0
        hi = float(max(r.max(), e.max())) if e.size else 1.0
    ax.plot([lo, hi], [lo, hi], "k--", lw=1)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("reference (ref)")
    ax.set_ylabel("evaluation (eval)")
    if title:
        ax.set_title(title)
    txt = (f"N={stat['N']}\nBias={stat['Bias']:.3f}\n"
           f"RMSE={stat['RMSE']:.3f}\nR={stat['R']:.3f}")
    ax.text(0.05, 0.95, txt, transform=ax.transAxes,
            va="top", ha="left", bbox=dict(boxstyle="round", fc="w"))
    fig.tight_layout()
    return fig
