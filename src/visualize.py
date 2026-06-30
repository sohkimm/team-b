import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    _HAS_CARTOPY = True
except ImportError:
    _HAS_CARTOPY = False


def plot_map(da, title="", save_path=None, vmin=25, vmax=40):
    """지도 이미지 반환 (cartopy 해안선 + 육지 마스킹). save_path 있으면 저장도."""
    import os
    data = da.squeeze()
    y = data["y"].values
    x = data["x"].values

    if _HAS_CARTOPY:
        fig, ax = plt.subplots(figsize=(8, 6),
                               subplot_kw={"projection": ccrs.PlateCarree()})
        ax.set_extent([x.min(), x.max(), y.min(), y.max()], crs=ccrs.PlateCarree())
        im = ax.pcolormesh(x, y, data.values, transform=ccrs.PlateCarree(),
                           cmap="turbo", shading="auto", vmin=vmin, vmax=vmax)
        ax.add_feature(cfeature.LAND, facecolor="lightgray", zorder=3)
        ax.add_feature(cfeature.COASTLINE, linewidth=0.8, zorder=4)
        ax.add_feature(cfeature.BORDERS, linewidth=0.4, linestyle=":", zorder=4)
        gl = ax.gridlines(draw_labels=True, linewidth=0.4, color="gray", alpha=0.5)
        gl.top_labels = False
        gl.right_labels = False
    else:
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.pcolormesh(x, y, data.values, cmap="turbo", shading="auto",
                           vmin=vmin, vmax=vmax)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

    plt.colorbar(im, ax=ax, label="PSU")
    if title:
        ax.set_title(title, fontsize=11)
    fig.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    return fig


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
