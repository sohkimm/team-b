import argparse
import os

from src.pipeline import Config, run
from src.io_out import save_fig, save_csv


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
    rows = []
    for g in grids:
        cfg = Config(ref=args.ref, var_a=args.var_a, var_b=args.var_b, grid=g,
                     outdir=args.outdir)
        res = run(args.path_a, args.path_b, cfg)
        s = res["stats"]
        # 방식별 산점도 별도 저장 (원래 방식=coarse 보존, 새 방식=fine)
        save_fig(res["figure"],
                 os.path.join(args.outdir, "figures", f"scatter_{g}_{res['grid_res']}deg.png"))
        rows.append({"grid": g, "res_deg": res["grid_res"],
                     "ref": res["ref_name"], "eval": res["eval_name"], **s})
        print(f"[grid={g:6s} {res['grid_res']}deg | ref={res['ref_name']} vs eval={res['eval_name']}] "
              f"N={s['N']} Bias={s['Bias']:.3f} RMSE={s['RMSE']:.3f} "
              f"MAE={s['MAE']:.3f} R={s['R']:.3f} R2_nse={s['R2_nse']:.3f}")

    # 비교 테이블 (두 방식 나란히)
    save_csv(rows, os.path.join(args.outdir, "tables", "stats_compare.csv"))


if __name__ == "__main__":
    main()
