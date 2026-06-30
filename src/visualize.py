import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import xarray as xr

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


def save_map(da: xr.DataArray, path: str, title: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig, ax = plt.subplots(
        subplot_kw={"projection": ccrs.PlateCarree()}, figsize=(8, 6)
    )
    da.plot(ax=ax, transform=ccrs.PlateCarree(), cmap="viridis",
            add_colorbar=True, robust=True)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.3)
    ax.set_title(title, fontsize=12)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, linestyle="--")
    gl.top_labels = False
    gl.right_labels = False
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


def save_scatter(
    ref: xr.DataArray,
    eval_da: xr.DataArray,
    stats_dict: dict,
    path: str,
    title: str,
) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    r = ref.values.flatten().astype(float)
    e = eval_da.values.flatten().astype(float)
    mask = ~(np.isnan(r) | np.isnan(e))
    r_v, e_v = r[mask], e[mask]

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(r_v, e_v, s=1, alpha=0.3, color="steelblue", rasterized=True)
    mn = min(r_v.min(), e_v.min())
    mx = max(r_v.max(), e_v.max())
    ax.plot([mn, mx], [mn, mx], "r--", lw=1, label="1:1")
    text = (f"N={stats_dict['N']}\n"
            f"Bias={stats_dict['Bias']:.4f}\n"
            f"RMSE={stats_dict['RMSE']:.4f}\n"
            f"R={stats_dict['R']:.4f}")
    ax.text(0.05, 0.95, text, transform=ax.transAxes,
            va="top", fontsize=9, family="monospace",
            bbox={"facecolor": "white", "alpha": 0.7})
    ax.set_xlabel("Reference", fontsize=10)
    ax.set_ylabel("Evaluation", fontsize=10)
    ax.set_title(title, fontsize=12)
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


def save_compare_table(
    stats_hilo: dict, stats_lohi: dict, path: str
) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    cols = ["N", "Bias", "RMSE", "MAE", "R", "R2"]
    rows = []
    for label, s in [("고→저 (권장)", stats_hilo), ("저→고 (비교)", stats_lohi)]:
        row = [label]
        for k in cols:
            v = s.get(k, np.nan)
            row.append(f"{int(v)}" if k == "N" else f"{v:.4f}")
        rows.append(row)

    fig, ax = plt.subplots(figsize=(9, 2))
    ax.axis("off")
    header = ["방향"] + cols
    table = ax.table(
        cellText=rows, colLabels=header,
        loc="center", cellLoc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(len(header))))
    ax.set_title("검증 통계 비교 (고→저 vs 저→고)", fontsize=12, pad=20)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
