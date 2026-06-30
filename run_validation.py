import argparse
import os

import numpy as np

from src.pipeline import Config, run
from src.io_out import save_fig, save_csv
from src.visualize import make_scatter


def _common_lim(results, pad_frac=0.03):
    """여러 run 결과의 eval/ref 유효값 전체에서 공통 [lo,hi] 산출 (축 동일화용)."""
    vals = []
    for res in results:
        for da in (res["eval_on"], res["ref_on"]):
            v = np.asarray(getattr(da, "values", da)).ravel()
            v = v[~np.isnan(v)]
            if v.size:
                vals.append(v)
    if not vals:
        return (0.0, 1.0)
    allv = np.concatenate(vals)
    lo, hi = float(allv.min()), float(allv.max())
    pad = (hi - lo) * pad_frac or 0.5
    return (lo - pad, hi + pad)


def main():
    ap = argparse.ArgumentParser(description="NC SSS 검증 파이프라인")
    ap.add_argument("path_a")
    ap.add_argument("path_b")
    ap.add_argument("--var-a", default=None)
    ap.add_argument("--var-b", default=None)
    ap.add_argument("--ref", default="auto", choices=["auto", "a", "b"])
    ap.add_argument("--grid", default="both", choices=["fine", "coarse", "both"],
                    help="fine=고해상도 격자(저해상도 업샘플) / coarse=저해상도 격자(고해상도 다운샘플) / both=둘 다 별도 산출")
    ap.add_argument("--outdir", default="results")
    args = ap.parse_args()

    grids = ["coarse", "fine"] if args.grid == "both" else [args.grid]

    # 1) 모든 방식 먼저 계산
    results = [run(args.path_a, args.path_b,
                   Config(ref=args.ref, var_a=args.var_a, var_b=args.var_b,
                          grid=g, outdir=args.outdir)) for g in grids]

    # 2) 두 방식 공통 축범위로 산점도 동일 스케일 재렌더 (비교 가능하게)
    lim = _common_lim(results)
    rows = []
    for g, res in zip(grids, results):
        s = res["stats"]
        fig = make_scatter(res["eval_on"], res["ref_on"], s,
                           title=res["title"], lim=lim)
        save_fig(fig, os.path.join(args.outdir, "figures",
                                   f"scatter_{g}_{res['grid_res']}deg.png"))
        rows.append({"grid": g, "res_deg": res["grid_res"],
                     "ref": res["ref_name"], "eval": res["eval_name"], **s})
        print(f"[grid={g:6s} {res['grid_res']}deg | ref={res['ref_name']} vs eval={res['eval_name']}] "
              f"N={s['N']} Bias={s['Bias']:.3f} RMSE={s['RMSE']:.3f} "
              f"MAE={s['MAE']:.3f} R={s['R']:.3f} R2_nse={s['R2_nse']:.3f}")

    print(f"[축범위 동일화] x=y=[{lim[0]:.2f}, {lim[1]:.2f}]")
    # 비교 테이블 (두 방식 나란히)
    save_csv(rows, os.path.join(args.outdir, "tables", "stats_compare.csv"))


if __name__ == "__main__":
    main()
